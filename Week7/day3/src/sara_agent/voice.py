from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import json
import mimetypes
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .latency import LatencyTracker
from .deepgram_config import (
    DEFAULT_DEEPGRAM_LANGUAGE,
    load_deepgram_keyterms,
)
from .deepgram_tts import DeepgramTTSConfig
from .fish_audio import FishAudioConfig
from .transcript_normalizer import normalize_transcript
from .voice_response_formatter import format_voice_response
from .natural_speech import auto_naturalize_speech, naturalize_speech


_ALLOWED_AUDIO_SUFFIXES = {
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
    ".mp4",
    ".mpeg",
    ".mpga",
}


class SpeechToTextProvider(Protocol):
    name: str

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "input.wav",
    ) -> str:
        ...


class TextToSpeechProvider(Protocol):
    name: str
    audio_mime_type: str

    def synthesize(self, text: str) -> bytes:
        ...


@dataclass
class VoiceTurnResult:
    transcript: str
    response_text: str
    audio_bytes: bytes
    latency_ms: dict[str, float]
    audio_mime_type: str = "audio/mpeg"
    raw_transcript: str = ""
    spoken_text: str = ""


class FasterWhisperSTTProvider:
    """Local CPU/GPU STT provider using faster-whisper.

    The model is loaded lazily on the first voice turn so text-only startup
    remains fast. CPU + int8 is the default development configuration and is
    Docker-friendly. A CUDA deployment can later switch device/compute type
    through environment variables without changing application code.
    """

    name = "faster-whisper"

    def __init__(self) -> None:
        self.model_name = os.getenv(
            "FASTER_WHISPER_MODEL",
            "base",
        ).strip() or "base"
        self.device = os.getenv(
            "FASTER_WHISPER_DEVICE",
            "cpu",
        ).strip() or "cpu"
        self.compute_type = os.getenv(
            "FASTER_WHISPER_COMPUTE_TYPE",
            "int8",
        ).strip() or "int8"
        self.language = (
            os.getenv("FASTER_WHISPER_LANGUAGE", "").strip()
            or None
        )
        self.initial_prompt = (
            os.getenv("FASTER_WHISPER_INITIAL_PROMPT", "").strip()
            or None
        )
        self.beam_size = self._env_int(
            "FASTER_WHISPER_BEAM_SIZE",
            1,
            minimum=1,
            maximum=5,
        )
        self.vad_filter = self._env_bool(
            "FASTER_WHISPER_VAD_FILTER",
            True,
        )
        self.cpu_threads = self._env_int(
            "FASTER_WHISPER_CPU_THREADS",
            0,
            minimum=0,
            maximum=64,
        )
        self._model = None
        self._model_lock = threading.Lock()

    def _get_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ImportError(
                    "faster-whisper is not installed. Run: "
                    "pip install faster-whisper"
                ) from exc

            kwargs = {
                "device": self.device,
                "compute_type": self.compute_type,
            }

            if self.cpu_threads > 0:
                kwargs["cpu_threads"] = self.cpu_threads

            self._model = WhisperModel(
                self.model_name,
                **kwargs,
            )

        return self._model

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "input.wav",
    ) -> str:
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise ValueError("audio_bytes must be non-empty")

        suffix = Path(filename).suffix.casefold() or ".wav"
        if suffix not in _ALLOWED_AUDIO_SUFFIXES:
            suffix = ".wav"

        path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            ) as temp:
                temp.write(audio_bytes)
                temp.flush()
                path = temp.name

            model = self._get_model()
            segments, _info = model.transcribe(
                path,
                language=self.language,
                task="transcribe",
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                condition_on_previous_text=False,
                word_timestamps=False,
                initial_prompt=self.initial_prompt,
            )

            return " ".join(
                segment.text.strip()
                for segment in segments
                if segment.text and segment.text.strip()
            ).strip()
        finally:
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass

    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError:
            value = default
        return max(minimum, min(maximum, value))

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().casefold() not in {
            "0",
            "false",
            "no",
            "off",
        }


class EdgeTTSProvider:
    """Development/demo TTS provider with no project API key required.

    This is intentionally behind the same interface as paid production TTS.
    It can later be replaced by ElevenLabs/Fish Audio without changing Sara.
    """

    name = "edge-tts"
    audio_mime_type = "audio/mpeg"

    def __init__(self) -> None:
        self.voice = os.getenv(
            "EDGE_TTS_VOICE",
            "ur-PK-UzmaNeural",
        ).strip() or "ur-PK-UzmaNeural"
        self.rate = os.getenv(
            "EDGE_TTS_RATE",
            "+0%",
        ).strip() or "+0%"
        self.volume = os.getenv(
            "EDGE_TTS_VOLUME",
            "+0%",
        ).strip() or "+0%"
        self.pitch = os.getenv(
            "EDGE_TTS_PITCH",
            "+0Hz",
        ).strip() or "+0Hz"

    def synthesize(self, text: str) -> bytes:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text must be non-empty")

        max_chars = self._env_int(
            "SARA_TTS_MAX_CHARS",
            1200,
            minimum=200,
            maximum=8000,
        )
        safe_text = text.strip()[:max_chars]

        try:
            return self._run_async(
                self._synthesize_async(safe_text)
            )
        except ImportError:
            raise
        except Exception as exc:
            raise RuntimeError(
                "Edge TTS synthesis failed. Check internet connectivity "
                "and EDGE_TTS_VOICE configuration."
            ) from exc

    async def _synthesize_async(self, text: str) -> bytes:
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError(
                "edge-tts is not installed. Run: pip install edge-tts"
            ) from exc

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                data = chunk.get("data")
                if data:
                    chunks.append(data)

        audio = b"".join(chunks)
        if not audio:
            raise RuntimeError("TTS provider returned empty audio")
        return audio

    @staticmethod
    def _run_async(coro):
        """Run an async TTS call safely from sync Streamlit/FastAPI code."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # A running event loop already exists in this thread. Execute the
        # coroutine in a short worker thread with its own loop.
        result: dict[str, object] = {}
        error: dict[str, BaseException] = {}

        def runner() -> None:
            try:
                result["value"] = asyncio.run(coro)
            except BaseException as exc:  # pragma: no cover - rare host case
                error["value"] = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "value" in error:
            raise error["value"]
        return result["value"]

    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError:
            value = default
        return max(minimum, min(maximum, value))


class DeepgramSTTProvider:
    """Cloud STT provider for low-latency UrduLish transcription.

    Uses Deepgram's HTTPS /v1/listen endpoint for the current Streamlit
    push-to-talk demo. The provider boundary is intentionally compatible
    with a later streaming/Vapi transport without changing SaraChatbot.
    """

    name = "deepgram"

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY is not configured")

        self.model = os.getenv(
            "DEEPGRAM_MODEL",
            "nova-3",
        ).strip() or "nova-3"

        # UrduLish code-switches inside a single utterance, so multilingual
        # Nova-3 is the measured default. Urdu-only deployments may set `ur`.
        self.language = os.getenv(
            "DEEPGRAM_LANGUAGE",
            DEFAULT_DEEPGRAM_LANGUAGE,
        ).strip() or DEFAULT_DEEPGRAM_LANGUAGE

        self.smart_format = self._env_bool(
            "DEEPGRAM_SMART_FORMAT",
            True,
        )

        self.keyterms = load_deepgram_keyterms()

        self.timeout_seconds = self._env_float(
            "DEEPGRAM_TIMEOUT_SECONDS",
            20.0,
            minimum=3.0,
            maximum=60.0,
        )

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "input.wav",
    ) -> str:
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise ValueError("audio_bytes must be non-empty")

        query_items = [
            ("model", self.model),
            ("language", self.language),
            (
                "smart_format",
                "true" if self.smart_format else "false",
            ),
        ]

        # Deepgram expects one repeated `keyterm` query parameter per term.
        # Do not join these into one comma-separated API value.
        query_items.extend(
            ("keyterm", term)
            for term in self.keyterms
        )

        url = (
            "https://api.deepgram.com/v1/listen?"
            + urllib.parse.urlencode(query_items)
        )

        content_type = (
            mimetypes.guess_type(filename)[0]
            or "audio/wav"
        )

        request = urllib.request.Request(
            url=url,
            data=bytes(audio_bytes),
            method="POST",
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": content_type,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except Exception as exc:
            raise RuntimeError(
                "Deepgram transcription failed. Check DEEPGRAM_API_KEY, "
                "internet connectivity, and provider configuration."
            ) from exc

        try:
            return str(
                payload["results"]["channels"][0]["alternatives"][0]["transcript"]
                or ""
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Deepgram returned an unexpected transcription response."
            ) from exc

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().casefold() not in {
            "0",
            "false",
            "no",
            "off",
        }

    @staticmethod
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


class OpenAISTTProvider:
    name = "openai"

    def __init__(self, client=None) -> None:
        self.client = client or self._build_client()

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "input.webm",
    ) -> str:
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise ValueError("audio_bytes must be non-empty")

        suffix = Path(filename).suffix.casefold() or ".webm"
        if suffix not in _ALLOWED_AUDIO_SUFFIXES:
            suffix = ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix) as temp:
            temp.write(audio_bytes)
            temp.flush()
            with open(temp.name, "rb") as audio:
                response = self.client.audio.transcriptions.create(
                    model=os.getenv(
                        "OPENAI_STT_MODEL",
                        "gpt-4o-mini-transcribe",
                    ),
                    file=audio,
                )

        return str(response.text or "").strip()

    @staticmethod
    def _build_client():
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        return OpenAI(api_key=api_key)


class OpenAITTSProvider:
    name = "openai"
    audio_mime_type = "audio/mpeg"

    def __init__(self, client=None) -> None:
        self.client = client or OpenAISTTProvider._build_client()

    def synthesize(self, text: str) -> bytes:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text must be non-empty")

        response = self.client.audio.speech.create(
            model=os.getenv(
                "OPENAI_TTS_MODEL",
                "gpt-4o-mini-tts",
            ),
            voice=os.getenv(
                "OPENAI_TTS_VOICE",
                "alloy",
            ),
            input=text.strip()[: int(os.getenv("SARA_TTS_MAX_CHARS", "1200"))],
        )
        return response.read()


class ElevenLabsTTSProvider:
    """Turn-based ElevenLabs TTS using the current SDK interface."""

    name = "elevenlabs"
    audio_mime_type = "audio/mpeg"

    def __init__(self, client=None) -> None:
        api_key = os.getenv(
            "ELEVENLABS_API_KEY",
            "",
        ).strip()
        if not api_key and client is None:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured"
            )

        if client is None:
            try:
                from elevenlabs.client import ElevenLabs
            except ImportError as exc:
                raise ImportError(
                    "elevenlabs is not installed. "
                    "Run: pip install elevenlabs"
                ) from exc
            client = ElevenLabs(api_key=api_key)

        self.client = client
        self.voice_id = os.getenv(
            "ELEVENLABS_VOICE_ID",
            "EXAVITQu4vr4xnSDxMaL",
        ).strip() or "EXAVITQu4vr4xnSDxMaL"
        self.model_id = os.getenv(
            "ELEVENLABS_MODEL_ID",
            "eleven_turbo_v2_5",
        ).strip() or "eleven_turbo_v2_5"
        self.output_format = os.getenv(
            "ELEVENLABS_OUTPUT_FORMAT",
            "mp3_44100_128",
        ).strip() or "mp3_44100_128"

    def synthesize(self, text: str) -> bytes:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text must be non-empty")

        max_chars = int(
            os.getenv(
                "SARA_TTS_MAX_CHARS",
                "1200",
            )
        )
        safe_text = text.strip()[:max_chars]
        text_to_speech = getattr(
            self.client,
            "text_to_speech",
            None,
        )

        if (
            text_to_speech is not None
            and hasattr(text_to_speech, "convert")
        ):
            chunks = text_to_speech.convert(
                text=safe_text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format=self.output_format,
            )
        else:
            chunks = self.client.generate(
                text=safe_text,
                voice=self.voice_id,
                model=self.model_id,
                stream=True,
            )

        audio = b"".join(chunks)
        if not audio:
            raise RuntimeError(
                "TTS provider returned empty audio"
            )
        return audio


class DeepgramTTSProvider:
    """Turn-based Deepgram Flux TTS using browser-native MP3."""

    name = "deepgram-flux-priya"
    audio_mime_type = "audio/mpeg"

    def __init__(self, config: DeepgramTTSConfig | None = None) -> None:
        self.config = config or DeepgramTTSConfig.from_env()

    def synthesize(self, text: str) -> bytes:
        request = urllib.request.Request(
            url=self.config.request_url,
            data=json.dumps(self.config.payload(text)).encode("utf-8"),
            method="POST",
            headers=self.config.headers(),
        )
        with urllib.request.urlopen(
            request,
            timeout=self.config.timeout_seconds,
        ) as response:
            audio = response.read()
        if not audio:
            raise RuntimeError("Deepgram TTS returned empty audio")
        return audio


class FishAudioTTSProvider:
    """Turn-based Fish Audio TTS over its production HTTP endpoint."""

    name = "fish-audio"

    def __init__(self, config: FishAudioConfig | None = None) -> None:
        self.config = config or FishAudioConfig.from_env()
        self.audio_mime_type = self.config.audio_mime_type
        self.sample_rate = self.config.sample_rate

    def synthesize(self, text: str) -> bytes:
        payload = self.config.payload(text)
        request = urllib.request.Request(
            url=self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=self.config.headers(),
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                audio = response.read()
        except Exception as exc:
            raise RuntimeError(
                "Fish Audio synthesis failed. Check the API key, account "
                "credits, reference ID, and provider connectivity."
            ) from exc

        if not audio:
            raise RuntimeError("Fish Audio returned empty audio")
        return audio


class FallbackTTSProvider:
    """Use a secondary TTS provider when the primary fails before playback."""

    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}-with-{fallback.name}-fallback"
        self.active_provider_name = primary.name
        self.active_provider = primary

    @property
    def audio_mime_type(self) -> str:
        return self.active_provider.audio_mime_type

    def synthesize(self, text: str) -> bytes:
        self.active_provider_name = self.primary.name
        self.active_provider = self.primary
        try:
            return self.primary.synthesize(text)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Primary TTS failed; using %s fallback (%s)",
                self.fallback.name,
                exc.__class__.__name__,
            )
            self.active_provider_name = self.fallback.name
            self.active_provider = self.fallback
            return self.fallback.synthesize(text)


class CompositeVoiceProvider:
    """Combines independently replaceable STT and TTS implementations."""

    def __init__(
        self,
        stt: SpeechToTextProvider,
        tts: TextToSpeechProvider,
    ) -> None:
        self.stt = stt
        self.tts = tts

    @property
    def audio_mime_type(self) -> str:
        return getattr(
            self.tts,
            "audio_mime_type",
            "audio/mpeg",
        )

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "input.wav",
    ) -> str:
        return self.stt.transcribe(audio_bytes, filename)

    def synthesize(self, text: str) -> bytes:
        return self.tts.synthesize(text)

    def status(self) -> dict[str, str]:
        return {
            "stt": getattr(self.stt, "name", self.stt.__class__.__name__),
            "tts": getattr(self.tts, "name", self.tts.__class__.__name__),
            "audio_mime_type": self.audio_mime_type,
        }


class OpenAIVoiceProvider(CompositeVoiceProvider):
    """Backward-compatible all-OpenAI provider."""

    def __init__(self, client=None) -> None:
        if client is not None:
            super().__init__(
                OpenAISTTProvider(client=client),
                OpenAITTSProvider(client=client),
            )
        else:
            super().__init__(
                OpenAISTTProvider(),
                OpenAITTSProvider(),
            )


def build_voice_provider() -> CompositeVoiceProvider:
    """Build the configured STT/TTS pair.

    Development supports provider switching without changing Sara:
      STT: faster-whisper (local) OR Deepgram (recommended voice demo)
      TTS: edge-tts, ElevenLabs, or OpenAI
    """

    stt_name = os.getenv(
        "VOICE_STT_PROVIDER",
        "faster-whisper",
    ).strip().casefold()
    tts_name = os.getenv(
        "VOICE_TTS_PROVIDER",
        "edge",
    ).strip().casefold()

    if stt_name in {
        "faster-whisper",
        "faster_whisper",
        "whisper",
        "local",
    }:
        stt = FasterWhisperSTTProvider()
    elif stt_name in {"deepgram", "dg"}:
        stt = DeepgramSTTProvider()
    elif stt_name == "openai":
        stt = OpenAISTTProvider()
    else:
        raise ValueError(
            f"Unsupported VOICE_STT_PROVIDER={stt_name!r}. "
            "Supported: faster-whisper, deepgram, openai."
        )

    if tts_name in {
        "edge",
        "edge-tts",
        "edge_tts",
    }:
        tts = EdgeTTSProvider()
    elif tts_name == "openai":
        tts = OpenAITTSProvider()
    elif tts_name in {
        "elevenlabs",
        "eleven-labs",
    }:
        tts = ElevenLabsTTSProvider()
    elif tts_name in {
        "fish",
        "fish-audio",
        "fish_audio",
    }:
        primary_tts = FishAudioTTSProvider()
        fallback_name = os.getenv(
            "SARA_TTS_FALLBACK_PROVIDER",
            "edge-tts",
        ).strip().casefold()
        tts = (
            FallbackTTSProvider(
                primary_tts,
                EdgeTTSProvider(),
            )
            if fallback_name in {"edge", "edge-tts", "edge_tts"}
            else primary_tts
        )
    elif tts_name in {"deepgram", "deepgram-tts", "deepgram_tts", "dg"}:
        primary_tts = DeepgramTTSProvider()
        fallback_name = os.getenv(
            "SARA_TTS_FALLBACK_PROVIDER",
            "edge-tts",
        ).strip().casefold()
        tts = (
            FallbackTTSProvider(
                primary_tts,
                EdgeTTSProvider(),
            )
            if fallback_name in {"edge", "edge-tts", "edge_tts"}
            else primary_tts
        )
    else:
        raise ValueError(
            f"Unsupported VOICE_TTS_PROVIDER={tts_name!r}. "
            "Supported: edge, deepgram, fish-audio, elevenlabs, openai."
        )

    return CompositeVoiceProvider(stt, tts)


class VoicePipeline:
    """Turn-based Speech -> Sara -> Voice pipeline.

    Day 3's <2s latency target is measured, not hard-coded. The first local
    Whisper turn can be slower because the model may need to download/load.
    Real production streaming/barge-in will be a separate provider/transport
    layer (for example Vapi + Deepgram + streaming TTS).
    """

    def __init__(self, chatbot, voice_provider) -> None:
        self.chatbot = chatbot
        self.voice = voice_provider

        setter = getattr(self.chatbot, "set_response_mode", None)
        if callable(setter):
            setter("voice")

    def run_turn(
        self,
        audio_bytes: bytes,
        filename: str = "input.wav",
    ) -> VoiceTurnResult:
        tracker = LatencyTracker()

        with tracker.track("stt_ms"):
            raw_transcript = self.voice.transcribe(
                audio_bytes,
                filename,
            )

        transcript = normalize_transcript(raw_transcript)

        if not transcript:
            response = (
                "Sorry, awaaz clear samajh nahi aayi. "
                "Please dobara bol dein."
            )
            spoken_response = naturalize_speech(
                response,
                event="clarification",
            )

            with tracker.track("tts_ms"):
                audio = self.voice.synthesize(spoken_response)

            metrics = dict(tracker.metrics)
            metrics["agent_ms"] = 0.0
            metrics["total_ms"] = tracker.total_ms()
            return VoiceTurnResult(
                transcript="",
                response_text=response,
                audio_bytes=audio,
                latency_ms=metrics,
                audio_mime_type=getattr(
                    self.voice,
                    "audio_mime_type",
                    "audio/mpeg",
                ),
                raw_transcript=raw_transcript,
                spoken_text=spoken_response,
            )

        with tracker.track("agent_ms"):
            response = self.chatbot.handle_message(transcript)

        spoken_response = format_voice_response(response)

        spoken_response = auto_naturalize_speech(
            spoken_response,
            user_text=transcript,
        )

        with tracker.track("tts_ms"):
            audio = self.voice.synthesize(spoken_response)

        metrics = dict(tracker.metrics)
        metrics["total_ms"] = tracker.total_ms()
        return VoiceTurnResult(
            transcript=transcript,
            response_text=response,
            audio_bytes=audio,
            latency_ms=metrics,
            audio_mime_type=getattr(
                self.voice,
                "audio_mime_type",
                "audio/mpeg",
            ),
            raw_transcript=raw_transcript,
            spoken_text=spoken_response,
        )
