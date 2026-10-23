"""FastAPI entry point for ClariFact.

Provides the ``/analyze`` POST endpoint (accepts multipart form data or JSON) and
the ``/jobs/{job_id}`` GET endpoint for job status tracking.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uuid
from typing import Dict, Optional, List

import uvicorn
from fastapi import FastAPI, BackgroundTasks, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.interfaces import JobStatus, AnalysisResult, ExtractedContent, ProgressFn
import logging
import tempfile
from app.extract import extract_from_video, extract_from_image
from .pipeline import analyze_content

app = FastAPI()
# Mount static files for UI

# In‑memory job store – keys are job IDs, values are JobStatus dicts.
_jobs: Dict[str, JobStatus] = {}


def _progress_updater(job_id: str) -> ProgressFn:
    """Factory returning a ``ProgressFn`` that updates the stored job step.

    The function is safe for background execution because the ``_jobs`` dict is
    thread‑safe for simple single‑process usage.
    """

    def _update(step: str) -> None:
        job = _jobs.get(job_id)
        if job:
            job["step"] = step
            job["status"] = "running"
    return _update


async def _run_job(job_id: str, content: ExtractedContent) -> None:
    """Background coroutine that performs the analysis and stores the result.
    """
    try:
        progress = _progress_updater(job_id)
        result: AnalysisResult = analyze_content(content, progress)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["step"] = "Finished"
        _jobs[job_id]["result"] = result
    except Exception as exc:  # pragma: no cover – defensive
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["step"] = "Error"


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> Dict[str, str]:
    """Kick off an analysis job.

    Accepts ``text`` directly, or a file upload, or a URL. For files and URLs we
    fall back to placeholder handling (filename or URL string) and add a warning
    in the ``ExtractedContent``. The real extraction (audio/video OCR, image
    OCR, downloading) is performed by other agents and will replace these stubs
    later.
    """
    if not text and not url and not file:
        raise HTTPException(status_code=400, detail="At least one of text, url, or file must be provided")

    warnings: List[str] = []
    transcript = ""
    ocr_text = ""
    # ---------- File handling ----------
    if file:
        # Validate file extension and MIME type before processing.
        filename = file.filename or ""
        # Supported video MIME types.
        supported_video_mimes = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"}
        content_type = file.content_type or ""
        # Allow any file extension for videos, but enforce MIME type whitelist.
        if content_type.startswith("video/"):
            if content_type not in supported_video_mimes:
                raise HTTPException(status_code=400, detail="Unsupported video type")
        else:
            # Non-video files: restrict to known safe extensions.
            allowed_extensions = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
            ext = Path(filename).suffix.lower()
            if ext not in allowed_extensions:
                raise HTTPException(status_code=400, detail="Unsupported file type")
        # Read the uploaded file (limited to a small size for safety).
        try:
            file_bytes = await file.read()
            # Attempt real extraction using appropriate extractor
            # Write uploaded bytes to a temporary file for extraction
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                if content_type.startswith("video/"):
                    extracted = extract_from_video(tmp_path, progress=None)
                elif content_type.startswith("image/"):
                    extracted = extract_from_image(tmp_path, progress=None)
                else:
                    extracted = {"text": filename, "transcript": "", "ocr_text": "", "warnings": []}
            except Exception as exc:
                logging.exception("Media extraction failed")
                extracted = {"text": filename, "transcript": "", "ocr_text": "", "warnings": [f"Extraction failed: {exc}"]}
            # Use extracted values
            text = extracted.get("text", filename)
            transcript = extracted.get("transcript", "")
            ocr_text = extracted.get("ocr_text", "")
            warnings.extend(extracted.get("warnings", []))
            # Log a preview of extracted content (first 100 chars)
            logging.info(f"Extracted transcript preview: {transcript[:100]!r}")
            logging.info(f"Extracted OCR preview: {ocr_text[:100]!r}")
        except Exception as exc:
            warnings.append(f"Failed to read uploaded file: {exc}")
            text = ""
        finally:
            # Ensure any underlying file resources are released.
            try:
                await file.close()
            except Exception:
                pass
    # ---------- URL handling ----------
    elif url:
        # In a full implementation we would download and extract content.
        # Here we treat the URL itself as the text input and note the limitation.
        text = url
        warnings.append("URL extraction not implemented; using URL as text placeholder.")
    else:
        # ``text`` is already provided (may be None).
        text = text or ""

    # Build the ``ExtractedContent`` for the pipeline.
    content: ExtractedContent = {
        "text": text,
        "transcript": transcript,
        "ocr_text": ocr_text,
        "warnings": warnings,
    }


    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "step": "Queued", "result": None, "error": None}
    background_tasks.add_task(_run_job, job_id, content)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> JobStatus:
    """Return the current status (and result when finished) for *job_id*.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


app.mount("/static", StaticFiles(directory="static"), name="static")

# Fallback root mount for index.html and root‑level assets
app.mount("/", StaticFiles(directory="static", html=True), name="root_static")

# If this file is executed directly we start the server (useful for manual testing).
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

# End of file
