import easyocr
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

import cv2
import numpy as np
from PIL import Image
import pytesseract
from difflib import SequenceMatcher
from transformers import pipeline
_grammar_model = None
import os
import re
import unicodedata
from wordfreq import zipf_frequency, top_n_list

reader = easyocr.Reader(['en'])
# build a vocabulary from wordfreq top list
_VOCAB = set(top_n_list("en", 50000))

# Optional grammar-correction model (load only if explicitly enabled via env)
try:
    _ENABLE_GRAMMAR = os.getenv("ENABLE_OCR_GRAMMAR", "0").lower() in ("1", "true", "yes")
    _GRAMMAR_MODEL_NAME = os.getenv("OCR_GRAMMAR_MODEL", "")
    if _ENABLE_GRAMMAR and _GRAMMAR_MODEL_NAME:
        try:
            _grammar_model = pipeline("text2text-generation", model=_GRAMMAR_MODEL_NAME)
            print(f"Loaded OCR grammar model: {_GRAMMAR_MODEL_NAME}", flush=True)
        except Exception as _e:
            print(f"Failed to load grammar model '{_GRAMMAR_MODEL_NAME}': {_e}", flush=True)
            _grammar_model = None
except Exception:
    _grammar_model = None


def _basic_clean(text: str) -> str:
    # normalize whitespace and remove control / non-printable chars
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _aggressive_clean(text: str) -> str:
    # additional cleaning: remove common OCR artifacts, stray brackets, non-word runs
    text = _basic_clean(text)
    # normalize unicode (ligatures, diacritics)
    text = unicodedata.normalize('NFKC', text)
    # replace common fancy punctuation
    text = text.replace('–', '-').replace('—', '-').replace('“', '"').replace('”', '"')
    text = text.replace('’', "'").replace('‘', "'")
    # remove long runs of non-alphanumeric characters
    text = re.sub(r"[^\w\s\.,;:\-']{2,}", " ", text)
    # replace isolated brackets and weird sequences
    text = re.sub(r"\[+|\]+|\{+|\}+,?", " ", text)
    # collapse sequences like HB[85_20u} -> HB 85 20u
    text = re.sub(r"[_\[\]\{\}]+", " ", text)
    # simple OCR misread fixes
    fixes = {
        '\\bI0\\b': '10',
        '\\b0CR\\b': 'OCR',
        'rn': 'm'
    }
    for pat, rep in fixes.items():
        try:
            text = re.sub(pat, rep, text)
        except re.error:
            pass

    # common OCR confusion fixes (safe heuristics)
    try:
        # fix common ligature artifacts
        text = text.replace('\ufb01', 'fi').replace('\ufb02', 'fl')
        # fix common numeric/letter confusions in isolated contexts
        text = re.sub(r"\b0([a-zA-Z]{2,})\b", r"O\1", text)  # 0 -> O at start of words
        text = re.sub(r"\b([a-zA-Z]{2,})0\b", r"\1O", text)  # trailing 0 -> O
    except Exception:
        pass

    # tighten spacing around punctuation
    text = re.sub(r"\s+([,.;:!?%])", r"\1", text)
    # remove non-ascii noise but keep common punctuation
    text = re.sub(r"[^\x00-\x7F]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(file_path):
    """Extract text from various file types with comprehensive error handling and fallbacks."""
    raw = ""
    
    print(f"🔍 Processing file: {file_path}", flush=True)
    print(f"   File exists: {os.path.exists(file_path)}", flush=True)
    print(f"   File size: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}", flush=True)

    def _remove_repeated_headers(text: str) -> str:
        # Remove short repeated header/footer lines that are likely page headers
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return text
        # count normalized form of lines (uppercase, collapse spaces)
        norm = [re.sub(r"\s+", " ", l.upper()) for l in lines]
        freq = {}
        for n, orig in zip(norm, lines):
            freq[n] = freq.get(n, 0) + 1

        # remove lines that appear more than once and are reasonably long (likely headers)
        to_remove = {k for k, v in freq.items() if v > 1 and len(k) > 20}
        if not to_remove:
            return text
        out_lines = [orig for n, orig in zip(norm, lines) if n not in to_remove]
        return "\n".join(out_lines)

    def _preprocess_pil_image(pil_img: Image.Image, fast_mode: bool = True) -> Image.Image:
        """Preprocess image for better OCR: denoise, enhance contrast, deskew.
        
        fast_mode=True: Skip expensive operations (deskew, morphology) for speed - 3x faster
        fast_mode=False: Full preprocessing with all enhancements for best quality
        """
        try:
            # convert to grayscale
            img = np.array(pil_img.convert("RGB"))
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            if fast_mode:
                # FAST MODE: Skip expensive preprocessing for speed (~100ms instead of 500ms)
                # Just do basic denoise and contrast (most impactful)
                den = cv2.fastNlMeansDenoising(gray, None, h=8)  # Reduced h for speed
                
                # Quick contrast enhancement (faster than CLAHE)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16,16))  # Larger tiles = faster
                enhanced = clahe.apply(den)
                
                return Image.fromarray(enhanced)
            else:
                # QUALITY MODE: Full preprocessing (slower but higher quality)
                # denoise
                den = cv2.fastNlMeansDenoising(gray, None, h=10)

                # enhance contrast via CLAHE
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                cl = clahe.apply(den)

                # adaptive thresholding
                th = cv2.adaptiveThreshold(cl, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 15, 9)

                # morphological opening to remove small noise
                kernel = np.ones((1,1), np.uint8)
                opened = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)

                # deskew using moments / minAreaRect
                coords = np.column_stack(np.where(opened > 0))
                if coords.shape[0] > 0:
                    rect = cv2.minAreaRect(coords)
                    angle = rect[-1]
                    if angle < -45:
                        angle = -(90 + angle)
                    else:
                        angle = -angle
                    (h, w) = opened.shape
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(opened, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                else:
                    rotated = opened

                return Image.fromarray(rotated)
        except Exception as e:
            print(f"⚠️ Preprocessing error: {e}", flush=True)
            return pil_img  # Return original if preprocessing fails

    def _ocr_on_image(pil_img: Image.Image, fast_mode: bool = True):
        """Run EasyOCR for text extraction. 
        fast_mode=True: Skip image preprocessing for speed (default)
        fast_mode=False: Full preprocessing for best quality OCR
        """
        best_text = ""
        best_conf = 0.0
        
        # run EasyOCR with details for confidence
        try:
            print("   Trying EasyOCR...", flush=True)
            easy_res = reader.readtext(np.array(pil_img))
            easy_text = " ".join([t[1] for t in easy_res if len(t) > 1])
            confidences = [t[2] for t in easy_res if len(t) > 2 and isinstance(t[2], (int, float))]
            mean_conf = float(np.mean(confidences)) if confidences else 0.0
            print(f"   EasyOCR: text_len={len(easy_text)}, conf={mean_conf:.2f}", flush=True)
            
            if easy_text.strip() and mean_conf > 0.3:  # Lowered threshold from 0.45
                best_text = easy_text
                best_conf = mean_conf
        except Exception as e:
            print(f"   ⚠️ EasyOCR error: {e}", flush=True)

        # run pytesseract as complementary OCR if EasyOCR didn't work well
        if best_conf < 0.4:
            try:
                print("   Trying Tesseract...", flush=True)
                pyt_text = pytesseract.image_to_string(pil_img)
                print(f"   Tesseract: text_len={len(pyt_text)}", flush=True)
                if pyt_text.strip() and len(pyt_text) > len(best_text):
                    best_text = pyt_text
                    best_conf = 0.5  # Arbitrary decent score
            except Exception as e:
                print(f"   ⚠️ Tesseract error: {e}", flush=True)

        return best_text, best_conf

    # === Main extraction logic ===
    try:
        if file_path.lower().endswith(".pdf"):
            print("   Detected PDF file", flush=True)
            try:
                pages = convert_from_path(file_path)
                print(f"   Extracted {len(pages)} pages from PDF", flush=True)
                
                for page_num, page in enumerate(pages, 1):
                    print(f"   Processing page {page_num}/{len(pages)}", flush=True)
                    try:
                        proc = _preprocess_pil_image(page)
                        page_text, conf = _ocr_on_image(proc)
                        if page_text.strip():
                            raw += page_text + " "
                            print(f"     ✓ Extracted {len(page_text)} chars from page {page_num}", flush=True)
                    except Exception as e:
                        print(f"     ⚠️ Error processing page {page_num}: {e}", flush=True)
                        
            except (PDFInfoNotInstalledError, FileNotFoundError) as e:
                print(f"   PDF processing failed ({e.__class__.__name__}), trying PyPDF2 fallback", flush=True)
                # fallback: try to extract text with PyPDF2 (works for text PDFs, not scanned images)
                if PdfReader is not None:
                    try:
                        with open(file_path, "rb") as f:
                            pdf = PdfReader(f)
                            print(f"   Extracted {len(pdf.pages)} pages with PyPDF2", flush=True)
                            for p in pdf.pages:
                                try:
                                    page_text = p.extract_text() or ""
                                    if page_text.strip():
                                        raw += page_text + " "
                                except Exception:
                                    pass
                    except Exception as pdfexc:
                        print(f"   ⚠️ PyPDF2 also failed: {pdfexc}", flush=True)
        else:
            # Image file
            print("   Detected image file", flush=True)
            try:
                result = reader.readtext(file_path)
                raw = " ".join([res[1] for res in result if len(res) > 1])
                print(f"   Extracted {len(raw)} chars from image", flush=True)
            except Exception as e:
                print(f"   ⚠️ EasyOCR on image failed: {e}", flush=True)
                # Try loading as PIL and OCRing
                try:
                    pil_img = Image.open(file_path)
                    proc = _preprocess_pil_image(pil_img)
                    raw, _ = _ocr_on_image(proc)
                except Exception as e2:
                    print(f"   ⚠️ Fallback OCR also failed: {e2}", flush=True)
    except Exception as e:
        print(f"❌ Extraction failed for {file_path}: {e}", flush=True)
        raw = ""

    # === Post-processing ===
    print(f"📊 Raw text extracted: {len(raw)} chars", flush=True)
    
    cleaned = _aggressive_clean(raw)
    print(f"📊 After aggressive clean: {len(cleaned)} chars", flush=True)
    
    # remove repeated page headers/footers that appear across PDF pages
    try:
        cleaned = _remove_repeated_headers(cleaned)
        print(f"📊 After removing headers: {len(cleaned)} chars", flush=True)
    except Exception as e:
        print(f"⚠️ Header removal failed: {e}", flush=True)
        pass

    # Apply light post-correction
    def _light_stat_correct(text: str, max_changes: int = 100) -> str:
        """Lightweight spell correction focused on common OCR errors."""
        try:
            def edits1(word):
                letters = 'abcdefghijklmnopqrstuvwxyz'
                splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
                deletes = [L + R[1:] for L, R in splits if R]
                transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
                replaces = [L + c + (R[1:] if len(R) > 1 else '') for L, R in splits if R for c in letters]
                inserts = [L + c + R for L, R in splits for c in letters]
                return set(deletes + transposes + replaces + inserts)

            def edits2(word):
                return set(e2 for e1 in edits1(word) for e2 in edits1(e1))

            def known(cands):
                return set(w for w in cands if w in _VOCAB)

            def candidate_corrections(word):
                w = word.lower()
                if w in _VOCAB:
                    return [w]
                c1 = known(edits1(w))
                if c1:
                    return sorted(list(c1), key=lambda x: -zipf_frequency(x, 'en'))
                c2 = known(edits2(w))
                if c2:
                    return sorted(list(c2), key=lambda x: -zipf_frequency(x, 'en'))
                return []
            
            words = re.findall(r"\w+", text)
            changes = 0
            corrected_text = text
            seen = set()

            for w in set(words):
                if changes >= max_changes:
                    break
                if len(w) <= 2 or w.isupper() or any(char.isdigit() for char in w):
                    continue
                lw = w.lower()
                if lw in seen or lw in _VOCAB:
                    seen.add(lw)
                    continue
                seen.add(lw)
                cands = candidate_corrections(w)
                if cands:
                    best = cands[0]
                    if best != lw:
                        replacement = best.capitalize() if w[0].isupper() else best
                        corrected_text = re.sub(rf"\b{re.escape(w)}\b", replacement, corrected_text)
                        changes += 1

            # basic sentence punctuation and capitalization fixes
            try:
                # ensure space after punctuation
                corrected_text = re.sub(r'([\.,;:!?])([^\s\.,;:!?])', r'\1 \2', corrected_text)
                # capitalize standalone I
                corrected_text = re.sub(r'\bi\b', 'I', corrected_text)
                # capitalize sentence starts (simple heuristic: after period + space)
                parts = re.split(r'(\.[ \n])', corrected_text)
                if parts and len(parts) > 1:
                    out = []
                    i = 0
                    while i < len(parts):
                        seg = parts[i]
                        if i + 1 < len(parts):
                            sep = parts[i+1]
                            seg = seg.strip()
                            if seg:
                                seg = seg[0].upper() + seg[1:]
                            out.append(seg + sep)
                            i += 2
                        else:
                            seg = seg.strip()
                            if seg:
                                seg = seg[0].upper() + seg[1:]
                            out.append(seg)
                            i += 1
                    corrected_text = ''.join(out)
            except Exception:
                pass

            # collapse repeated spaces again
            corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()

            # optional grammar model correction (if model loaded via env)
            try:
                if _grammar_model is not None:
                    # keep output size reasonable
                    out = _grammar_model(corrected_text, max_length=min(512, max(128, len(corrected_text.split()) + 50)))
                    if isinstance(out, list) and out and isinstance(out[0], dict) and 'generated_text' in out[0]:
                        corrected_text = out[0]['generated_text']
                    elif isinstance(out, str):
                        corrected_text = out
            except Exception as _e:
                print(f"⚠️ Grammar model failed: {_e}", flush=True)

            return corrected_text
        except Exception as e:
            print(f"⚠️ Spell correction failed: {e}", flush=True)
            return text

    try:
        final = _light_stat_correct(cleaned, max_changes=100)
        print(f"📊 After spell correction: {len(final)} chars", flush=True)
    except Exception as e:
        print(f"⚠️ Spell correction error: {e}", flush=True)
        final = cleaned

    # Ensure minimum text is extracted
    if not final.strip() or len(final.strip()) < 20:
        print(f"⚠️ Insufficient text extracted ({len(final)} chars). Using raw cleaned text.", flush=True)
        final = cleaned

    if not final.strip():
        print(f"❌ No text could be extracted from file", flush=True)
        final = "Unable to extract text from this document."

    return raw.strip(), final
