import requests
import json

# Test 1: Non-existent term
response = requests.get('http://127.0.0.1:8001/search?query=xyz123nonexistent')
data = response.json()
print(f"Test 1 - Non-existent term 'xyz123nonexistent':")
print(f"  Results count: {len(data['results'])}")
if len(data['results']) == 0:
    print("  ✅ PASS - Returns empty results as expected")
else:
    print(f"  ❌ FAIL - Expected 0 results, got {len(data['results'])}")
    for r in data['results'][:2]:
        print(f"     - {r['title']}")

# Test 2: Real term that should work
response2 = requests.get('http://127.0.0.1:8001/search?query=university')
data2 = response2.json()
print(f"\nTest 2 - Real term 'university':")
print(f"  Results count: {len(data2['results'])}")
if len(data2['results']) > 0:
    print("  ✅ PASS - Returns results as expected")
    print(f"     - Top result: {data2['results'][0]['title']}")
else:
    print("  ❌ FAIL - Expected results, got none")
