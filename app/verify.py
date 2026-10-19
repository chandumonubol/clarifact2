"""Verification of a single claim.

Provides :func:`verify_claim` which gathers web evidence and asks an LLM to
judge the claim. The function never raises – any unexpected error results in a
fallback ``unverified`` result.
"""

import logging
import os
import time
import urllib.parse
from typing import List, Dict

import httpx
from ddgs import DDGS

from app.interfaces import (
    VerifiedClaim,
    Source,
    VERDICTS,
)
from app.llm import llm_json

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _run_llm(prompt: str) -> dict:
    """Call :func:`app.llm.llm_json` and return a dict, never raising.

    If the LLM call fails or does not return a proper dict, returns an empty
    dict and logs the error.
    """
    try:
        result = llm_json(prompt)
        if isinstance(result, dict):
            return result
        logging.warning("LLM returned non‑dict, treating as empty")
    except Exception as exc:  # pragma: no cover – defensive
        logging.warning(f"LLM call failed: {exc}")
    return {}


def _dedupe_by_url(evidence: List[Dict]) -> List[Dict]:
    """Remove duplicate evidence items based on the ``url`` field.

    Preserves order of first occurrence.
    """
    seen = set()
    uniq: List[Dict] = []
    for ev in evidence:
        url = ev.get("url")
        if url and url not in seen:
            seen.add(url)
            uniq.append(ev)
    return uniq


def _trim_to_limit(evidence_strings: List[str], limit: int = 1500) -> List[str]:
    """Trim a list of numbered evidence strings so the concatenated length
    does not exceed ``limit`` characters.
    """
    out: List[str] = []
    total = 0
    for s in evidence_strings:
        if total + len(s) + 1 > limit:
            break
        out.append(s)
        total += len(s) + 1  # include a space/newline separator
    return out

# ---------------------------------------------------------------------------
# Main verification function
# ---------------------------------------------------------------------------

def verify_claim(claim_text: str) -> VerifiedClaim:
    """Verify a single *claim_text*.

    The function follows the specification in the B3 step:
    1. Generate 1‑2 short search queries via ``llm_json``.
    2. Gather evidence from DuckDuckGo, Wikipedia, and optionally the Google Fact
       Check Tools API.
    3. If no usable evidence is found, return ``unverified``.
    4. Otherwise ask the LLM to judge the claim using ONLY the collected
       evidence and return a :class:`VerifiedClaim`.
    The function never raises – any unexpected exception results in a safe
    ``unverified`` result with an explanatory message.
    """
    # --------------------------------------------------------------------
    # 1️⃣  Generate search queries
    # --------------------------------------------------------------------
    try:
        query_prompt = (
            "Generate 1‑2 short web‑search queries that would help verify the following claim. "
            "Return ONLY JSON with the key \"queries\": [\"...\", \"...\"].\n"
            f"Claim: {claim_text}"
        )
        q_resp = _run_llm(query_prompt)
        queries = q_resp.get("queries") if isinstance(q_resp, dict) else None
        if not isinstance(queries, list) or not queries:
            raise ValueError("No queries returned")
    except Exception:  # pragma: no cover – fallback
        logging.warning("LLM query generation failed, falling back to claim text as query")
        queries = [claim_text]

    # --------------------------------------------------------------------
    # 2️⃣  Gather evidence
    # --------------------------------------------------------------------
    evidence_items: List[Dict] = []
    # a) DuckDuckGo (ddgs)
    for q in queries:
        attempts = 0
        while attempts < 2:
            try:
                ddgs = DDGS()
                results = ddgs.text(q, max_results=5)
                for r in results:
                    title = r.get("title", "")
                    url = r.get("url", "")
                    snippet = r.get("body", "") or r.get("snippet", "")
                    if url:
                        evidence_items.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet[:250],
                        })
                break
            except Exception as exc:  # pragma: no cover – network/parse errors
                attempts += 1
                logging.warning(f"DDGS search failed (attempt {attempts}) for query '{q}': {exc}")
                time.sleep(0.5)
    # b) Wikipedia
    try:
        wiki_search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": claim_text,
            "format": "json",
        }
        rsp = httpx.get(wiki_search_url, params=params, timeout=10.0)
        rsp.raise_for_status()
        data = rsp.json()
        search_results = data.get("query", {}).get("search", [])
        if search_results:
            title = search_results[0].get("title")
            if title:
                # Fetch summary via REST API
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                sum_rsp = httpx.get(summary_url, timeout=10.0)
                sum_rsp.raise_for_status()
                sum_data = sum_rsp.json()
                snippet = sum_data.get("extract", "")[:250]
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                evidence_items.append({
                    "title": title,
                    "url": page_url,
                    "snippet": snippet,
                })
    except Exception as exc:  # pragma: no cover – optional source
        logging.warning(f"Wikipedia evidence fetch failed: {exc}")
    # c) Google Fact Check Tools (optional)
    factcheck_key = os.getenv("FACTCHECK_API_KEY")
    if factcheck_key:
        try:
            fc_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {"query": claim_text, "key": factcheck_key}
            fc_rsp = httpx.get(fc_url, params=params, timeout=10.0)
            fc_rsp.raise_for_status()
            fc_data = fc_rsp.json()
            for claim in fc_data.get("claims", []):
                for review in claim.get("claimReview", []):
                    title = review.get("title", "")
                    url = review.get("url", "")
                    snippet = review.get("textualRating", "")[:250]
                    if url:
                        evidence_items.append({"title": title, "url": url, "snippet": snippet})
        except Exception as exc:  # pragma: no cover – optional source
            logging.warning(f"Fact‑check API failed: {exc}")

    # Deduplicate by URL and keep order
    evidence_items = _dedupe_by_url(evidence_items)

    # --------------------------------------------------------------------
    # 3️⃣  No evidence case
    # --------------------------------------------------------------------
    if not evidence_items:
        return {
            "text": claim_text,
            "verdict": "unverified",
            "explanation": "No usable evidence found.",
            "sources": [],
            "had_evidence": False,
        }

    # --------------------------------------------------------------------
    # 4️⃣  Build evidence list for LLM prompt (limit ~1500 chars)
    # --------------------------------------------------------------------
    numbered_strings: List[str] = []
    for idx, ev in enumerate(evidence_items, start=1):
        title = ev.get("title", "")
        snippet = ev.get("snippet", "")
        numbered_strings.append(f"[{idx}] {title} - {snippet}")
    numbered_strings = _trim_to_limit(numbered_strings, limit=1500)
    evidence_text = "\n".join(numbered_strings)

    # --------------------------------------------------------------------
    # 5️⃣  LLM judgment on the claim
    # --------------------------------------------------------------------
    try:
        judge_prompt = (
            f"Claim: {claim_text}\n"
            f"Evidence (numbered):\n{evidence_text}\n"
            "Using ONLY this evidence, decide: supported, contradicted, misleading (partly true but exaggerated or missing context), or unverified (evidence does not decide).\n"
            "Return ONLY JSON: {\"verdict\": \"supported|contradicted|misleading|unverified\", \"explanation\": \"...\", \"used_sources\": [1, 3]}"
        )
        verdict_resp = _run_llm(judge_prompt)
        verdict = verdict_resp.get("verdict", "unverified")
        explanation = verdict_resp.get("explanation", "")
        used_idxs = verdict_resp.get("used_sources", [])
        if verdict not in VERDICTS:
            logging.warning(f"LLM returned unknown verdict '{verdict}', treating as unverified")
            verdict = "unverified"
    except Exception as exc:  # pragma: no cover – fallback
        logging.warning(f"LLM judgment failed: {exc}")
        verdict = "unverified"
        explanation = "LLM judgment failed."
        used_idxs = []

    # --------------------------------------------------------------------
    # 6️⃣  Build sources list
    # --------------------------------------------------------------------
    sources: List[Source] = []
    if used_idxs and verdict != "unverified":
        for i in used_idxs:
            if 1 <= i <= len(evidence_items):
                ev = evidence_items[i - 1]
                sources.append({"title": ev.get("title", ""), "url": ev.get("url", "")})
    else:
        # fallback to top two evidence items if verdict is not unverified
        if verdict != "unverified":
            for ev in evidence_items[:2]:
                sources.append({"title": ev.get("title", ""), "url": ev.get("url", "")})

    return {
        "text": claim_text,
        "verdict": verdict,
        "explanation": explanation,
        "sources": sources,
        "had_evidence": bool(evidence_items),
    }

# End of file
