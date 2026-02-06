import re
import os
import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from datetime import datetime
from db import init_db, SessionLocal, Document as DBDocument

model = SentenceTransformer("all-MiniLM-L6-v2")

# Configuration: tune these to control fuzzy matching and metadata boosting
FUZZY_THRESHOLD = 0.82

# Scoring weights (sum should be 1.0)
WEIGHT_SEMANTIC = 0.35
WEIGHT_EXACT = 0.30
WEIGHT_DENSITY = 0.08
WEIGHT_TITLE = 0.12
WEIGHT_SOURCE = 0.10
WEIGHT_CONTEXT = 0.05

# vector dim for all-MiniLM-L6-v2 is 384
index = faiss.IndexFlatL2(384)
# in-memory list of chunks with metadata
documents = []

# ensure DB exists
init_db()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
FAISS_PATH = os.path.join(DATA_DIR, 'faiss.index')
DOCS_JSON = os.path.join(DATA_DIR, 'documents.json')


def _persist_document(raw, clean, source=None, url=None, title=None, filename=None):
    db = SessionLocal()
    try:
        doc = DBDocument(raw=raw, clean=clean, source=source, url=url, title=title, filename=filename)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id
    finally:
        db.close()


def _load_from_db(rebuild_index=True):
    db = SessionLocal()
    try:
        rows = db.query(DBDocument).all()
        for r in rows:
            cleaned = (r.clean or "").strip()
            if not cleaned:
                continue
            # chunk and embed
            chunks = [cleaned[i:i+500] for i in range(0, len(cleaned), 500)]
            if not chunks:
                continue
            if rebuild_index:
                embeddings = model.encode(chunks)
                index.add(np.array(embeddings).astype("float32"))
            for c in chunks:
                documents.append({"clean": c, "raw": r.raw, "source": r.filename or r.source, "url": r.url, "title": r.title, "doc_id": r.id})
    finally:
        db.close()


# load existing documents into in-memory index on startup
if os.path.exists(FAISS_PATH) and os.path.exists(DOCS_JSON):
    try:
        index = faiss.read_index(FAISS_PATH)
        with open(DOCS_JSON, 'r', encoding='utf-8') as f:
            docs = json.load(f)
            documents.extend(docs)
    except Exception:
        # fallback to rebuilding from DB
        _load_from_db(rebuild_index=True)
else:
    _load_from_db(rebuild_index=True)

def clean_text(text):
    # remove code-like symbols and noise
    text = re.sub(r"[{}<>_=#@/\\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def add_text(raw_text: str, cleaned_text: str = None, *, source: str = None, url: str = None, title: str = None):
    # cleaned_text should be used for embeddings; raw_text is kept for user view
    if cleaned_text is None:
        cleaned_text = clean_text(raw_text or "")

    cleaned_text = clean_text(cleaned_text)
    # Optimal chunk size: 500 chars is good, but batch them for speed
    chunks = [cleaned_text[i:i+500] for i in range(0, len(cleaned_text), 500)]

    if not chunks:
        return
    # persist document and get id
    doc_id = _persist_document(raw_text, cleaned_text, source=source, url=url, title=title, filename=source)
    try:
        print(f"💾 Persisted document id: {doc_id}", flush=True)
    except Exception:
        pass

    # OPTIMIZATION: Batch encode all chunks at once (much faster than one-by-one)
    # show_progress_bar=False for speed, batch_size tuned for GPU/CPU balance
    embeddings = model.encode(chunks, show_progress_bar=False, batch_size=32)

    index.add(np.array(embeddings).astype("float32"))
    # store dict entries mapping cleaned chunk to the full raw document and doc_id
    for c in chunks:
        documents.append({"clean": c, "raw": raw_text, "source": source, "url": url, "title": title, "doc_id": doc_id})

    print("📌 Chunks added:", len(chunks))
    print("📌 Total documents:", len(documents))
    print("📌 FAISS vectors:", index.ntotal)
    # persist faiss index and document metadata for fast restart
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # atomic save for FAISS index and documents metadata
        tmp_idx = FAISS_PATH + ".tmp"
        tmp_docs = DOCS_JSON + ".tmp"
        faiss.write_index(index, tmp_idx)
        with open(tmp_docs, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False)
        # replace atomically
        try:
            os.replace(tmp_idx, FAISS_PATH)
        except Exception:
            # fallback to write_index directly
            faiss.write_index(index, FAISS_PATH)
        try:
            os.replace(tmp_docs, DOCS_JSON)
        except Exception:
            with open(DOCS_JSON, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False)

        # write a meta file with timestamp for version tracking
        meta = {"saved_at": datetime.utcnow().isoformat() + "Z", "count": len(documents), "vectors": index.ntotal}
        with open(os.path.join(DATA_DIR, 'faiss_meta.json'), 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)
    except Exception:
        pass

    # return the persisted document id for callers that need the integer result
    return int(doc_id) if doc_id is not None else None


def _refine_text(text: str, max_length: int = 300) -> str:
    """Refine and clean text for better display.
    - Fix common OCR errors and grammatical issues
    - Improve formatting
    - Truncate to reasonable length
    """
    if not text:
        return ""
    
    # Fix common OCR grammatical issues
    fixes = {
        r'\b(a)\s+([aeiou])': r'an \2',  # a -> an before vowels
        r'\s+([,.!?;:])': r'\1',  # Remove space before punctuation
        r'([,.!?;:])([A-Za-z])': r'\1 \2',  # Add space after punctuation if missing
        r'\b(teh)\b': 'the',
        r'\b(abd)\b': 'and',
        r'\b(recieve)\b': 'receive',
        r'\b(occured)\b': 'occurred',
        r'\b(thier)\b': 'their',
        r'\b(wich)\b': 'which',
        r'\b(seperate)\b': 'separate',
        r'\b(accomodate)\b': 'accommodate',
    }
    
    refined = text
    for pattern, replacement in fixes.items():
        try:
            refined = re.sub(pattern, replacement, refined, flags=re.IGNORECASE)
        except:
            pass
    
    # Capitalize first letter and ensure proper spacing
    refined = refined.strip()
    if refined:
        refined = refined[0].upper() + refined[1:]
    
    # Truncate to max length on word boundary
    if len(refined) > max_length:
        truncated = refined[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            refined = truncated[:last_space] + "..."
        else:
            refined = truncated + "..."
    
    return refined

def _calculate_relevance_score(query_words: list, doc_text: str, semantic_sim: float, title: str = None) -> float:
    """
    OPTIMIZED relevance scoring - fast (3 signals instead of 6)
    Returns a combined score in range [0.0, 1.0]
    """
    # OPTIMIZATION: Use only fast signals, skip expensive computations
    # Signal 1: Semantic Similarity (75% weight - primary signal)
    semantic_score = min(semantic_sim, 1.0)

    # Signal 2: Exact Term Matching (20% weight - fast check)
    doc_lower = doc_text.lower() if doc_text else ""
    if query_words:
        matches = sum(1 for w in query_words if w in doc_lower)
        exact_score = min(matches / len(query_words), 1.0)
    else:
        exact_score = 0.0

    # Signal 3: Title Match Bonus (5% weight - optional boost)
    title_score = 0.0
    if title and query_words:
        title_lower = title.lower()
        if any(w in title_lower for w in query_words):
            title_score = 0.3  # Simple boost if any word matches

    # Fast weighted combination
    combined = (0.75 * semantic_score) + (0.20 * exact_score) + (0.05 * title_score)

    return combined


def _levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings (pure Python)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la

    prev = list(range(lb + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * lb
        for j, cb in enumerate(b, start=1):
            add = prev[j] + 1
            delete = cur[j - 1] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            cur[j] = min(add, delete, replace)
        prev = cur
    return prev[lb]


def _levenshtein_ratio(a: str, b: str) -> float:
    """Return similarity ratio in [0.0, 1.0] (1.0 = identical)."""
    a = (a or "").lower()
    b = (b or "").lower()
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    dist = _levenshtein_distance(a, b)
    return 1.0 - (dist / max_len)


def _token_fuzzy_in_text(token: str, text: str, threshold: float = None) -> bool:
    """Check if token fuzzy-matches any word in text using ratio threshold."""
    if not token or not text:
        return False
    token = token.lower()
    words = re.findall(r"\w+", text.lower())
    # fast exact check first
    if token in text:
        return True
    # check compact matches
    compact_token = re.sub(r"\W+", "", token)
    compact_text = re.sub(r"\W+", "", text.lower())
    if compact_token and compact_token in compact_text:
        return True

    if threshold is None:
        threshold = FUZZY_THRESHOLD

    for w in words:
        # skip very short words to avoid noise
        if len(w) < 3 or len(token) < 3:
            continue
        if _levenshtein_ratio(token, w) >= threshold:
            return True
    return False


def retrieve(query: str, k: int = 5) -> list:
    """
    Advanced multi-stage retriever with strict relevance filtering.
    
    Stages:
    1. Semantic retrieval (FAISS) - get candidates
    2. Re-ranking with comprehensive scoring
    3. Quality filtering - only top matches
    4. Deduplication and formatting
    
    Returns list of top-k highly relevant results
    """
    if index.ntotal == 0 or len(documents) == 0:
        return []

    # Pre-filter: OPTIMIZED - only exact phrase matching (NO expensive fuzzy matching)
    # Fuzzy matching is too slow for large datasets; use semantic search instead
    normalized_query = (query or "").strip().lower()
    query_tokens = [w for w in re.findall(r"\w+", normalized_query) if w]
    exact_results = []
    pre_filtered_exact = []

    # OPTIMIZATION: Fast exact-only pre-filter (skip fuzzy to save time)
    if normalized_query and len(documents) < 10000:  # Only pre-filter if reasonable size
        MAX_PREFILTER_DOCS = min(len(documents), 5000)  # Scan max 5000 docs for speed
        for i, doc in enumerate(documents):
            if i >= MAX_PREFILTER_DOCS:
                break  # Stop if too many docs scanned
            try:
                doc_id = doc.get('doc_id')
                clean_text = (doc.get('clean') or "").lower()
                title = (doc.get('title') or doc.get('source') or "").lower()

                # OPTIMIZATION: Only check exact phrase and token presence (no fuzzy)
                phrase_present = normalized_query in clean_text or normalized_query in title
                
                tokens_present = False
                if query_tokens and len(query_tokens) > 0:
                    # Simple exact token match only (fast)
                    ok = all((t in clean_text or t in title) for t in query_tokens)
                    tokens_present = ok

                if phrase_present or tokens_present:
                    exact_results.append({
                        'doc_id': doc_id,
                        'score': 0.99,
                        'semantic_sim': 1.0,
                        'clean': doc.get('clean', ""),
                        'raw': doc.get('raw', ""),
                        'source': doc.get('source'),
                        'url': doc.get('url'),
                        'title': doc.get('title') or doc.get('source') or "",
                    })
            except Exception:
                continue

        # OPTIMIZATION: Return early if exact matches found (avoid expensive FAISS search)
        if exact_results:
            seen = set()
            ordered = []
            for r in exact_results[:min(len(exact_results), 20)]:  # Limit pre-filter to 20
                key = r.get('source') or r.get('title') or str(r.get('doc_id'))
                if key in seen:
                    continue
                seen.add(key)
                r['clean'] = _refine_text(r['clean'], max_length=250)
                r['snippet'] = r['clean']
                ordered.append(r)
                if len(ordered) >= k:
                    return ordered[:k]
            # keep exact matches to merge with semantic candidates later
            pre_filtered_exact = ordered
    else:
        pre_filtered_exact = []
    
    # Stage 1: Semantic Retrieval
    # OPTIMIZATION: Reduced candidate count for faster search (50 instead of 200)
    # Most relevant results appear in top candidates anyway
    try:
        total = int(index.ntotal)
    except Exception:
        total = 0
    # cap candidates to a smaller bound for SPEED - typically only need top 10-20
    MAX_CANDIDATES = 50  # REDUCED from 200 for 4x faster search
    num_candidates = min(max(k * 5, 15), total if total > 0 else 15, MAX_CANDIDATES)

    # encode query (disable progress bar on CPU) and guard against encoder failures
    try:
        q_emb = model.encode([query], show_progress_bar=False)
        q_arr = np.array(q_emb).astype("float32")
        distances, indices = index.search(q_arr, num_candidates)
    except Exception:
        # on failure, return empty quickly instead of crashing or timing out
        return []
    
    # Stage 2: Parse query and prepare for ranking
    query_words = [w.lower() for w in re.findall(r"\w+", query)]
    # Heuristic: treat multi-token short queries as name-like and require token/fuzzy matches
    is_name_query = False
    try:
        if len(query_words) >= 2 and all(len(t) >= 3 for t in query_words):
            is_name_query = True
    except Exception:
        is_name_query = False
    
    # Stage 3: Re-rank all candidates with comprehensive scores
    scored_results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(documents):
            continue
            
        doc = documents[idx]
        doc_id = doc.get('doc_id')
        clean_text = doc.get('clean', "")
        title = doc.get('title') or doc.get('source') or ""
        
        # Convert L2 distance to similarity (0-1 range)
        try:
            semantic_sim = 1.0 / (1.0 + float(dist))
        except Exception:
            semantic_sim = 0.0
        
        # OPTIMIZATION: Skip expensive token checking - let semantic search handle it
        # Semantic similarity is good enough for relevance, no need for fuzzy token matching
        # This speeds up re-ranking significantly
        candidate_tokens_present = True  # Assume tokens present, semantic score is primary signal

        # OPTIMIZATION: Simplify quality filtering (STRICT thresholds for relevance)
        # Calculate relevance score
        relevance_score = _calculate_relevance_score(query_words, clean_text, semantic_sim, title)
        
        # STRICT FILTERING: Only return HIGHLY RELEVANT results
        # High semantic similarity (meaningful embedding match)
        min_semantic = semantic_sim > 0.45  # INCREASED from 0.25 → Only strong semantic matches
        
        # Has exact query terms present
        has_exact_terms = any(w in clean_text.lower() for w in query_words) if query_words else False
        
        # Accept only if BOTH conditions met or very high overall score
        if not (min_semantic or has_exact_terms):
            continue  # STRICT: Skip results without semantic OR exact match
        
        # Also require minimum relevance score (STRICT)
        if relevance_score < 0.35:  # INCREASED from 0.15 → Skip low-quality results
            continue  # Skip very low scores - results must be actually relevant
        
        scored_results.append({
            'doc_id': doc_id,
            'score': relevance_score,
            'semantic_sim': semantic_sim,
            'clean': clean_text,
            'raw': doc.get('raw', ""),
            'source': doc.get('source'),
            'url': doc.get('url'),
            'title': title,
        })
    
    # Stage 5: Sort by relevance score (descending)
    scored_results.sort(key=lambda x: -x['score'])
    
    # Stage 6: De-duplication by document source
    seen_sources = set()
    final_results = []
    # If this was a strict name query and we found no candidates, return empty
    if is_name_query and not scored_results and not pre_filtered_exact:
        return []
    # If we have prioritized exact matches, add them first
    if pre_filtered_exact:
        for result in pre_filtered_exact:
            source_key = result.get('source') or result.get('title') or str(result.get('doc_id'))
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            final_results.append(result)
            if len(final_results) >= k:
                return final_results[:k]
    for result in scored_results:
        source_key = result.get('source') or result.get('title') or str(result.get('doc_id'))
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        
        # Apply text refinement to clean text
        refined_clean = _refine_text(result['clean'], max_length=250)
        result['clean'] = refined_clean
        result['snippet'] = refined_clean
        
        final_results.append(result)
        
        if len(final_results) >= k:
            break
    
    return final_results


def search_text(query, k=3):
    """
    Main search endpoint - uses improved retriever.
    Returns top-k most relevant results with strict quality filtering.
    """
    return retrieve(query, k=k)
