import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the repository root is on the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import analyze_content

def make_content(text: str = "", ocr_text: str = "", transcript: str = "", warnings=None):
    if warnings is None:
        warnings = []
    return {
        "text": text,
        "ocr_text": ocr_text,
        "transcript": transcript,
        "warnings": warnings,
    }

def test_text_only_input():
    content = make_content(text="The Earth revolves around the Sun.")
    with patch("app.pipeline.analyze_claims_and_promo") as mock_analyze, \
         patch("app.pipeline.verify_claim") as mock_verify:
        mock_analyze.return_value = {
            "claims": ["The Earth revolves around the Sun"],
            "promo": {"detected": False, "type": "none", "evidence": []},
            "red_flags": [],
            "warnings": [],
        }
        mock_verify.return_value = {
            "text": "The Earth revolves around the Sun",
            "verdict": "supported",
            "explanation": "Supported by astronomy.",
            "sources": [],
            "had_evidence": True,
        }
        result = analyze_content(content)
    assert result["credibility_score"] >= 0
    assert result["label"] in ("High Trust", "Mixed / Low Trust", "Very Low / Unreliable")
    assert result["ocr_text"] == ""

def test_ocr_input_extraction():
    content = make_content(ocr_text="Miracle cure discovered.")
    with patch("app.pipeline.analyze_claims_and_promo") as mock_analyze, \
         patch("app.pipeline.verify_claim") as mock_verify:
        mock_analyze.return_value = {
            "claims": ["Miracle cure discovered"],
            "promo": {"detected": False, "type": "none", "evidence": []},
            "red_flags": [],
            "warnings": [],
        }
        mock_verify.return_value = {
            "text": "Miracle cure discovered",
            "verdict": "unverified",
            "explanation": "No evidence.",
            "sources": [],
            "had_evidence": False,
        }
        result = analyze_content(content)
    assert result["ocr_text"] == "Miracle cure discovered."
    assert "credibility_score" in result

def test_invalid_file_type_rejection():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    files = {"file": ("malicious.exe", b"dummy content")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"
