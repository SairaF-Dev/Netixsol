"""One place that talks to the language model (Day 1 rewrites, Day 3 tutor).

Settings come from .env (git-ignored): LLM_PROVIDER, LLM_MODEL, LLM_API_KEY. The key is
never printed or logged. Retries with backoff on rate limits and server errors, because a
free-tier key hits per-minute limits during benchmark runs.
"""
from __future__ import annotations

import time
from functools import lru_cache

from ilm import config

RETRIES = 5


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
    code = getattr(err, "code", None) or getattr(err, "status_code", None)
    return code in (429, 500, 502, 503, 504) or "RESOURCE_EXHAUSTED" in str(err) or "UNAVAILABLE" in str(err)


def ask(prompt: str, system: str | None = None, temperature: float = 0.2,
        model: str | None = None, max_tokens: int = 1024) -> str:
    """Send one prompt, return the text answer."""
    from google.genai import types
    cfg = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens,
                                      system_instruction=system)
    for attempt in range(RETRIES):
        try:
            r = _client().models.generate_content(model=model or config.LLM_MODEL, contents=prompt, config=cfg)
            return r.text or ""
        except Exception as err:                     # the SDK raises several error types
            if attempt == RETRIES - 1 or not _retryable(err):
                raise
            time.sleep(2 ** attempt * 2)             # 2, 4, 8, 16 s
    return ""
