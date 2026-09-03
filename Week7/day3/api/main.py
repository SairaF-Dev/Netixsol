from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

import anyio
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field


# ============================================================
# PROJECT SETUP
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIR),
    )

load_dotenv(
    ROOT / ".env"
)


# ============================================================
# SARA IMPORTS
# ============================================================

from sara_agent.chatbot import SaraChatbot
from sara_agent.runtime import SaraRuntime
from sara_agent.session_store import SessionStore

# Existing stable push-to-talk voice pipeline.
from sara_agent.voice import (
    VoicePipeline,
    build_voice_provider,
)

# Day-3 true streaming voice pipeline.
from sara_agent.streaming_voice import (
    DeepgramLiveSTT,
    EdgeTTSStreamer,
    ElevenLabsStreamer,
    StreamEvent,
    StreamingVoiceSession,
    build_tts_provider,
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Sara Real Estate Agent",
    version="1.4.0",
    description=(
        "Verified real-estate assistant with PostgreSQL, "
        "Day-2 RAG, text chat, push-to-talk voice and "
        "Day-3 live streaming voice."
    ),
)


# ============================================================
# SHARED APPLICATION DEPENDENCIES
# ============================================================

_runtime: SaraRuntime | None = None

_voice_provider = None

_sessions: SessionStore[SaraChatbot] | None = None


def get_runtime() -> SaraRuntime:
    """
    Return the shared Sara runtime.

    Runtime-level dependencies such as PostgreSQL and RAG can
    be reused, while conversational state remains isolated
    inside SaraChatbot instances.
    """

    global _runtime

    if _runtime is None:
        _runtime = SaraRuntime()

    return _runtime


def make_bot() -> SaraChatbot:
    """
    Create one independent Sara conversation bot.
    """

    return get_runtime().new_bot()


def get_sessions() -> SessionStore[SaraChatbot]:
    """
    Shared in-memory conversation session store.

    Used by:
        - HTTP text chat
        - push-to-talk voice
        - text WebSocket
        - live streaming voice

    This allows different transports to reuse the same
    conversation when they provide the same session_id.
    """

    global _sessions

    if _sessions is None:

        ttl_seconds = int(
            os.getenv(
                "SARA_SESSION_TTL_SECONDS",
                "3600",
            )
        )

        max_sessions = int(
            os.getenv(
                "SARA_MAX_SESSIONS",
                "500",
            )
        )

        _sessions = SessionStore(
            make_bot,
            ttl_seconds=ttl_seconds,
            max_sessions=max_sessions,
        )

    return _sessions


def get_voice_provider():
    """
    Return the existing stable turn-based voice provider.

    Typical configuration:
        Deepgram prerecorded STT
        +
        Edge TTS
    """

    global _voice_provider

    if _voice_provider is None:
        _voice_provider = build_voice_provider()

    return _voice_provider


def set_bot_mode(
    bot: SaraChatbot,
    mode: str,
) -> None:
    """
    Safely configure Sara response mode.

    Important when the same session is reused between
    text and voice transports.
    """

    setter = getattr(
        bot,
        "set_response_mode",
        None,
    )

    if callable(setter):
        setter(mode)


# ============================================================
# REQUEST MODELS
# ============================================================


class ChatIn(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    session_id: str | None = Field(
        default=None,
        max_length=128,
    )


# ============================================================
# ROOT
# ============================================================


@app.get("/")
async def root():
    """
    Simple service landing endpoint.
    """

    return {
        "service": "Sara Real Estate Agent",
        "status": "running",
        "version": app.version,
        "health": "/health",
        "ready": "/ready",
        "docs": "/docs",
        "live_voice": "/live-voice",
        "debug_voice": "/debug-voice",
        "simple_audio_test": "/simple-audio-test",
        "tts_test": "/tts-test",
        "tts_test_page": "/tts-test-page",
    }


# ============================================================
# LIVE VOICE HTML PAGE
# ============================================================


@app.get("/live-voice")
async def live_voice_page():
    """
    Serve the existing standalone browser client.

    Expected project structure:

        day3/
        ├── api/
        │   └── main.py
        ├── streaming_voice_client.html
        └── src/
    """

    client_file = (
        ROOT
        / "streaming_voice_client.html"
    )

    if not client_file.exists():

        logger.error(
            "Live voice client not found: %s",
            client_file,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                "streaming_voice_client.html "
                "was not found in the project root."
            ),
        )

    return FileResponse(
        path=client_file,
        media_type="text/html",
        filename=None,
    )


# ============================================================
# DEBUG VOICE PAGE
# ============================================================


@app.get("/debug-voice")
async def debug_voice_page():
    """
    Serve the debug diagnostic panel for voice issues.
    """

    debug_file = (
        ROOT
        / "debug_voice.html"
    )

    if not debug_file.exists():

        logger.error(
            "Debug voice page not found: %s",
            debug_file,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                "debug_voice.html "
                "was not found in the project root."
            ),
        )

    return FileResponse(
        path=debug_file,
        media_type="text/html",
        filename=None,
    )


# ============================================================
# SIMPLE AUDIO TEST PAGE
# ============================================================


@app.get("/simple-audio-test")
async def simple_audio_test_page():
    """
    Serve a simple audio playback test without WebSocket.
    """

    test_file = (
        ROOT
        / "simple_audio_test.html"
    )

    if not test_file.exists():

        logger.error(
            "Simple audio test page not found: %s",
            test_file,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                "simple_audio_test.html "
                "was not found in the project root."
            ),
        )

    return FileResponse(
        path=test_file,
        media_type="text/html",
        filename=None,
    )


# ============================================================
# TTS TEST ENDPOINT
# ============================================================


@app.get("/tts-test-page")
async def tts_test_page():
    """
    Serve the TTS test interface.
    """

    test_file = (
        ROOT
        / "tts_test.html"
    )

    if not test_file.exists():

        logger.error(
            "TTS test page not found: %s",
            test_file,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                "tts_test.html "
                "was not found in the project root."
            ),
        )

    return FileResponse(
        path=test_file,
        media_type="text/html",
        filename=None,
    )


@app.get("/tts-test")
async def tts_test(text: str = "Hello, this is a test"):
    """
    Generate MP3 audio from text using the configured TTS provider.
    
    This endpoint helps diagnose TTS pipeline issues.
    
    Usage:
        GET /tts-test?text=Assalam-o-Alaikum
    
    Returns:
        MP3 audio/mpeg stream
    """

    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="text parameter is required"
        )

    try:
        from sara_agent.streaming_voice import (
            build_tts_provider,
        )

        tts_provider = build_tts_provider()

        logger.info(
            f"TTS test: generating audio for: {text[:50]}"
        )

        # Collect all audio chunks
        audio_chunks = []

        async for chunk in tts_provider.stream(
            text.strip()[:1200]
        ):
            audio_chunks.append(chunk)

        if not audio_chunks:
            raise HTTPException(
                status_code=500,
                detail=(
                    "TTS provider returned no audio. "
                    "Check your API keys and configuration."
                )
            )

        # Combine all chunks
        complete_audio = b"".join(
            audio_chunks
        )

        logger.info(
            f"TTS test: generated {len(complete_audio)} bytes"
        )

        return Response(
            content=complete_audio,
            media_type=tts_provider.audio_mime_type,
            headers={
                "Content-Disposition": (
                    'attachment; filename="sara_test_audio"'
                ),
            },
        )

    except ValueError as e:
        logger.error(f"TTS configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS configuration error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        provider_response = getattr(
            e,
            "response",
            None,
        )
        provider_status = getattr(
            provider_response,
            "status_code",
            None,
        )
        status_hint = (
            f" Upstream provider returned HTTP {provider_status}."
            if isinstance(provider_status, int)
            else ""
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"TTS generation failed: {type(e).__name__}. "
                f"{status_hint} Check API logs for details."
            )
        )


# ============================================================
# HEALTH
# ============================================================


@app.get("/health")
def health():
    """
    Lightweight application liveness endpoint.

    This does not require PostgreSQL/RAG initialization
    to succeed.
    """

    if _runtime is not None:

        try:

            rag = (
                _runtime
                .status()
                .get(
                    "rag",
                    {},
                )
            )

        except Exception:

            rag = {
                "initialized": False,
            }

    else:

        rag_enabled = (
            os.getenv(
                "SARA_RAG_ENABLED",
                "1",
            )
            .strip()
            .casefold()
            not in {
                "0",
                "false",
                "no",
                "off",
            }
        )

        rag = {
            "enabled": rag_enabled,
            "initialized": False,
        }

    return {
        "status": "ok",
        "service": "sara-real-estate-agent",
        "version": app.version,
        "rag": rag,
    }


# ============================================================
# READINESS
# ============================================================


@app.get("/ready")
def ready():
    """
    Verify dependencies required for serving Sara.

    PostgreSQL must be ready.

    RAG is required only when:
        SARA_RAG_REQUIRED=1
    """

    try:

        runtime = get_runtime()

    except Exception as exc:

        logger.exception(
            "Runtime readiness initialization failed"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Sara runtime is not ready. "
                "Configuration error type: "
                f"{exc.__class__.__name__}"
            ),
        ) from exc

    try:

        dependencies = (
            runtime.readiness()
        )

    except Exception as exc:

        logger.exception(
            "Runtime readiness check failed"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Sara runtime readiness check failed. "
                f"Error type: {exc.__class__.__name__}"
            ),
        ) from exc

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    database_status = (
        dependencies.get(
            "database",
            {},
        )
    )

    if not database_status.get(
        "ready",
        False,
    ):

        raise HTTPException(
            status_code=503,
            detail=(
                "Sara runtime is not ready: "
                "PostgreSQL connectivity check failed."
            ),
        )

    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    rag_required = (
        os.getenv(
            "SARA_RAG_REQUIRED",
            "0",
        )
        .strip()
        .casefold()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    rag_status = (
        dependencies.get(
            "rag",
            {},
        )
    )

    if (
        rag_required
        and not rag_status.get(
            "ready",
            False,
        )
    ):

        raise HTTPException(
            status_code=503,
            detail=(
                "Sara runtime is not ready: "
                "required RAG dependency is unavailable."
            ),
        )

    return {
        "status": "ready",
        "service": "sara-real-estate-agent",
        "version": app.version,
        **dependencies,
    }


# ============================================================
# TEXT CHAT HTTP
# ============================================================


@app.post("/chat")
async def chat(
    body: ChatIn,
):
    """
    Standard text chat endpoint.

    Memory is preserved using SessionStore.

    Re-send the returned session_id on the next request
    to continue the same conversation.
    """

    session_id, bot = (
        get_sessions()
        .get_or_create(
            body.session_id
        )
    )

    set_bot_mode(
        bot,
        "text",
    )

    try:

        response = (
            await anyio.to_thread.run_sync(
                bot.handle_message,
                body.message,
            )
        )

    except Exception as exc:

        logger.exception(
            "Text chat turn failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Sara could not process the message. "
                f"Error type: {exc.__class__.__name__}"
            ),
        ) from exc

    return {
        "session_id": session_id,
        "response": response,
    }


# ============================================================
# TURN-BASED / PUSH-TO-TALK VOICE
# ============================================================


@app.post("/voice/turn")
async def voice_turn(
    file: UploadFile = File(...),
    session_id: str | None = Form(
        default=None
    ),
):
    """
    Existing stable push-to-talk voice endpoint.

    Flow:

        complete recording
        -> prerecorded STT
        -> transcript normalizer
        -> Sara
        -> TTS
        -> complete audio response

    This remains as the fallback voice pipeline.
    """

    # --------------------------------------------------------
    # Maximum upload size
    # --------------------------------------------------------

    max_bytes = int(
        os.getenv(
            "SARA_MAX_AUDIO_BYTES",
            str(
                10 * 1024 * 1024
            ),
        )
    )

    data = await file.read(
        max_bytes + 1
    )

    if len(data) > max_bytes:

        raise HTTPException(
            status_code=413,
            detail="Audio file is too large.",
        )

    if not data:

        raise HTTPException(
            status_code=400,
            detail="Audio file is empty.",
        )

    # --------------------------------------------------------
    # Session
    # --------------------------------------------------------

    resolved_session_id, bot = (
        get_sessions()
        .get_or_create(
            session_id
        )
    )

    set_bot_mode(
        bot,
        "voice",
    )

    filename = (
        file.filename
        or "input.webm"
    )

    # --------------------------------------------------------
    # Run synchronous VoicePipeline outside event loop
    # --------------------------------------------------------

    try:

        result = (
            await anyio.to_thread.run_sync(
                lambda: VoicePipeline(
                    bot,
                    get_voice_provider(),
                ).run_turn(
                    data,
                    filename,
                )
            )
        )

    except Exception as exc:

        logger.exception(
            "Push-to-talk voice turn failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Voice provider is temporarily unavailable. "
                "Please retry or use text chat."
            ),
        ) from exc

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "session_id": (
            resolved_session_id
        ),
        "transcript": (
            result.transcript
        ),
        "raw_transcript": getattr(
            result,
            "raw_transcript",
            "",
        ),
        "response": (
            result.response_text
        ),
        "spoken_text": getattr(
            result,
            "spoken_text",
            "",
        ),
        "audio_base64": (
            base64.b64encode(
                result.audio_bytes
            ).decode(
                "ascii"
            )
        ),
        "audio_mime_type": (
            result.audio_mime_type
        ),
        "latency_ms": (
            result.latency_ms
        ),
    }


# ============================================================
# TEXT CHAT WEBSOCKET
# ============================================================


@app.websocket("/ws/chat")
async def ws_chat(
    ws: WebSocket,
):
    """
    Persistent text WebSocket.

    Optional session reuse:

        ws://127.0.0.1:8000/ws/chat?session_id=...

    Without a session_id a new session is created.
    """

    await ws.accept()

    requested_session_id = (
        ws.query_params.get(
            "session_id"
        )
    )

    session_id, bot = (
        get_sessions()
        .get_or_create(
            requested_session_id
        )
    )

    set_bot_mode(
        bot,
        "text",
    )

    try:

        while True:

            text = (
                await ws.receive_text()
            )

            text = text.strip()

            if not text:

                await ws.send_json(
                    {
                        "type": "protocol_warning",
                        "message": (
                            "Empty message ignored."
                        ),
                        "session_id": session_id,
                    }
                )

                continue

            if len(text) > 4000:

                await ws.send_json(
                    {
                        "type": "protocol_error",
                        "message": (
                            "Message exceeds "
                            "4000 characters."
                        ),
                        "session_id": session_id,
                    }
                )

                continue

            response = (
                await anyio.to_thread.run_sync(
                    bot.handle_message,
                    text,
                )
            )

            await ws.send_json(
                {
                    "type": "assistant_text",
                    "session_id": session_id,
                    "response": response,
                }
            )

    except WebSocketDisconnect:

        logger.info(
            "Text WebSocket disconnected: %s",
            session_id,
        )

    except Exception:

        logger.exception(
            "Text WebSocket failed"
        )

        try:

            await ws.send_json(
                {
                    "type": "server_error",
                    "message": (
                        "Text conversation failed."
                    ),
                    "session_id": session_id,
                }
            )

        except Exception:
            pass


# ============================================================
# TRUE STREAMING VOICE WEBSOCKET
# ============================================================


@app.websocket("/ws/voice")
async def ws_voice(
    ws: WebSocket,
):
    """
    Day-3 true streaming voice endpoint.

    ----------------------------------------------------------
    Browser -> FastAPI
    ----------------------------------------------------------

    First JSON message:

        {
            "type": "start",
            "sample_rate": 48000,
            "channels": 1,
            "encoding": "linear16"
        }

    Optional:

        {
            "type": "start",
            "sample_rate": 48000,
            "channels": 1,
            "encoding": "linear16",
            "session_id": "existing-session-id"
        }

    Then browser sends binary PCM microphone chunks.

    Control messages:

        {"type": "finalize"}
        {"type": "ping"}
        {"type": "stop"}

    ----------------------------------------------------------
    FastAPI -> Browser
    ----------------------------------------------------------

        stt_connected
        ready
        speech_started
        transcript_partial
        transcript_segment_final
        transcript_final
        assistant_text
        tts_start
        first_audio
        binary MP3 chunks
        tts_end
        interruption
        tts_cancelled
        assistant_superseded
        utterance_ignored
        server_error
        session_closed
    """

    await ws.accept()

    send_lock = asyncio.Lock()

    voice_session: (
        StreamingVoiceSession | None
    ) = None

    resolved_session_id: (
        str | None
    ) = None


    # ========================================================
    # SAFE JSON SEND
    # ========================================================

    async def send_json(
        payload: dict,
    ) -> None:
        """
        Serialize WebSocket writes so streaming events,
        ping replies and control responses don't write
        concurrently.
        """

        async with send_lock:

            await ws.send_json(
                payload
            )


    # ========================================================
    # STREAM EVENT SINK
    # ========================================================

    async def emit(
        event: StreamEvent,
    ) -> None:
        """
        Forward StreamingVoiceSession events.

        Audio -> binary WebSocket frame.
        Everything else -> JSON.
        """

        async with send_lock:

            if event.audio is not None:

                await ws.send_bytes(
                    event.audio
                )

                return

            payload = {
                "type": event.type,
                **event.data,
            }

            if (
                resolved_session_id
                and "session_id"
                not in payload
            ):

                payload["session_id"] = (
                    resolved_session_id
                )

            await ws.send_json(
                payload
            )


    # ========================================================
    # MAIN WEBSOCKET SESSION
    # ========================================================

    try:

        # ====================================================
        # 1. WAIT FOR START CONFIGURATION
        # ====================================================

        first_message = (
            await ws.receive_text()
        )

        try:

            start_message = (
                json.loads(
                    first_message
                )
            )

        except json.JSONDecodeError:

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "First WebSocket message "
                        "must be valid JSON."
                    ),
                }
            )

            return

        if not isinstance(
            start_message,
            dict,
        ):

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "Start message must "
                        "be a JSON object."
                    ),
                }
            )

            return

        if (
            start_message.get("type")
            != "start"
        ):

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "First WebSocket message "
                        "must have type='start'."
                    ),
                }
            )

            return


        # ====================================================
        # 2. READ AUDIO CONFIGURATION
        # ====================================================

        try:

            sample_rate = int(
                start_message.get(
                    "sample_rate",
                    48000,
                )
            )

            channels = int(
                start_message.get(
                    "channels",
                    1,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "Invalid sample_rate "
                        "or channels."
                    ),
                }
            )

            return

        encoding = str(
            start_message.get(
                "encoding",
                "linear16",
            )
        ).strip().casefold()


        # ----------------------------------------------------
        # Validate configuration before provider connection
        # ----------------------------------------------------

        if not (
            8000
            <= sample_rate
            <= 96000
        ):

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "sample_rate must be "
                        "between 8000 and 96000."
                    ),
                }
            )

            return

        if channels not in {
            1,
            2,
        }:

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "channels must be "
                        "1 or 2."
                    ),
                }
            )

            return

        if encoding != "linear16":

            await send_json(
                {
                    "type": "protocol_error",
                    "message": (
                        "Current browser streaming "
                        "transport supports "
                        "linear16 only."
                    ),
                }
            )

            return


        # ====================================================
        # 3. SESSION / SHARED MEMORY
        # ====================================================

        requested_session_id = (
            str(
                start_message.get(
                    "session_id"
                )
                or ""
            )
            .strip()
            or None
        )

        resolved_session_id, bot = (
            get_sessions()
            .get_or_create(
                requested_session_id
            )
        )

        set_bot_mode(
            bot,
            "voice",
        )


        # ====================================================
        # 4. CREATE STREAMING VOICE SESSION
        # ====================================================

        voice_session = (
            StreamingVoiceSession(
                chatbot=bot,
                stt=DeepgramLiveSTT(),
                tts=build_tts_provider(),
                event_sink=emit,
            )
        )


        # ====================================================
        # 5. CONNECT DEEPGRAM
        # ====================================================

        try:

            await voice_session.start(
                sample_rate=sample_rate,
                channels=channels,
                encoding=encoding,
            )

        except Exception as exc:

            logger.exception(
                "Unable to start live STT session"
            )

            await send_json(
                {
                    "type": "stt_error",
                    "message": (
                        "Live speech recognition "
                        "could not be started."
                    ),
                    "error_type": (
                        exc.__class__.__name__
                    ),
                    "session_id": (
                        resolved_session_id
                    ),
                }
            )

            return


        # ====================================================
        # 6. READY
        # ====================================================

        await send_json(
            {
                "type": "ready",
                "session_id": (
                    resolved_session_id
                ),
                "sample_rate": (
                    sample_rate
                ),
                "channels": channels,
                "encoding": encoding,
                "message": (
                    "Sara live voice session "
                    "is ready."
                ),
            }
        )

        await voice_session.greet()


        # ====================================================
        # 7. RECEIVE LIVE AUDIO / CONTROL MESSAGES
        # ====================================================

        while True:

            message = (
                await ws.receive()
            )


            # ------------------------------------------------
            # Browser disconnected
            # ------------------------------------------------

            if (
                message.get("type")
                == "websocket.disconnect"
            ):

                break


            # ------------------------------------------------
            # Binary PCM microphone audio
            # ------------------------------------------------

            audio_chunk = (
                message.get("bytes")
            )

            if audio_chunk is not None:

                if audio_chunk:

                    await voice_session.send_audio(
                        audio_chunk
                    )

                continue


            # ------------------------------------------------
            # Text control frame
            # ------------------------------------------------

            text = (
                message.get("text")
            )

            if text is None:
                continue

            try:

                control = json.loads(
                    text
                )

            except json.JSONDecodeError:

                await send_json(
                    {
                        "type": "protocol_warning",
                        "message": (
                            "Ignoring non-JSON "
                            "control message."
                        ),
                        "session_id": (
                            resolved_session_id
                        ),
                    }
                )

                continue

            if not isinstance(
                control,
                dict,
            ):

                await send_json(
                    {
                        "type": "protocol_warning",
                        "message": (
                            "Control message "
                            "must be an object."
                        ),
                        "session_id": (
                            resolved_session_id
                        ),
                    }
                )

                continue

            control_type = str(
                control.get(
                    "type"
                )
                or ""
            ).strip().casefold()


            # ------------------------------------------------
            # FINALIZE CURRENT AUDIO
            # ------------------------------------------------

            if (
                control_type
                == "finalize"
            ):

                await voice_session.finalize()

                continue


            # ------------------------------------------------
            # PING
            # ------------------------------------------------

            if (
                control_type
                == "ping"
            ):

                await send_json(
                    {
                        "type": "pong",
                        "session_id": (
                            resolved_session_id
                        ),
                    }
                )

                continue


            # ------------------------------------------------
            # STOP
            # ------------------------------------------------

            if (
                control_type
                == "stop"
            ):

                # Ask Deepgram to finalize any remaining
                # user speech before closing.
                await voice_session.finalize()

                try:

                    finalize_wait_ms = float(
                        os.getenv(
                            "SARA_STREAM_FINALIZE_WAIT_MS",
                            "650",
                        )
                    )

                except ValueError:

                    finalize_wait_ms = 650.0

                finalize_wait_ms = max(
                    0.0,
                    min(
                        finalize_wait_ms,
                        850.0,
                    ),
                )

                if finalize_wait_ms > 0:

                    await asyncio.sleep(
                        finalize_wait_ms
                        / 1000.0
                    )

                await voice_session.close()

                voice_session = None

                await send_json(
                    {
                        "type": "session_closed",
                        "session_id": (
                            resolved_session_id
                        ),
                    }
                )

                break


            # ------------------------------------------------
            # UNKNOWN CONTROL
            # ------------------------------------------------

            await send_json(
                {
                    "type": "protocol_warning",
                    "message": (
                        "Unknown streaming "
                        f"control: {control_type!r}"
                    ),
                    "session_id": (
                        resolved_session_id
                    ),
                }
            )


    # ========================================================
    # CLIENT DISCONNECT
    # ========================================================

    except WebSocketDisconnect:

        logger.info(
            "Streaming voice WebSocket "
            "disconnected. session_id=%s",
            resolved_session_id,
        )


    # ========================================================
    # SESSION FAILURE
    # ========================================================

    except Exception as exc:

        logger.exception(
            "Streaming voice WebSocket failed"
        )

        try:

            await send_json(
                {
                    "type": "server_error",
                    "message": (
                        "Streaming voice session failed. "
                        "Check server logs for details."
                    ),
                    "error_type": (
                        exc.__class__.__name__
                    ),
                    "session_id": (
                        resolved_session_id
                    ),
                }
            )

        except Exception:
            pass


    # ========================================================
    # CLEANUP
    # ========================================================

    finally:

        if voice_session is not None:

            try:

                await voice_session.close()

            except Exception:

                logger.exception(
                    "Streaming voice cleanup failed"
                )
