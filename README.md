# ClariFact

**ClariFact** is an open‑source, multimodal AI‑powered fact‑checking and credibility analysis framework. It accepts text, images, video, or audio, extracts claims, verifies them against real‑time web evidence, and scores the overall credibility of the content.

---

## 1. Project Overview

- **What it is**: A FastAPI‑based backend that orchestrates media extraction, claim detection, web verification, and deterministic scoring, exposing a simple `/analyze` API for downstream clients.
- **Key features**:
  - Supports **text, image, video, audio** inputs.
  - Automatic claim extraction and promo detection.
  - Real‑time evidence lookup via **DuckDuckGo (`ddgs`)**, optional Wikipedia and Google Fact Check APIs.
  - Deterministic trust/penalty **scoring dashboard** with clear labels (`Credible`, `Use caution`, `Likely misleading`).
  - Structured source citations per claim.
  - Sample benchmarking script for quick local validation.

---

## 2. Architecture & Tech Stack

| Layer | Technologies |
|------|----------------|
| **Backend** | **FastAPI**, **Uvicorn**, **Python 3.12**, **Pydantic**, **python‑dotenv**, **httpx** |
| **AI & Media Pipeline** | LLM provider (local Ollama `qwen2.5:3b` or cloud Gemini/Groq via `.env`), **faster‑whisper** (CPU, `int8`), **RapidOCR‑onnxruntime**, **ffmpeg/ffprobe** for media handling |
| **Search** | **ddgs** (no API key required), optional **Wikipedia API**, optional **Google Fact Check Tools API** |
| **Download** | **yt‑dlp** for YouTube Shorts/Reels extraction |
| **Frontend** | Plain HTML, CSS, vanilla JS served from the `static/` folder (no React, no npm) |

> **Note** – All constants (e.g., max video length, max claims, label strings) are defined in `app/interfaces.py` and should be used throughout the code.

---

## 3. Prerequisites

## 0️⃣ Quick Start (Agent‑Friendly)

The following commands are sufficient for an automated agent (or a human) to get the project up‑and‑running after cloning the repo:

```powershell
git clone <repo‑url>
cd clarifact   # or the folder name you cloned into
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows; on Unix: cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

All required python packages are listed in `requirements.txt`. The environment variables required for optional cloud LLM providers and the Fact‑Check API are defined in `.env.example`; the defaults will run the local Ollama model (`qwen2.5:3b`). The server will be reachable at `http://127.0.0.1:8000`.

**Recent changes**
- Verification now generates concise 3‑6 word search queries and never injects unrelated fallback text when no results are found.
- Scoring aligns with the SPEC and uses the label constants `LABEL_CREDIBLE`, `LABEL_CAUTION`, `LABEL_MISLEADING` from `app/interfaces.py`.


- **Python** 3.12 or newer
- **Git**
- **FFmpeg** (including `ffprobe`) – must be on `PATH`
- **API keys** (optional but recommended for better verification):
  - `GEMINI_API_KEY`
  - `GROQ_API_KEY`
  - `FACTCHECK_API_KEY`
- **Environment** – copy `.env.example` to `.env` and fill in the required values.

---

## 4. Local Setup & Installation Guide (Step‑by‑Step)

```powershell
# 1️⃣ Clone the repository
git clone https://github.com/chandumonubol/clarifact2.git

# 2️⃣ Enter the project folder (adjust if you used the original name)
cd clarifact   # or `cd clarifact2`

# 3️⃣ Create and activate a virtual environment (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # on macOS/Linux: source .venv/bin/activate

# 4️⃣ Install Python dependencies (the project’s requirements.txt already pins the needed packages)
pip install -r requirements.txt
# `ddgs` and `pytest` are already listed in requirements.txt, but they can be installed explicitly if needed:
# pip install ddgs pytest

# 5️⃣ Configure environment variables
copy .env.example .env   # Windows PowerShell – creates a copy named `.env`
# Edit `.env` and set any keys you have (e.g., GEMINI_API_KEY, FACTCHECK_API_KEY, etc.)

# 6️⃣ Verify the installation (runs a quick health check script)
python -m scripts.startup_check.py
```

---

## 5. Running the Application

```powershell
# Start the FastAPI server (auto‑reload enabled for development)
python -m uvicorn app.main:app --reload --port 8000
```

- The API will be available at **http://127.0.0.1:8000**.
- UI can be accessed via the same address (serves `static/index.html`).
- **Endpoints** (see `app/interfaces.py` for full contract):
  - `POST /analyze` – multipart form with optional `text`, `file`, or `url`. Returns a job ID.
  - `GET /jobs/{job_id}` – poll for status and final `AnalysisResult`.

---

## 6. Testing & Sample Benchmarking

```powershell
# Run the full test suite
python -m pytest

# Execute the provided sample benchmark script
python scripts/run_samples.py
```

The benchmark expects a ground‑truth file at `C:\clarifact-samples\expected.json`. Adjust the path if needed.

---

## 7. Repository Structure

```
clarifact/
├─ app/                     # Core backend code
│   ├─ interfaces.py        # Shared data shapes, constants, and signatures (human‑only)
│   ├─ config.py            # Loads environment variables
│   ├─ llm.py               # LLM JSON wrapper (only LLM call site)
│   ├─ claims.py            # Claim extraction & promo detection
│   ├─ verify.py            # Web evidence lookup & verdict generation
│   ├─ scoring.py           # Deterministic scoring algorithm
│   ├─ pipeline.py          # Orchestrates the full analysis flow
│   ├─ extract.py           # Media extraction (text, image, video)
│   ├─ download.py          # yt‑dlp download helper
│   ├─ schemas.py           # Pydantic models mirroring interfaces
│   └─ main.py              # FastAPI routes + background job handling
├─ static/                  # Plain HTML/CSS/JS UI (no React)
│   ├─ index.html
│   ├─ style.css
│   └─ app.js
├─ scripts/                 # Helper scripts & test helpers
│   ├─ run_samples.py       # Benchmark runner
│   ├─ mock_server.py       # Fake API for UI development
│   ├─ test_extract.py
│   ├─ test_llm.py
│   ├─ test_claims.py
│   ├─ test_verify.py
│   ├─ test_api.py
│   └─ startup_check.py     # Quick sanity‑check on first run
├─ tests/                   # Pytest suite (unit & integration tests)
├─ .env.example             # Template for required env vars
├─ requirements.txt          # Pinned Python dependencies
├─ SPEC.md                  # Source of truth for architecture & contracts
├─ CLAUDE.md                # Agent instructions (this file)
└─ README.md                # **You are reading it now**
```

---

## 8. Known Limitations & Future Work

- **OCR**: RapidOCR defaults to English/Chinese; other languages may be missed.
- **LLM strength**: The bundled 3B local model is weaker than cloud providers for nuanced claim judgment.
- **Search coverage**: DuckDuckGo returns a limited set of results; some claims will be reported as `unverified` rather than false.
- **Media size limits** (see `app/interfaces.py`):
  - Video length ≤ **`MAX_VIDEO_SECONDS`** (`90` s)
  - Video size ≤ **`MAX_VIDEO_MB`** (`100` MiB)
  - Max claims per request ≤ **`MAX_CLAIMS`** (`6`)
  - Max text characters ≤ **`MAX_TEXT_CHARS`** (`5000`)

---

## 9. Contributing

Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch.
3. Ensure the test suite passes (`pytest`).
4. Open a pull request with a clear description of the change.

---

## 10. License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

*Generated with **Claude Code** – https://claude.com/claude-code*