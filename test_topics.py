import urllib.request
import json
import urllib.parse

# Test JARVIS with different topics to verify topic detection works
test_queries = [
    "when are exams?",
    "admission information",
    "what are the fees?",
    "registration deadline",
    "latest notices"
]

print("Testing JARVIS Chat Endpoint with Different Topics\n" + "="*50)

for query in test_queries:
    try:
        url = f"http://127.0.0.1:8000/chat?query={urllib.parse.quote(query)}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        print(f"\n📝 Query: '{query}'")
        print(f"✅ Found: {data['found_documents']} documents")
        print(f"💡 Response Preview: {data['response'][:120]}...")
        print(f"📌 Suggestions: {', '.join(data['suggestions'][:2])}")
    except Exception as e:
        print(f"\n❌ Query: '{query}' - Error: {e}")

print("\n" + "="*50)
print("✓ All chat tests completed!")
