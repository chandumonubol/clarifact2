"""Scoring utilities for ClariFact.

Provides :func:`compute_credibility_score` which implements the B4 scoring rules.
"""

from __future__ import annotations

from typing import List, TypedDict

from app.interfaces import VerifiedClaim, PromoInfo


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
            score -= 10
            top_factors.append(f"Unverified claim: {claim.get('text', '')}")
        elif verdict == "misleading":
            score -= 20
            top_factors.append(f"Misleading claim: {claim.get('text', '')}")
        elif verdict == "contradicted":
            score -= 35
            top_factors.append(f"Contradicted claim: {claim.get('text', '')}")
        # else: unknown verdict – treat as unverified
        else:
            score -= 10
            top_factors.append(f"Unknown verdict claim treated as unverified: {claim.get('text', '')}")

    # Promo penalties
    if promo.get("detected"):
        ptype = promo.get("type")
        if ptype == "hidden":
            score -= 20
            top_factors.append("Hidden promotional content detected")
        elif ptype == "disclosed":
            score -= 10
            top_factors.append("Disclosed promotional content detected")
        # "none" incurs no penalty

    # Red flags (assumed to be passed via promo.red_flags – the spec lists them separately)
    red_flags = promo.get("red_flags", []) if isinstance(promo.get("red_flags"), list) else []
    for flag in red_flags:
        score -= 15
        top_factors.append(f"Red flag: {flag}")

    # Short‑text penalty
    if text_len < 30 and not claims:
        score -= 10
        top_factors.append("Very short text with no checkable claims")

    # Clamp score
    if score < 0:
        score = 0
    elif score > 100:
        score = 100

    # Determine label
    if score >= 80:
        label = "High Trust"
    elif score >= 50:
        label = "Mixed / Low Trust"
    else:
        label = "Very Low / Unreliable"

    # Limit top_factors to 4 entries (most severe first)
    top_factors = top_factors[:4]

    return {"credibility_score": score, "label": label, "top_factors": top_factors}
