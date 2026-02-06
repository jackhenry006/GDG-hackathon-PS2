import os
import sys
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# load UniversityCrawler dynamically
import importlib.util
uc_path = os.path.abspath(os.path.join(BASE_DIR, "..", "crawler", "crawler", "crawler", "UniversityCrawler.py"))
spec = importlib.util.spec_from_file_location("UniversityCrawler", uc_path)
uc_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uc_mod)
UniversityCrawler = uc_mod.UniversityCrawler

# seeds (copied from crawler/runner.py)
seed_urls = [
    "https://www.giet.edu/examinations/schedule",
    "https://www.giet.edu/examinations/notices",
    "https://www.giet.edu/examinations/downloads",
    "https://www.giet.edu/examinations/instructions",
    "https://www.giet.edu/happenings/announcements",
    "https://www.giet.edu/happenings/notices",
    "https://www.giet.edu/academics-regulations/",
    "https://www.giet.edu/academics/downloads",
    "https://www.giet.edu/academics/syllabus",
    "https://www.giet.edu/academics-calender/"
]

from embed import add_text
from ocr import extract_text
from app import add_notification


def safe_filename_from_url(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    if not name:
        name = "downloaded_doc"
    return name


def fetch_title(page_url):
    try:
        r = requests.get(page_url, timeout=8)
        if r.status_code == 200:
            s = BeautifulSoup(r.text, "html.parser")
            t = s.title.string.strip() if s.title and s.title.string else None
            return t
    except Exception:
        pass
    return None


def run_crawl_and_index():
    crawler = UniversityCrawler(seed_urls=seed_urls, allowed_domain="giet.edu", max_depth=3, max_pages=200, max_documents=500)
    docs = crawler.crawl()

    for doc in docs:
        url = doc.get("url")
        source = doc.get("source")
        file_name = safe_filename_from_url(url)
        dest_path = os.path.join(UPLOAD_DIR, file_name)

        if os.path.exists(dest_path):
            add_notification(f"Skipping download (exists): {file_name}")
            raw, cleaned = extract_text(dest_path)
            add_text(raw, cleaned, source=file_name, url=url, title=fetch_title(source) or file_name)
            continue

        try:
            r = requests.get(url, timeout=12)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                add_notification(f"Downloaded: {file_name}")
                raw, cleaned = extract_text(dest_path)
                if cleaned.strip():
                    add_text(raw, cleaned, source=file_name, url=url, title=fetch_title(source) or file_name)
        except Exception:
            add_notification(f"Failed to fetch: {url}")

    add_notification("Crawl & indexing complete")


if __name__ == "__main__":
    run_crawl_and_index()
