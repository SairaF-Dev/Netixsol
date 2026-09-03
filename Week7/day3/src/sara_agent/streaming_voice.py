from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

import websockets

from .deepgram_config import (
    DEFAULT_DEEPGRAM_LANGUAGE,
    load_deepgram_keyterms,
)
from .deepgram_tts import DeepgramTTSConfig
from .fish_audio import FishAudioConfig
from .transcript_normalizer import normalize_transcript
from .voice_response_formatter import format_voice_response

try:
    from .natural_speech import auto_naturalize_speech
except Exception:  # pragma: no cover
    auto_naturalize_speech = None


logger = logging.getLogger(__name__)


# ============================================================
# STREAM EVENT
# ============================================================


@dataclass
class StreamEvent:
    """
    One server-side event emitted to the browser transport.
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    audio: bytes | None = None


StreamEventSink = Callable[
    [StreamEvent],
    Awaitable[None],
]


# ============================================================
# DEEPGRAM LIVE STT
# ============================================================


class DeepgramLiveSTT:
    """
    Low-level Deepgram live STT WebSocket client.

    Audio contract:
        - raw PCM
        - linear16
        - mono by default
        - sample rate supplied by browser

    This class contains NO Sara business logic.
    """

    def __init__(self) -> None:

        self.api_key = os.getenv(
            "DEEPGRAM_API_KEY",
            "",
        ).strip()

        if not self.api_key:
            raise ValueError(
                "DEEPGRAM_API_KEY is not configured"
            )

        self.model = (
            os.getenv(
                "DEEPGRAM_MODEL",
                "nova-3",
            ).strip()
            or "nova-3"
        )

        self.language = (
            os.getenv(
                "DEEPGRAM_LANGUAGE",
                DEFAULT_DEEPGRAM_LANGUAGE,
            ).strip()
            or DEFAULT_DEEPGRAM_LANGUAGE
        )

        self.smart_format = self._env_bool(
            "DEEPGRAM_SMART_FORMAT",
            True,
        )

        # Slightly safer than 300ms for natural
        # Pakistani UrduLish pauses.
        self.endpointing_ms = self._env_int(
            "DEEPGRAM_STREAM_ENDPOINTING_MS",
            500,
            minimum=100,
            maximum=2000,
        )

        self.utterance_end_ms = self._env_int(
            "DEEPGRAM_STREAM_UTTERANCE_END_MS",
            1000,
            minimum=1000,
            maximum=5000,
        )

        self.keepalive_seconds = self._env_float(
            "DEEPGRAM_STREAM_KEEPALIVE_SECONDS",
            4.0,
            minimum=2.0,
            maximum=8.0,
        )

        # ----------------------------------------------------
        # Connection robustness
        # ----------------------------------------------------

        self.open_timeout_seconds = self._env_float(
            "DEEPGRAM_STREAM_OPEN_TIMEOUT_SECONDS",
            30.0,
            minimum=5.0,
            maximum=60.0,
        )

        self.disable_proxy = self._env_bool(
            "DEEPGRAM_STREAM_DISABLE_PROXY",
            True,
        )

        # ----------------------------------------------------
        # Keyterms
        # ----------------------------------------------------

        self.keyterms = load_deepgram_keyterms()

        # ----------------------------------------------------
        # Runtime state
        # ----------------------------------------------------

        self._ws = None

        self._receive_task: (
            asyncio.Task | None
        ) = None

        self._keepalive_task: (
            asyncio.Task | None
        ) = None

        self._event_sink: (
            StreamEventSink | None
        ) = None

        self._connection_config: dict[str, Any] | None = None

        self._send_lock = asyncio.Lock()

        self._final_segments: list[str] = []

        self._last_audio_at = (
            time.monotonic()
        )

        self._closed = True


    # ========================================================
    # START CONNECTION
    # ========================================================

    async def start(
        self,
        *,
        sample_rate: int,
        channels: int = 1,
        encoding: str = "linear16",
        event_sink: StreamEventSink,
    ) -> None:

        # ----------------------------------------------------
        # Validate browser audio configuration
        # ----------------------------------------------------

        if (
            sample_rate < 8000
            or sample_rate > 96000
        ):
            raise ValueError(
                "sample_rate must be between "
                "8000 and 96000"
            )

        if channels not in {1, 2}:
            raise ValueError(
                "channels must be 1 or 2"
            )

        if encoding != "linear16":
            raise ValueError(
                "This Day-3 browser transport "
                "currently supports linear16 only"
            )

        self._event_sink = event_sink

        self._connection_config = {
            "sample_rate": sample_rate,
            "channels": channels,
            "encoding": encoding,
        }

        self._final_segments.clear()

        # ----------------------------------------------------
        # Deepgram query
        # ----------------------------------------------------

        query_items = [
            (
                "model",
                self.model,
            ),
            (
                "language",
                self.language,
            ),
            (
                "smart_format",
                (
                    "true"
                    if self.smart_format
                    else "false"
                ),
            ),
            (
                "interim_results",
                "true",
            ),
            (
                "endpointing",
                str(
                    self.endpointing_ms
                ),
            ),
            (
                "utterance_end_ms",
                str(
                    self.utterance_end_ms
                ),
            ),
            (
                "vad_events",
                "true",
            ),
            (
                "encoding",
                encoding,
            ),
            (
                "sample_rate",
                str(sample_rate),
            ),
            (
                "channels",
                str(channels),
            ),
        ]

        # Nova-3 supports repeated keyterm params.
        query_items.extend(
            (
                "keyterm",
                term,
            )
            for term in self.keyterms
        )

        url = (
            "wss://api.deepgram.com/v1/listen?"
            + urllib.parse.urlencode(
                query_items
            )
        )

        # ----------------------------------------------------
        # WebSocket configuration
        # ----------------------------------------------------

        connect_kwargs: dict[
            str,
            Any,
        ] = {
            "additional_headers": {
                "Authorization": (
                    f"Token {self.api_key}"
                ),
            },
            "ping_interval": None,
            "open_timeout": (
                self.open_timeout_seconds
            ),
            "close_timeout": 5,
            "max_size": (
                4 * 1024 * 1024
            ),
            "compression": None,
        }

        # Modern websockets can automatically use
        # system proxy settings.
        if self.disable_proxy:
            connect_kwargs["proxy"] = None

        # ----------------------------------------------------
        # Connect
        # ----------------------------------------------------

        try:

            try:

                self._ws = (
                    await websockets.connect(
                        url,
                        **connect_kwargs,
                    )
                )

            except TypeError as exc:

                # Compatibility fallback for older
                # websockets versions without proxy=.
                if (
                    "proxy"
                    in connect_kwargs
                    and "proxy"
                    in str(exc).casefold()
                ):

                    connect_kwargs.pop(
                        "proxy",
                        None,
                    )

                    self._ws = (
                        await websockets.connect(
                            url,
                            **connect_kwargs,
                        )
                    )

                else:
                    raise

        except TimeoutError as exc:

            raise ConnectionError(
                "Deepgram live WebSocket opening "
                "handshake timed out. Check internet, "
                "firewall/proxy settings and "
                "DEEPGRAM_API_KEY."
            ) from exc

        # ----------------------------------------------------
        # Connected
        # ----------------------------------------------------

        self._closed = False

        self._last_audio_at = (
            time.monotonic()
        )

        self._receive_task = (
            asyncio.create_task(
                self._receive_loop(),
                name=(
                    "deepgram-live-receive"
                ),
            )
        )

        self._keepalive_task = (
            asyncio.create_task(
                self._keepalive_loop(),
                name=(
                    "deepgram-live-keepalive"
                ),
            )
        )

        await self._emit(
            "stt_connected",
            model=self.model,
            language=self.language,
            endpointing_ms=(
                self.endpointing_ms
            ),
            utterance_end_ms=(
                self.utterance_end_ms
            ),
        )

    # ========================================================
    # AUDIO
    # ========================================================

    async def send_audio(
        self,
        audio_chunk: bytes,
    ) -> None:
        if not audio_chunk:
            return

        async with self._send_lock:
            if (
                self._closed
                or self._ws is None
            ):
                raise RuntimeError(
                    "Deepgram live connection "
                    "is not open"
                )

            try:
                await self._ws.send(
                    audio_chunk
                )
            except Exception as exc:
                await self._reconnect_after_drop(exc)
                assert self._ws is not None
                await self._ws.send(
                    audio_chunk
                )

        self._last_audio_at = (
            time.monotonic()
        )

    async def _reconnect_after_drop(
        self,
        exc: Exception,
    ) -> None:
        """Reconnect once after a transient Deepgram socket reset."""

        config = self._connection_config
        event_sink = self._event_sink
        if config is None or event_sink is None:
            raise ConnectionError(
                "Deepgram connection was lost and cannot be restored"
            ) from exc

        logger.warning(
            "Deepgram connection dropped; reconnecting (%s)",
            exc.__class__.__name__,
        )
        await self._emit(
            "stt_reconnecting",
            message="Speech recognition disconnected; reconnecting.",
        )
        await self.close()
        await self.start(
            **config,
            event_sink=event_sink,
        )


    # ========================================================
    # FINALIZE
    # ========================================================

    async def finalize(
        self,
    ) -> None:

        if (
            self._closed
            or self._ws is None
        ):
            return

        try:

            await self._ws.send(
                json.dumps(
                    {
                        "type": "Finalize",
                    }
                )
            )

        except Exception:

            logger.exception(
                "Deepgram Finalize failed"
            )


    # ========================================================
    # CLOSE
    # ========================================================

    async def close(
        self,
    ) -> None:

        if self._closed:
            return

        self._closed = True

        if self._keepalive_task:
            self._keepalive_task.cancel()

        if self._ws is not None:

            try:

                await self._ws.send(
                    json.dumps(
                        {
                            "type":
                                "CloseStream",
                        }
                    )
                )

            except Exception:
                pass

            try:

                await self._ws.close()

            except Exception:
                pass

        if self._receive_task:
            self._receive_task.cancel()

        for task in (
            self._keepalive_task,
            self._receive_task,
        ):

            if task:

                try:
                    await task

                except asyncio.CancelledError:
                    pass

                except Exception:
                    pass

        self._ws = None
        self._receive_task = None
        self._keepalive_task = None


    # ========================================================
    # RECEIVE DEEPGRAM EVENTS
    # ========================================================

    async def _receive_loop(
        self,
    ) -> None:

        assert self._ws is not None

        try:

            async for message in self._ws:

                if isinstance(
                    message,
                    bytes,
                ):
                    continue

                try:

                    payload = json.loads(
                        message
                    )

                except json.JSONDecodeError:

                    logger.warning(
                        "Ignoring non-JSON "
                        "Deepgram message"
                    )

                    continue

                event_type = (
                    payload.get("type")
                )

                # --------------------------------------------
                # Voice Activity Detection
                # --------------------------------------------

                if (
                    event_type
                    == "SpeechStarted"
                ):

                    await self._emit(
                        "speech_started",
                        timestamp=(
                            payload.get(
                                "timestamp"
                            )
                        ),
                    )

                    continue

                # --------------------------------------------
                # Transcript results
                # --------------------------------------------

                if event_type == "Results":

                    channel = (
                        payload.get(
                            "channel"
                        )
                        or {}
                    )

                    alternatives = (
                        channel.get(
                            "alternatives"
                        )
                        or []
                    )

                    transcript = ""
                    confidence = None

                    if alternatives:

                        transcript = str(
                            alternatives[0].get(
                                "transcript"
                            )
                            or ""
                        ).strip()

                        confidence = (
                            alternatives[0].get(
                                "confidence"
                            )
                        )

                    is_final = bool(
                        payload.get(
                            "is_final"
                        )
                    )

                    speech_final = bool(
                        payload.get(
                            "speech_final"
                        )
                    )

                    # ----------------------------------------
                    # Partial
                    # ----------------------------------------

                    if (
                        transcript
                        and not is_final
                    ):

                        display_transcript = (
                            normalize_transcript(transcript)
                            or transcript
                        )

                        await self._emit(
                            "transcript_partial",
                            transcript=(
                                display_transcript
                            ),
                            confidence=(
                                confidence
                            ),
                        )

                    # ----------------------------------------
                    # Final segment
                    # ----------------------------------------

                    if (
                        transcript
                        and is_final
                    ):

                        self._final_segments.append(
                            transcript
                        )

                        display_transcript = (
                            normalize_transcript(transcript)
                            or transcript
                        )

                        await self._emit(
                            "transcript_segment_final",
                            transcript=(
                                display_transcript
                            ),
                            confidence=(
                                confidence
                            ),
                        )

                    # ----------------------------------------
                    # End of speech
                    # ----------------------------------------

                    if speech_final:

                        await self._flush_utterance(
                            source=(
                                "speech_final"
                            )
                        )

                    continue

                # --------------------------------------------
                # Utterance end fallback
                # --------------------------------------------

                if (
                    event_type
                    == "UtteranceEnd"
                ):

                    await self._flush_utterance(
                        source=(
                            "utterance_end"
                        )
                    )

                    continue

                if (
                    event_type
                    == "Metadata"
                ):
                    continue

                # --------------------------------------------
                # Deepgram error
                # --------------------------------------------

                if event_type == "Error":

                    await self._emit(
                        "stt_error",
                        message=str(
                            payload.get(
                                "description"
                            )
                            or payload.get(
                                "message"
                            )
                            or (
                                "Deepgram "
                                "streaming error"
                            )
                        ),
                    )

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            if not self._closed:

                logger.warning(
                    "Deepgram receive loop disconnected (%s)",
                    exc.__class__.__name__,
                )

                await self._emit(
                    "stt_reconnecting",
                    message=(
                        "Speech recognition connection dropped; "
                        "the next microphone chunk will reconnect it."
                    ),
                )


    # ========================================================
    # BUILD ONE COMPLETE USER UTTERANCE
    # ========================================================

    async def _flush_utterance(
        self,
        *,
        source: str,
    ) -> None:

        if not self._final_segments:
            return

        raw_transcript = " ".join(
            self._final_segments
        ).strip()

        self._final_segments.clear()

        if not raw_transcript:
            return

        now = time.perf_counter()

        await self._emit(
            "utterance_final",
            raw_transcript=(
                raw_transcript
            ),
            source=source,

            # Correct v2 terminology.
            stt_final_monotonic=now,

            # Compatibility with existing
            # server/client code.
            speech_final_monotonic=now,
        )


    # ========================================================
    # KEEPALIVE
    # ========================================================

    async def _keepalive_loop(
        self,
    ) -> None:

        try:

            while not self._closed:

                await asyncio.sleep(
                    self.keepalive_seconds
                )

                if (
                    self._closed
                    or self._ws is None
                ):
                    return

                silent_for = (
                    time.monotonic()
                    - self._last_audio_at
                )

                if (
                    silent_for
                    >= self.keepalive_seconds
                ):

                    await self._ws.send(
                        json.dumps(
                            {
                                "type":
                                    "KeepAlive",
                            }
                        )
                    )

        except asyncio.CancelledError:
            raise

        except Exception:

            if not self._closed:

                logger.exception(
                    "Deepgram keepalive "
                    "loop failed"
                )


    # ========================================================
    # EVENT EMITTER
    # ========================================================

    async def _emit(
        self,
        event_type: str,
        **data: Any,
    ) -> None:

        if self._event_sink is not None:

            await self._event_sink(
                StreamEvent(
                    event_type,
                    data,
                )
            )


    # ========================================================
    # ENV HELPERS
    # ========================================================

    @staticmethod
    def _env_bool(
        name: str,
        default: bool,
    ) -> bool:

        value = os.getenv(
            name
        )

        if value is None:
            return default

        return (
            value
            .strip()
            .casefold()
            not in {
                "0",
                "false",
                "no",
                "off",
            }
        )


    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:

        try:

            value = int(
                os.getenv(
                    name,
                    str(default),
                )
            )

        except ValueError:
            value = default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )


    @staticmethod
    def _env_float(
        name: str,
        default: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:

        try:

            value = float(
                os.getenv(
                    name,
                    str(default),
                )
            )

        except ValueError:
            value = default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )


# ============================================================
# EDGE STREAMING TTS
# ============================================================


class EdgeTTSStreamer:
    """
    Yield Edge TTS audio as soon as
    the provider emits each MP3 chunk.
    """

    name = "edge-tts-streaming"

    audio_mime_type = "audio/mpeg"


    def __init__(
        self,
    ) -> None:

        self.voice = (
            os.getenv(
                "EDGE_TTS_VOICE",
                "ur-PK-UzmaNeural",
            ).strip()
            or "ur-PK-UzmaNeural"
        )

        self.rate = (
            os.getenv(
                "EDGE_TTS_RATE",
                "+0%",
            ).strip()
            or "+0%"
        )

        self.volume = (
            os.getenv(
                "EDGE_TTS_VOLUME",
                "+0%",
            ).strip()
            or "+0%"
        )

        self.pitch = (
            os.getenv(
                "EDGE_TTS_PITCH",
                "+0Hz",
            ).strip()
            or "+0Hz"
        )

        self.max_chars = self._env_int(
            "SARA_TTS_MAX_CHARS",
            1200,
            minimum=200,
            maximum=8000,
        )


    async def stream(
        self,
        text: str,
    ) -> AsyncIterator[bytes]:

        if (
            not isinstance(
                text,
                str,
            )
            or not text.strip()
        ):

            raise ValueError(
                "TTS text must be non-empty"
            )

        try:

            import edge_tts

        except ImportError as exc:

            raise ImportError(
                "edge-tts is not installed. "
                "Run: pip install edge-tts"
            ) from exc

        communicate = edge_tts.Communicate(
            text=(
                text.strip()[
                    : self.max_chars
                ]
            ),
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        async for chunk in (
            communicate.stream()
        ):

            if (
                chunk.get("type")
                != "audio"
            ):
                continue

            data = chunk.get(
                "data"
            )

            if data:
                yield bytes(data)


    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:

        try:

            value = int(
                os.getenv(
                    name,
                    str(default),
                )
            )

        except ValueError:
            value = default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )


class ElevenLabsStreamer:
    """
    Yield ElevenLabs TTS audio chunks as a stream.
    
    Supports streaming audio output with natural,
    expressive Pakistani voices.
    """

    name = "elevenlabs-streaming"

    audio_mime_type = "audio/mpeg"

    def __init__(self) -> None:

        self.api_key = (
            os.getenv(
                "ELEVENLABS_API_KEY",
                "",
            ).strip()
        )

        if not self.api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured"
            )

        self.voice_id = (
            os.getenv(
                "ELEVENLABS_VOICE_ID",
                "EXAVITQu4vr4xnSDxMaL",
            ).strip()
            or "EXAVITQu4vr4xnSDxMaL"
        )

        self.model_id = (
            os.getenv(
                "ELEVENLABS_MODEL_ID",
                "eleven_turbo_v2_5",
            ).strip()
            or "eleven_turbo_v2_5"
        )

        self.output_format = (
            os.getenv(
                "ELEVENLABS_OUTPUT_FORMAT",
                "mp3_44100_128",
            ).strip()
            or "mp3_44100_128"
        )

        self.stability = self._env_float(
            "ELEVENLABS_STABILITY",
            0.5,
            minimum=0.0,
            maximum=1.0,
        )

        self.similarity_boost = (
            self._env_float(
                "ELEVENLABS_SIMILARITY_BOOST",
                0.75,
                minimum=0.0,
                maximum=1.0,
            )
        )

        self.max_chars = self._env_int(
            "SARA_TTS_MAX_CHARS",
            1200,
            minimum=200,
            maximum=8000,
        )

    async def stream(
        self,
        text: str,
    ) -> AsyncIterator[bytes]:
        """
        Stream audio chunks from ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            
        Yields:
            Audio bytes chunks
        """

        if (
            not isinstance(
                text,
                str,
            )
            or not text.strip()
        ):
            raise ValueError(
                "TTS text must be non-empty"
            )

        try:
            from elevenlabs.client import (
                ElevenLabs,
            )
        except ImportError as exc:
            raise ImportError(
                "elevenlabs is not installed. "
                "Run: pip install elevenlabs"
            ) from exc

        client = ElevenLabs(
            api_key=self.api_key
        )

        truncated_text = (
            text.strip()[
                : self.max_chars
            ]
        )

        try:
            # elevenlabs 1.x/2.x moved synthesis from the legacy
            # client.generate() helper to text_to_speech.convert().
            # Keep the fallback so older supported SDKs still work.
            text_to_speech = getattr(
                client,
                "text_to_speech",
                None,
            )

            if (
                text_to_speech is not None
                and hasattr(
                    text_to_speech,
                    "convert",
                )
            ):
                audio_stream = (
                    text_to_speech.convert(
                        text=truncated_text,
                        voice_id=self.voice_id,
                        model_id=self.model_id,
                        output_format=self.output_format,
                    )
                )
            else:
                audio_stream = client.generate(
                    text=truncated_text,
                    voice=self.voice_id,
                    model=self.model_id,
                    stream=True,
                )

            async for chunk in (
                self._async_stream_wrapper(
                    audio_stream
                )
            ):
                yield chunk

        except Exception as exc:
            logger.error(
                f"ElevenLabs streaming error: {exc}"
            )
            raise

    async def _async_stream_wrapper(
        self,
        sync_stream,
    ):
        """
        Wrap synchronous stream for async iteration.
        """
        for chunk in sync_stream:
            yield chunk
            await asyncio.sleep(0)

    @staticmethod
    def _env_float(
        name: str,
        default: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:
        """Read float from environment."""

        try:
            value = float(
                os.getenv(
                    name,
                    str(default),
                )
            )
        except ValueError:
            value = default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        """Read int from environment."""

        try:
            value = int(
                os.getenv(
                    name,
                    str(default),
                )
            )
        except ValueError:
            value = default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )


class DeepgramTTSStreamer:
    """Stream MP3 chunks from Deepgram Flux TTS REST."""

    name = "deepgram-flux-priya-streaming"
    audio_mime_type = "audio/mpeg"

    def __init__(self, config: DeepgramTTSConfig | None = None) -> None:
        self.config = config or DeepgramTTSConfig.from_env()

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is not installed. Run: pip install httpx"
            ) from exc

        timeout = httpx.Timeout(self.config.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                self.config.request_url,
                headers=self.config.headers(),
                json=self.config.payload(text),
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk


class FishAudioStreamer:
    """Yield Fish Audio HTTP response chunks as soon as they arrive."""

    name = "fish-audio-streaming"

    def __init__(self, config: FishAudioConfig | None = None) -> None:
        self.config = config or FishAudioConfig.from_env()
        self.audio_mime_type = self.config.audio_mime_type
        self.sample_rate = self.config.sample_rate

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        payload = self.config.payload(text)
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is not installed. Run: pip install httpx"
            ) from exc

        timeout = httpx.Timeout(self.config.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                self.config.endpoint,
                headers=self.config.headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk


class FallbackTTSStreamer:
    """Fall back only when the primary fails before sending audio bytes."""

    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}-with-{fallback.name}-fallback"
        self.active_provider_name = primary.name
        self.active_provider = primary

    @property
    def audio_mime_type(self) -> str:
        return self.active_provider.audio_mime_type

    @property
    def sample_rate(self) -> int | None:
        return getattr(
            self.active_provider,
            "sample_rate",
            None,
        )

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        yielded = False
        self.active_provider_name = self.primary.name
        self.active_provider = self.primary
        try:
            async for chunk in self.primary.stream(text):
                yielded = True
                yield chunk
        except Exception as exc:
            if yielded:
                raise
            logger.warning(
                "Primary streaming TTS failed; using %s fallback (%s)",
                self.fallback.name,
                exc.__class__.__name__,
            )

        if yielded:
            return

        self.active_provider_name = self.fallback.name
        self.active_provider = self.fallback
        async for chunk in self.fallback.stream(text):
            yield chunk


def build_tts_provider(
) -> EdgeTTSStreamer | ElevenLabsStreamer | FishAudioStreamer | DeepgramTTSStreamer:
    """
    Factory function to select TTS provider based on config.
    
    Returns:
        EdgeTTSStreamer or ElevenLabsStreamer instance
    """

    provider = (
        os.getenv(
            "SARA_TTS_PROVIDER",
            "edge-tts",
        ).strip()
        .lower()
    )

    if provider == "elevenlabs":
        logger.info(
            "Using ElevenLabs for TTS"
        )
        return ElevenLabsStreamer()

    elif provider in {"deepgram", "deepgram-tts", "deepgram_tts", "dg"}:
        logger.info("Using Deepgram Flux Priya for TTS")
        primary = DeepgramTTSStreamer()
        fallback_name = os.getenv(
            "SARA_TTS_FALLBACK_PROVIDER",
            "edge-tts",
        ).strip().casefold()
        if fallback_name in {"edge", "edge-tts", "edge_tts"}:
            return FallbackTTSStreamer(primary, EdgeTTSStreamer())
        return primary

    elif provider in {
        "fish",
        "fish-audio",
        "fish_audio",
    }:
        logger.info(
            "Using Fish Audio for TTS"
        )
        primary = FishAudioStreamer()
        fallback_name = os.getenv(
            "SARA_TTS_FALLBACK_PROVIDER",
            "edge-tts",
        ).strip().casefold()
        if fallback_name in {"edge", "edge-tts", "edge_tts"}:
            return FallbackTTSStreamer(
                primary,
                EdgeTTSStreamer(),
            )
        return primary

    elif provider == "edge-tts":
        logger.info(
            "Using Edge TTS for TTS"
        )
        return EdgeTTSStreamer()

    else:
        logger.warning(
            f"Unknown TTS provider: {provider}. "
            "Defaulting to edge-tts"
        )
        return EdgeTTSStreamer()


# ============================================================
# STREAMING VOICE SESSION
# ============================================================


class StreamingVoiceSession:
    """
    Speech
        -> frozen Sara chatbot
        -> streaming speech.

    Business rules remain in SaraChatbot.

    This class handles:
        - streaming STT
        - turn control
        - confirmed barge-in
        - transcript normalization
        - streaming TTS
        - latency measurement
    """

    # --------------------------------------------------------
    # Tiny common STT fragments.
    #
    # IMPORTANT:
    # We intentionally do NOT use a generic
    # len(text) < N filter because valid replies
    # can be:
    #
    #     3
    #     5
    #     ji
    #
    # --------------------------------------------------------

    _NOISE_UTTERANCES = {
        "ke",
        "ka",
        "ki",
        "uh",
        "um",
        "umm",
        "erm",
        "ah",
        "hmm",
        "hm",
    }


    def __init__(
        self,
        *,
        chatbot,
        stt: DeepgramLiveSTT,
        tts: EdgeTTSStreamer,
        event_sink: StreamEventSink,
    ) -> None:

        self.chatbot = chatbot

        self.stt = stt

        self.tts = tts

        self.event_sink = (
            event_sink
        )

        setter = getattr(
            self.chatbot,
            "set_response_mode",
            None,
        )

        if callable(setter):
            setter("voice")

        self._turn_lock = (
            asyncio.Lock()
        )

        self._tts_task: (
            asyncio.Task | None
        ) = None

        self._turn_tasks: set[
            asyncio.Task
        ] = set()

        # ----------------------------------------------------
        # Generation counter
        # ----------------------------------------------------

        # Every CONFIRMED meaningful user
        # utterance advances generation.
        #
        # Old responses can then be suppressed.
        self._speech_generation = 0

        # ----------------------------------------------------
        # Confirmed barge-in state
        # ----------------------------------------------------

        # SpeechStarted alone is only VAD evidence.
        # We wait for a meaningful transcript before
        # cancelling Sara.
        self._barge_in_pending = False

        self._speech_registered = False

        self._closed = False


    # ========================================================
    # START
    # ========================================================

    async def start(
        self,
        *,
        sample_rate: int,
        channels: int = 1,
        encoding: str = "linear16",
    ) -> None:

        await self.stt.start(
            sample_rate=sample_rate,
            channels=channels,
            encoding=encoding,
            event_sink=(
                self._on_stt_event
            ),
        )

    async def greet(self) -> None:
        """Introduce Sara when a new live call becomes ready."""

        enabled = os.getenv(
            "SARA_VOICE_GREETING_ENABLED",
            "1",
        ).strip().casefold() not in {"0", "false", "no", "off"}
        if not enabled or self._closed:
            return

        greeting = os.getenv(
            "SARA_VOICE_GREETING",
            (
                "Assalam-o-Alaikum! Main Sara hoon, aapki real estate "
                "agent. Main property buy, rent, budget aur location ke "
                "mutabiq options dhoondhne mein aapki help kar sakti hoon. "
                "Aap kis type ki property dekh rahe hain?"
            ),
        ).strip()
        if not greeting:
            return

        await self.event_sink(
            StreamEvent(
                "assistant_text",
                {
                    "text": greeting,
                    "agent_ms": 0.0,
                    "intro": True,
                },
            )
        )

        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()

        generation = self._speech_generation
        task = asyncio.create_task(
            self._stream_tts(
                spoken_text=format_voice_response(greeting),
                stt_final_at=time.perf_counter(),
                agent_ms=0.0,
                generation=generation,
            ),
            name="sara-streaming-greeting",
        )
        self._tts_task = task

        def clear_greeting(completed: asyncio.Task) -> None:
            if self._tts_task is completed:
                self._tts_task = None

        task.add_done_callback(clear_greeting)


    # ========================================================
    # AUDIO
    # ========================================================

    async def send_audio(
        self,
        audio_chunk: bytes,
    ) -> None:

        await self.stt.send_audio(
            audio_chunk
        )


    # ========================================================
    # FINALIZE
    # ========================================================

    async def finalize(
        self,
    ) -> None:

        await self.stt.finalize()


    # ========================================================
    # CLOSE
    # ========================================================

    async def close(
        self,
    ) -> None:

        if self._closed:
            return

        self._closed = True

        if (
            self._tts_task
            and not self._tts_task.done()
        ):

            self._tts_task.cancel()

        for task in list(
            self._turn_tasks
        ):

            if not task.done():
                task.cancel()

        await self.stt.close()

        for task in list(
            self._turn_tasks
        ):

            try:

                await task

            except asyncio.CancelledError:
                pass

            except Exception:
                pass

        self._turn_tasks.clear()

        self._tts_task = None


    # ========================================================
    # STT EVENT ROUTER
    # ========================================================

    async def _on_stt_event(
        self,
        event: StreamEvent,
    ) -> None:

        # ----------------------------------------------------
        # Speech Started
        # ----------------------------------------------------

        if (
            event.type
            == "speech_started"
        ):

            # IMPORTANT:
            #
            # Do NOT immediately cancel TTS.
            #
            # SpeechStarted can be triggered by:
            #   - speaker echo
            #   - breathing
            #   - noise
            #
            # Wait for meaningful transcript first.

            self._barge_in_pending = True

            self._speech_registered = False

            # If Sara isn't speaking, forwarding the
            # VAD event is useful for UI status.
            #
            # If Sara IS speaking, do not tell the UI
            # "Sara stopping" until interruption is
            # actually confirmed.
            tts_active = (
                self._tts_task is not None
                and not self._tts_task.done()
            )

            if not tts_active:

                await self.event_sink(
                    event
                )

            return


        # ----------------------------------------------------
        # Partial/final transcript segment
        # ----------------------------------------------------

        if event.type in {
            "transcript_partial",
            "transcript_segment_final",
        }:

            candidate = str(
                event.data.get(
                    "transcript"
                )
                or ""
            ).strip()

            if (
                self._barge_in_pending
                and not self._speech_registered
                and self._looks_meaningful_speech(
                    candidate
                )
            ):

                await self._confirm_new_user_speech(
                    transcript=candidate,
                    source=event.type,
                )

            await self.event_sink(
                event
            )

            return


        # ----------------------------------------------------
        # Complete utterance
        # ----------------------------------------------------

        if (
            event.type
            == "utterance_final"
        ):

            raw_transcript = str(
                event.data.get(
                    "raw_transcript"
                )
                or ""
            ).strip()

            if not raw_transcript:

                self._reset_current_speech_flags()

                return

            # Preview normalization lets us reject
            # known tiny noise fragments BEFORE
            # cancelling Sara.
            preview = (
                normalize_transcript(
                    raw_transcript
                )
                .strip()
            )

            # ----------------------------------------------
            # Noise fragment
            # ----------------------------------------------

            if self._is_noise_utterance(
                preview
            ):

                self._reset_current_speech_flags()

                await self.event_sink(
                    StreamEvent(
                        "utterance_ignored",
                        {
                            "raw_transcript":
                                raw_transcript,
                            "transcript":
                                preview,
                            "reason":
                                "probable_noise_fragment",
                        },
                    )
                )

                return

            # ----------------------------------------------
            # If no useful interim was emitted, final
            # transcript itself confirms real user speech.
            # ----------------------------------------------

            if (
                not self._speech_registered
            ):

                await self._confirm_new_user_speech(
                    transcript=(
                        preview
                        or raw_transcript
                    ),
                    source=(
                        "utterance_final"
                    ),
                )

            stt_final_at = float(
                event.data.get(
                    "stt_final_monotonic"
                )
                or event.data.get(
                    "speech_final_monotonic"
                )
                or time.perf_counter()
            )

            generation = (
                self._speech_generation
            )

            # ----------------------------------------------
            # Schedule user turn
            # ----------------------------------------------

            task = asyncio.create_task(
                self._handle_utterance(
                    raw_transcript=(
                        raw_transcript
                    ),
                    stt_final_at=(
                        stt_final_at
                    ),
                    generation=(
                        generation
                    ),
                ),
                name=(
                    "sara-streaming-turn"
                ),
            )

            self._turn_tasks.add(
                task
            )

            task.add_done_callback(
                self._turn_tasks.discard
            )

            self._reset_current_speech_flags()

            return


        # ----------------------------------------------------
        # Other STT event
        # ----------------------------------------------------

        await self.event_sink(
            event
        )


    # ========================================================
    # CONFIRM NEW SPEECH / BARGE-IN
    # ========================================================

    async def _confirm_new_user_speech(
        self,
        *,
        transcript: str,
        source: str,
    ) -> None:

        if self._speech_registered:
            return

        self._speech_registered = True

        self._barge_in_pending = False

        # Every meaningful user utterance receives
        # a new generation.
        self._speech_generation += 1

        interrupted = (
            self._tts_task is not None
            and not self._tts_task.done()
        )

        # ----------------------------------------------
        # True interruption
        # ----------------------------------------------

        if interrupted:

            self._tts_task.cancel()

            await self.event_sink(
                StreamEvent(
                    "interruption",
                    {
                        "message": (
                            "Meaningful user speech "
                            "confirmed; Sara audio stopped."
                        ),
                        "source": source,
                        "transcript": transcript,
                    },
                )
            )


    # ========================================================
    # PROCESS ONE USER UTTERANCE
    # ========================================================

    async def _handle_utterance(
        self,
        *,
        raw_transcript: str,
        stt_final_at: float,
        generation: int,
    ) -> None:

        transcript = (
            normalize_transcript(
                raw_transcript
            )
            .strip()
        )

        # ----------------------------------------------------
        # Empty transcript
        # ----------------------------------------------------

        if not transcript:

            await self.event_sink(
                StreamEvent(
                    "transcript_empty",
                    {
                        "raw_transcript":
                            raw_transcript,
                    },
                )
            )

            return

        # ----------------------------------------------------
        # Second defensive noise guard
        # ----------------------------------------------------

        if self._is_noise_utterance(
            transcript
        ):

            await self.event_sink(
                StreamEvent(
                    "utterance_ignored",
                    {
                        "raw_transcript":
                            raw_transcript,
                        "transcript":
                            transcript,
                        "reason":
                            "probable_noise_fragment",
                    },
                )
            )

            return

        # ----------------------------------------------------
        # Send normalized transcript to browser
        # ----------------------------------------------------

        await self.event_sink(
            StreamEvent(
                "transcript_final",
                {
                    "raw_transcript":
                        raw_transcript,
                    "transcript":
                        transcript,
                },
            )
        )

        # ----------------------------------------------------
        # Serialize chatbot state mutations
        # ----------------------------------------------------

        async with self._turn_lock:

            # The turn may already be stale while
            # waiting for an older turn.
            if (
                generation
                != self._speech_generation
            ):

                await self.event_sink(
                    StreamEvent(
                        "assistant_superseded",
                        {
                            "message": (
                                "A newer user utterance "
                                "arrived before this turn "
                                "started processing."
                            ),
                        },
                    )
                )

                return

            agent_started = (
                time.perf_counter()
            )

            try:

                response = (
                    await asyncio.to_thread(
                        self.chatbot.handle_message,
                        transcript,
                    )
                )

            except Exception as exc:

                logger.exception(
                    "Sara agent turn failed"
                )

                await self.event_sink(
                    StreamEvent(
                        "agent_error",
                        {
                            "message": (
                                "Sara agent request failed; "
                                "no factual response was "
                                "fabricated."
                            ),
                            "error_type":
                                exc.__class__.__name__,
                        },
                    )
                )

                return

            agent_finished = (
                time.perf_counter()
            )

            agent_ms = (
                agent_finished
                - agent_started
            ) * 1000.0

            # ------------------------------------------------
            # IMPORTANT:
            # Check generation BEFORE assistant_text.
            #
            # This prevents stale Lahore response from
            # appearing after user corrected to Karachi.
            # ------------------------------------------------

            if (
                generation
                != self._speech_generation
            ):

                await self.event_sink(
                    StreamEvent(
                        "assistant_superseded",
                        {
                            "message": (
                                "A newer user utterance "
                                "arrived before response "
                                "delivery."
                            ),
                            "agent_ms":
                                round(
                                    agent_ms,
                                    2,
                                ),
                        },
                    )
                )

                return

            # ------------------------------------------------
            # Send verified assistant text
            # ------------------------------------------------

            await self.event_sink(
                StreamEvent(
                    "assistant_text",
                    {
                        "text":
                            response,
                        "agent_ms":
                            round(
                                agent_ms,
                                2,
                            ),
                    },
                )
            )

            # ------------------------------------------------
            # Voice-friendly formatting
            # ------------------------------------------------

            spoken_text = (
                format_voice_response(
                    response
                )
            )

            # ------------------------------------------------
            # Natural speech behavior
            # ------------------------------------------------

            if (
                auto_naturalize_speech
                is not None
            ):

                try:

                    spoken_text = (
                        auto_naturalize_speech(
                            spoken_text,
                            user_text=(
                                transcript
                            ),
                        )
                    )

                except Exception:

                    logger.exception(
                        "Natural speech decoration "
                        "failed; using formatted text"
                    )

            # ------------------------------------------------
            # Cancel any old TTS
            # ------------------------------------------------

            if (
                self._tts_task
                and not self._tts_task.done()
            ):

                self._tts_task.cancel()

            # ------------------------------------------------
            # Start streaming TTS
            # ------------------------------------------------

            self._tts_task = (
                asyncio.create_task(
                    self._stream_tts(
                        spoken_text=(
                            spoken_text
                        ),
                        stt_final_at=(
                            stt_final_at
                        ),
                        agent_ms=(
                            agent_ms
                        ),
                        generation=(
                            generation
                        ),
                    ),
                    name=(
                        "sara-streaming-tts"
                    ),
                )
            )

            current_tts_task = (
                self._tts_task
            )

            try:

                await current_tts_task

            except asyncio.CancelledError:

                # Expected normal barge-in path.
                pass

            finally:

                if (
                    self._tts_task
                    is current_tts_task
                ):

                    self._tts_task = None


    # ========================================================
    # STREAM TTS
    # ========================================================

    async def _stream_tts(
        self,
        *,
        spoken_text: str,
        stt_final_at: float,
        agent_ms: float,
        generation: int,
    ) -> None:

        tts_started = (
            time.perf_counter()
        )

        first_audio_at: (
            float | None
        ) = None

        chunks = 0

        audio_bytes = 0

        # ----------------------------------------------------
        # Processing latency before provider starts
        # ----------------------------------------------------

        stt_final_to_tts_start_ms = (
            tts_started
            - stt_final_at
        ) * 1000.0

        await self.event_sink(
            StreamEvent(
                "tts_start",
                {
                    "spoken_text":
                        spoken_text,

                    "mime_type":
                        self.tts.audio_mime_type,

                    "provider":
                        getattr(
                            self.tts,
                            "name",
                            self.tts.__class__.__name__,
                        ),

                    "sample_rate":
                        getattr(
                            self.tts,
                            "sample_rate",
                            None,
                        ),

                    "agent_ms":
                        round(
                            agent_ms,
                            2,
                        ),

                    "stt_final_to_tts_start_ms":
                        round(
                            stt_final_to_tts_start_ms,
                            2,
                        ),
                },
            )
        )

        # ----------------------------------------------------
        # Stream provider audio
        # ----------------------------------------------------

        try:

            async for chunk in (
                self.tts.stream(
                    spoken_text
                )
            ):

                # --------------------------------------------
                # New user speech arrived
                # --------------------------------------------

                if (
                    generation
                    != self._speech_generation
                ):

                    raise asyncio.CancelledError

                # --------------------------------------------
                # First audio
                # --------------------------------------------

                if first_audio_at is None:

                    first_audio_at = (
                        time.perf_counter()
                    )

                    first_audio_latency_ms = (
                        first_audio_at
                        - stt_final_at
                    ) * 1000.0

                    await self.event_sink(
                        StreamEvent(
                            "first_audio",
                            {
                                # Correct terminology.
                                "stt_final_to_first_audio_ms":
                                    round(
                                        first_audio_latency_ms,
                                        2,
                                    ),

                                # --------------------------------
                                # Compatibility alias.
                                #
                                # Keep temporarily because current
                                # UI may expect this field.
                                #
                                # It is NOT true acoustic
                                # speech-end latency.
                                # --------------------------------

                                "speech_end_to_first_audio_ms":
                                    round(
                                        first_audio_latency_ms,
                                        2,
                                    ),

                                "latency_basis": (
                                    "deepgram_final_to_"
                                    "first_tts_chunk"
                                ),

                                "target_ms":
                                    2000.0,

                                "provider":
                                    getattr(
                                        self.tts,
                                        "active_provider_name",
                                        getattr(
                                            self.tts,
                                            "name",
                                            self.tts.__class__.__name__,
                                        ),
                                    ),

                                "mime_type":
                                    self.tts.audio_mime_type,

                                "sample_rate":
                                    getattr(
                                        self.tts,
                                        "sample_rate",
                                        None,
                                    ),

                                "under_target": (
                                    first_audio_latency_ms
                                    < 2000.0
                                ),
                            },
                        )
                    )

                # --------------------------------------------
                # Audio chunk
                # --------------------------------------------

                chunks += 1

                audio_bytes += len(
                    chunk
                )

                await self.event_sink(
                    StreamEvent(
                        "tts_audio",
                        audio=chunk,
                    )
                )

        # ----------------------------------------------------
        # Confirmed interruption
        # ----------------------------------------------------

        except asyncio.CancelledError:

            cancelled_at = (
                time.perf_counter()
            )

            await self.event_sink(
                StreamEvent(
                    "tts_cancelled",
                    {
                        "reason": (
                            "barge_in_or_"
                            "newer_speech"
                        ),

                        "stt_final_to_cancel_ms":
                            round(
                                (
                                    cancelled_at
                                    - stt_final_at
                                )
                                * 1000.0,
                                2,
                            ),

                        "first_audio_was_sent":
                            (
                                first_audio_at
                                is not None
                            ),

                        "audio_chunks_sent":
                            chunks,

                        "audio_bytes_sent":
                            audio_bytes,
                    },
                )
            )

            raise

        # ----------------------------------------------------
        # Provider failure
        # ----------------------------------------------------

        except Exception as exc:

            logger.exception(
                "Streaming TTS failed"
            )

            await self.event_sink(
                StreamEvent(
                    "tts_error",
                    {
                        "message": (
                            "Streaming TTS failed; "
                            "text response remains valid."
                        ),

                        "error_type":
                            exc.__class__.__name__,
                    },
                )
            )

            return

        # ----------------------------------------------------
        # Complete TTS stream
        # ----------------------------------------------------

        tts_finished = (
            time.perf_counter()
        )

        # This is provider generation /
        # streaming time.
        #
        # It is NOT browser playback duration.
        tts_ms = (
            tts_finished
            - tts_started
        ) * 1000.0

        first_audio_latency_ms = (
            (
                first_audio_at
                - stt_final_at
            )
            * 1000.0

            if first_audio_at
            is not None

            else None
        )

        stt_final_to_tts_end_ms = (
            tts_finished
            - stt_final_at
        ) * 1000.0

        await self.event_sink(
            StreamEvent(
                "tts_end",
                {
                    "agent_ms":
                        round(
                            agent_ms,
                            2,
                        ),

                    "tts_total_ms":
                        round(
                            tts_ms,
                            2,
                        ),

                    "stt_final_to_tts_start_ms":
                        round(
                            stt_final_to_tts_start_ms,
                            2,
                        ),

                    "stt_final_to_first_audio_ms":
                        (
                            round(
                                first_audio_latency_ms,
                                2,
                            )

                            if (
                                first_audio_latency_ms
                                is not None
                            )

                            else None
                        ),

                    # Compatibility alias.
                    "speech_end_to_first_audio_ms":
                        (
                            round(
                                first_audio_latency_ms,
                                2,
                            )

                            if (
                                first_audio_latency_ms
                                is not None
                            )

                            else None
                        ),

                    "stt_final_to_tts_end_ms":
                        round(
                            stt_final_to_tts_end_ms,
                            2,
                        ),

                    # Compatibility alias.
                    "speech_end_to_tts_end_ms":
                        round(
                            stt_final_to_tts_end_ms,
                            2,
                        ),

                    "latency_basis": (
                        "deepgram_final_to_"
                        "first_tts_chunk"
                    ),

                    "audio_chunks":
                        chunks,

                    "audio_bytes":
                        audio_bytes,

                    "target_first_audio_ms":
                        2000.0,

                    "under_2s_first_audio_target":
                        (
                            first_audio_latency_ms
                            is not None
                            and first_audio_latency_ms
                            < 2000.0
                        ),
                },
            )
        )


    # ========================================================
    # SPEECH HELPERS
    # ========================================================

    def _reset_current_speech_flags(
        self,
    ) -> None:

        self._barge_in_pending = False

        self._speech_registered = False


    @classmethod
    def _is_noise_utterance(
        cls,
        text: str,
    ) -> bool:

        normalized = " ".join(
            (
                text
                or ""
            )
            .casefold()
            .split()
        )

        return (
            normalized
            in cls._NOISE_UTTERANCES
        )


    @classmethod
    def _looks_meaningful_speech(
        cls,
        text: str,
    ) -> bool:

        normalized = " ".join(
            (
                text
                or ""
            )
            .casefold()
            .split()
        )

        if not normalized:
            return False

        if cls._is_noise_utterance(
            normalized
        ):
            return False

        compact = re.sub(
            r"[^A-Za-z0-9\u0600-\u06FF]+",
            "",
            normalized,
        )

        if not compact:
            return False

        # --------------------------------------------
        # Valid short numeric replies:
        #
        # Bedrooms?
        # → 3
        #
        # Which option?
        # → 1
        # --------------------------------------------

        if compact.isdigit():
            return True

        # "ji" should also remain valid.
        return len(compact) >= 2
