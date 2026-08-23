from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from day5_graph import run_query


# ============================================================================
# APP
# ============================================================================

app = FastAPI(
    title="AFL Assistant API",
    description=(
        "Domain-locked AFL chat and prediction assistant."
    ),
    version="1.0.0",
)


# ============================================================================
# MONITORING LOG
# ============================================================================

LOG = Path("monitoring.jsonl")


def write_log(event: dict) -> None:
    """
    Append one structured monitoring event to monitoring.jsonl.

    Logging failures must never crash the API.
    """

    try:
        with LOG.open(
            "a",
            encoding="utf-8",
        ) as f:

            f.write(
                json.dumps(
                    event,
                    default=str,
                )
                + "\n"
            )

    except Exception as exc:

        print(
            f"[monitoring warning] "
            f"Failed to write log: {exc}"
        )


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """
    Incoming chat request.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User's AFL assistant query.",
    )

    conversation_id: str = Field(
        default="default",
        min_length=1,
        max_length=200,
        description="Conversation/session identifier.",
    )


class ChatResponse(BaseModel):
    """
    API response returned to the client.
    """

    response: str

    conversation_id: str

    intent: str | None = None

    prediction: dict | None = None

    latency_ms: float | None = None


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
def health():
    """
    Basic service health endpoint.
    """

    return {
        "status": "ok",
        "service": "afl-assistant",
        "version": "1.0.0",
    }


# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(req: ChatRequest):

    started = time.perf_counter()

    try:

        # ====================================================================
        # RUN LANGGRAPH APPLICATION
        # ====================================================================

        result = run_query(
            req.message,
            req.conversation_id,
        )

        # ====================================================================
        # CALCULATE LATENCY
        # ====================================================================

        latency = round(
            (
                time.perf_counter()
                - started
            ) * 1000,
            2,
        )

        # ====================================================================
        # FINAL RESPONSE PROTECTION
        # ====================================================================

        response = (
            result.get("final_response")
            or
            "Sorry, I could not generate a response. "
            "Please try again."
        )

        # ====================================================================
        # PREDICTION RESULT
        # ====================================================================

        prediction = (
            result.get("prediction_metadata")
            or
            result.get("tool_result")
        )

        # Only expose dictionary prediction data.
        # This keeps the API response compatible with
        # prediction: dict | None.
        if not isinstance(
            prediction,
            dict,
        ):
            prediction = None

        # ====================================================================
        # SUCCESS STATUS
        # ====================================================================

        success = not bool(
            result.get("error")
        )

        # ====================================================================
        # MONITORING EVENT
        # ====================================================================

        event = {
            "timestamp": time.time(),

            "conversation_id": (
                req.conversation_id
            ),

            "query": req.message,

            "intent": result.get(
                "intent"
            ),

            "tool_name": result.get(
                "tool_name"
            ),

            "tools_called": result.get(
                "tools_called",
                [],
            ),

            "validation_status": result.get(
                "validation_status"
            ),

            "latency_ms": latency,

            "token_usage": result.get(
                "token_usage"
            ),

            "success": success,

            "error": result.get(
                "error",
                "",
            ),
        }

        write_log(event)

        # ====================================================================
        # RETURN API RESPONSE
        # ====================================================================

        return ChatResponse(
            response=response,

            conversation_id=(
                req.conversation_id
            ),

            intent=result.get(
                "intent"
            ),

            prediction=prediction,

            latency_ms=latency,
        )

    # ========================================================================
    # EXPECTED APPLICATION ERRORS
    # ========================================================================

    except ValueError as exc:

        latency = round(
            (
                time.perf_counter()
                - started
            ) * 1000,
            2,
        )

        write_log(
            {
                "timestamp": time.time(),

                "conversation_id": (
                    req.conversation_id
                ),

                "query": req.message,

                "intent": None,

                "tool_name": None,

                "tools_called": [],

                "validation_status": "invalid",

                "latency_ms": latency,

                "token_usage": None,

                "success": False,

                "error": str(exc),
            }
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # ========================================================================
    # UNEXPECTED APPLICATION ERRORS
    # ========================================================================

    except Exception as exc:

        latency = round(
            (
                time.perf_counter()
                - started
            ) * 1000,
            2,
        )

        write_log(
            {
                "timestamp": time.time(),

                "conversation_id": (
                    req.conversation_id
                ),

                "query": req.message,

                "intent": None,

                "tool_name": None,

                "tools_called": [],

                "validation_status": "error",

                "latency_ms": latency,

                "token_usage": None,

                "success": False,

                "error": str(exc),
            }
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Internal AFL assistant error."
            ),
        )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
def root():
    """
    Basic API information.
    """

    return {
        "service": "AFL Assistant",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs",
        },
    }