#!/usr/bin/env python
"""Quick check for import errors in backend modules."""
import sys
import traceback

modules = ['db', 'ocr', 'embed', 'app']

for mod in modules:
    try:
        print(f"Importing {mod}...", end=' ')
        __import__(mod)
        print("✓ OK")
    except Exception as e:
        print(f"✗ FAILED")
        print(f"  Error: {e}")
        traceback.print_exc()
        print()

print("\n--- Attempting to start uvicorn ---")
try:
    import uvicorn
    from app import app
    print("✓ FastAPI app imported OK")
    print("\nStarting server on http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
except Exception as e:
    print(f"✗ Failed to start: {e}")
    traceback.print_exc()
