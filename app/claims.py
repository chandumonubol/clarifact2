"""ClariFact claims analysis.

Implements the `analyze` function required by the pipeline.
"""

import logging
from typing import List

from app.interfaces import (
    ExtractedContent,
    Signals,
    PromoInfo,
    MAX_CLAIMS,
)
from app.llm import llm_json

# Keywords for deterministic promo detection (case‑insensitive)
DISCLOSURE_KEYWORDS = [
    "#ad",
    "#sponsored",
    "paid partnership",
    "sponsored by",
    "in collaboration with",
]
COMMERCIAL_KEYWORDS = [
    "use code",
    "discount code",
    "link in bio",
    "affiliate",
    "% off",
    "dm me",
    "free trial",
    "limited offer",
    "buy now",
]


def _detect_keywords(text: str, keywords: List[str]) -> List[str]:
    """Return the list of keywords that appear (case‑insensitively) in *text*."""
    lowered = text.lower()
    hits: List[str] = []
    for kw in keywords:
        if kw.lower() in lowered:
            hits.append(kw)
    return hits


def analyze(content: ExtractedContent) -> Signals:
    """Analyse *content* and return :class:`Signals`.

    Steps:
    1. Build a labelled input string from the three possible text sources.
    2. Call the LLM (via :func:`app.llm.llm_json`) to obtain raw claims,
       hidden‑promo flag/reason and red‑flags.
    3. Apply deterministic promo rules.
    4. Deduplicate claims, enforce ``MAX_CLAIMS`` and drop empty entries.
    5. Return a :class:`Signals` dict, populating ``warnings`` on any issue.
    """
    warnings: List[str] = []

    # ---------- 1. Build labelled input ----------
    parts: List[str] = []
    if content.get("text"):
        parts.append(f"TEXT: {content['text']}")
    if content.get("transcript"):
        parts.append(f"SPEECH: {content['transcript']}")
    if content.get("ocr_text"):
        parts.append(f"ON-SCREEN TEXT: {content['ocr_text']}")

    if not parts:
        warnings.append("No content to analyze")
        empty_signals: Signals = {
            "claims": [],
            "promo": {"detected": False, "type": "none", "evidence": []},
            "red_flags": [],
            "warnings": warnings,
        }
        return empty_signals

    combined_input = "\n".join(parts)

    # ---------- 2. LLM call ----------
    prompt = (
        "You analyze short-form social media videos. From the content below extract:\n"
        "1) claims: up to 6 CHECKABLE FACTUAL claims (health, money, product performance, statistics, 'scientists say'). Each claim must be short and self‑contained. Skip opinions, jokes, greetings.\n"
        "2) hidden_promo: true if the speaker is pushing a product/service/brand without clearly saying it is sponsored, else false; plus a one‑sentence reason.\n"
        "3) red_flags: any of: miracle or guaranteed results, false urgency, 'doctors hate this', fake authority, cherry‑picked statistics, too‑good‑to‑be‑true numbers.\n"
        "Return ONLY JSON: {\"claims\": [\"...\"], \"hidden_promo\": {\"value\": true, \"reason\": \"...\"}, \"red_flags\": [\"...\"]}\n"
        "CONTENT:\n" + combined_input
    )
    try:
        llm_resp = llm_json(prompt)
    except Exception as exc:  # pragma: no cover – defensive
        warnings.append(f"LLM call failed: {exc}")
        llm_resp = {}

    # ---------- 3. Validate LLM response ----------
    claims_raw = llm_resp.get("claims") if isinstance(llm_resp, dict) else []
    hidden_promo_raw = llm_resp.get("hidden_promo") if isinstance(llm_resp, dict) else {}
    red_flags_raw = llm_resp.get("red_flags") if isinstance(llm_resp, dict) else []

    if not isinstance(claims_raw, list):
        warnings.append("LLM returned invalid claims; using empty list")
        claims_raw = []
    if not isinstance(red_flags_raw, list):
        warnings.append("LLM returned invalid red_flags; using empty list")
        red_flags_raw = []

    # ---------- 4. Deduplicate claims & cap ----------
    seen = set()
    claims: List[str] = []
    for c in claims_raw:
        if not isinstance(c, str):
            continue
        c_clean = c.strip()
        if not c_clean:
            continue
        lowered = c_clean.lower()
        if lowered not in seen:
            seen.add(lowered)
            claims.append(c_clean)
        if len(claims) >= MAX_CLAIMS:
            break

    # ---------- 5. Deterministic promo detection ----------
    # Gather keyword hits from any of the three text sources.
    all_text = " ".join([content.get("text", ""), content.get("transcript", ""), content.get("ocr_text", "")])
    disclosure_hits = _detect_keywords(all_text, DISCLOSURE_KEYWORDS)
    commercial_hits = _detect_keywords(all_text, COMMERCIAL_KEYWORDS)

    promo: PromoInfo = {"detected": False, "type": "none", "evidence": []}
    if disclosure_hits:
        promo["detected"] = True
        promo["type"] = "disclosed"
        promo["evidence"] = disclosure_hits
    else:
        hidden_flag = False
        reason = ""
        if isinstance(hidden_promo_raw, dict):
            hidden_flag = bool(hidden_promo_raw.get("value"))
            reason = hidden_promo_raw.get("reason", "") or ""
        if commercial_hits or hidden_flag:
            promo["detected"] = True
            promo["type"] = "hidden"
            evidence = list(commercial_hits)
            if reason:
                evidence.append(reason)
            promo["evidence"] = evidence

    # ---------- 6. Assemble Signals ----------
    signals: Signals = {
        "claims": claims,
        "promo": promo,
        "red_flags": red_flags_raw,
        "warnings": warnings,
    }
    return signals
