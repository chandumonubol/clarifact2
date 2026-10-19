"""FastAPI entry point for ClariFact.

Provides the ``/analyze`` POST endpoint (accepts multipart form data or JSON) and
the ``/jobs/{job_id}`` GET endpoint for job status tracking.
"""

from __future__ import annotations

import uuid
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.interfaces import JobStatus, AnalysisResult, ExtractedContent, ProgressFn
from .pipeline import analyze_content

app = FastAPI()

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

    Only the ``text`` field is currently used; ``url`` and ``file`` are accepted
    for API compatibility but are ignored in this minimal implementation.
    """
    if not text and not url and not file:
        raise HTTPException(status_code=400, detail="At least one of text, url, or file must be provided")

    # Build a minimal ``ExtractedContent`` – other extraction steps are out of scope
    # for this brain implementation.
    content: ExtractedContent = {
        "text": text or "",
        "transcript": "",
        "ocr_text": "",
        "warnings": [],
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


# If this file is executed directly we start the server (useful for manual testing).
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

# End of file
