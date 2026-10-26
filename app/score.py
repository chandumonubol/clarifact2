"""Scoring utilities for ClariFact.

Provides :func:`compute_credibility_score` which implements the B4 scoring rules.
"""

from __future__ import annotations

from typing import List, TypedDict

from app.interfaces import VerifiedClaim, PromoInfo, LABEL_CREDIBLE, LABEL_CAUTION, LABEL_MISLEADING


class CredibilityScore(TypedDict, total=False):
    credibility_score: int
    label: str
    top_factors: List[str]


def compute_credibility_score(
    claims: List[VerifiedClaim],
    promo: PromoInfo,
    text_len: int,
) -> CredibilityScore:
    """Calculate a credibility score for a piece of content.

    Scoring rules (B4 specification):
    - Start at 100.
    - For each claim:
        * ``supported``: +0
        * ``unverified``: -10
        * ``misleading``: -20
        * ``contradicted``: -35
    - Promo penalties:
        * hidden: -20
        * disclosed: -5
    - Each red flag in ``promo.red_flags``: -5.
    - If the total text length is < 30 characters **and** there are no checkable claims,
      apply an additional -10 penalty.
    - Clamp the final score to the range 0–100.
    - Labels:
        * >= 80 → "High Trust"
        * >= 50 → "Mixed / Low Trust"
        * < 50 → "Very Low / Unreliable"
    - ``top_factors`` is a list (≤4) of human‑readable bullet points that explain the most
      significant deductions (e.g. "Contradicted claim: …").
    """
    score = 100
    top_factors: List[str] = []

    # Claim penalties and factor collection
    for claim in claims:
        verdict = claim.get("verdict")
        if verdict == "supported":
            # no penalty
            continue
        elif verdict == "unverified":
            score -= 5
            top_factors.append(f"Unverified claim: {claim.get('text', '')}")
        elif verdict == "misleading":
            score -= 15
            top_factors.append(f"Misleading claim: {claim.get('text', '')}")
        elif verdict == "contradicted":
            score -= 25
            top_factors.append(f"Contradicted claim: {claim.get('text', '')}")
        else:
            # unknown verdict – treat as unverified
            score -= 5
            top_factors.append(f"Unknown verdict claim treated as unverified: {claim.get('text', '')}")


    # Promo penalties
    if promo.get("detected"):
        ptype = promo.get("type")
        if ptype == "hidden":
            score -= 20
            top_factors.append("Hidden promotional content detected")
        elif ptype == "disclosed":
            score -= 5
            top_factors.append("Disclosed promotional content detected")
        # "none" incurs no penalty

    # Red flags (each -5, cap total -20)
    red_flags = promo.get("red_flags", []) if isinstance(promo.get("red_flags"), list) else []
    red_penalty = min(len(red_flags) * 5, 20)
    if red_penalty:
        score -= red_penalty
        top_factors.append(f"Red flags ({len(red_flags)}): {', '.join(red_flags[:3])}")


    # Clamp score
    if score < 0:
        score = 0
    elif score > 100:
        score = 100

    # Determine label using interface constants
    if score >= 75:
        label = LABEL_CREDIBLE
    elif score >= 50:
        label = LABEL_CAUTION
    else:
        label = LABEL_MISLEADING

    # Limit top_factors to 4 entries (most severe first)
    top_factors = top_factors[:4]

    return {"credibility_score": score, "label": label, "top_factors": top_factors}
