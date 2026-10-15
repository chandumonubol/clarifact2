"""LLM wrapper for ClariFact.
Provides a single public function ``llm_json`` that sends a prompt to the configured
LLM provider (Ollama, Gemini, or Groq) and returns a parsed JSON dict.
All network calls use httpx and respect the time‑outs defined in the spec.
"""

import json
import logging
import time
from typing import Any

import httpx

from . import config

_logger = logging.getLogger(__name__)

def _strip_code_fences(text: str) -> str:
    """Remove surrounding markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove the first line if it is just fences (maybe with language)
        lines = text.splitlines()
        # If first line is ``` or ```json then drop it
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Drop a trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()

def _parse_json(text: str) -> Any:
    """Parse ``text`` as JSON, returning {} on failure.
    The caller may retry with a stricter prompt.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def _call_ollama(prompt: str) -> Any:
    url = f"{config.OLLAMA_URL}/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    try:
        resp = httpx.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("response", "")
        stripped = _strip_code_fences(raw)
        return _parse_json(stripped)
    except Exception as e:
        _logger.warning("Ollama request failed: %s", e)
        return None

def _call_gemini(prompt: str) -> Any:
    if not config.GEMINI_API_KEY:
        _logger.warning("Gemini API key not set")
        return None
    url = f"https://generativelanguage.googleapis.com/v1/models/{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=40.0)
        resp.raise_for_status()
        data = resp.json()
        # Navigate to the first text part
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        stripped = _strip_code_fences(text)
        return _parse_json(stripped)
    except Exception as e:
        _logger.warning("Gemini request failed: %s", e)
        return None

def _call_groq(prompt: str) -> Any:
    if not config.GROQ_API_KEY:
        _logger.warning("Groq API key not set")
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=40.0)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        stripped = _strip_code_fences(text)
        return _parse_json(stripped)
    except Exception as e:
        _logger.warning("Groq request failed: %s", e)
        return None

def llm_json(prompt: str, schema_hint: str = "") -> dict:
    """Send *prompt* to the configured LLM and return a JSON dict.
    If *schema_hint* is provided it is appended to the prompt to guide the model.
    The function never raises; on any error it returns an empty dict.
    """
    # Append schema hint if supplied
    full_prompt = prompt
    if schema_hint:
        full_prompt = f"{prompt}\nReturn ONLY JSON matching this shape: {schema_hint}"

    provider = config.LLM_PROVIDER
    # Helper to attempt a call and optionally fallback to Ollama
    def attempt(provider_name: str) -> Any:
        if provider_name == "ollama":
            return _call_ollama(full_prompt)
        if provider_name == "gemini":
            return _call_gemini(full_prompt)
        if provider_name == "groq":
            return _call_groq(full_prompt)
        return None

    # Primary attempt
    result = attempt(provider)
    if result is not None:
        return result

    # If primary provider failed and it's not Ollama, fallback to Ollama
    if provider != "ollama":
        _logger.warning("Falling back to Ollama for LLM request")
        result = _call_ollama(full_prompt)
        if result is not None:
            return result

    # Retry once with stricter instruction
    stricter_prompt = f"{prompt}\nReturn only valid JSON, no explanation."
    if schema_hint:
        stricter_prompt = f"{stricter_prompt}\nReturn ONLY JSON matching this shape: {schema_hint}"
    result = attempt(provider)
    if result is not None:
        return result
    # Fallback again with stricter prompt if not already using Ollama
    if provider != "ollama":
        result = _call_ollama(stricter_prompt)
        if result is not None:
            return result
    # Final failure – log and return empty dict
    _logger.error("LLM JSON request failed after retries")
    return {}
