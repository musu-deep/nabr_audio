from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .audio_engine import analyze_audio, process_audio
from .nlp_intent import parse_message
from .schemas import ChatRequest, ProcessRequest


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
WORK_DIR = BASE_DIR / "workspace"
UPLOAD_DIR = WORK_DIR / "uploads"
PROCESSED_DIR = WORK_DIR / "processed"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nabr Audio Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}:
        raise HTTPException(status_code=400, detail="صيغة الملف غير مدعومة.")

    file_id = uuid.uuid4().hex
    dst = UPLOAD_DIR / f"{file_id}{suffix}"
    with dst.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        analysis = analyze_audio(dst)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"تعذر قراءة الملف: {e}")

    return {
        "file_id": file_id,
        "filename": file.filename,
        "stored_filename": dst.name,
        "analysis": analysis,
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    actions, summary = parse_message(req.message)
    return {"actions": actions, "summary": summary}


@app.post("/api/process")
def process(req: ProcessRequest):
    candidates = list(UPLOAD_DIR.glob(f"{req.file_id}.*"))
    if not candidates:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الملف.")

    src = candidates[0]
    try:
        result = process_audio(
            input_path=src,
            output_dir=PROCESSED_DIR,
            actions=req.actions,
            silence_min_ms=req.silence_min_ms or 900,
            silence_keep_ms=req.silence_keep_ms or 120,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء المعالجة: {e}")

    return {
        "download_url": f"/api/download/{result['output_filename']}",
        "logs": result["logs"],
        "analysis": result["analysis"],
    }


@app.get("/api/download/{filename}")
def download(filename: str):
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="الملف غير موجود.")
    return FileResponse(path, filename=filename, media_type="audio/wav")
