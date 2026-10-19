"""Scoring wrapper that conforms to the required interface.

Provides :func:`score` which takes verified claims, promo info, and red flags,
and returns a :class:`ScoreResult` as defined in ``app.interfaces``.
"""

from __future__ import annotations

from typing import List

from app.interfaces import VerifiedClaim, PromoInfo, ScoreResult
from .score import compute_credibility_score


def _confidence_from_claims(claims: List[VerifiedClaim]) -> str:
    """Derive confidence level based on the proportion of claims that have
    usable evidence (``had_evidence``). Mirrors the logic from SPEC.
    """
    if not claims:
        return "low"
    with_evidence = sum(1 for c in claims if c.get("had_evidence"))
    ratio = with_evidence / len(claims)
    if ratio >= 0.7:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"


def score(
    claims: List[VerifiedClaim],
    promo: PromoInfo,
    red_flags: List[str],
) -> ScoreResult:
    """Calculate the overall score for an analysis.

    The heavy lifting is delegated to :func:`compute_credibility_score`.
    ``red_flags`` are passed via the ``promo`` argument because the existing
    ``PromoInfo`` type does not include them; we therefore treat them as an extra
    field on the dict for scoring purposes.
    """
    # Prepare a promo dict that also carries red flags for the scoring util.
    promo_with_flags = dict(promo)
    promo_with_flags["red_flags"] = red_flags

    # Text length is not directly available here; callers (pipeline) will add it
    # via the ``credibility_score`` function when assembling the final result.
    # For compatibility we default to 0 – the pipeline will recompute the score
    # with the correct length.
    dummy_text_len = 0

    cred = compute_credibility_score(claims, promo_with_flags, dummy_text_len)

    # Confidence based on evidence presence
    confidence = _confidence_from_claims(claims)

    return {
        "credibility_score": cred["credibility_score"],
        "label": cred["label"],
        "confidence": confidence,
    }

# End of file
