"""
Direct server startup - paste this into the Python terminal
"""
import sys
import os

# Setup path
os.chdir(r"d:\GDG HACKATHON\backend")
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("BACKEND SERVER STARTUP")
print("=" * 60)

# Step 1: Check imports
print("\n[1/3] Checking imports...")
try:
    print("  Importing db...", end=" ")
    from db import init_db, SessionLocal, Notification as DBNotification, add_notification_db
    print("✓")
    
    print("  Importing ocr...", end=" ")
    from ocr import extract_text
    print("✓")
    
    print("  Importing embed...", end=" ")
    from embed import add_text, search_text, documents, index
    print("✓")
    
    print("  Importing uvicorn...", end=" ")
    import uvicorn
    print("✓")
    
    print("  All imports successful!")
    
except Exception as e:
    print(f"\n✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Import and prepare FastAPI app
print("\n[2/3] Preparing FastAPI app...")
try:
    from app import app
    print("  ✓ FastAPI app loaded")
except Exception as e:
    print(f"  ✗ Failed to load app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Start server
print("\n[3/3] Starting Uvicorn server on http://127.0.0.1:8001")
print("-" * 60)
try:
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
except KeyboardInterrupt:
    print("\n\nServer stopped by user")
except Exception as e:
    print(f"\n✗ Server error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
