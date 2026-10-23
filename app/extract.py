"""Extraction utilities for ClariFact.

Provides helper functions to combine textual sources (text, OCR, transcript) and
perform any required preprocessing before claim analysis.

Implements real media extraction for video files using Whisper (faster-whisper) for
speech‑to‑text and RapidOCR (rapidocr_onnxruntime) for on‑screen OCR.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from faster_whisper import WhisperModel
from rapidocr_onnxruntime import RapidOCR

from .interfaces import ExtractedContent, ProgressFn

# Global lazy‑loaded models to avoid re‑initialisation overhead.
_whisper_model: Optional[WhisperModel] = None
_ocr_model: Optional[RapidOCR] = None

def _load_whisper() -> Optional[WhisperModel]:
    global _whisper_model
    if _whisper_model is None:
        try:
            # "base" is a small model that runs quickly on CPU.
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as exc:
            logging.exception("Failed to load Whisper model")
            _whisper_model = None
    return _whisper_model

def _load_ocr() -> Optional[RapidOCR]:
    global _ocr_model
    if _ocr_model is None:
        try:
            _ocr_model = RapidOCR()
        except Exception as exc:
            logging.exception("Failed to initialise RapidOCR")
            _ocr_model = None
    return _ocr_model

def extract_from_video(file_path: str, progress: Optional[ProgressFn] = None) -> ExtractedContent:
    """Extract speech transcript and on‑screen text from a video file.

    * **Whisper** is used to transcribe the audio track.
    * **RapidOCR** runs on a sampled frame (approximately one frame per second)
      to collect any visible text.
    Returns an :class:`ExtractedContent` dict expected by the pipeline.
    """
    warnings: list[str] = []
    transcript = ""
    ocr_text = ""

    # ---------------------------------------------------------------------
    # 1️⃣ Speech‑to‑text via Faster‑Whisper
    # ---------------------------------------------------------------------
    if progress:
        progress("Transcribing speech")
    whisper = _load_whisper()
    if whisper:
        try:
            # Decode audio to mono 16kHz PCM using ffmpeg.
            cmd = ["ffmpeg", "-i", file_path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
            raw_audio = result.stdout
            if raw_audio:
                audio_np = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_np = np.array([], dtype=np.float32)
            segments, _ = whisper.transcribe(audio_np, beam_size=5)
            transcript = " ".join(seg.text for seg in segments)
        except Exception as exc:
            logging.exception("Whisper transcription failed")
            warnings.append(f"Whisper transcription error: {exc}")
    else:
        warnings.append("Whisper model unavailable – transcript not generated")

    # ---------------------------------------------------------------------
    # 2️⃣ OCR via RapidOCR (sample one frame per second)
    # ---------------------------------------------------------------------
    if progress:
        progress("Running OCR on video frames")
    ocr = _load_ocr()
    if ocr:
        try:
            cap = cv2.VideoCapture(file_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # fallback
            frame_interval = int(fps)  # one frame each second
            frame_idx = 0
            texts: list[str] = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_interval == 0:
                    # Convert BGR (OpenCV) -> RGB for RapidOCR.
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # RapidOCR expects a NumPy array.
                    results = ocr(rgb)
                    # Each result is (box, text, confidence).
                    for res in results:
                        if isinstance(res, (list, tuple)) and len(res) >= 3:
                            txt = res[1]
                            if isinstance(txt, str) and txt.strip():
                                texts.append(txt.strip())
                frame_idx += 1
            cap.release()
            ocr_text = " ".join(texts)
        except Exception as exc:
            logging.exception("RapidOCR failed")
            warnings.append(f"OCR error: {exc}")
    else:
        warnings.append("RapidOCR unavailable – on‑screen text not extracted")

    # ---------------------------------------------------------------
    # Return the gathered content in the required shape.
    # ---------------------------------------------------------------
    return {
        "text": "",  # No raw text input for video extraction.
        "transcript": transcript,
        "ocr_text": ocr_text,
        "warnings": warnings,
    }

# ---------------------------------------------------------------------
# Existing helper to combine arbitrary sources (kept for compatibility).
# ---------------------------------------------------------------------

def combine_sources(text: str = "", ocr_text: str = "", transcript: str = "", warnings=None) -> ExtractedContent:
    """Combine various content sources into an :class:`ExtractedContent` dict.

    Args:
        text: Raw text content.
        ocr_text: OCR‑extracted text from images.
        transcript: Speech‑to‑text transcript.
        warnings: Optional list of warning strings.

    Returns:
        ExtractedContent: Dictionary conforming to the spec.
    """
    if warnings is None:
        warnings = []
    return {
        "text": text,
        "ocr_text": ocr_text,
        "transcript": transcript,
        "warnings": warnings,
    }

