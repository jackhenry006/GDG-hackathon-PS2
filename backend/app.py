from fastapi import FastAPI, UploadFile, File
import asyncio
import uuid
import threading
from datetime import datetime
import shutil
import os

from ocr import extract_text
from embed import add_text, search_text, documents, index
from db import init_db, add_notification_db, SessionLocal, Notification as DBNotification
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "data", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ensure DB ready
init_db()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), sync: bool = False):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        raw_text, cleaned_text = extract_text(file_path)

        if not cleaned_text or len(cleaned_text.strip()) < 10:
            return {"message": "File uploaded but no readable text found"}

        # If client requested synchronous indexing, run and return doc_id
        if sync:
            try:
                doc_id = await asyncio.to_thread(add_text, raw_text, cleaned_text, source=file.filename)
            except TypeError:
                doc_id = await asyncio.to_thread(add_text, raw_text, cleaned_text, file.filename)
            add_notification(f"Uploaded and indexed: {file.filename} (id={doc_id})")
            return {"message": "File uploaded and indexed successfully", "doc_id": doc_id}

        # Otherwise schedule background indexing and return a job id immediately
        job_id = uuid.uuid4().hex
        with jobs_lock:
            jobs[job_id] = {"status": "pending", "doc_id": None, "error": None, "filename": file.filename}

        asyncio.create_task(_run_index_job(job_id, raw_text, cleaned_text, file.filename))

        return {"message": "File uploaded, indexing started", "job_id": job_id}

    except Exception as e:
        return {"error": str(e)}

@app.get("/upload")
def upload_info():
    return {"message": "Use POST /upload via Swagger UI"}

 
@app.get("/")
def home():
   return {
        "message": "Digital Archaeology API is running",
        "upload": "Use POST /upload via /docs",
        "search": "Use GET /search?query=your_text"
    }
@app.get("/search")
async def search(query: str):
    # run search in thread to avoid blocking the event loop
    results = await asyncio.to_thread(search_text, query)
    if not results:
        add_notification(f"Search: No results for '{query}'")
    return {"results": results}


@app.get("/chat")
async def chat(query: str):
    """Search endpoint - returns document search results (removed conversational responses)"""
    results = await asyncio.to_thread(search_text, query, 5)
    add_notification(f"Search query: {query}")
    return {"query": query, "results": results, "found_documents": len(results)}



@app.get("/download")
def download(filename: str):
    # prevent path traversal
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.exists(file_path):
        add_notification(f"Download failed: {safe_name} not found")
        return {"error": "File not found"}

    add_notification(f"Downloaded: {safe_name}")
    from fastapi.responses import FileResponse

    return FileResponse(path=file_path, filename=safe_name, media_type='application/octet-stream')


# simple in-memory notifications
notifications = []

# job tracking for background indexing
jobs = {}
jobs_lock = threading.Lock()


async def _run_index_job(job_id: str, raw_text: str, cleaned_text: str, filename: str):
    with jobs_lock:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["started_at"] = datetime.utcnow().isoformat() + "Z"
    try:
        doc_id = await asyncio.to_thread(add_text, raw_text, cleaned_text, source=filename)
        with jobs_lock:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["doc_id"] = int(doc_id) if doc_id is not None else None
            jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        add_notification(f"Uploaded and indexed: {filename} (id={doc_id})")
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        add_notification(f"Upload failed: {filename} - {e}")

def add_notification(message: str):
    from datetime import datetime
    notifications.append({"message": message, "time": datetime.utcnow().isoformat() + "Z"})
    # also persist to DB
    try:
        add_notification_db(message)
    except Exception:
        pass


@app.get("/notifications")
def get_notifications():
    # return all notifications (frontend may clear on display)
    # also return persisted notifications (merge)
    db = SessionLocal()
    persisted = []
    try:
        rows = db.query(DBNotification).order_by(DBNotification.time.desc()).limit(100).all()
        persisted = [{"message": r.message, "time": (r.time.isoformat() + "Z") if hasattr(r, 'time') else str(r.time)} for r in rows]
    except Exception as e:
        # log DB read errors to console so issues are visible
        print("⚠️ Failed to read persisted notifications:", e)
    finally:
        try:
            db.close()
        except Exception:
            pass

    merged = persisted[::-1] + notifications
    return {"notifications": merged}


@app.get("/status")
def status():
    try:
        vectors = int(index.ntotal) if hasattr(index, 'ntotal') else 0
    except Exception:
        vectors = 0
    return {"documents": len(documents), "vectors": vectors}


@app.get("/job/{job_id}")
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return {"error": "job not found"}
        # shallow copy to avoid exposing lock-protected structure
        return {"job_id": job_id, "status": job.get("status"), "doc_id": job.get("doc_id"), "error": job.get("error"), "filename": job.get("filename"), "started_at": job.get("started_at"), "completed_at": job.get("completed_at")}
