"""Test script for the ClariFact API.

Usage:
    python scripts/test_api.py "<text>"

Sends a POST request to ``http://127.0.0.1:8000/analyze`` and polls the
``/jobs/{job_id}`` endpoint until the job reaches the ``done`` status, then
prints the final ``AnalysisResult`` as pretty‑printed JSON.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

# Ensure the repository root is on ``sys.path`` so imports (if needed) resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_URL = "http://127.0.0.1:8000"


def submit_job(text: str) -> str:
    """POST to ``/analyze`` with a single ``text`` field and return the job ID."""
    # Use multipart/form-data to match FastAPI expectations.
    response = httpx.post(f"{API_URL}/analyze", data={"text": text})
    response.raise_for_status()
    data = response.json()
    return data["job_id"]


def poll_job(job_id: str, interval: float = 1.0) -> dict:
    """Poll ``/jobs/{job_id}`` until ``status`` is ``done`` or ``error``.
    Returns the final job dict.
    """
    while True:
        resp = httpx.get(f"{API_URL}/jobs/{job_id}")
        resp.raise_for_status()
        job = resp.json()
        status = job.get("status")
        if status in ("done", "error"):
            return job
        # Show progress for user feedback.
        step = job.get("step", "")
        print(f"[poll] status={status!r} step={step!r}")
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a full API analysis via HTTP")
    parser.add_argument("text", help="Input text to analyze")
    args = parser.parse_args(argv)

    try:
        job_id = submit_job(args.text)
        print(f"Submitted job_id={job_id}")
        final_job = poll_job(job_id)
        if final_job.get("status") == "done":
            result = final_job.get("result")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("Job failed:", final_job.get("error"))
    except Exception as exc:
        print(f"Error during API test: {exc}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
