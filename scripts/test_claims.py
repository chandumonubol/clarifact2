"""Simple test harness for app.claims.analyze.

Usage:
    python scripts/test_claims.py "<text>"

Creates a minimal :class:`ExtractedContent` with the supplied *text* and empty
transcript/ocr fields, runs :func:`app.claims.analyze`, and pretty‑prints the
resulting :class:`Signals` as JSON.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import json
import sys
from typing import Any

# Import the function under test.
from app.claims import analyze
from app.interfaces import ExtractedContent


def build_content(text: str) -> ExtractedContent:
    """Return an :class:`ExtractedContent` with *text* and empty auxiliary fields."""
    return {
        "text": text,
        "transcript": "",
        "ocr_text": "",
        "warnings": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run claims.analyze on a single text string")
    parser.add_argument("text", help="The raw text / caption supplied by the user")
    args = parser.parse_args(argv)

    content = build_content(args.text)
    signals = analyze(content)
    # Pretty‑print JSON for easy visual verification.
    print(json.dumps(signals, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
