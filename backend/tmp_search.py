from embed import search_text
import json

if __name__ == '__main__':
    results = search_text("registration", k=5)
    print(json.dumps(results, indent=2))
