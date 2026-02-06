from scraper import scrape_notices
from ocr import extract_text
from embed import add_text
import os

NOTICE_DIR = "data/auto_notices"

def run_auto_index():
    scrape_notices()

    for file in os.listdir(NOTICE_DIR):
        path = os.path.join(NOTICE_DIR, file)
        raw, cleaned = extract_text(path)

        if cleaned.strip():
            add_text(raw, cleaned, source=file, title=file)

    print("✅ Auto indexing complete")

if __name__ == "__main__":
    run_auto_index()
