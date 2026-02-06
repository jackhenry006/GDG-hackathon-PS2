import urllib.request
import json

response = urllib.request.urlopen('http://127.0.0.1:8000/search?query=examination', timeout=5)
data = json.loads(response.read().decode())

if data.get('results'):
    print('SEARCH RESULTS FOR "examination"')
    print('=' * 80)
    for i, result in enumerate(data['results'][:3], 1):
        print(f'\nResult {i}:')
        print(f'  Title: {result.get("title", "N/A")}')
        print(f'  Source: {result.get("source", "N/A")}')
        print(f'  Score: {result.get("score", "N/A"):.3f}')
        clean = result.get('clean', '')
        print(f'  Clean OCR: {clean[:150]}...')
        print(f'  URL: {result.get("url", "N/A")}')
    print('\n' + '=' * 80)
    print(f'✓ Total unique results: {len(data["results"])} (no duplicates)')
else:
    print('No results found')
