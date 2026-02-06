import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import time


class UniversityCrawler:

    def __init__(
        self,
        seed_urls,
        allowed_domain,
        max_depth=3,
        max_pages=100,
        max_documents=100
    ):
        self.seed_urls = seed_urls
        self.allowed_domain = allowed_domain
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.max_documents = max_documents

        self.visited_urls = set()
        self.document_links = []

        self.document_extensions = [".pdf", ".doc", ".docx"]

        self.allowed_path_prefixes = [
            "/happenings",
            "/examinations",
            "/academics"
        ]

        self.noise_patterns = [
            "/wp-json/",
            "/feed",
            "/category/",
            "/tag/",
            "/author/",
            "?utm_",
            "?replytocom="
        ]

    # ---------- HELPERS ----------

    def is_same_domain(self, url):
        return urlparse(url).netloc.lower().endswith(self.allowed_domain)

    def get_path(self, url):
        return urlparse(url).path.lower().rstrip("/")

    def is_document(self, url):
        return any(url.lower().endswith(ext) for ext in self.document_extensions)

    def is_noise_url(self, url):
        return any(n in self.get_path(url) for n in self.noise_patterns)

    def is_allowed_page(self, url):
        path = self.get_path(url)
        return any(path.startswith(prefix) for prefix in self.allowed_path_prefixes)

    # ---------- NETWORK ----------

    def fetch_page(self, url):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
                return r.text
        except requests.RequestException:
            pass
        return None

    # ---------- PARSING ----------

    def extract_links(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        links = set()

        for tag in soup.find_all("a", href=True):
            abs_url = urljoin(base_url, tag["href"])
            links.add(abs_url.split("#")[0])

        return links

    # ---------- MAIN CRAWLER ----------

    def crawl(self):
        queue = deque()

        for url in self.seed_urls:
            queue.append((url, 0))

        while queue:
            if len(self.visited_urls) >= self.max_pages:
                break

            if len(self.document_links) >= self.max_documents:
                break

            current_url, depth = queue.popleft()

            if current_url in self.visited_urls:
                continue

            if depth > self.max_depth:
                continue

            if not self.is_same_domain(current_url):
                continue

            if depth > 0 and not self.is_allowed_page(current_url):
                continue

            self.visited_urls.add(current_url)
            print(f"🕷 Crawling ({len(self.visited_urls)}): {current_url}")

            html = self.fetch_page(current_url)
            if not html:
                continue

            links = self.extract_links(html, current_url)

            for link in links:
                if link in self.visited_urls:
                    continue

                if not self.is_same_domain(link):
                    continue

                if self.is_noise_url(link):
                    continue

                if self.is_document(link):
                    self.document_links.append({
                        "url": link,
                        "source": current_url
                    })
                    print(f"  📄 Found document: {link}")

                elif self.is_allowed_page(link):
                    queue.append((link, depth + 1))

            time.sleep(0.2)

        print(
            f"\n✅ Crawl complete | "
            f"Visited: {len(self.visited_urls)} | "
            f"Documents: {len(self.document_links)}"
        )

        return self.document_links
