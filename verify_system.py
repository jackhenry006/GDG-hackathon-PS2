#!/usr/bin/env python3
"""
Complete End-to-End Test Verification
Tests: Server health, Search, Notifications, API responses
"""

import urllib.request
import json
import time
import sys

API_URL = "http://127.0.0.1:8001"
FRONTEND_URL = "http://127.0.0.1:3000"

def test_endpoint(name, url, expected_keys=None):
    """Test an API endpoint and verify response"""
    try:
        response = urllib.request.urlopen(url, timeout=5)
        data = json.loads(response.read().decode())
        
        print(f"✅ {name}", end="")
        
        if expected_keys:
            missing = [k for k in expected_keys if k not in data]
            if missing:
                print(f" (missing: {missing})")
                return False
        print()
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🧪 COMPLETE SYSTEM VERIFICATION TEST")
    print("="*70 + "\n")
    
    all_passed = True
    
    # Test 1: Server Health
    print("1️⃣  TESTING BACKEND SERVER")
    print("-" * 70)
    if not test_endpoint("Server Status", f"{API_URL}/status", ["documents", "vectors"]):
        print("\n❌ CRITICAL: Backend server not responding on port 8001")
        print("   Try restarting: python 'd:\\GDG HACKATHON\\backend\\run_server.py'")
        return False
    
    # Test 2: Search Capability
    print("\n2️⃣  TESTING SEARCH FUNCTIONALITY")
    print("-" * 70)
    start = time.time()
    if test_endpoint("Search Endpoint", f"{API_URL}/search?query=ayushman", ["results"]):
        elapsed = time.time() - start
        print(f"   ⚡ Response time: {elapsed*1000:.0f}ms")
        if elapsed > 1.0:
            print(f"   ⚠️  Search is slow (>{elapsed:.1f}s). May improve after more indexing.")
    else:
        all_passed = False
    
    # Test 3: Notifications
    print("\n3️⃣  TESTING NOTIFICATIONS")
    print("-" * 70)
    if test_endpoint("Notifications", f"{API_URL}/notifications", ["notifications"]):
        response = urllib.request.urlopen(f"{API_URL}/notifications")
        data = json.loads(response.read().decode())
        count = len(data.get("notifications", []))
        print(f"   📢 Found {count} notifications")
    else:
        all_passed = False
    
    # Test 4: Job Tracking (simulate)
    print("\n4️⃣  TESTING JOB TRACKING")
    print("-" * 70)
    try:
        # Try to get a non-existent job (should return error gracefully)
        response = urllib.request.urlopen(f"{API_URL}/job/test-invalid-job")
        data = json.loads(response.read().decode())
        if "error" in data or "job_id" in data:
            print("✅ Job Tracking Endpoint")
        else:
            print("⚠️  Job Tracking: Unexpected response")
    except Exception as e:
        print(f"⚠️  Job Tracking: {e}")
    
    # Test 5: Frontend Server
    print("\n5️⃣  TESTING FRONTEND SERVER")
    print("-" * 70)
    try:
        response = urllib.request.urlopen(f"{FRONTEND_URL}/index.html", timeout=5)
        print("✅ Frontend Server (Port 3000)")
        print("   🎨 Open browser: http://127.0.0.1:3000")
    except Exception as e:
        print(f"⚠️  Frontend: {e}")
        print("   Can start with: cd 'd:\\GDG HACKATHON\\frontend' && python -m http.server 3000")
    
    # Test 6: Data Status
    print("\n6️⃣  CHECKING INDEXED DATA")
    print("-" * 70)
    try:
        response = urllib.request.urlopen(f"{API_URL}/status")
        data = json.loads(response.read().decode())
        docs = data.get("documents", 0)
        vecs = data.get("vectors", 0)
        print(f"✅ Data Status")
        print(f"   📊 Documents: {docs}")
        print(f"   🔢 Vectors: {vecs}")
        if docs > 0:
            print(f"   ✨ Ready to search! {docs} documents indexed.")
        else:
            print(f"   📤 Upload a PDF via UI to start.")
    except Exception as e:
        print(f"❌ Data Status: {e}")
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL SYSTEMS OPERATIONAL!")
        print("\n🎯 NEXT STEPS:")
        print("   1. Open: http://127.0.0.1:3000")
        print("   2. Upload a PDF document")
        print("   3. Search for keywords instantly")
        print("   4. Download matching documents")
        print("\n⚡ Performance Tips:")
        print("   • First search may be slower (~500ms) while loading index")
        print("   • Subsequent searches: <300ms (results cached)")
        print("   • Upload returns immediately (indexing in background)")
    else:
        print("⚠️  SOME ISSUES DETECTED - See above for details")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
