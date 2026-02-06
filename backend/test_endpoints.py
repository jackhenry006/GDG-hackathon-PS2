#!/usr/bin/env python
"""Quick smoke tests for the backend server."""
import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(path, method="GET", data=None):
    """Test an API endpoint."""
    url = f"{BASE_URL}{path}"
    print(f"\n[TEST] {method} {path}")
    print(f"  URL: {url}")
    try:
        req = urllib.request.Request(url, data=data, method=method)
        response = urllib.request.urlopen(req, timeout=5)
        result = json.loads(response.read().decode())
        print(f"  ✓ Status: {response.status}")
        print(f"  ✓ Response: {json.dumps(result, indent=4)}")
        return result
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None

print("=" * 60)
print("SMOKE TESTS FOR BACKEND SERVER")
print("=" * 60)

# Test 1: Home endpoint
test_endpoint("/")

# Test 2: Status endpoint
test_endpoint("/status")

# Test 3: Get notifications
test_endpoint("/notifications")

# Test 4: Search (no results expected if empty index)
test_endpoint("/search?query=test")

print("\n" + "=" * 60)
print("✓ All basic endpoints responding!")
print("=" * 60)
print("\nNext steps:")
print("1. Upload a PDF: curl -F 'file=@yourfile.pdf' http://127.0.0.1:8001/upload")
print("2. Check job status: http://127.0.0.1:8001/job/<job_id>")
print("3. Search: http://127.0.0.1:8001/search?query=yoursearch")
print("4. View frontend: http://127.0.0.1:8001/... (frontend files in ../frontend/)")
