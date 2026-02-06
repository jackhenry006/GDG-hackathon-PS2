# Digital Archaeology - Complete Setup & Usage Guide

## ✓ Status: SERVER RUNNING ON PORT 8001

The backend server is successfully running with all imports loaded and application startup complete.

### Server Details
- **URL**: http://127.0.0.1:8001
- **Status**: Running (Uvicorn PID: 23080)
- **Last Started**: 2026-02-06
- **All imports**: ✓ OK (db, ocr, embed, uvicorn)

---

## API Endpoints

### 1. **Status Check**
```
GET /status
```
Returns: `{"documents": N, "vectors": M}`
- Shows how many documents are indexed and vectors in FAISS

### 2. **Upload Document (Async)**
```
POST /upload
Body: multipart/form-data with file
Query params: ?sync=false (default, returns job_id) or ?sync=true (wait for doc_id)
```
Returns:
- **Async** (default): `{"message": "File uploaded, indexing started", "job_id": "xyz123"}`
- **Sync**: `{"message": "File uploaded and indexed successfully", "doc_id": 5}`

### 3. **Check Job Status**
```
GET /job/{job_id}
```
Returns: `{"job_id": "...", "status": "pending|running|done|failed", "doc_id": N, "filename": "...", "started_at": "...", "completed_at": "..."}`

### 4. **Search Documents**
```
GET /search?query=your+search+term
```
Returns: `{"results": [...list of matching documents...]}`

### 5. **List Notifications**
```
GET /notifications
```
Returns: `{"notifications": [{"message": "...", "time": "..."}]}`

### 6. **Home**
```
GET /
```
Returns: Basic API info

---

## How to Use (Step by Step)

### Step 1: Upload a Document
```powershell
# Using PowerShell (async - returns job_id immediately)
$file = "C:\path\to\your\document.pdf"
$form = @{
    file = Get-Item $file
}
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/upload" -Method Post -Form $form
$response.Content | ConvertFrom-Json

# Or with curl (if available)
curl -F "file=@C:/path/to/file.pdf" http://127.0.0.1:8001/upload
```

**Response (async):**
```json
{
  "message": "File uploaded, indexing started",
  "job_id": "a1b2c3d4e5f6"
}
```

### Step 2: Monitor Job Progress
```powershell
$jobId = "a1b2c3d4e5f6"
$job = (Invoke-WebRequest -Uri "http://127.0.0.1:8001/job/$jobId").Content | ConvertFrom-Json
$job
# Will show: status = "pending", "running", "done", or "failed"
```

Keep polling until `status` = `"done"`, then use `doc_id` for searching.

### Step 3: Search Documents
```powershell
$query = "registration deadline"
$results = (Invoke-WebRequest -Uri "http://127.0.0.1:8001/search?query=$query").Content | ConvertFrom-Json
$results | ConvertTo-Json -Depth 3
```

**Response:**
```json
{
  "results": [
    {
      "doc_id": 1,
      "score": 0.87,
      "source": "document.pdf",
      "clean": "Registration deadline is December 15, 2025.",
      "snippet": "Registration deadline is December 15..."
    }
  ]
}
```

### Step 4: View Notifications
```powershell
(Invoke-WebRequest -Uri http://127.0.0.1:8001/notifications).Content | ConvertFrom-Json | ConvertTo-Json
```

Shows all upload/search/download events with timestamps.

---

## Frontend Setup

### Option A: Use Python HTTP Server
```powershell
cd "d:\GDG HACKATHON\frontend"
python -m http.server 3000
# Open browser: http://127.0.0.1:3000
```

### Option B: Use Node.js (if installed)
```bash
cd "d:\GDG HACKATHON\frontend"
npx http-server -p 3000
```

### Option C: Open HTML Directly
Open `d:\GDG HACKATHON\frontend\index.html` in your browser

---

## OCR & Embedding Features

### ✓ What's Included:
1. **Enhanced OCR Cleaning**
   - Ligature fixes (fi → fi, fl → fl)
   - Common number/letter confusion fixes (0 → O)
   - Punctuation spacing normalization
   - Sentence capitalization fixes
   - Spell correction on unknown words

2. **Light Grammar Correction** (built-in)
   - Capitalizes "I"
   - Fixes "a" → "an"
   - Removes orphaned brackets/noise
   - Removes repeated page headers/footers

3. **Optional Advanced Grammar Model** (disabled by default)
   - To enable, set environment variables before starting server:
   ```powershell
   $env:ENABLE_OCR_GRAMMAR = "1"
   $env:OCR_GRAMMAR_MODEL = "prithivida/grammar_error_correcter_v1"  # or another model
   ```
   - Then restart the server

### Embedding:
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension**: 384
- **Index**: FAISS (IndexFlatL2)
- **Search**: Top-K retrieval with multi-stage re-ranking

---

## File Structure

```
D:\GDG HACKATHON\
├── backend/
│   ├── app.py                  # FastAPI server
│   ├── embed.py               # Embedding & FAISS indexing
│   ├── ocr.py                 # OCR with preprocessing & cleanup
│   ├── db.py                  # SQLite models & persistence
│   ├── run_server.py          # Startup script
│   ├── test_endpoints.py      # Smoke tests
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── index.html             # Main UI
│   ├── script.js              # Upload/Search/Notification logic
│   └── style.css              # Dark theme
├── data/
│   ├── app.db                 # SQLite database (notifications, documents)
│   ├── faiss.index            # FAISS vector index
│   ├── faiss_meta.json        # Index metadata
│   ├── documents.json         # Document chunk cache
│   └── uploads/               # Uploaded files
└── README.md
```

---

## Troubleshooting

### Issue: "Port 8001 already in use"
```powershell
# Find process using port 8001
$proc = (Get-NetTCPConnection -LocalPort 8001).OwningProcess
Stop-Process -Id $proc -Force

# Then restart server
python "d:\GDG HACKATHON\backend\run_server.py"
```

### Issue: "Module not found" errors
Install dependencies:
```powershell
pip install -r "d:\GDG HACKATHON\backend\requirements.txt"
```

### Issue: Search returning no results
1. Check `/status` to see if documents were indexed
2. Upload a PDF first using `/upload`
3. Wait for job to complete (check `/job/{job_id}`)
4. Then search

### Issue: OCR producing poor results
Try:
1. Uploading a different PDF format (e.g., text PDF vs scanned image)
2. Enabling the optional grammar model (see section above)
3. Checking server logs for OCR errors

---

## Performance Notes

- **First Query**: ~2-3 seconds (model loading on CPU)
- **Subsequent Queries**: ~200-500ms (embedding + FAISS search)
- **Upload Time**: Depends on file size
  - Simple PDF (5 pages): ~5-10 seconds
  - Complex scanned PDF (50 pages + OCR): ~60-120 seconds
- **CPU Usage**: High during uploads (multi-page OCR), minimal during searches

---

## Next Steps

1. **Quick Test**:
   - Upload a PDF document
   - Wait for job to complete
   - Search for keywords from the document
   - Verify results appear in the frontend

2. **Production Deployment**:
   - Add authentication (JWT tokens)
   - Use a persistent job queue (Redis/RQ)
   - Deploy on port 80 or behind nginx
   - Enable HTTPS

3. **Further Customization**:
   - Modify OCR preprocessing in `ocr.py`
   - Adjust FAISS retrieval parameters in `embed.py`
   - Customize UI theme in `frontend/style.css`

---

**Server Status**: ✓ RUNNING
**Last Updated**: 2026-02-06
**Ready**: Yes ✓
