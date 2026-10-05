"""
llm_client.py
-------------
LLM client wrapper with OpenRouter / OpenAI support and deterministic fallback.
Adheres strictly to the rule:
- Do not hardcode API keys.
- Use environment variables (OPENROUTER_API_KEY, OPENAI_API_KEY).
- Supports mock/deterministic mode for automated testing without network flakiness.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around LLM providers with automatic fallback and deterministic mode."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.is_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1" if self.is_openrouter else None)
        )
        self.model_name = (
            model_name
            or os.getenv("OPENROUTER_MODEL")
            or os.getenv("OPENAI_MODEL", "gpt-4o-mini" if self.is_openrouter else "gpt-4-turbo")
        )
        self.temperature = temperature
        self._client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        if not self.api_key:
            logger.info("No API key configured for LLMClient. Running in deterministic rule-synthesis mode.")
            return

        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
            logger.info("LLMClient initialized successfully with model %s.", self.model_name)
        except Exception as e:
            logger.warning("Could not initialize OpenAI client: %s. Using deterministic synthesizer.", e)
            self._client = None

    def is_available(self) -> bool:
        return self._client is not None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Query LLM if available; otherwise return empty string for deterministic synthesis."""
        if not self._client:
            return ""

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=600,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("LLM API call failed: %s. Falling back to deterministic synthesizer.", e)
            return ""
