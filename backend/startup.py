#!/usr/bin/env python
"""Startup script that captures all errors to a log file."""
import sys
import os

# Change to backend directory
os.chdir(r"d:\GDG HACKATHON\backend")
sys.path.insert(0, os.getcwd())

log_file = "startup_errors.log"

with open(log_file, 'w') as f:
    f.write("=== Backend Startup Diagnostics ===\n\n")
    
    # Test imports
    f.write("1. Testing imports:\n")
    for mod in ['db', 'ocr', 'embed']:
        try:
            f.write(f"  {mod}...: ")
            __import__(mod)
            f.write("OK\n")
        except Exception as e:
            f.write(f"FAILED\n    {type(e).__name__}: {e}\n")
    
    # Test FastAPI app
    f.write("\n2. Testing FastAPI app:\n")
    try:
        from app import app
        f.write("  FastAPI app import: OK\n")
    except Exception as e:
        f.write(f"  FastAPI app import: FAILED\n    {type(e).__name__}: {e}\n")
        import traceback
        f.write(traceback.format_exc())
    
    # Try to start server
    f.write("\n3. Attempting server startup:\n")
    try:
        import uvicorn
        f.write("  uvicorn import: OK\n")
        f.write("  Starting on http://127.0.0.1:8001...\n")
        f.write("  (Check console output for server logs)\n")
        
        # Note: This will block, so we just log and prepare
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
    except Exception as e:
        f.write(f"  Server startup: FAILED\n    {type(e).__name__}: {e}\n")
        import traceback
        f.write(traceback.format_exc())

print(f"Diagnostics written to {log_file}")
