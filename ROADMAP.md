# ClariFact — Your Roadmap (what YOU do, and when)

Budget: 10 hours. **T+0:00 = the moment you start Phase 1.**
Work only in `C:\projects\...` (never inside OneDrive: it syncs the venv and models and breaks Git).
All commands are for **PowerShell** (Start menu → type PowerShell).

Files that go with this roadmap (download them all from the chat):
`ROADMAP.md` (this) · `AGENT_PROMPTS.md` · `SPEC.md` · `CLAUDE.md` · `interfaces.py` · `gemini_reference.png`

## The picture in 30 seconds

```
C:\projects\clarifact          <- MAIN folder. No agent works here. You merge and run the finished app here.
C:\projects\clarifact-brain    <- Claude Code works here (branch feat/brain): AI logic, API, scoring, pipeline
C:\projects\clarifact-media    <- OpenCode works here (branch feat/media): UI, video/image extraction
```
They never edit the same files, so merging is boring. You are the integrator and the tester.

## Timeline at a glance

| Time | Phase | Your main job |
|---|---|---|
| 0:00–0:30 | **1. Skeleton** | Clean start, files, git, worktrees, start the venv install |
| 0:30–0:45 | **2. Launch agents** | Start both agents, paste opening + first prompts |
| 0:45–3:00 | **3. Wave 1** (agents: B1–B4, C1–C3) | Environment + models + samples in parallel, test each step |
| **3:00** | **Checkpoint 1** | Merge, full test of text / image / video |
| 3:15–5:15 | **4. Wave 2** (B5–B7, C4–C5) | Run sample runner, collect failures |
| **5:15** | **Checkpoint 2** | Merge, read `samples_report.md` |
| 5:30–8:00 | **5. Wave 3** (B8, C6) | Feed failures back, polish |
| **8:00** | **FEATURE FREEZE** | Final merge. Bug fixes only after this |
| 8:00–10:00 | **6. Demo prep** | Rehearse, screenshots, report, backup recording |

Running late? Cut in this order: **link download (B6)** → UI extras → polish. Never cut: text + video + scoring + UI.

---

# PHASE 1 — Skeleton (T+0:00 → 0:30)

### 1.1 Download the files (3 min)
Click each file card in this chat to download. Then find your real Downloads folder (yours is under OneDrive, so `$HOME\Downloads` does not exist):
```powershell
$dl = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path
$dl
dir $dl | Where-Object { $_.Name -match "ROADMAP|AGENT_PROMPTS|SPEC|CLAUDE|interfaces|gemini_reference" }
```
Old versions of `SPEC.md`, `CLAUDE.md`, `interfaces.py` from earlier in the chat may also be there. Chrome renames repeats as `SPEC (1).md`. Delete the **old** ones first so there is no confusion:
```powershell
Remove-Item "$dl\SPEC*.md","$dl\CLAUDE*.md","$dl\interfaces*.py","$dl\PROMPTS*.md","$dl\TWO_AGENT*","$dl\PARALLEL*" -ErrorAction SilentlyContinue
```
Then download the new files again from the chat and re-run the `dir` line. Keep this PowerShell window open: the variable `$dl` disappears when you close it.

### 1.2 Fresh project folder
If an old `C:\projects\clarifact` exists, move it aside first:
```powershell
if (Test-Path C:\projects\clarifact) { Rename-Item C:\projects\clarifact clarifact-old }
mkdir C:\projects\clarifact
cd C:\projects\clarifact
mkdir app, scripts, tests, reference
pwd
```
`pwd` must show `C:\projects\clarifact`.

### 1.3 Put the shared files in place
Use the exact file names `dir` showed you (adjust if Chrome added `(1)`):
```powershell
Copy-Item "$dl\SPEC.md" .
Copy-Item "$dl\CLAUDE.md" .
Copy-Item "$dl\CLAUDE.md" .\AGENTS.md
Copy-Item "$dl\ROADMAP.md" .
Copy-Item "$dl\AGENT_PROMPTS.md" .
Copy-Item "$dl\interfaces.py" .\app\interfaces.py
Copy-Item "$dl\gemini_reference.png" .\reference\gemini.png
New-Item app\__init__.py, scripts\__init__.py, tests\__init__.py -ItemType File
```
(`AGENTS.md` is the same text as `CLAUDE.md`: Claude Code reads one name, OpenCode the other.)

### 1.4 Create the three config files
Paste each block whole. The closing `'@` must be at the very start of its line.
```powershell
@'
fastapi
uvicorn[standard]
python-multipart
pydantic
python-dotenv
httpx
faster-whisper
rapidocr-onnxruntime
ddgs
yt-dlp
huggingface_hub
'@ | Set-Content requirements.txt -Encoding ascii
```
```powershell
@'
.venv/
__pycache__/
*.pyc
.env
tmp/
uploads/
models/
*.mp4
*.mov
samples_report.md
'@ | Set-Content .gitignore -Encoding ascii
```
```powershell
@'
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
GEMINI_API_KEY=
GEMINI_MODEL=
GROQ_API_KEY=
GROQ_MODEL=
FACTCHECK_API_KEY=
WHISPER_MODEL=C:/clarifact-models/faster-whisper-small
WHISPER_TASK=translate
'@ | Set-Content .env.example -Encoding ascii
Copy-Item .env.example .env
```
`LLM_PROVIDER` is `ollama`, `gemini` or `groq`. Keys come later.

### 1.5 Git, base commit and worktrees
```powershell
git --version
```
If "not recognized": `winget install Git.Git`, close PowerShell, reopen, `cd C:\projects\clarifact`.
```powershell
git init -b main
git config user.name "Chandu"
git config user.email "you@example.com"
git add -A
git commit -m "base: spec, rules, interfaces"
git status
git branch feat/brain
git branch feat/media
git worktree add ..\clarifact-brain feat/brain
git worktree add ..\clarifact-media feat/media
git worktree list
```
- `git init -b main` fails on very old Git: run `git init` then after the commit `git branch -M main`.
- "LF will be replaced by CRLF" warnings are harmless.
- `git worktree list` must show **3 lines**.

Copy `.env` into the two worktrees (Git does not carry it):
```powershell
Copy-Item .env ..\clarifact-brain\.env
Copy-Item .env ..\clarifact-media\.env
```

### 1.6 Start the Python environment installing (runs ~10 min while you continue)
Open a **second** PowerShell window:
```powershell
cd C:\projects\clarifact
py -0
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
- Use 3.11 if that is what you have (`py -3.11`). If no Python 3.11/3.12 is installed: `winget install Python.Python.3.12`, reopen PowerShell, retry.
- "running scripts is disabled": `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, reopen the window.
- Leave this window alone until it finishes. Then run:
  `python -c "import fastapi, faster_whisper, rapidocr_onnxruntime, ddgs, yt_dlp; print('imports ok')"`
  It must print `imports ok`.

**Checkpoint:** `git worktree list` shows 3 folders and the install is running. Go to Phase 2.

---

# PHASE 2 — Launch the agents (T+0:30 → 0:45)

### 2.1 Brain (Claude Code)
New PowerShell window:
```powershell
cd C:\projects\clarifact-brain
```
Start Claude Code the same way you did for Ollama. First message:
> What is your current working directory and git branch?

It must answer `clarifact-brain` and `feat/brain`. If not, quit and restart from the right folder.
Then open `AGENT_PROMPTS.md`, copy the block **Session opening — Brain**, paste it, and wait for its 5 bullets. Check that the bullets mention: its file list, the files it must not touch, the venv Python path, the commit rule, and "stop and ask if a package is needed". If it gets them wrong, tell it what is wrong.
Then paste **B1**.

### 2.2 Media (OpenCode)
New PowerShell window:
```powershell
cd C:\projects\clarifact-media
opencode
```
Same directory/branch question (`clarifact-media`, `feat/media`). Paste **Session opening — Media**, check the 5 bullets, then paste **C1**.

### Rules while agents work
- Approve file edits and commands inside their own folder. **Refuse** anything touching `C:\projects\clarifact` (main), `git push`, deleting folders outside their worktree, or installing packages.
- If an agent loops or ignores rules: restart its session, paste the opening again, and give a smaller piece of the step.
- If both agents run on the same local Ollama model they will queue and slow each other. If you can, run one on a hosted/free-tier model.
- When an agent says "done", **run its test yourself** (tables below).

---

# PHASE 3 — Wave 1 (T+0:45 → 3:00)

Agents: Brain B1 → B2 → B3 → B4. Media C1 → C2 → C3.
You work through the **parallel to-do list** below, then test each step as it finishes.

## 3A. Your parallel to-do list (with deadlines)

### Deadline 0:55 — Python venv finished
Check window 2 printed `imports ok`. Brain's B1 test needs this.

### Deadline 1:00 — Ollama model (needed for B1 test)
```powershell
ollama list
ollama pull qwen2.5:3b
ollama run qwen2.5:3b "Reply with only the word ready"
ollama ps
```
- If `ollama list` errors, start the Ollama app from the Start menu.
- Pull is about 2 GB. `ollama ps` shows GPU/CPU; either is fine.

### Deadline 1:15 — ffmpeg (needed for C2 test)
```powershell
winget install Gyan.FFmpeg
```
Close **all** PowerShell windows (including the agents' terminals), reopen, and check in a fresh one:
```powershell
ffmpeg -version
ffprobe -version
```
Both must print versions. Fallback if winget fails: download "release essentials" from gyan.dev, unzip to `C:\ffmpeg`, add `C:\ffmpeg\bin` to your user `Path` (Start → "Edit the system environment variables" → Environment Variables → Path → Edit → New). Then **restart both agent CLIs** so they see ffmpeg (re-paste the opening line after restarting).

### Deadline 1:30 — Whisper model (needed for C2 test)
In the activated venv window:
```powershell
mkdir C:\clarifact-models
$env:HF_HUB_DISABLE_SYMLINKS_WARNING="1"
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', local_dir=r'C:\clarifact-models\faster-whisper-small')"
python -c "from faster_whisper import WhisperModel; WhisperModel(r'C:\clarifact-models\faster-whisper-small', device='cpu', compute_type='int8'); print('whisper ok')"
```
About 0.5 GB, no Hugging Face account needed; if it stops, re-run and it resumes. Use multilingual models, not `.en`. Optional faster fallback: same command with `Systran/faster-whisper-base` into `C:\clarifact-models\faster-whisper-base`, then point `WHISPER_MODEL` at it.

### Deadline 1:45 — Free cloud LLM keys (optional but strongly recommended)
- **Gemini:** aistudio.google.com → sign in with a Google account → **Get API key** → **Create API key** → copy. In the model dropdown pick a current "Flash" model with a free tier and copy its exact id.
- **Groq:** console.groq.com → sign up → **API Keys** → **Create API Key** → copy. On the Models page pick a current Llama/Qwen instruct model and copy its id.
Edit the main `.env`:
```powershell
notepad C:\projects\clarifact\.env
```
Fill the lines (no spaces around `=`):
```
GEMINI_API_KEY=paste_key_here
GEMINI_MODEL=model_id_here
GROQ_API_KEY=paste_key_here
GROQ_MODEL=model_id_here
```
Keep `LLM_PROVIDER=ollama` in the main `.env`. Save, then copy to the worktrees:
```powershell
Copy-Item C:\projects\clarifact\.env C:\projects\clarifact-brain\.env -Force
Copy-Item C:\projects\clarifact\.env C:\projects\clarifact-media\.env -Force
```
Then edit only the brain copy and set `LLM_PROVIDER=gemini` (or `groq`) so the app's LLM does not compete with your coding model for RAM during development. Never paste keys into chat; never commit `.env`.

### Deadline 2:30 — Test samples
Create `C:\clarifact-samples\` with 8 items (15–60 s each):

| File | Content | Expected |
|---|---|---|
| `01_false_health.mp4` | You saying a false claim ("this herbal drink cures diabetes in a week") | Likely misleading |
| `02_true_tip.mp4` | An accurate tip ("sleeping 7–8 hours improves memory") | Credible |
| `03_finance_scam.mp4` | "Guaranteed 10x returns in 30 days" pitch | Likely misleading |
| `04_hidden_promo.mp4` | Enthusiastic product push, "use code FIT20", no #ad | hidden promo |
| `05_disclosed_promo.mp4` | Same style but "this is a paid partnership" | disclosed promo |
| `06_neutral_vlog.mp4` | Plain daily vlog/opinion, no facts or products | Credible, no promo |
| `07_miracle_ad.png` | Image: "Lose 10 kg in 7 days, guaranteed!" | Likely misleading |
| `08_whatsapp.txt` | A pasted viral false claim | Likely misleading |

Best: **record 4–5 yourself** on your phone (you or friends reading a scripted false claim or sponsored pitch). You control the truth, no copyright issues. Get them to the laptop via Google Drive / WhatsApp Web / USB. Others may be downloaded for personal local testing only (`yt-dlp -f "mp4[height<=720]" -o "C:\clarifact-samples\%(title).40s.%(ext)s" "<url>"`); don't redistribute them. Ask me and I will write all the scripts for you to read.

Then create `C:\clarifact-samples\expected.json` in Notepad (Save as type **All files** so it is not `.json.txt`):
```json
[
  {"file": "01_false_health.mp4",    "expect_label": "Likely misleading", "expect_promo": "none",      "notes": "herbal drink cures diabetes"},
  {"file": "02_true_tip.mp4",        "expect_label": "Credible",          "expect_promo": "none",      "notes": "sleep and memory"},
  {"file": "03_finance_scam.mp4",    "expect_label": "Likely misleading", "expect_promo": "none",      "notes": "guaranteed 10x returns"},
  {"file": "04_hidden_promo.mp4",    "expect_label": "Use caution",       "expect_promo": "hidden",    "notes": "use code FIT20, no disclosure"},
  {"file": "05_disclosed_promo.mp4", "expect_label": "Credible",          "expect_promo": "disclosed", "notes": "paid partnership stated"},
  {"file": "06_neutral_vlog.mp4",    "expect_label": "Credible",          "expect_promo": "none",      "notes": "no claims"},
  {"file": "07_miracle_ad.png",      "expect_label": "Likely misleading", "expect_promo": "none",      "notes": "lose 10kg in 7 days"},
  {"file": "08_whatsapp.txt",        "expect_label": "Likely misleading", "expect_promo": "none",      "notes": "viral false claim"}
]
```
File names must match exactly. Expected values are your best guess; adjust later if you disagree with the system after reading its reasoning.

## 3B. How to test each step (run these yourself; "done" from an agent is not proof)

Use the **agent's own folder** and the shared Python. For Brain steps:
```powershell
cd C:\projects\clarifact-brain
$py = "C:\projects\clarifact\.venv\Scripts\python.exe"
```
For Media steps: `cd C:\projects\clarifact-media` and the same `$py`.

| Step | Test command (PowerShell) | You should see |
|---|---|---|
| **B1** LLM | `& $py scripts\test_llm.py "Return JSON {\"ok\": true}"` | provider name, latency, `{'ok': True}`. Then set `LLM_PROVIDER=gemini` in this folder's `.env` and re-run: works. Put a wrong key: it logs a fallback and still answers via Ollama |
| **B2** claims | `& $py scripts\test_claims.py "This pill melts belly fat in 3 days, doctors hate it! Use code FIT20 for 50% off"` | 1–2 claims, promo `hidden`, red flags listed |
| | `& $py scripts\test_claims.py "#ad I love this moisturizer, link in bio"` | promo `disclosed` |
| | `& $py scripts\test_claims.py "Today I went to the park and had a sandwich"` | no claims, promo `none` |
| **B3** verify | `& $py scripts\test_verify.py "Drinking hot water cures diabetes"` | contradicted/misleading + real URLs |
| | `& $py scripts\test_verify.py "Water boils at 100 degrees Celsius at sea level"` | supported |
| **B4** API | `& $py tests\test_scoring.py` | all asserts pass |
| | Terminal 1: `& $py -m uvicorn app.main:app --port 8000`. Terminal 2: `& $py scripts\test_api.py "Drinking hot water cures diabetes"` | steps ("Finding claims", "Checking claim 1 of 1", "Scoring") then a full result JSON; startup log says extract = stub |
| **C1** UI | `& $py scripts\mock_server.py` then open http://localhost:8001 | dark Gemini-like home, type + Enter → progress steps → all 6 card types, 3 verdict colors |
| **C2** video | `& $py scripts\test_extract.py C:\clarifact-samples\01_false_health.mp4` | transcript in English, OCR text, per-stage seconds (expect 60–90 s total on your CPU) |
| **C3** image | `& $py scripts\test_extract.py C:\clarifact-samples\07_miracle_ad.png` | OCR text printed |

Compare the UI with `reference\gemini.png`: if it is far off (not dark, no centered pill input), tell OpenCode exactly what is wrong and ask it to fix only that.

**If a test fails**, paste the agent the exact command and the full output, and say: *"Find the root cause, fix it in your files only, and re-run this test."* If it is the second failure for the same test, ask it to explain the cause in 3 sentences before editing.

**If something is a bug in the other agent's area** (e.g. Brain sees garbage from extract), write the bug report (command, actual, expected) and give it to the owner at the next checkpoint.

Commit check after each step: in the agent's folder `git log --oneline` should show a new commit per step.

---

# CHECKPOINT 1 (T+3:00): first merge

Goal: B1–B4 and C1–C3 done and tested.

1. Make sure both agents committed. In **each** worktree:
   ```powershell
   git status
   ```
   It must say "nothing to commit". If not: `git add -A; git commit -m "wip"`.
2. Merge in the **main** folder:
   ```powershell
   cd C:\projects\clarifact
   git merge feat/brain
   git merge feat/media
   ```
   Files do not overlap, so these merge cleanly. If you see `CONFLICT`:
   - `git status` shows the files. For a file the Brain owns after merging `feat/brain` (or the Media owns after `feat/media`) run `git checkout --theirs <file>`, then `git add <file>` and `git commit`.
   - If it looks messy: `git merge --abort`, then ask the agent why it edited a file outside its list.
3. Sync the worktrees so both agents see everything:
   ```powershell
   cd C:\projects\clarifact-brain; git merge main
   cd C:\projects\clarifact-media; git merge main
   ```
4. Run the integrated app in the main folder:
   ```powershell
   cd C:\projects\clarifact
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn app.main:app --port 8000
   ```
   Open http://localhost:8000. Test, by hand, in the real UI:
   - a text claim ("Drinking hot water cures diabetes")
   - the image `07_miracle_ad.png` (use the `+` button)
   - the video `01_false_health.mp4`
   For each: progress text changes, a score appears, claims have verdicts and sources.
5. Write down every problem (what you did, what you saw, what you expected). Sort them: wrong transcript/OCR/UI → Media; wrong claims/promo/verdict/score/API → Brain.
6. Give **Brain**: B5 (paste into the Brain agent in its folder, after re-pasting the opening line if it was restarted), then B6, then B7. Give **Media**: C4, then C5. Add any bug reports to the beginning of those prompts.

---

# PHASE 4 — Wave 2 (T+3:15 → 5:15)

| Step | Agent | Test |
|---|---|---|
| **B5** integration check | Brain | Startup log shows "real" for extract_*; it reports status of text/image/video through the API |
| **B6** link download | Brain | `& $py scripts\test_download.py "<YouTube Shorts url>"` → saved mp4; garbage URL → friendly message |
| **B7** sample runner | Brain | `& $py scripts\run_samples.py` → table with PASS/FAIL, creates `samples_report.md` |
| **C4** UI polish | Media | `& $py scripts\mock_server.py`: try the 3 example chips, attach, history restore, New chat, "How we score" panel |
| **C5** startup check + speed | Media | `& $py scripts\startup_check.py` → all PASS; before/after seconds for video stages reported |

While they work: collect your 8 samples if not done, then keep notes on UI polish ideas.

**Warm-up reminder:** the first video run after starting the app is slow (models load). Always do one throwaway run before timing or demoing.

---

# CHECKPOINT 2 (T+5:15): merge and measure

1. Same merge procedure as Checkpoint 1 (commit check → `git merge feat/brain` / `feat/media` in main → sync worktrees).
2. In main, with the venv active and `ollama` running:
   ```powershell
   python scripts\startup_check.py
   python scripts\run_samples.py
   ```
   All checks should PASS. Open `samples_report.md`.
3. **Triage every FAIL** (this is the most valuable 20 minutes of the project):
   - Look at the transcript/OCR text of the failing sample. If that text is wrong or empty → **Media** (extraction).
   - If the text is fine but claims or promo are wrong → **Brain** (prompts/rules).
   - If claims/verdicts look right but the score/label seems off → check `SPEC.md` scoring numbers; it is deterministic, so decide if you want to change a weight (you decide, then tell Brain).
   - Also decide if the **expected** value was wrong. It is fine to change `expected.json` if the system's reasoning is better than your guess, as long as you can justify it.
4. Record the pass count (e.g. "5/8"); this goes in the report.

---

# PHASE 5 — Wave 3 (T+5:30 → 8:00)

- **Brain: B8.** Paste the failing rows (transcript, claims, verdicts) and 3–5 neutral texts that must stay clean. Ask it to report the before/after pass count.
- **Media: C6.** Paste any extraction/UI bug reports; it also writes the README.
- Run `run_samples.py` again after each fix round. Keep a running list: date/time, pass count, what changed.
- UI check with a fresh eye: ask a friend to use it without instructions. Note where they hesitate.
- If any step runs long, stop at T+7:30 and take whatever works.

## Local vs cloud test (do this once around T+7:00)
1. Set `LLM_PROVIDER=ollama` in the main `.env`, restart the app, run the 3 demo inputs. Note timings and quality.
2. Set `LLM_PROVIDER=gemini` (or `groq`), restart, run the same 3. Note timings and quality.
3. Decide which one you will demo with, and keep the other as a fallback. A good plan: demo with the cloud key, and show Ollama once to prove it works offline.

---

# FEATURE FREEZE (T+8:00)

From now on: **bug fixes only, no new features.**
Final merge (same procedure). Then in main:
```powershell
git log --oneline
git tag v1-demo
```

---

# PHASE 6 — Demo prep and report (T+8:00 → 10:00)

### 6.1 Pick and rehearse the demo (30 min)
Choose 3 inputs: one **video** with a hidden promo (strongest, clearly shows the point), one **image** ad, one **text** claim. Run each twice. Aim for under 90 seconds each. Demo flow (3–4 minutes):
1. One sentence on the problem (short-form misinformation and hidden promotions).
2. Upload the video, narrate the progress steps as they appear (speech → on-screen text → claims → web check → score).
3. Open the result: score, promo banner, 1–2 claims with sources, red flags.
4. Show the image and the text claim quickly.
5. 30 seconds on how it was built: existing models (Whisper, OCR, an LLM) + web evidence + a transparent scoring formula, no training needed.

### 6.2 Safety nets
- [ ] A **screen recording** of a full successful run (Windows: Win+G or the Snipping Tool's video mode) saved on the desktop and a USB.
- [ ] Demo files in one folder on the desktop.
- [ ] Laptop plugged in, battery saver off, other apps closed, notifications off.
- [ ] Start the app and do one throwaway analysis 10 minutes before the viva so models are warm.
- [ ] Wi-Fi checked; hotspot as backup. With the cloud key off, the app still works locally (slower).
- [ ] `.env` is **not** in Git (`git ls-files | findstr .env` shows only `.env.example`).

### 6.3 Report skeleton (ask me and I will draft each part)
1. Problem statement and motivation (short-form content, influencer promotion, misinformation)
2. Related work (fact-checking tools, FTC-style disclosure rules, speech/OCR/LLM models)
3. Objectives and scope
4. Architecture diagram (extract → claims → verify → score → UI) and module descriptions
5. Models and data sources used (Whisper, RapidOCR, LLM, ddgs/Wikipedia) and why
6. Scoring method (the formula, why deterministic)
7. Implementation (stack, folder layout, API contract)
8. Testing and results: the `samples_report.md` table, pass rate, 2–3 case studies, timings
9. Limitations (OCR languages, small-model accuracy, search coverage, not a legal fact-checker)
10. Future work (more languages, better OCR, browser extension, fine-tuned classifier)

### 6.4 Viva questions to prepare
- Why did you use existing models instead of training your own?
- How does the credibility score work? Why not let the LLM decide the score?
- How do you prevent the LLM from inventing sources?
- What happens with Hindi/Kannada content? What is the OCR limitation?
- How do you detect hidden promotion versus disclosed? What are the false-positive risks?
- Why is "unverified" different from "false"?
- How would you scale or deploy this?
- What would you do with more time?

---

# If things go wrong (decision guide)

| Situation | What to do |
|---|---|
| Agent edits a file it does not own | In its folder: `git checkout -- <file>`; re-paste the opening line |
| Agent loops, forgets rules, half-finishes | Restart session, re-paste the opening, give half the step: "Do only part (1) now" |
| An agent hits its quota or stops | Start the **other** CLI in the same folder, paste the opening line and the unfinished step; the folder holds all the state |
| Both agents painfully slow | They are sharing one local model; move one to a hosted model or run lanes one at a time |
| PC freezing / out of memory | Close browser tabs; use cloud `LLM_PROVIDER` while developing; `WHISPER_MODEL` = base; one heavy test at a time |
| Whisper too slow | Use `faster-whisper-base`; keep clips under 60 s |
| `ddgs` returns nothing | Wait 30 s and retry; claims will show `unverified` (acceptable); Wikipedia is the backup |
| Port already in use | Use `--port 8001`, or close the old uvicorn window |
| `ffmpeg` not found in agent terminal | Restart the agent CLI after installing ffmpeg |
| yt-dlp fails on Instagram | Expected. Demo with uploaded files and YouTube Shorts |
| JSON errors from the 3B model | Use the cloud provider for the demo; or try `llama3.2:3b` |
| Merge conflict | `git status`; keep the owner's version with `git checkout --theirs <file>`, `git add`, `git commit`; if messy, `git merge --abort` |
| You are totally stuck | Paste me: what step you are on, the exact command, and the **full** error text |

---

# Master checklist

**Phase 1:** [ ] files downloaded [ ] folder + files [ ] base commit [ ] 3 worktrees [ ] venv installing
**Phase 2:** [ ] Brain launched, 5 bullets OK [ ] Media launched, 5 bullets OK [ ] B1 and C1 pasted
**Wave 1 env:** [ ] imports ok [ ] Ollama model [ ] ffmpeg [ ] Whisper model [ ] API keys [ ] 8 samples + expected.json
**Wave 1 steps:** [ ] B1 [ ] B2 [ ] B3 [ ] B4 [ ] C1 [ ] C2 [ ] C3
**Checkpoint 1:** [ ] merged [ ] text/image/video work in the real UI
**Wave 2:** [ ] B5 [ ] B6 [ ] B7 [ ] C4 [ ] C5
**Checkpoint 2:** [ ] merged [ ] startup_check passes [ ] samples_report.md read [ ] failures triaged
**Wave 3:** [ ] B8 [ ] C6 [ ] local vs cloud test [ ] pass count recorded
**Freeze:** [ ] final merge [ ] tag v1-demo
**Demo:** [ ] 3 inputs chosen [ ] rehearsed twice [ ] backup recording [ ] report drafted [ ] viva answers ready
