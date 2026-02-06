from fastapi import FastAPI, UploadFile, File
import shutil
import os

from ocr import extract_text
from embed import add_text, search_text

app = FastAPI()

UPLOAD_DIR = "../data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"{UPLOAD_DIR}/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    raw, cleaned = extract_text(file_path)
    add_text(raw, cleaned, source=file.filename)

    return {"message": "File processed and indexed successfully"}

@app.get("/search")
def search(query: str):
    results = search_text(query)
    return {"results": results}
