"""One place that talks to the language model (Day 1 rewrites, Day 3 tutor).

Settings come from .env (git-ignored): LLM_PROVIDER, LLM_MODEL, LLM_API_KEY. The key is
never printed or logged. Retries with backoff on rate limits and server errors, because a
free-tier key hits per-minute limits during benchmark runs.
"""
from __future__ import annotations

import os
import re
import threading
import time
from functools import lru_cache

from ilm import config

RETRIES = 8
RPM = int(os.getenv("LLM_RPM", "14"))       # free tier allows 15 requests/minute per model
_last_call: dict[str, float] = {}
_lock = threading.Lock()


class LLMUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _client():
    if config.LLM_PROVIDER != "gemini":
        raise LLMUnavailable(f"LLM_PROVIDER={config.LLM_PROVIDER!r} is not supported yet (only 'gemini').")
    if not config.LLM_API_KEY:
        raise LLMUnavailable("No LLM_API_KEY in .env (copy .env.example to .env and fill it in).")
    from google import genai
    return genai.Client(api_key=config.LLM_API_KEY)


def _retryable(err: Exception) -> bool:
    """Per-minute limits and server errors pass; a used-up DAILY quota does not (it resets in
    hours, and every retry still counts against it)."""
    if "PerDay" in str(err):
        return False
    code = getattr(err, "code", None) or getattr(err, "status_code", None)
    return code in (429, 500, 502, 503, 504) or "RESOURCE_EXHAUSTED" in str(err) or "UNAVAILABLE" in str(err)


def _throttle(model: str):
    """Keep at least 60/RPM seconds between calls to the same model."""
    with _lock:
        wait = _last_call.get(model, 0.0) + 60 / RPM - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[model] = time.monotonic()


def _retry_after(err: Exception, attempt: int) -> float:
    """The server says 'Please retry in 5.3s' on rate limits; otherwise back off 2, 4, 8 ... s."""
    m = re.search(r"retry in ([0-9.]+)s", str(err))
    return float(m.group(1)) + 1 if m else min(2 ** attempt * 2, 60)


def ask(prompt: str, system: str | None = None, temperature: float = 0.2,
        model: str | None = None, max_tokens: int = 1024, json_mode: bool = False) -> str:
    """Send one prompt, return the text answer (a JSON string when json_mode)."""
    from google.genai import types
    cfg = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens,
                                      system_instruction=system,
                                      response_mime_type="application/json" if json_mode else None)
    model = model or config.LLM_MODEL
    for attempt in range(RETRIES):
        _throttle(model)
        try:
            r = _client().models.generate_content(model=model, contents=prompt, config=cfg)
            return r.text or ""
        except Exception as err:                     # the SDK raises several error types
            if attempt == RETRIES - 1 or not _retryable(err):
                raise
            time.sleep(_retry_after(err, attempt))
    return ""
