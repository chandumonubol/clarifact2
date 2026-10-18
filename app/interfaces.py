"""Shared data shapes, constants and function signatures for ClariFact.

OWNED BY THE HUMAN. No coding agent may edit this file.
If a change is needed, the agent must STOP and ask.

Every module accepts / returns ONLY these shapes so code written by different
agents in different branches plugs together without edits.
"""
from typing import Callable, Literal, Optional, TypedDict

# progress("Transcribing speech") -> shown live in the UI
ProgressFn = Callable[[str], None]

# ---------------------------------------------------------------------------
# Constants (use these, never retype the strings)
# ---------------------------------------------------------------------------
LABEL_CREDIBLE = "Credible"                # score >= 75
LABEL_CAUTION = "Use caution"              # 50 <= score < 75
LABEL_MISLEADING = "Likely misleading"     # score < 50

VERDICTS = ("supported", "contradicted", "misleading", "unverified")
PROMO_TYPES = ("hidden", "disclosed", "none")

MAX_VIDEO_SECONDS = 90
MAX_VIDEO_MB = 100
MAX_CLAIMS = 6
MAX_TEXT_CHARS = 5000

# ---------------------------------------------------------------------------
# Internal shapes (between modules)
# ---------------------------------------------------------------------------


class ExtractedContent(TypedDict):
    text: str          # text/caption typed by the user ("" if none)
    transcript: str    # speech-to-text from video audio ("" if none)
    ocr_text: str      # on-screen text from frames / image ("" if none)
    warnings: list[str]


class PromoInfo(TypedDict):
    detected: bool
    type: Literal["hidden", "disclosed", "none"]
    evidence: list[str]


class Signals(TypedDict):
    claims: list[str]      # checkable factual claims, max MAX_CLAIMS
    promo: PromoInfo
    red_flags: list[str]
    warnings: list[str]


class Source(TypedDict):
    title: str
    url: str


class VerifiedClaim(TypedDict):
    text: str
    verdict: Literal["supported", "contradicted", "misleading", "unverified"]
    explanation: str
    sources: list[Source]
    had_evidence: bool     # internal only; pipeline.py removes it from the API result


class ScoreResult(TypedDict):
    credibility_score: int                       # 0-100
    label: str                                   # one of the LABEL_* constants
    confidence: Literal["low", "medium", "high"]


# ---------------------------------------------------------------------------
# API shapes (what the browser sees; identical in the real API and mock_server)
# ---------------------------------------------------------------------------


class ClaimOut(TypedDict):
    text: str
    verdict: Literal["supported", "contradicted", "misleading", "unverified"]
    explanation: str
    sources: list[Source]


class AnalysisResult(TypedDict):
    credibility_score: int
    label: str
    confidence: Literal["low", "medium", "high"]
    promo: PromoInfo
    claims: list[ClaimOut]
    red_flags: list[str]
    transcript: str
    ocr_text: str
    warnings: list[str]


class JobStatus(TypedDict):
    status: Literal["queued", "running", "done", "error"]
    step: str                          # e.g. "Transcribing speech"
    result: Optional[AnalysisResult]   # set only when status == "done"
    error: Optional[str]               # set only when status == "error"


# ---------------------------------------------------------------------------
# HTTP endpoints (implemented by app/main.py; mocked by scripts/mock_server.py)
# ---------------------------------------------------------------------------
# POST /analyze   multipart form: text (str, optional), file (upload, optional),
#                 url (str, optional)            -> {"job_id": "<id>"}
# GET  /jobs/{id}                                -> JobStatus
# GET  /health                                   -> {"ok": true}
# GET  /                                         -> static/index.html

# ---------------------------------------------------------------------------
# REQUIRED FUNCTION SIGNATURES (each owner implements theirs)
# ---------------------------------------------------------------------------
# app/llm.py       llm_json(prompt: str, schema_hint: str = "") -> dict
# app/claims.py    analyze(content: ExtractedContent) -> Signals
# app/verify.py    verify_claim(claim_text: str) -> VerifiedClaim
# app/scoring.py   score(claims: list[VerifiedClaim], promo: PromoInfo,
#                        red_flags: list[str]) -> ScoreResult
# app/extract.py   extract_from_text(text: str) -> ExtractedContent
#                  extract_from_image(path: str, progress: ProgressFn | None = None) -> ExtractedContent
#                  extract_from_video(path: str, progress: ProgressFn | None = None) -> ExtractedContent
# app/download.py  download_from_url(url: str, dest_dir: str) -> str   # local video path
# app/pipeline.py  run_pipeline(text: str | None, file_path: str | None,
#                               url: str | None, progress: ProgressFn) -> AnalysisResult
