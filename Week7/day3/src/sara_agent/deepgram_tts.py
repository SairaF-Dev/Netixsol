"""Shared Deepgram Flux TTS request configuration."""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class DeepgramTTSConfig:
    api_key: str
    endpoint: str
    model: str
    encoding: str
    speed: float
    expressivity: int
    timeout_seconds: float
    max_chars: int

    audio_mime_type: str = "audio/mpeg"

    @classmethod
    def from_env(cls) -> "DeepgramTTSConfig":
        api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY is not configured")

        encoding = os.getenv(
            "DEEPGRAM_TTS_ENCODING",
            "mp3",
        ).strip().casefold() or "mp3"
        if encoding != "mp3":
            raise ValueError(
                "DEEPGRAM_TTS_ENCODING must be mp3 for browser playback"
            )

        try:
            speed = float(os.getenv("DEEPGRAM_TTS_SPEED", "1.0"))
        except ValueError:
            speed = 1.0
        supported_speeds = {
            0.85,
            0.9,
            0.95,
            1.0,
            1.05,
            1.1,
            1.15,
        }
        if speed not in supported_speeds:
            speed = 1.0

        try:
            expressivity = int(
                os.getenv("DEEPGRAM_TTS_EXPRESSIVITY", "0")
            )
        except ValueError:
            expressivity = 0
        expressivity = max(-2, min(2, expressivity))

        return cls(
            api_key=api_key,
            endpoint=os.getenv(
                "DEEPGRAM_TTS_URL",
                "https://api.deepgram.com/v2/speak",
            ).strip()
            or "https://api.deepgram.com/v2/speak",
            model=os.getenv(
                "DEEPGRAM_TTS_MODEL",
                "flux-priya-en",
            ).strip()
            or "flux-priya-en",
            encoding=encoding,
            speed=speed,
            expressivity=expressivity,
            timeout_seconds=_bounded_float(
                "DEEPGRAM_TTS_TIMEOUT_SECONDS",
                45.0,
                5.0,
                120.0,
            ),
            max_chars=_bounded_int(
                "SARA_TTS_MAX_CHARS",
                2000,
                200,
                2000,
            ),
        )

    @property
    def request_url(self) -> str:
        query = urllib.parse.urlencode(
            {
                "model": self.model,
                "encoding": self.encoding,
                "speed": self.speed,
                "expressivity": self.expressivity,
            }
        )
        return f"{self.endpoint}?{query}"

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": self.audio_mime_type,
        }

    def payload(self, text: str) -> dict[str, str]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text must be non-empty")
        return {"text": text.strip()[: self.max_chars]}


def _bounded_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _bounded_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))
