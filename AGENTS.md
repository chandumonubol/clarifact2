# CLAUDE.md / AGENTS.md — ClariFact working rules

Read `SPEC.md` and `app/interfaces.py` before doing anything. They are the single source of truth.
(This same text is saved as `AGENTS.md` for OpenCode.)

## Golden rules
1. Work on ONE step at a time (the human names it). Do not build ahead.
2. **Ownership:** at the start of the session the human gives you a list of files you own. Create or edit ONLY those. Never edit `app/interfaces.py`, `requirements.txt`, `SPEC.md`, `CLAUDE.md`, `AGENTS.md`, `.env.example`.
3. Never change the API contract or any shape in `app/interfaces.py`. If you think it must change, STOP and ask.
4. Keep it simple: no new frameworks, no npm/React, no databases, no Docker, no vendor SDKs. Plain Python + plain JS.
5. If you need a new package, STOP and ask. Don't edit `requirements.txt` and don't `pip install` anything on your own.
6. Every stage must be runnable alone via a script in `scripts/` before it is wired into the API.
7. Use the constants from `app/interfaces.py` (labels, verdicts, limits). Don't retype those strings.
8. Never hardcode or print API keys. Read from `.env` through `os.getenv` / `config.py`.
9. When something fails, show the real error and fix the root cause. Don't silently swallow exceptions: log them and add to `warnings`.
10. Don't rewrite working files wholesale. Make small, targeted edits.
11. Finish every step with: `git add -A` and `git commit -m "<step>: <what works>"`, then reply with (a) files created/changed, (b) the exact test command, (c) the expected output, (d) anything that does not work yet. Then stop and wait.

## Environment (Windows 11, PowerShell, 16 GB RAM, small GPU)
- Always run Python with the shared venv: `C:\projects\clarifact\.venv\Scripts\python.exe`
- ffmpeg/ffprobe are on PATH (installed with `winget install Gyan.FFmpeg`).
- Ollama runs locally; app model is `qwen2.5:3b` unless `.env` says otherwise.
- Whisper runs on CPU with `compute_type="int8"`. Don't fight CUDA setup.
- Run app: `python -m uvicorn app.main:app --port 8000` (from the main folder after merging)
- Use PowerShell syntax for any shell command you show the human.

## Packages available (do not add others)
```
fastapi  uvicorn[standard]  python-multipart  pydantic  python-dotenv  httpx
faster-whisper  rapidocr-onnxruntime  ddgs  yt-dlp  huggingface_hub
```

## Style
- Type hints, small functions, short docstrings.
- Logging via `logging`: one line per stage start/finish with duration.
- Comments only where the reason isn't obvious.
- Every function that touches the network, disk or a model must handle failure and return a safe value or a clear `ValueError` message.

## Git
- You are in a worktree on your own branch. Commit there only. Never push, never switch branches, never touch other folders.
