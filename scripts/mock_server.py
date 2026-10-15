"""Mock server for ClariFact UI development.

Serves static/ folder at "/" and implements POST /analyze and GET /jobs/{id}
exactly as the contract in SPEC.md and app/interfaces.py (JobStatus).

Each job walks through 5 fake steps (about 1 second each):
  "Extracting audio", "Transcribing speech", "Finding claims",
  "Checking claim 1 of 3", "Scoring"
and returns a hardcoded sample AnalysisResult.
"""

import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# App & static serving
# ---------------------------------------------------------------------------
app = FastAPI()

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
JOBS: dict = {}

STEPS = [
    "Extracting audio",
    "Transcribing speech",
    "Finding claims",
    "Checking claim 1 of 3",
    "Scoring",
]


def _hardcoded_result():
    return {
        "credibility_score": 38,
        "label": "Likely misleading",
        "confidence": "medium",
        "promo": {
            "detected": True,
            "type": "hidden",
            "evidence": ["● The product claims 'miraculous cure' with no scientific backing",
                        "● Uses 'limited time offer' pressure tactic"],
        },
        "claims": [
            {
                "text": "This supplement guarantees weight loss of 10 lbs in 7 days without diet or exercise",
                "verdict": "contradicted",
                "explanation": "No clinical evidence supports such rapid weight loss without lifestyle changes.",
                "sources": [
                    {"title": "WHO obesity guidelines", "url": "https://www.who.int/topics/obesity"},
                    {"title": "Mayo Clinic", "url": "https://www.mayoclinic.org/healthy-weight-loss"},
                ],
            },
            {
                "text": "Scientists have proven that this cream reverses aging in 2 weeks",
                "verdict": "misleading",
                "explanation": "The study was tiny and funded by the product company; results not reproducible.",
                "sources": [
                    {"title": "PubMed study note", "url": "https://pubmed.ncbi.nlm.nih.gov"},
                ],
            },
            {
                "text": "Use this code SAVE20 at checkout for 20% off",
                "verdict": "supported",
                "explanation": "The discount code SAVE20 is valid and applies at checkout.",
                "sources": [
                    {"title": "Store promo page", "url": "https://example.com/promo"},
                ],
            },
        ],
        "red_flags": [
            "miracle cure language",
            "false urgency",
        ],
        "transcript": "Extracting audio from video... [simulated transcript]",
        "ocr_text": "On-screen text from frames: [simulated OCR]",
        "warnings": ["Simulated warning: analysis performed with mock data"],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """Serve static index.html"""
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/static/{path:path}")
async def static_files(path: str):
    """Serve static files"""
    return FileResponse(static_dir / path)


@app.post("/analyze")
async def analyze(request: Request):
    """POST /analyze — multipart form: text (optional str), file (optional upload), url (optional str)"""
    form = await request.form()
    text = form.get("text")
    url = form.get("url") if "url" in form else None
    file = form.get("file")

    # If text starts with http, treat as url; otherwise as text
    if text and (text.startswith("http://") or text.startswith("https://")):
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "step": STEPS[0],
            "current_step_index": 0,
        }
        # Start background step progression
        asyncio.create_task(_progress_job(job_id))
        return {"job_id": job_id}
    else:
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "step": STEPS[0],
            "current_step_index": 0,
        }
        asyncio.create_task(_progress_job(job_id))
        return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def jobs(job_id: str):
    """GET /jobs/{id} — JobStatus"""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    # Remove had_evidence from verified claims before sending
    result = job.get("result")
    if result and isinstance(result, dict):
        for claim in result.get("claims", []):
            claim.pop("had_evidence", None)
    return {
        "status": job.get("status", "queued"),
        "step": job.get("step", ""),
        "result": result,
        "error": job.get("error"),
    }


# ---------------------------------------------------------------------------
# Background: progress through 5 steps then return result
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8001)
    
async def _progress_job(job_id: str):
    """Walk through 5 fake steps (~1s each) then return hardcoded analysis result."""
    job = JOBS[job_id]
    try:
        for i, step in enumerate(STEPS, start=1):
            await asyncio.sleep(1)  # ~1 second per step
            job["step"] = step
            job["current_step_index"] = i
            # Update job in store
            JOBS[job_id] = job

        # After all steps, attach hardcoded result and mark done
        result = _hardcoded_result()
        job["status"] = "done"
        job["result"] = result
        JOBS[job_id] = job
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        JOBS[job_id] = job