"""Extraction utilities for ClariFact.

Provides helper functions to combine textual sources (text, OCR, transcript) and
perform any required preprocessing before claim analysis.

Only a minimal stub is provided here; actual media extraction (audio/video OCR)
is handled by external agents.
"""

from .interfaces import ExtractedContent


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
