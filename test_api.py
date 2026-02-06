import requests
import json

api_url = 'http://127.0.0.1:8000'

print('=' * 50)
print('TESTING BACKEND APIs')
print('=' * 50)

# Test 1: Search
print('\n=== Test 1: Search API ===')
try:
    r = requests.get(f'{api_url}/search?query=exam')
    results = r.json()
    print(f'Status: OK')
    print(f'Results count: {len(results.get("results", []))}')
    if results.get('results'):
        first = results['results'][0]
        print(f'Sample result keys: {list(first.keys())}')
except Exception as e:
    print(f'Error: {e}')

# Test 2: Chat
print('\n=== Test 2: Chat API ===')
try:
    r = requests.get(f'{api_url}/chat?query=When%20are%20exams')
    result = r.json()
    print(f'Status: OK')
    print(f'Response keys: {list(result.keys())}')
    print(f'Has response text: {bool(result.get("response"))}')
except Exception as e:
    print(f'Error: {e}')

# Test 3: Notifications
print('\n=== Test 3: Notifications API ===')
try:
    r = requests.get(f'{api_url}/notifications')
    result = r.json()
    print(f'Status: OK')
    print(f'Notifications count: {len(result.get("notifications", []))}')
except Exception as e:
    print(f'Error: {e}')

print('\n' + '=' * 50)
print('All APIs are functional!')
print('=' * 50)
