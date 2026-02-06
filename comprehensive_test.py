import requests

def test_search(query, expected_empty=False):
    response = requests.get(f'http://127.0.0.1:8001/search?query={query}')
    data = response.json()
    count = len(data['results'])
    
    if expected_empty:
        status = "✅" if count == 0 else "❌"
        print(f"{status} Query '{query}': {count} results (expected 0)")
        if count > 0:
            print(f"   ERROR: Got results when expecting none!")
            for r in data['results'][:2]:
                print(f"   - {r['title'][:50]}")
    else:
        status = "✅" if count > 0 else "❌"
        print(f"{status} Query '{query}': {count} results (expected >0)")
        if count > 0:
            print(f"   - Top: {data['results'][0]['title'][:50]}")
        else:
            print(f"   ERROR: Expected results but got none!")

print("=" * 60)
print("COMPREHENSIVE SEARCH QUALITY TESTS")
print("=" * 60)

print("\n[REAL TERMS - Should return results]")
test_search("GIET", expected_empty=False)
test_search("university", expected_empty=False)
test_search("professor", expected_empty=False)
test_search("student", expected_empty=False)
test_search("engineering", expected_empty=False)

print("\n[NON-EXISTENT TERMS - Should return EMPTY]")
test_search("xyz123nonexistent", expected_empty=True)
test_search("asdfqwerty", expected_empty=True)
test_search("foobarbazboing", expected_empty=True)
test_search("jabberw0cky", expected_empty=True)
test_search("nonexistentterm999", expected_empty=True)

print("\n[PARTIAL/VAGUE TERMS - May or may not return results]")
test_search("abc", expected_empty=False)  # Too generic, but let's see
test_search("the", expected_empty=False)  # Common word

print("\n" + "=" * 60)
print("TEST COMPLETE ✅")
print("=" * 60)
