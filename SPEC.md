# ClariFact — SPEC (source of truth)

Detects misleading claims and hidden promotions in short-form content (reels/shorts).
Input: text, image, video file, or (stretch) a Shorts/Reel link.
Output: a credibility analysis with per-claim verdicts and sources.

Scope: working local demo only. No hosting, no accounts, no paid services.
All data shapes, constants and function signatures live in `app/interfaces.py`.
That file wins over this one if they ever disagree.

## Stack (do not add anything else without asking the human)
- Python 3.11/3.12, FastAPI, uvicorn, pydantic, python-dotenv, httpx
- Frontend: plain HTML + CSS + vanilla JS in `static/`, served by FastAPI (NO React, NO npm)
- Speech: faster-whisper (multilingual `small`, CPU, int8)
- OCR: rapidocr-onnxruntime
- Frames/audio: ffmpeg + ffprobe (system binaries)
- Search: `ddgs` (no key) + Wikipedia API; optional Google Fact Check Tools API if key set
- LLM: provider switch via `.env` (ollama | gemini | groq), plain httpx, no vendor SDKs
- Link download (stretch): yt-dlp

## Folder layout and ownership
```
clarifact/
  app/
    interfaces.py    # HUMAN ONLY: shapes, constants, signatures
    config.py        # [Brain] env loading
    llm.py           # [Brain] llm_json(); the ONLY module that talks to an LLM
    claims.py        # [Brain] claims + promo + red flags
    verify.py        # [Brain] web evidence + verdict
    scoring.py       # [Brain] deterministic score
    pipeline.py      # [Brain] orchestration run_pipeline()
    stubs.py         # [Brain] canned stand-ins until real modules are merged
    schemas.py       # [Brain] pydantic models mirroring interfaces.py
    main.py          # [Brain] FastAPI routes + background jobs
    download.py      # [Brain] yt-dlp link download
    extract.py       # [Media] video/image/text -> ExtractedContent
  static/            # [Media] index.html, style.css, app.js
  scripts/
    mock_server.py   # [Media] serves static/ + fake API for UI development
    test_extract.py, startup_check.py             # [Media]
    test_llm.py, test_claims.py, test_verify.py,
    test_api.py, test_download.py, run_samples.py # [Brain]
  tests/             # [Brain]
  .env  .env.example  CLAUDE.md  AGENTS.md  SPEC.md  README.md [Media]  requirements.txt
```

## API contract (types in interfaces.py: JobStatus, AnalysisResult)

`POST /analyze` — multipart form: `text` (optional str), `file` (optional upload), `url` (optional str)
→ `{"job_id": "abc123"}`

`GET /jobs/{job_id}` — the UI polls once per second
```json
{
  "status": "queued|running|done|error",
  "step": "Extracting audio | Transcribing speech | Reading on-screen text | Finding claims | Checking claim 2 of 5 | Scoring",
  "result": null,
  "error": null
}
```
When `status == "done"`, `result` is:
```json
{
  "credibility_score": 0,
  "label": "Credible | Use caution | Likely misleading",
  "confidence": "low | medium | high",
  "promo": {"detected": true, "type": "hidden | disclosed | none", "evidence": ["quote or reason"]},
  "claims": [
    {
      "text": "claim as stated in the content",
      "verdict": "supported | contradicted | misleading | unverified",
      "explanation": "1-2 sentences, based only on the evidence",
      "sources": [{"title": "", "url": ""}]
    }
  ],
  "red_flags": ["miracle cure language", "false urgency"],
  "transcript": "",
  "ocr_text": "",
  "warnings": ["any stage that failed or was skipped"]
}
```

## Pipeline
1. **extract** → `ExtractedContent{text, transcript, ocr_text, warnings}`
   - video: ffprobe validation (≤ 90 s, ≤ 100 MB) → ffmpeg 16 kHz mono wav → faster-whisper (`vad_filter=True`, `task` from `WHISPER_TASK`, default `translate` so Hindi/Kannada/Hinglish speech comes out in English); ffmpeg frames at 1 per 2 s (max 20) → RapidOCR, dedupe repeated lines
   - image: RapidOCR (downscale if long side > 1600 px)
   - text: passthrough (trim to 5000 chars)
2. **claims.analyze** → `Signals`
   - One LLM call, JSON out. Max 6 claims. Only *checkable factual* claims (health, money, product performance, statistics, "scientists say"). Skip opinions and jokes.
   - Promo rules (deterministic): disclosure keywords (#ad, #sponsored, paid partnership, sponsored by, in collaboration with) → `disclosed`; commercial keywords (use code, discount code, link in bio, affiliate, % off, DM me, free trial, limited offer, buy now) or LLM says hidden → `hidden`; else `none`.
   - Red flags: miracle/guaranteed language, false urgency, "doctors hate this", fake authority, cherry-picked statistics.
3. **verify.verify_claim** → `VerifiedClaim`
   - 1–2 search queries → ddgs top 5 + Wikipedia intro (+ Fact Check API if key). Evidence trimmed to ~1500 characters, numbered `[1]..[n]`.
   - LLM judges using ONLY the numbered evidence and returns which evidence numbers it used. Sources are taken from those evidence items. No evidence → `unverified`, `had_evidence=False`. Never invent URLs.
4. **scoring.score** — deterministic, no LLM:
   - start 100; contradicted −25, misleading −15, unverified −5 (each claim)
   - hidden promo −20, disclosed promo −5
   - each red flag −5 (cap −20)
   - clamp 0–100. Label: ≥ 75 Credible, 50–74 Use caution, < 50 Likely misleading.
   - confidence = share of claims with `had_evidence`: ≥ 0.7 high, ≥ 0.4 medium, else low (no claims → low).
5. **pipeline.run_pipeline** glues steps 1–4 and builds the `AnalysisResult` (removes `had_evidence`).

## LLM provider (config only; names from `.env.example`)
```
LLM_PROVIDER=ollama            # ollama | gemini | groq
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
GEMINI_API_KEY=   GEMINI_MODEL=
GROQ_API_KEY=     GROQ_MODEL=
FACTCHECK_API_KEY=             # optional
WHISPER_MODEL=C:/clarifact-models/faster-whisper-small
WHISPER_TASK=translate
```
`llm_json(prompt, schema_hint)` must: request JSON, strip code fences, retry once on parse failure, return `{}` + log on second failure. If a cloud provider errors or rate-limits, fall back to Ollama and log a warning.

## Robustness rules
- Every stage is wrapped: on failure add to `warnings` and continue with what exists. The API must never 500 on bad content.
- Limits: video ≤ 90 s and ≤ 100 MB; reject otherwise with a clear message.
- Run stages sequentially (low RAM). Load Whisper once, lazily, at first use.
- Never print API keys. Never commit `.env`.

## UI (Gemini-style; reference image: `reference/gemini.png`)
- Dark theme (#131314 base, soft blue radial glow), left sidebar: app name ClariFact, New chat, history list (in memory).
- Home: centered heading "Where should we start?" and a rounded pill input bar: `+` (attach image/video), text box "Paste a claim, caption, or link…", send button.
- After submit: chat-like view: user message (text + filename/thumbnail), a live progress line (`step`), then result cards:
  1. Score ring (0–100) + label + confidence
  2. Promotion banner (hidden/disclosed/none) with evidence
  3. Claims list: verdict chip (supported green, contradicted red, misleading amber, unverified grey), explanation, collapsible sources
  4. Red flag chips
  5. Collapsible transcript + OCR text, and warnings if any
  6. Small "How we score" expandable panel
- Friendly error states. Works on a 1366×768 laptop screen. Footer: "ClariFact can make mistakes. Verify important information." (do NOT claim data stays local when a cloud LLM is configured)

## Known limitations (state them in the report)
- RapidOCR default models read English/Chinese text; Hindi/Kannada on-screen text is not read.
- A 3B local model is weaker than a cloud model at judging claims.
- Search coverage is limited; unverifiable claims are reported as `unverified`, not false.

## Definition of done
- 3 demo inputs (one video, one image, one text) each return a sensible result in ~90 s or less on the laptop.
- Cloud API key optional: with it off, everything still works locally.
- README with setup steps from a clean machine.
