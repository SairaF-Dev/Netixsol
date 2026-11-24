"""
Small Gemini wrapper used by the Day 2 RAG code.

* The API key is read from .env (LLM_API_KEY) and never logged.
* Models: LLM_MODEL (default gemini-3.5-flash-lite, fast; used for drafting,
  rewriting, HyDE and answers) and LLM_JUDGE_MODEL (default gemini-3.5-flash,
  used where more care is needed, e.g. judging).
* `generate_json` asks for JSON matching a Pydantic model and validates it.
* Transient errors (rate limits, disconnects, 5xx) are retried with backoff.
* Every successful call is cached on disk (data/llm_cache) by a hash of
  model + prompt + schema, so re-running a script costs nothing and gives the
  same output.
"""

import hashlib
import re
import json
import os
import time
from pathlib import Path
from typing import Optional, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

from src.utils.logger import setup_logger

logger = setup_logger("gemini_client")

T = TypeVar("T", bound=BaseModel)
CACHE_DIR = Path("data/llm_cache")
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_JUDGE_MODEL = "gemini-3.5-flash-lite"  # free tier: gemini-3.5-flash allows only 20 requests/day


class GeminiClient:
    def __init__(self, model: Optional[str] = None, use_cache: bool = True, max_retries: int = 6):
        from google import genai

        load_dotenv(Path(".env"))
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY is not set in .env")
        self._client = genai.Client(api_key=api_key)
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self.use_cache = use_cache
        self.max_retries = max_retries
        # Free-tier keys allow only a few requests per minute: keep a minimum gap between calls.
        self.min_interval = float(os.getenv("LLM_MIN_INTERVAL", "4"))
        self._last_call = 0.0
        self.calls = 0          # API calls actually made (cache hits excluded)
        self.tokens = 0         # total tokens reported by the API
        # one entry per successful API call: seconds spent in the call itself (not the rate-limit wait above,
        # not failed attempts) and the token counts - used by evaluations/latency_cost.py
        self.call_log: list = []
        self.overloaded = 0                # 503 'high demand' retries (Gemini side), for the latency report

    @classmethod
    def judge(cls, **kwargs) -> "GeminiClient":
        load_dotenv(Path(".env"))
        return cls(model=os.getenv("LLM_JUDGE_MODEL", DEFAULT_JUDGE_MODEL), **kwargs)

    def _cache_path(self, payload: str) -> Path:
        digest = hashlib.sha256(f"{self.model}\n{payload}".encode("utf-8")).hexdigest()
        return CACHE_DIR / digest[:2] / f"{digest}.json"

    def _call(self, prompt: str, system: Optional[str], schema: Optional[Type[BaseModel]],
              temperature: float) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if schema else None,
            response_schema=schema,
        )
        delay = 4.0
        # Network drops (no DNS, laptop asleep, server disconnect, 503 overload) get many more
        # attempts than other errors: a long run should wait for the connection, not fail.
        network_errors = ("getaddrinfo", "disconnected", "503", "UNAVAILABLE", "timed out", "Connection")
        network_retries = 30
        attempt = 0
        while True:
            attempt += 1
            wait = self.min_interval - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()
            try:
                call_start = time.perf_counter()
                response = self._client.models.generate_content(model=self.model, contents=prompt, config=config)
                seconds = time.perf_counter() - call_start
                self.calls += 1
                usage = response.usage_metadata
                if usage and usage.total_token_count:
                    self.tokens += usage.total_token_count
                self.call_log.append({"seconds": round(seconds, 3),
                                      "input_tokens": (usage.prompt_token_count or 0) if usage else 0,
                                      "output_tokens": ((usage.total_token_count or 0) - (usage.prompt_token_count or 0)) if usage else 0})
                if not response.text:
                    raise RuntimeError("empty response")
                return response.text
            except Exception as exc:  # network / rate limit / server errors
                message = str(exc)
                if any(code in message for code in ("400 INVALID_ARGUMENT", "401", "403", "404 NOT_FOUND")):
                    raise
                limit = network_retries if any(e in message for e in network_errors) else self.max_retries
                if "503" in message or "UNAVAILABLE" in message:
                    self.overloaded += 1
                if attempt >= limit:
                    raise
                # A 429 says how long to wait ("retryDelay": "37s"); otherwise back off exponentially.
                suggested = re.search(r"retry(?:Delay)?['\"]?:?\s*['\"]?(\d+(?:\.\d+)?)s", message)
                pause = float(suggested.group(1)) + 1 if suggested else delay
                if "PerDay" in message or "per day" in message.lower():
                    raise RuntimeError("Gemini daily quota exhausted; try again tomorrow or use another key") from exc
                logger.warning("Gemini call failed (%s/%s): %s; retrying in %.0fs",
                               attempt, limit, message[:300], pause)
                time.sleep(pause)
                delay = min(delay * 2, 90)

    def generate_text(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
        return self._cached(prompt, system, None, temperature)

    def generate_json(self, prompt: str, schema: Type[T], system: Optional[str] = None,
                      temperature: float = 0.2) -> T:
        return schema.model_validate_json(self._cached(prompt, system, schema, temperature))

    def _cached(self, prompt, system, schema, temperature) -> str:
        key = json.dumps({"p": prompt, "s": system, "t": temperature,
                          "schema": schema.model_json_schema() if schema else None}, ensure_ascii=False, sort_keys=True)
        path = self._cache_path(key)
        if self.use_cache and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["text"]
        text = self._call(prompt, system, schema, temperature)
        if self.use_cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": self.model, "text": text}, ensure_ascii=False), encoding="utf-8")
        return text
