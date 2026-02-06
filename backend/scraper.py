import requests
from bs4 import BeautifulSoup
import os

BASE_URL = "https://gietu.edu"
DOWNLOAD_DIR = "data/auto_notices"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def scrape_notices():
    print("🔎 Scraping notices...")
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.find_all("a", href=True)

    for link in links:
        href = link["href"]
        if href.endswith(".pdf"):
            file_url = href if href.startswith("http") else BASE_URL + href
            file_name = file_url.split("/")[-1]
            file_path = os.path.join(DOWNLOAD_DIR, file_name)

            if not os.path.exists(file_path):
                r = requests.get(file_url)
                with open(file_path, "wb") as f:
                    f.write(r.content)
                print(f"✅ Downloaded: {file_name}")
