"""Test harness for the ClariFact pipeline.

Usage:
    python scripts/test_pipeline.py "<text>"

Runs :func:`app.pipeline.analyze_content` on the supplied text and prints the
resulting :class:`AnalysisResult` as pretty‑printed JSON.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import analyze_content
from app.interfaces import ExtractedContent


def build_content(text: str) -> ExtractedContent:
    return {
        "text": text,
        "transcript": "",
        "ocr_text": "",
        "warnings": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full pipeline on a text string")
    parser.add_argument("text", help="Input text to analyze")
    args = parser.parse_args(argv)
    content = build_content(args.text)
    result = analyze_content(content)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
