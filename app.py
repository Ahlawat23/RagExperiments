from typing import List
from pathlib import Path
import pathlib, datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from ragHandler import RagHandler
from dataUploadHandler import DataUploadHandler

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
rag = RagHandler()

UPLOADS_DIR = Path("uploads")
uploader = DataUploadHandler(UPLOADS_DIR)

# Serve /static/* from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- UI route (serves templates/chat.html) ---
@app.get("/", response_class=HTMLResponse)
async def serve_chat():
    html_path = Path("templates/chat.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="templates/chat.html not found")
    return html_path.read_text(encoding="utf-8")

# --- UI route (serves templates/upload.html) ---
@app.get("/upload", response_class=HTMLResponse)
async def serve_UploadUI():
    html_path = Path("templates/upload.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="templates/chat.html not found")
    return html_path.read_text(encoding="utf-8")

# --- File upload API (PDFs) ---
@app.post("/upload-pdf/")
async def upload_pdf(files: List[UploadFile] = File(...)):
    # Ensure it's a PDF
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    summary = await uploader.save_all(files)
    
    #alter the message based on number of pdf saved
    if summary["saved"] == 0:
        summary["message"] = "No PDFs saved"
    elif summary["skipped"] > 0:
        summary["message"] = "Some files skipped (non-PDF)"
    else:
        summary["message"] = "All PDFs uploaded"

    return summary

# --- Get the list of pdfs ---
@app.get("/list-uploads")
def list_uploads() -> dict:
    files: List[dict] = []
    for p in sorted(UPLOADS_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            st = p.stat()
            files.append({
                "name": p.name,
                "size": st.st_size,
                "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
                "url": f"/uploads/{p.name}",
            })
    return {"files": files}

# --- Rebuild/refresh your Qdrant index ---
@app.get("/updateQdrant/")
async def updateQdrant():
    rag.updateQDrant()
    return "updated"

# --- JSON question endpoint ---
@app.post("/createThrea/")
async def createThread(request: Request):
    body = await request.json()
    query = body.get("query", "")
    return rag.GenrateQuery(query)

# --- Chat endpoint for the web UI form (multipart: message + optional files) ---
@app.post("/chat")
async def chat(message: str = Form(...)):
    res = rag.GenrateQuery(message)
    print(res["prompt"])
    return JSONResponse({
        "query": message,
        "prompt": res["prompt"],
        "answer": res["answer"]

    })
