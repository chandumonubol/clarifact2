# ClariFact — Agent Prompts (paste-ready)

Two agents, two folders, two branches. You paste one block at a time and wait for the agent to finish.
Everything in a gray code block is meant to be copied exactly.

| Lane | Tool | Folder | Branch |
|---|---|---|---|
| **B Brain** | Claude Code (on Ollama) | `C:\projects\clarifact-brain` | `feat/brain` |
| **C Media** | OpenCode | `C:\projects\clarifact-media` | `feat/media` |

Step order: **Brain** B1 → B2 → B3 → B4 → (merge) → B5 → B6 → B7 → (merge) → B8.
**Media** C1 → C2 → C3 → (merge) → C4 → C5 → (merge) → C6.
The ROADMAP.md tells you *when* to paste each one and how to test it.

General rules for you:
- Paste the **session opening** first in every new session, wait for the agent's 5 bullets, then paste the step.
- One step at a time. If an agent says "done", run the test command yourself.
- If an agent starts editing files it doesn't own, stop it, run `git checkout -- <file>` in its folder, and paste the opening again.
- If a step is too big for the agent (it loops, forgets, or half-finishes), say: `Do only part (1) of this step now, then stop.` and continue with part (2) afterwards.

---

## Session opening — Brain (Claude Code)

```
Read CLAUDE.md, SPEC.md and app/interfaces.py fully, in that order.

You are the BRAIN agent, working in the git worktree C:\projects\clarifact-brain on branch feat/brain.

You own ONLY these files (create/edit nothing else):
app/config.py, app/llm.py, app/claims.py, app/verify.py, app/scoring.py, app/pipeline.py, app/stubs.py, app/schemas.py, app/main.py, app/download.py,
scripts/test_llm.py, scripts/test_claims.py, scripts/test_verify.py, scripts/test_api.py, scripts/test_download.py, scripts/run_samples.py,
tests/*

Never edit: app/interfaces.py, requirements.txt, SPEC.md, CLAUDE.md, AGENTS.md, .env.example, static/*, app/extract.py (another agent owns static/ and extract.py and works in a different folder at the same time).

Always run Python with C:\projects\clarifact\.venv\Scripts\python.exe (shared venv). Environment variable names come from .env.example. If you need a new package or a change to app/interfaces.py, STOP and tell me instead of doing it.

When a step is done: run git add -A and git commit -m "<step>: <what works>", then tell me (a) files created/changed, (b) the exact test command, (c) the expected output, (d) anything that does not work yet. Then stop and wait for my next step.

First, confirm in exactly 5 bullets what you understood (your files, the files you must never touch, the Python path, the commit rule, what you do when you need a package). Then wait.
```

## Session opening — Media (OpenCode)

```
Read AGENTS.md, SPEC.md and app/interfaces.py fully, in that order.

You are the MEDIA agent, working in the git worktree C:\projects\clarifact-media on branch feat/media.

You own ONLY these files (create/edit nothing else):
static/index.html, static/style.css, static/app.js, scripts/mock_server.py, app/extract.py, scripts/test_extract.py, scripts/startup_check.py, README.md

Never edit: app/interfaces.py, requirements.txt, SPEC.md, CLAUDE.md, AGENTS.md, .env.example, and any other file under app/ (another agent owns the rest of app/ and works in a different folder at the same time).

Always run Python with C:\projects\clarifact\.venv\Scripts\python.exe (shared venv). Environment variable names come from .env.example. In extract.py read settings with os.getenv (do not import app.config; it does not exist in your branch). If you need a new package or a change to app/interfaces.py, STOP and tell me instead of doing it.

When a step is done: run git add -A and git commit -m "<step>: <what works>", then tell me (a) files created/changed, (b) the exact test command, (c) the expected output, (d) anything that does not work yet. Then stop and wait for my next step.

First, confirm in exactly 5 bullets what you understood (your files, the files you must never touch, the Python path, the commit rule, what you do when you need a package). Then wait.
```

---

# LANE B — BRAIN (Claude Code)

## B1 — Config + LLM layer

```
Step B1: config and LLM layer.

1. Create app/config.py: load .env with python-dotenv (look for .env in the repo root, i.e. the parent of app/) and expose a Settings object or module-level values for: LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL, GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_MODEL, FACTCHECK_API_KEY. Defaults: LLM_PROVIDER=ollama, OLLAMA_URL=http://localhost:11434, OLLAMA_MODEL=qwen2.5:3b. Do not print keys.

2. Create app/llm.py with exactly one public function:
   llm_json(prompt: str, schema_hint: str = "") -> dict
   - Uses plain httpx (no vendor SDKs). Provider is chosen by LLM_PROVIDER.
   - ollama: POST {OLLAMA_URL}/api/generate with {"model": OLLAMA_MODEL, "prompt": ..., "stream": false, "format": "json"}; read the "response" field.
   - gemini: REST generateContent for GEMINI_MODEL with the API key, generationConfig.responseMimeType = "application/json"; read candidates[0].content.parts[0].text.
   - groq: POST https://api.groq.com/openai/v1/chat/completions (OpenAI style) with GROQ_MODEL, response_format {"type":"json_object"}; read choices[0].message.content.
   - Timeouts: 120 s for ollama, 40 s for cloud providers.
   - If schema_hint is non-empty, append it to the prompt as "Return ONLY JSON matching this shape: <schema_hint>".
   - Strip ``` code fences, parse JSON. On parse failure retry ONCE with a stricter instruction ("Return only valid JSON, no explanation"). After a second failure log it and return {}.
   - If a cloud provider raises an error, times out or returns HTTP 429, log a warning (no keys in the log) and fall back to Ollama for that call.
   - Never raise to the caller: return {} on total failure.

3. Create scripts/test_llm.py: usage `python scripts/test_llm.py "<prompt>"`. It prints which provider was used, latency in seconds, and the parsed JSON. It must work when run from the repo root.

Acceptance test (run it and show me the output):
  C:\projects\clarifact\.venv\Scripts\python.exe scripts\test_llm.py "Return JSON {\"ok\": true}"
Expected: provider name, a latency, and {'ok': True}.
If Ollama is not reachable, the script must print a clear message, not a traceback.
```

## B2 — Claims + promo detection

```
Step B2: claims and promo detection. Create app/claims.py with
  analyze(content: ExtractedContent) -> Signals
using the types from app/interfaces.py.

1. Build one input string from content["text"], content["transcript"], content["ocr_text"], each labelled (TEXT:, SPEECH:, ON-SCREEN TEXT:). If everything is empty return an empty Signals (claims [], promo none) with the warning "No content to analyze".

2. Make ONE llm_json call. Use this prompt structure (you may improve wording but keep the JSON shape):
   "You analyze short-form social media videos. From the content below extract:
    1) claims: up to 6 CHECKABLE FACTUAL claims (health, money, product performance, statistics, 'scientists say'). Each claim must be short and self-contained. Skip opinions, jokes, greetings.
    2) hidden_promo: true if the speaker is pushing a product/service/brand without clearly saying it is sponsored, else false; plus a one-sentence reason.
    3) red_flags: any of: miracle or guaranteed results, false urgency, 'doctors hate this', fake authority, cherry-picked statistics, too-good-to-be-true numbers.
    Return ONLY JSON: {\"claims\": [\"...\"], \"hidden_promo\": {\"value\": true, \"reason\": \"...\"}, \"red_flags\": [\"...\"]}
    CONTENT: ..."

3. Deterministic promo rules in this file (case-insensitive substring match):
   DISCLOSURE_KEYWORDS = ["#ad", "#sponsored", "paid partnership", "sponsored by", "in collaboration with"]
   COMMERCIAL_KEYWORDS = ["use code", "discount code", "link in bio", "affiliate", "% off", "dm me", "free trial", "limited offer", "buy now"]
   Combine: a disclosure keyword found -> promo type "disclosed", detected True; else a commercial keyword found OR the LLM says hidden_promo.value is true -> type "hidden", detected True; else type "none", detected False. promo["evidence"] = the matched keyword snippets or quotes plus the LLM reason.

4. Dedupe claims (case-insensitive), cap at MAX_CLAIMS, drop empty strings. Robust to the LLM returning {} or wrong types (then use empty claims and add a warning).

5. Create scripts/test_claims.py: `python scripts/test_claims.py "<text>"` builds an ExtractedContent with that text and prints the Signals as pretty JSON.

Acceptance tests (run and show output):
  test_claims.py "This pill melts belly fat in 3 days, doctors hate it! Use code FIT20 for 50% off"
  -> 1-2 claims, promo type "hidden", red_flags non-empty.
  test_claims.py "#ad I really love this moisturizer, link in bio"
  -> promo type "disclosed".
  test_claims.py "Today I went to the park and had a sandwich"
  -> claims empty or trivial, promo "none".
```

## B3 — Verification with web evidence

```
Step B3: verification. Create app/verify.py with
  verify_claim(claim_text: str) -> VerifiedClaim
using the types from app/interfaces.py. It must NEVER raise.

1. Queries: one small llm_json call asking for 1-2 short web search queries for the claim ({"queries": ["..."]}); if it fails use the claim text itself.

2. Evidence gathering, each part wrapped in try/except with timeouts:
   a) ddgs: DDGS().text(query, max_results=5) for each query (retry once on exception, small sleep). Keep title, url, snippet.
   b) Wikipedia: MediaWiki search API for the claim keywords, then the REST page summary of the top hit. Keep as an evidence item with its URL.
   c) Google Fact Check Tools API ONLY if FACTCHECK_API_KEY is set.
   Deduplicate by URL. Build a numbered list of evidence items [1]..[n] and trim the total text to about 1500 characters (each snippet cut to ~250 chars).

3. If there are no evidence items: return verdict "unverified", explanation "No usable evidence found.", sources [], had_evidence False.

4. Otherwise make ONE llm_json call:
   "Claim: <claim>
    Evidence (numbered): [1] <title> - <snippet> ...
    Using ONLY this evidence, decide: supported, contradicted, misleading (partly true but exaggerated or missing context), or unverified (evidence does not decide it).
    Return ONLY JSON: {\"verdict\": \"supported|contradicted|misleading|unverified\", \"explanation\": \"max 2 sentences\", \"used_sources\": [1, 3]}"
   Validate the verdict against VERDICTS (anything else -> "unverified"). sources = the evidence items whose numbers are in used_sources (title+url), never invented URLs. If used_sources is empty but the verdict is not "unverified", use the top 2 items. had_evidence = True.

5. On any unexpected failure return verdict "unverified", an explanation that says why, had_evidence False.

6. Create scripts/test_verify.py: `python scripts/test_verify.py "<claim>"` prints the VerifiedClaim as pretty JSON.

Acceptance tests (run and show output):
  "Drinking hot water cures diabetes" -> contradicted (or misleading) with real source URLs.
  "Water boils at 100 degrees Celsius at sea level" -> supported.
  "The moon is made of cheese" -> contradicted.
  With Wi-Fi off it must return unverified without crashing (tell me if you could not test this).
```

## B4 — Scoring, pipeline, API

```
Step B4: scoring, pipeline, stubs, API. Do these in order and commit after part (3).

(1) app/scoring.py: score(claims: list[VerifiedClaim], promo: PromoInfo, red_flags: list[str]) -> ScoreResult exactly per the Scoring rules in SPEC.md: start 100; contradicted -25, misleading -15, unverified -5 per claim; hidden promo -20; disclosed promo -5; each red flag -5 capped at -20 total; clamp 0-100. Labels use LABEL_CREDIBLE (>=75), LABEL_CAUTION (50-74), LABEL_MISLEADING (<50) from app/interfaces.py. confidence: share of claims with had_evidence >= 0.7 high, >= 0.4 medium, else low; no claims -> low.
    tests/test_scoring.py runnable as `python tests/test_scoring.py` with plain asserts: all supported -> 100 Credible; one contradicted + hidden promo -> 55 Use caution; five contradicted -> clamps at 0 and Likely misleading; no claims -> 100 with confidence low.

(2) app/stubs.py: canned stand-ins returning exact shapes from app/interfaces.py for extract_from_text, extract_from_image, extract_from_video and download_from_url (e.g. transcript "This is a stub transcript. This pill cures diabetes in 3 days.").

(3) app/pipeline.py: run_pipeline(text: str | None, file_path: str | None, url: str | None, progress: ProgressFn) -> AnalysisResult.
    - Input handling: url -> download_from_url(url, "tmp") then treat as video; file_path extension decides: .mp4 .mov .mkv .webm = video, .jpg .jpeg .png .webp = image, .txt = read as text; text alone = text. If both text and a file/url are given, put the typed text into content["text"] of the extracted content.
    - progress(...) steps: "Extracting audio" etc. come from the extractor itself; you call progress("Finding claims"), progress(f"Checking claim {i} of {n}"), progress("Scoring").
    - Flow: extract -> claims.analyze -> verify_claim for each claim -> scoring.score -> build AnalysisResult per SPEC.md (claims WITHOUT had_evidence; include transcript, ocr_text, promo, red_flags, merged warnings from every stage).
    - Wrap every stage in try/except: add a warning and continue with whatever exists. Never raise.
    - Import real modules with a fallback to stubs, one try/except per module, e.g.
        try: from app.extract import extract_from_video
        except ImportError: from app.stubs import extract_from_video
      (same for extract_from_image, extract_from_text, download_from_url). Log at startup which implementation each function uses ("real" or "stub").

(4) app/schemas.py (pydantic models mirroring JobStatus and AnalysisResult) and app/main.py (FastAPI):
    - POST /analyze (multipart: text, file, url) -> {"job_id"}. Save uploaded files under tmp/ with a safe unique name; reject files over 100 MB or unsupported extensions with HTTP 400 and a friendly message.
    - GET /jobs/{id} returns JobStatus exactly as in app/interfaces.py. Jobs are kept in an in-memory dict; each runs in a background thread calling run_pipeline with a progress callback that updates job["step"]. On exception set status "error" with a friendly message.
    - GET /health -> {"ok": true}.
    - If a static/ folder exists next to app/, serve it at "/" (StaticFiles with html=True); otherwise GET / returns a small "UI not merged yet" HTML page.
    - Clean up temp files after the job finishes.

(5) scripts/test_api.py: `python scripts/test_api.py "<text>"` (and later `--file <path>`) posts to http://localhost:8000/analyze, polls /jobs/{id} every second printing the step, then prints the final JSON.

Acceptance tests (run and show output):
  python tests/test_scoring.py -> all asserts pass.
  Start the server: C:\projects\clarifact\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
  In another terminal: python scripts\test_api.py "Drinking hot water cures diabetes"
  Expected: steps like "Finding claims", "Checking claim 1 of 1", "Scoring", then a full result JSON with a real verdict and a score below 100. Extraction uses stubs for now and the startup log says so.
```

## B5 — Integration check (after Checkpoint 1)

```
Step B5: integration check. The branch feat/media has been merged into your branch, so app/extract.py and static/ now exist here.

1. Start the app and confirm the startup log now shows "real" for extract_from_text, extract_from_image and extract_from_video (download_from_url is still a stub).
2. Extend scripts/test_api.py with `--file <path>` and use it to test: a text-only input, an image from C:\clarifact-samples, and a video from C:\clarifact-samples. Show me each result's step sequence and the final score/label.
3. Open http://localhost:8000 logic check: confirm GET / serves static/index.html and that the fields the UI expects (see AnalysisResult in app/interfaces.py) are all present in a real result.
4. Fix problems ONLY in your own files. If something is wrong in app/extract.py or static/*, do NOT edit it: write a bug report with the file, function, input, actual output and expected output so I can hand it to the other agent.
```

## B6 — Link download (cut this first if time is short)

```
Step B6: link download. Create app/download.py with
  download_from_url(url: str, dest_dir: str) -> str
using yt-dlp's Python API (import yt_dlp).
- Format: best[height<=720][ext=mp4]/best[height<=720]/best. Output template inside dest_dir with a unique id.
- Before downloading, extract_info(download=False) and reject videos longer than MAX_VIDEO_SECONDS (from app/interfaces.py) with ValueError("That video is longer than 90 seconds. Please use a shorter clip.").
- Return the local file path of the downloaded video.
- Convert yt-dlp failures (private, unsupported site, network, login required) into ValueError with a friendly message that suggests uploading the video file instead. Never leak stack traces to the user.
- Make sure app/pipeline.py imports download_from_url from app.download (keep the stub fallback).
- Create scripts/test_download.py: `python scripts/test_download.py <url>` prints the saved path.

Acceptance: a YouTube Shorts URL gives a playable mp4; a garbage URL prints a friendly message; an Instagram URL may fail and that is acceptable.
```

## B7 — Sample runner

```
Step B7: evaluation runner. Create scripts/run_samples.py.
- Folder: env SAMPLES_DIR or default C:/clarifact-samples. Read expected.json there: a list of {"file", "expect_label", "expect_promo", "notes"}.
- For each entry call app.pipeline.run_pipeline(text, file_path, None, progress): files ending in .txt are read and passed as text; everything else as file_path. Catch exceptions per sample and record them as FAIL with the error.
- Print a table: file | expected label | actual label | expected promo | actual promo | score | seconds | PASS/FAIL. PASS means label AND promo type both match.
- Write samples_report.md in the repo root: the table, the pass count, and for every FAIL the transcript, OCR text, claims with verdicts and the promo evidence.
- Run sequentially (low RAM). Print progress per sample.

Acceptance: run it on whatever samples exist and show me the table and pass count.
```

## B8 — Fixes from the report

```
Step B8: fix these failures by tuning prompts, rules and evidence handling in YOUR files only.

Failures from samples_report.md:
<paste the failing rows with the transcript/claims here>

Rules:
- First re-run scripts/run_samples.py and note the baseline pass count.
- Make the smallest change that fixes a failure (prompt wording, keyword lists, evidence trimming, verdict thresholds in the prompt). Do not change scoring weights unless I say so.
- Do not introduce false positives: these neutral texts must still give promo "none" and no claims marked contradicted:
<paste 3-5 neutral example texts here>
- Re-run run_samples.py after each change, and tell me the before/after pass count.
```

---

# LANE C — MEDIA (OpenCode)

## C1 — UI + mock server

```
Step C1: Gemini-style UI and a mock server. Plain HTML/CSS/vanilla JS only: no npm, no React, no CDN dependencies, no build step.

Look (if reference/gemini.png exists and you can view images, match it; otherwise follow this):
- Dark theme, page background #131314, subtle deep-blue radial glow in the center. Font: system UI stack. Rounded corners everywhere.
- Left sidebar (dark, ~260 px): app name "ClariFact" with a small spark icon, a "New chat" button, a "Recent" list of past analyses (in memory only; clicking one shows its saved result), a small footer note.
- Home view: centered heading "Where should we start?" (large, light weight), under it a wide rounded pill input bar with: a "+" button on the left that opens a file picker (images and videos), a text input with placeholder "Paste a claim, caption, or link…", and a round send button on the right. Enter sends (Shift+Enter = newline). Under the bar a small grey line: "ClariFact can make mistakes. Verify important information."

Behaviour:
- On send: build FormData with `text` (the typed text, unless it starts with http, in which case send it as `url`) and `file` (if attached). POST /analyze, then poll GET /jobs/{job_id} every 1000 ms.
- Switch to a chat-like view: the user's message bubble (text and file name; show an image thumbnail for images), then a live progress line showing the `step` text with a small animated spinner.
- When status is "done" render result cards from `result` (shape in app/interfaces.py: AnalysisResult):
  1. Score ring (SVG circle, 0-100) with the label and a confidence chip. Ring color: green for Credible, amber for Use caution, red for Likely misleading.
  2. Promotion banner: type hidden = red-ish, disclosed = amber, none = neutral; list promo.evidence.
  3. Claims list: each with a colored verdict chip (supported green, contradicted red, misleading amber, unverified grey), the claim text, the explanation, and a collapsible "Sources" list of links (open in a new tab).
  4. Red flag chips.
  5. Collapsible "Transcript" and "On-screen text" sections.
  6. Warnings (if any) in a subtle box.
- When status is "error" show the error text in a friendly red card with a "Try again" button. Network failures also show a friendly message.
- Escape all text before inserting into the DOM (use textContent); never inject server text as HTML.
- Must be usable at 1366x768.

Mock server: create scripts/mock_server.py, a FastAPI app that serves the ../static folder at "/" and implements POST /analyze and GET /jobs/{id} exactly as the contract in SPEC.md and app/interfaces.py (JobStatus). Each job walks through 5 fake steps (about 1 second each: "Extracting audio", "Transcribing speech", "Finding claims", "Checking claim 1 of 3", "Scoring") and returns a hardcoded sample AnalysisResult with: score 38, label "Likely misleading", confidence "medium", promo hidden with 2 evidence strings, 3 claims with verdicts contradicted / misleading / supported (each with 1-2 sources), 2 red flags, a short transcript, some OCR text, and one warning. Accept an optional --port argument (default 8001).

Acceptance (run and tell me exactly how you tested):
  C:\projects\clarifact\.venv\Scripts\python.exe scripts\mock_server.py
  Open http://localhost:8001, type anything, press Enter -> progress steps change every second -> all six card types render. Attach a file -> its name shows. Check that the three verdict colors are visibly different.
```

## C2 — Video extraction

```
Step C2: video extraction. In app/extract.py implement
  extract_from_video(path: str, progress: ProgressFn | None = None) -> ExtractedContent
using the types and constants (MAX_VIDEO_SECONDS, MAX_VIDEO_MB) from app/interfaces.py. Read settings with os.getenv (do not import app.config).

1. Validate: file exists; size <= MAX_VIDEO_MB; duration via ffprobe <= MAX_VIDEO_SECONDS. Otherwise raise ValueError with a friendly message (e.g. "That video is longer than 90 seconds. Please use a shorter clip.").
2. Work in a temp directory (tempfile) that is ALWAYS deleted in a finally block.
3. progress("Extracting audio"): ffmpeg to 16 kHz mono wav. If there is no audio track, set transcript "" and add a warning, continue.
4. progress("Transcribing speech"): faster-whisper WhisperModel(os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8"). Load it lazily ONCE into a module-level variable (thread-safe with a lock). Call transcribe with vad_filter=True and task=os.getenv("WHISPER_TASK", "translate"). Join segment texts. Log the detected language and the time taken.
5. progress("Reading on-screen text"): ffmpeg frames at 1 frame per 2 seconds, at most 20 frames, scaled so the long side is at most 960 px. Run RapidOCR (from rapidocr_onnxruntime import RapidOCR; create the engine lazily once) on each frame, collect text lines, dedupe repeated lines (case-insensitive) preserving order, drop lines shorter than 3 characters.
6. Every sub-step failure becomes an entry in warnings, never a crash. Return {"text": "", "transcript": ..., "ocr_text": ..., "warnings": [...]}.
7. Use subprocess with a timeout for ffmpeg/ffprobe calls and capture stderr for the warning text.

Create scripts/test_extract.py: `python scripts/test_extract.py <video>` prints the transcript, the OCR text, the warnings and the seconds each stage took.

Acceptance (run on a 15-30 s video from C:\clarifact-samples and show the output): readable transcript, OCR lines for any captions, total time printed. Then run it on a silent video or an audio-less file and show that it gives a warning, not a crash.
```

## C3 — Image + text extraction

```
Step C3: add to app/extract.py (do not change extract_from_video's behavior):
  extract_from_image(path: str, progress: ProgressFn | None = None) -> ExtractedContent
  extract_from_text(text: str) -> ExtractedContent
- Image: supported extensions .jpg .jpeg .png .webp, otherwise raise ValueError("Unsupported image format."). Read with cv2; if the long side is over 1600 px, downscale. progress("Reading on-screen text") then RapidOCR (reuse the same lazily created engine as the video code). Dedupe lines. Return transcript "".
- Text: strip, trim to MAX_TEXT_CHARS, return {"text": ..., "transcript": "", "ocr_text": "", "warnings": []}.
- Extend scripts/test_extract.py so it chooses image vs video by file extension.

Acceptance: run on a screenshot/ad image and show the OCR text; run on a large phone photo (several MB) and show it still works; run with a .gif and show the friendly error.
```

## C4 — UI polish (after Checkpoint 1)

```
Step C4: polish the UI only. Do not change any backend file or the API contract. Use scripts/mock_server.py to test.
- Animated score ring (counts up from 0, about 800 ms).
- Verdict chips and banners with consistent colors and good contrast on the dark theme.
- Sidebar history: each analysis gets a short title (first ~30 characters of the input or the file name); clicking restores that result; "New chat" returns to the home view.
- Show a thumbnail (images) or a video icon + file name for the user's attachment.
- Loading skeleton cards while waiting; spinner next to the step text.
- Three "Try an example" chips under the input bar that fill the input with sample claims: "This herbal tea cures diabetes in 7 days, doctors hate it!", "Use code FIT20 for 50% off my new protein powder, link in bio", "Drinking enough water helps maintain healthy kidney function."
- An expandable "How we score" panel under the score ring: start at 100, minus 25 per contradicted claim, 15 per misleading, 5 per unverified, 20 for hidden promotion, 5 for disclosed promotion, 5 per red flag (max 20); label thresholds 75 and 50.
- Smooth fade-in for result cards, visible keyboard focus, responsive down to 1280 px width, a minimal mobile layout (sidebar collapses).
- Keep everything dependency-free.
Acceptance: run the mock server, test the three example chips, a file attach, history restore, and "New chat". Tell me exactly what you checked.
```

## C5 — Startup check + speed

```
Step C5: two tasks, commit after each.

(1) scripts/startup_check.py: print one PASS/FAIL line each for: ffmpeg on PATH, ffprobe on PATH, Ollama reachable at OLLAMA_URL and OLLAMA_MODEL present in /api/tags, Whisper model path (WHISPER_MODEL) exists or is a known size name, an API key present for the selected LLM_PROVIDER (PASS with "not needed" for ollama), a ddgs test query returns at least one result, RapidOCR imports. Load settings with python-dotenv from the repo root .env. End with "All checks passed" or "N checks failed". Never print keys.

(2) Speed: instrument extract_from_video to log seconds per stage (audio, whisper, frames, OCR). Measure on a 30 s sample from C:\clarifact-samples, then reduce latency without losing accuracy: for example fewer frames, skip OCR on near-identical consecutive frames (cheap pixel-difference check), keep the models loaded between calls, set whisper beam_size=1. Report before/after seconds for each stage. Keep the earlier acceptance tests passing.
```

## C6 — Final fixes + README

```
Step C6: two tasks.

(1) Fix the extraction/UI problems listed here (leave empty if none):
<paste bug reports here>
Make the smallest change that fixes each, and re-run scripts/test_extract.py and the mock server to confirm.

(2) Write README.md for a final-year project report appendix: what ClariFact is; architecture in 5 lines; setup from a clean Windows machine (Python 3.11/3.12, ffmpeg via winget, Ollama + `ollama pull qwen2.5:3b`, Whisper model download with huggingface_hub snapshot_download('Systran/faster-whisper-small', local_dir=...), copy .env.example to .env and fill it); how to run (`python -m uvicorn app.main:app --port 8000` then open http://localhost:8000); how to switch LLM provider; how to run scripts/startup_check.py; known limitations (OCR languages, small-model accuracy, search coverage); and a short "How the score works" section. No marketing language.
```
