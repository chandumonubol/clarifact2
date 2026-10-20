"""Pipeline for ClariFact analysis.

The :func:`analyze_content` function orchestrates claim extraction, verification,
scoring, and builds the final :class:`AnalysisResult`.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from app.interfaces import (
    ExtractedContent,
    ProgressFn,
    ClaimOut,
    AnalysisResult,
    VerifiedClaim,
    PromoInfo,
    ScoreResult,
)

from .claims import analyze as analyze_claims_and_promo
from .verify import verify_claim
from .scoring import score as compute_score
from .score import compute_credibility_score


def _to_claim_out(vc: VerifiedClaim) -> ClaimOut:
    """Convert a :class:`VerifiedClaim` to the API ``ClaimOut`` shape.

    ``had_evidence`` is omitted as required by the API contract.
    """
    return {
        "text": vc.get("text", ""),
        "verdict": vc.get("verdict", "unverified"),
        "explanation": vc.get("explanation", ""),
        "sources": vc.get("sources", []),
    }


def analyze_content(
    content: ExtractedContent, progress: Optional[ProgressFn] = None
) -> AnalysisResult:
    """Run the full analysis pipeline on *content*.

    Steps (mirroring the B4 specification):
    1️⃣ Extract claims and promo information.
    2️⃣ Verify each claim with web evidence.
    3️⃣ Compute the credibility score.
    4️⃣ Assemble the :class:`AnalysisResult`.
    """
    # Step 1 – claim extraction & promo detection
    if progress:
        progress("Extracting claims")
    # Combine textual sources for claim analysis (text, OCR, transcript)
    full_text = " ".join(filter(None, [content.get("text", ""), content.get("ocr_text", ""), content.get("transcript", "")]))
    # Prepare a minimal content dict for the claims analyzer (preserve warnings)
    claims_content = {
        "text": full_text,
        "transcript": "",
        "ocr_text": "",
        "warnings": content.get("warnings", []),
    }
    signals = analyze_claims_and_promo(claims_content)
    claims_texts: List[str] = signals.get("claims", [])
    promo: PromoInfo = signals.get("promo", {})
    red_flags: List[str] = signals.get("red_flags", [])
    warnings: List[str] = signals.get("warnings", [])

    # Step 2 – verification
    verified: List[VerifiedClaim] = []
    if progress:
        progress("Verifying web evidence")
    for claim_text in claims_texts:
        try:
            vc = verify_claim(claim_text)
        except Exception as exc:  # pragma: no cover – safety net
            logging.warning(f"verify_claim raised for '{claim_text}': {exc}")
            vc = {
                "text": claim_text,
                "verdict": "unverified",
                "explanation": "Verification failed.",
                "sources": [],
                "had_evidence": False,
            }
        verified.append(vc)

    # Step 3 – compute score
    if progress:
        progress("Calculating credibility score")
    text_len = sum(len(content.get(k, "")) for k in ("text", "transcript", "ocr_text"))
    # The scoring function in app/scoring expects promo without red_flags, so we
    # pass the promo as‑is and provide red_flags separately.
    cred = compute_score(verified, promo, red_flags)
    # Overwrite label/score with the more detailed compute_credibility_score that
    # also respects text_len.
    # Combine promo with red flags for the detailed scoring step
    promo_with_flags = dict(promo)
    promo_with_flags["red_flags"] = red_flags
    detailed = compute_credibility_score(verified, promo_with_flags, text_len)
    credibility_score = detailed["credibility_score"]
    label = detailed["label"]
    # confidence comes from the wrapper score (already set based on evidence)
    confidence = cred["confidence"]

    # Build claim output list (dropping had_evidence)
    claim_outs: List[ClaimOut] = [_to_claim_out(vc) for vc in verified]

    result: AnalysisResult = {
        "credibility_score": credibility_score,
        "label": label,
        "confidence": confidence,
        "promo": promo,
        "claims": claim_outs,
        "red_flags": red_flags,
        "transcript": content.get("transcript", ""),
        "ocr_text": content.get("ocr_text", ""),
        "warnings": warnings,
    }
    # optional metadata (not defined in the TypedDict but useful for debugging)
    result["processed_at"] = datetime.now(timezone.utc).isoformat()
    result["summary"] = f"Analyzed {len(claim_outs)} claim(s)"
    return result

# End of file
