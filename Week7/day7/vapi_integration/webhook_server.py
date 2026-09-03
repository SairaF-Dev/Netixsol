"""VAPI Webhook Server — FastAPI server that receives VAPI events and
routes them through Sara's LangGraph conversation engine.

VAPI sends events to this server via HTTP POST. We process each
message turn through the Sara agent and return the response text,
which VAPI then converts to speech and plays back to the caller.

Event flow per call:
    1. call-start   → initialize session state
    2. transcript   → run LangGraph turn, return response text
    3. tool-calls   → execute Day 4 appointment tools (book/reschedule/cancel)
    4. call-end     → persist CRM log, close session

Usage:
    uvicorn vapi_integration.webhook_server:app --host 0.0.0.0 --port 8007
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Uvicorn is often started directly, so load the service-owned environment
# before importing modules that initialize database access.
_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_FILE, override=False)

# ── add Day 3 sara_agent to path ──────────────────────────────────────────────
_DAY3_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "day3", "src")
if _DAY3_SRC not in sys.path:
    sys.path.insert(0, os.path.abspath(_DAY3_SRC))

# ── add Day 4 to path ─────────────────────────────────────────────────────────
_DAY4_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "day4")
if _DAY4_SRC not in sys.path:
    sys.path.insert(0, os.path.abspath(_DAY4_SRC))

from vapi_integration.session_manager import VapiSessionManager
from vapi_integration.tool_handler import VapiToolHandler
from vapi_integration.metrics import metrics
from vapi_integration.models import (
    VapiWebhookPayload,
    VapiMessageResponse,
    VapiToolCallResult,
)

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vapi.webhook")

# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sara VAPI Webhook Server",
    description="Routes VAPI phone call events to Sara's LangGraph conversation engine",
    version="1.0.0",
)

# ── globals (initialised on startup) ─────────────────────────────────────────
session_manager: VapiSessionManager | None = None
tool_handler: VapiToolHandler | None = None


@app.on_event("startup")
async def startup() -> None:
    global session_manager, tool_handler

    day4_url = os.getenv("DAY4_API_URL", "http://localhost:8004")
    session_manager = VapiSessionManager()
    tool_handler = VapiToolHandler(day4_api_url=day4_url)
    logger.info("Sara VAPI webhook server started. Day4 API: %s", day4_url)


# ── health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "sara-vapi-webhook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_sessions": session_manager.active_count() if session_manager else 0,
    }


@app.get("/metrics")
async def operational_metrics() -> dict:
    """Return privacy-safe counters and latency percentiles."""
    return metrics.snapshot()


# ── VAPI secret verification ──────────────────────────────────────────────────
def _verify_vapi_secret(secret: str | None) -> None:
    """Reject requests that don't carry the VAPI shared secret."""
    expected = os.getenv("VAPI_WEBHOOK_SECRET")
    if expected and secret != expected:
        raise HTTPException(status_code=403, detail="Invalid VAPI webhook secret")


# ── main webhook endpoint ─────────────────────────────────────────────────────
@app.post("/vapi/webhook")
async def vapi_webhook(
    request: Request,
    x_vapi_secret: str | None = Header(default=None),
) -> JSONResponse:
    """
    Main VAPI webhook endpoint.

    VAPI sends POST requests here for every call event. We handle:
      - assistant-request  : VAPI asks which assistant config to use
      - call-start         : New call → create session
      - transcript         : User spoke → run LangGraph turn → reply
      - tool-calls         : Agent wants to call a tool (book appointment etc.)
      - call-end           : Call ended → flush CRM log
    """
    _verify_vapi_secret(x_vapi_secret)

    body = await request.json()
    message_type: str = body.get("message", {}).get("type", "unknown")
    call_id: str = body.get("message", {}).get("call", {}).get("id", str(uuid.uuid4()))

    logger.info("VAPI event: type=%s call_id=%s", message_type, call_id)

    # ── assistant-request ─────────────────────────────────────────────────────
    if message_type == "assistant-request":
        return JSONResponse(content=_build_assistant_config())

    # ── call-start ────────────────────────────────────────────────────────────
    elif message_type == "call-start":
        caller_phone = (
            body.get("message", {})
            .get("call", {})
            .get("customer", {})
            .get("number", "unknown")
        )
        await session_manager.create_session(call_id, caller_phone=caller_phone)
        logger.info("New call session created. call_id=%s caller=%s", call_id, caller_phone)
        return JSONResponse(content={"status": "ok"})

    # ── transcript (main conversation turn) ───────────────────────────────────
    elif message_type == "transcript":
        transcript = body.get("message", {}).get("transcript", "")
        role = body.get("message", {}).get("role", "user")

        if role != "user" or not transcript.strip():
            return JSONResponse(content={"status": "ignored"})

        # Run Sara's LangGraph agent
        response_text = await session_manager.process_turn(
            call_id=call_id,
            user_message=transcript,
        )

        logger.info(
            "Turn complete. call_id=%s user=%r sara=%r",
            call_id,
            transcript[:80],
            response_text[:80],
        )

        # VAPI reads the "content" field aloud via the configured TTS
        return JSONResponse(
            content={
                "type": "text",
                "content": response_text,
            }
        )

    # ── tool-calls (agent wants to call calendar/email/booking) ───────────────
    elif message_type == "tool-calls":
        message = body.get("message", {})
        # Support both VAPI's current payload and the legacy OpenAI-shaped one.
        tool_calls = message.get("toolCallList") or message.get("toolCalls", [])
        results = []

        for tc in tool_calls:
            tool_call_id = tc.get("id", str(uuid.uuid4()))
            function = tc.get("function", {})
            function_name = tc.get("name") or function.get("name", "")
            arguments = tc.get("parameters") or function.get("arguments", {})

            logger.info("Tool call: %s args=%s", function_name, arguments)

            result = await tool_handler.execute(
                tool_name=function_name,
                arguments=arguments,
                call_id=call_id,
                session=await session_manager.get_session(call_id),
            )

            results.append({
                "name": function_name,
                "toolCallId": tool_call_id,
                "result": result,
            })

        return JSONResponse(content={"results": results})

    # ── call-end ──────────────────────────────────────────────────────────────
    elif message_type == "end-of-call-report":
        summary = body.get("message", {}).get("summary", "")
        transcript_full = body.get("message", {}).get("transcript", "")
        recording_url = body.get("message", {}).get("recordingUrl", "")

        await session_manager.close_session(
            call_id=call_id,
            summary=summary,
            transcript=transcript_full,
            recording_url=recording_url,
        )
        logger.info("Call ended. call_id=%s", call_id)
        return JSONResponse(content={"status": "ok"})

    # ── unknown ───────────────────────────────────────────────────────────────
    else:
        logger.debug("Unhandled VAPI event type: %s", message_type)
        return JSONResponse(content={"status": "ignored"})


# ── assistant config builder ──────────────────────────────────────────────────
def _build_assistant_config() -> dict:
    """
    Build the VAPI assistant configuration.

    This is returned when VAPI sends 'assistant-request' — it tells VAPI
    which STT, TTS, and LLM providers to use, and which tools Sara has.
    The LLM is overridden to 'custom-llm' so VAPI forwards transcripts
    to OUR server instead of calling OpenAI directly.
    """
    server_url = os.getenv("VAPI_SERVER_URL", "https://your-server.com")

    return {
        "assistant": {
            "name": "Sara",
            "model": {
                # Tell VAPI to use our server as the LLM backend
                "provider": "custom-llm",
                "url": f"{server_url}/vapi/webhook",
                "model": "sara-langgraph-agent",
                # Tools Sara can call during a conversation
                "tools": _get_sara_tools(),
            },
            # STT: Deepgram Nova-3 (same provider as Day 3)
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-3",
                # Callers code-switch between Pakistani Urdu and English.
                "language": "multi",
                "smartFormat": True,
                "numerals": True,
                "endpointing": 450,
                # Nova-3 uses unweighted keyterm prompting.
                "keyterm": [
                    "DHA", "DHA Phase 6", "Bahria Town", "apartment",
                    "one bedroom", "crore", "lakh", "property visit",
                    "appointment", "RealEstate Hub",
                ],
            },
            # TTS: Fish Audio (same provider as Day 3)
            "voice": {
                "provider": "11labs",  # fish-audio maps via 11labs API in VAPI
                # Alternative: use "playht" or "openai" if fish-audio not available
                "voiceId": os.getenv("VAPI_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
                "speed": 0.95,
                "stability": 0.7,
                "similarityBoost": 0.8,
            },
            # Call behaviour
            "firstMessage": (
                "Assalam-o-Alaikum! RealEstate Hub se Sara baat kar rahi hoon. "
                "Main aap ki kis tarah help kar sakti hoon?"
            ),
            "endCallMessage": (
                "Bahut shukriya aap ne call ki! Agar koi aur sawal ho toh "
                "please dobara call karein. Allah Hafiz!"
            ),
            # Barge-in: let caller interrupt Sara mid-sentence
            "backchannel": {"enabled": True},
            "interruptionThreshold": 10,  # 0-100, lower = more sensitive
            # Background noise handling
            "backgroundSound": "off",
            # Max call duration (30 minutes)
            "maxDurationSeconds": 1800,
            # Record the call
            "recordingEnabled": True,
            # System prompt (Sara's persona from Day 1)
            "systemPrompt": _load_system_prompt(),
        }
    }


def _load_system_prompt() -> str:
    """Load Sara's system prompt from Day 1."""
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "day1",
        "05_system_prompt", "system_prompt.md"
    )
    try:
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "You are Sara, an AI real estate sales agent for RealEstate Hub. "
            "Speak in UrduLish (natural Pakistani Urdu mixed with English). "
            "Be warm, professional, and helpful."
        )


def _get_sara_tools() -> list[dict]:
    """
    Define the tools VAPI can ask Sara to call.

    These match the Day 4 appointment workflow API endpoints.
    When the LangGraph agent decides to call a tool, VAPI sends a
    'tool-calls' event to /vapi/webhook and we execute it via Day 4.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": (
                    "Property visit appointment book karo. Use this when the "
                    "customer agrees to visit a property and provides their "
                    "name, phone number, and preferred date/time."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Customer ka naam",
                        },
                        "client_phone": {
                            "type": "string",
                            "description": "Customer ka phone number (e.g. +923001234567)",
                        },
                        "client_email": {
                            "type": "string",
                            "description": "Confirmation aur reminder ke liye customer email (optional)",
                        },
                        "property_name": {
                            "type": "string",
                            "description": "Property ka naam jahan visit karni hai",
                        },
                        "property_id": {
                            "type": "string",
                            "description": "Property ID from the knowledge base",
                        },
                        "starts_at": {
                            "type": "string",
                            "description": "Visit ka time ISO 8601 format mein timezone ke saath (e.g. 2025-09-05T10:00:00+05:00)",
                        },
                        "meeting_notes": {
                            "type": "string",
                            "description": "Koi khaas notes ya requirements customer ki",
                        },
                    },
                    "required": ["client_name", "client_phone", "property_id", "property_name", "starts_at"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reschedule_appointment",
                "description": (
                    "Existing appointment ka time badlo. Use when customer "
                    "wants to change their visit date/time."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {
                            "type": "string",
                            "description": "Appointment UUID",
                        },
                        "starts_at": {
                            "type": "string",
                            "description": "Naya visit time ISO 8601 format mein",
                        },
                    },
                    "required": ["appointment_id", "starts_at"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_appointment",
                "description": (
                    "Appointment cancel karo. Use when customer explicitly "
                    "says they want to cancel their property visit."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {
                            "type": "string",
                            "description": "Appointment UUID jise cancel karna hai",
                        },
                    },
                    "required": ["appointment_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_properties",
                "description": (
                    "Customer ki requirements ke mutabiq properties dhoondo. "
                    "Use when customer mentions budget, location, bedrooms, or purpose."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City ya area (e.g. DHA Karachi, Bahria Town Lahore)",
                        },
                        "max_price": {
                            "type": "integer",
                            "description": "Maximum budget PKR mein",
                        },
                        "min_price": {
                            "type": "integer",
                            "description": "Minimum budget PKR mein",
                        },
                        "bedrooms": {
                            "type": "integer",
                            "description": "Bedrooms ki taadad",
                        },
                        "property_type": {
                            "type": "string",
                            "enum": ["Apartment", "House", "Plot", "Commercial"],
                            "description": "Customer ki required property category",
                        },
                        "purpose": {
                            "type": "string",
                            "enum": ["buy", "rent", "invest", "commercial"],
                            "description": "Property ka maqsad",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
    ]
