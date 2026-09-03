"""Shared Fish Audio S2-Pro TTS request configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "opus": "audio/ogg; codecs=opus",
}


@dataclass(frozen=True)
class FishAudioConfig:
    api_key: str
    endpoint: str
    model: str
    reference_id: str | None
    audio_format: str
    latency: str
    sample_rate: int
    mp3_bitrate: int
    speed: float
    chunk_length: int
    timeout_seconds: float
    max_chars: int

    @property
    def audio_mime_type(self) -> str:
        return _MIME_TYPES[self.audio_format]

    @classmethod
    def from_env(cls) -> "FishAudioConfig":
        api_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
        if not api_key:
            raise ValueError("FISH_AUDIO_API_KEY is not configured")

        audio_format = (
            os.getenv("FISH_AUDIO_FORMAT")
            or os.getenv("FISH_AUDIO_OUTPUT_FORMAT")
            or "mp3"
        ).strip().casefold() or "mp3"
        if audio_format not in _MIME_TYPES:
            raise ValueError(
                "FISH_AUDIO_FORMAT must be mp3, wav, pcm, or opus"
            )

        latency = os.getenv(
            "FISH_AUDIO_LATENCY",
            "balanced",
        ).strip().casefold() or "balanced"
        if latency not in {"low", "balanced", "normal"}:
            raise ValueError(
                "FISH_AUDIO_LATENCY must be low, balanced, or normal"
            )

        reference_id = (
            os.getenv("FISH_AUDIO_REFERENCE_ID")
            or os.getenv("FISH_AUDIO_VOICE_ID")
            or ""
        ).strip() or None

        return cls(
            api_key=api_key,
            endpoint=(
                os.getenv("FISH_AUDIO_TTS_URL")
                or os.getenv("FISH_AUDIO_API_URL")
                or "https://api.fish.audio/v1/tts"
            ).strip()
            or "https://api.fish.audio/v1/tts",
            model=os.getenv(
                "FISH_AUDIO_MODEL",
                "s2-pro",
            ).strip()
            or "s2-pro",
            reference_id=reference_id,
            audio_format=audio_format,
            latency=latency,
            sample_rate=_env_int(
                "FISH_AUDIO_SAMPLE_RATE",
                44100,
                minimum=8000,
                maximum=48000,
            ),
            mp3_bitrate=_env_choice_int(
                "FISH_AUDIO_MP3_BITRATE",
                128,
                {64, 128, 192},
            ),
            speed=_env_float(
                "FISH_AUDIO_SPEED",
                1.0,
                minimum=0.5,
                maximum=2.0,
            ),
            chunk_length=_env_int(
                "FISH_AUDIO_CHUNK_LENGTH",
                200,
                minimum=100,
                maximum=300,
            ),
            timeout_seconds=_env_float(
                "FISH_AUDIO_TIMEOUT_SECONDS",
                60.0,
                minimum=5.0,
                maximum=240.0,
            ),
            max_chars=_env_int(
                "SARA_TTS_MAX_CHARS",
                1200,
                minimum=200,
                maximum=8000,
            ),
        )

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": self.audio_mime_type,
            "model": self.model,
        }

    def payload(self, text: str) -> dict[str, object]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text must be non-empty")

        payload: dict[str, object] = {
            "text": text.strip()[: self.max_chars],
            "format": self.audio_format,
            "latency": self.latency,
            "sample_rate": self.sample_rate,
            "chunk_length": self.chunk_length,
            "normalize": True,
            "prosody": {
                "speed": self.speed,
                "volume": 0,
                "normalize_loudness": True,
            },
        }
        if self.audio_format == "mp3":
            payload["mp3_bitrate"] = self.mp3_bitrate
        if self.reference_id:
            payload["reference_id"] = self.reference_id
        return payload


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _env_choice_int(
    name: str,
    default: int,
    choices: set[int],
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return value if value in choices else default


def _env_float(
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))
