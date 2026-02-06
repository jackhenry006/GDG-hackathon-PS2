import sys
import json
from db import SessionLocal, Document

def find(query, limit=20):
    db = SessionLocal()
    try:
        q = f"%{query}%"
        rows = db.query(Document).filter(
            (Document.clean.ilike(q)) |
            (Document.raw.ilike(q)) |
            (Document.title.ilike(q)) |
            (Document.source.ilike(q)) |
            (Document.filename.ilike(q))
        ).limit(limit).all()
        out = []
        for r in rows:
            out.append({
                'id': r.id,
                'title': r.title,
                'source': r.source,
                'filename': r.filename,
                'clean_snippet': (r.clean or '')[:300],
            })
        return out
    finally:
        db.close()

def main():
    if len(sys.argv) < 2:
        print('Usage: python find_docs.py <query>')
        return
    query = sys.argv[1]
    results = find(query)
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
