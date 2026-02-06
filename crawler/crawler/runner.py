from crawler.UniversityCrawler import UniversityCrawler

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

crawler = UniversityCrawler(
    seed_urls=seed_urls,
    allowed_domain="giet.edu",
    max_depth=3,
    max_pages=80,
    max_documents=1000
)

documents = crawler.crawl()

print("\nDiscovered Documents:")
for d in documents:
    print(d["url"])
