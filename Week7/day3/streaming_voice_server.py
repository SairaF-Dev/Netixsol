from __future__ import annotations

import asyncio
import json
import hmac
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from sara_agent.runtime import SaraRuntime
from sara_agent.streaming_voice import (
    DeepgramLiveSTT,
    EdgeTTSStreamer,
    StreamEvent,
    StreamingVoiceSession,
)


logging.basicConfig(
    level=getattr(
        logging,
        os.getenv("LOG_LEVEL", "INFO").upper(),
        logging.INFO,
    )
)
logger = logging.getLogger("sara-streaming-server")

app = FastAPI(
    title="Sara Day 3 Streaming Voice",
    version="1.0",
)


@lru_cache(maxsize=1)
def get_runtime() -> SaraRuntime:
    # Runtime can share DB/RAG/provider composition, while every WebSocket
    # receives its own bot and therefore its own conversation memory.
    return SaraRuntime()


@app.get("/")
async def home():
    return FileResponse(
        ROOT / "streaming_voice_client.html",
        media_type="text/html",
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "sara-streaming-voice",
    }


@app.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket):
    expected = os.getenv("SARA_API_KEY", "").strip()
    authorization = websocket.headers.get("authorization", "")
    header_token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    supplied = header_token or websocket.query_params.get("access_token", "")
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        await websocket.close(code=1008, reason="Authentication required")
        return
    await websocket.accept()

    send_lock = asyncio.Lock()
    session: StreamingVoiceSession | None = None

    async def emit(event: StreamEvent) -> None:
        async with send_lock:
            if event.audio is not None:
                await websocket.send_bytes(
                    event.audio
                )
                return

            payload = {
                "type": event.type,
                **event.data,
            }
            await websocket.send_json(
                payload
            )

    try:
        first = await websocket.receive_text()
        try:
            start_message = json.loads(first)
        except json.JSONDecodeError:
            await websocket.send_json(
                {
                    "type": "protocol_error",
                    "message": "First message must be JSON start configuration.",
                }
            )
            return

        if start_message.get("type") != "start":
            await websocket.send_json(
                {
                    "type": "protocol_error",
                    "message": "First message must have type='start'.",
                }
            )
            return

        sample_rate = int(
            start_message.get("sample_rate", 48000)
        )
        channels = int(
            start_message.get("channels", 1)
        )
        encoding = str(
            start_message.get("encoding", "linear16")
        )

        bot = get_runtime().new_bot(
            response_mode="voice"
        )

        session = StreamingVoiceSession(
            chatbot=bot,
            stt=DeepgramLiveSTT(),
            tts=EdgeTTSStreamer(),
            event_sink=emit,
        )

        await session.start(
            sample_rate=sample_rate,
            channels=channels,
            encoding=encoding,
        )

        await websocket.send_json(
            {
                "type": "ready",
                "sample_rate": sample_rate,
                "channels": channels,
                "encoding": encoding,
                "message": "Sara live voice session is ready.",
            }
        )

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            audio = message.get("bytes")
            if audio is not None:
                await session.send_audio(
                    audio
                )
                continue

            text = message.get("text")
            if text is None:
                continue

            try:
                control = json.loads(
                    text
                )
            except json.JSONDecodeError:
                continue

            control_type = control.get("type")

            if control_type == "finalize":
                await session.finalize()
                continue

            if control_type == "stop":
                await session.finalize()
                await asyncio.sleep(
                    max(
                        0.0,
                        float(
                            os.getenv(
                                "SARA_STREAM_FINALIZE_WAIT_MS",
                                "650",
                            )
                        )
                        / 1000.0,
                    )
                )
                await session.close()
                session = None
                await websocket.send_json(
                    {
                        "type": "session_closed",
                    }
                )
                break

            if control_type == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception(
            "Streaming voice session failed"
        )
        try:
            await websocket.send_json(
                {
                    "type": "server_error",
                    "message": (
                        "Streaming session failed. "
                        "Check server logs for provider details."
                    ),
                    "error_type": exc.__class__.__name__,
                }
            )
        except Exception:
            pass
    finally:
        if session is not None:
            try:
                await session.close()
            except Exception:
                logger.exception(
                    "Streaming session cleanup failed"
                )
