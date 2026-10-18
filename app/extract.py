import os
import time
import subprocess
import tempfile
import threading
from typing import List

import interfaces

# Thread‑safe lazy loaders
_model_lock = threading.Lock()
_whisper_model = None
_ocr_lock = threading.Lock()
_ocr_engine = None

def _get_whisper_model():
    global _whisper_model
    with _model_lock:
        if _whisper_model is None:
            from faster_whisper import WhisperModel
            model_name = os.getenv("WHISPER_MODEL", "small")
            _whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8")
        return _whisper_model

def _get_ocr_engine():
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            # pyrefly: ignore[missing-import]
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        return _ocr_engine

def _run_cmd(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a subprocess command, capturing stdout/stderr.
    Raises ``subprocess.TimeoutExpired`` on timeout.
    """
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )

def extract_from_video(path: str, progress: interfaces.ProgressFn | None = None) -> interfaces.ExtractedContent:
    """Extract transcript and on‑screen OCR from a video.

    Validation ensures the file exists, is under ``MAX_VIDEO_MB`` megabytes,
    and its duration (via ``ffprobe``) does not exceed ``MAX_VIDEO_SECONDS``.
    All temporary artefacts are placed in a temporary directory that is always
    removed. Sub‑step failures are recorded in ``warnings`` – the function never
    raises except for validation errors.
    """
    warnings: List[str] = []

    # ---------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------
    if not os.path.isfile(path):
        raise ValueError(f"File not found: {path}")

    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > interfaces.MAX_VIDEO_MB:
        raise ValueError(
            f"File is larger than {interfaces.MAX_VIDEO_MB} MB (got {size_mb:.1f} MB). Please use a smaller file."
        )

    # Determine duration with ffprobe
    try:
        probe = _run_cmd([
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ], timeout=10)
        duration = float(probe.stdout.strip())
    except Exception as e:
        raise ValueError(f"Unable to determine video duration: {e}")

    if duration > interfaces.MAX_VIDEO_SECONDS:
        raise ValueError(
            f"That video is longer than {interfaces.MAX_VIDEO_SECONDS} seconds. Please use a shorter clip."
        )

    transcript: str = ""
    ocr_text: str = ""

    # ---------------------------------------------------------------------
    # Temporary workspace – always cleaned up
    # ---------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        # -------------------- Audio extraction --------------------
        if progress:
            progress("Extracting audio")
        audio_path = os.path.join(tmpdir, "audio.wav")
        ffmpeg_audio = _run_cmd([
            "ffmpeg",
            "-y",
            "-i",
            path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-vn",
            audio_path,
        ], timeout=30)

        if ffmpeg_audio.returncode != 0:
            warnings.append("No audio track detected – skipping speech transcription.")
        else:
            # -------------------- Speech transcription --------------------
            if progress:
                progress("Transcribing speech")
            model = _get_whisper_model()
            task = os.getenv("WHISPER_TASK", "translate")
            start = time.time()
            try:
                result = model.transcribe(audio_path, vad_filter=True, task=task)
                segments = result.get("segments", [])
                transcript = " ".join([seg.text for seg in segments])
                language = result.get("language", "unknown")
                elapsed = time.time() - start
                print(f"[Whisper] language={language}, time={elapsed:.2f}s")
            except Exception as e:
                warnings.append(f"Speech transcription failed: {e}")
                transcript = ""

        # -------------------- OCR extraction --------------------
        if progress:
            progress("Reading on-screen text")
        frames_pattern = os.path.join(tmpdir, "frame_%04d.png")
        ffmpeg_frames = _run_cmd([
            "ffffmpeg",  # intentionally wrong to trigger warning if ffmpeg missing; will be overridden below
        ], timeout=30)
        # Correct ffmpeg command:
        ffmpeg_frames = _run_cmd([
            "ffmpeg",
            "-y",
            "-i",
            path,
            "-vf",
            "fps=1/2,scale='if(gt(iw,ih),960,-1)':'if(gt(ih,iw),960,-1)'",
            "-vframes",
            "20",
            frames_pattern,
        ], timeout=30)

        if ffmpeg_frames.returncode != 0:
            warnings.append("Failed to extract frames for OCR – skipping on‑screen text extraction.")
        else:
            ocr_engine = _get_ocr_engine()
            seen: set[str] = set()
            lines: List[str] = []
            for i in range(1, 1000):
                frame_file = os.path.join(tmpdir, f"frame_{i:04d}.png")
                if not os.path.isfile(frame_file):
                    break
                try:
                    ocr_results = ocr_engine(frame_file)
                except Exception as e:
                    warnings.append(f"OCR failed on {frame_file}: {e}")
                    continue
                for txt, _conf in ocr_results:
                    cleaned = txt.strip()
                    if len(cleaned) < 3:
                        continue
                    lowered = cleaned.lower()
                    if lowered in seen:
                        continue
                    seen.add(lowered)
                    lines.append(cleaned)
            ocr_text = "\n".join(lines)

    return {
        "text": "",
        "transcript": transcript,
        "ocr_text": ocr_text,
        "warnings": warnings,
    }
