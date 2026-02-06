import time
import urllib.request
import urllib.error
import json

for attempt in range(20):
    try:
        response = urllib.request.urlopen('http://127.0.0.1:8000/search?query=registration', timeout=2)
        data = json.loads(response.read().decode())
        print('✓ Server responding')
        if 'results' in data and data['results']:
            result = data['results'][0]
            print(f'✓ Top result: {result.get("title", "N/A")}')
            print(f'  Score: {result.get("score", "N/A")}')
            clean_text = result.get("clean", "N/A")
            print(f'  Clean preview: {clean_text[:100]}...')
        break
    except urllib.error.URLError:
        time.sleep(0.5)
        continue
    except Exception as e:
        print(f'Error: {e}')
        break
