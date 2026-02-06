from ocr import extract_text
import os

p = os.path.join('..','data','uploads')
if not os.path.isdir(p):
    p = os.path.join('data','uploads')

pdfs = []
for root,_,files in os.walk(p):
    for f in files:
        if f.lower().endswith('.pdf'):
            pdfs.append(os.path.join(root,f))

if not pdfs:
    print('NO_PDF_FOUND')
    raise SystemExit(0)

fp = pdfs[0]
print('TEST_FILE:', fp)
raw, clean = extract_text(fp)
print('RAW_LEN:', len(raw), 'CLEAN_LEN:', len(clean))
print('\n---- CLEAN SAMPLE ----\n')
print(clean[:1000])
print('\n---- END SAMPLE ----\n')
