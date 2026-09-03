"""Structured node-transition tracing for the Day 5 graph."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def trace_transition(state: Any, node: str, outcome: str = "ok") -> dict:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": node,
        "outcome": outcome,
        "stage": getattr(getattr(state, "conversation_stage", None), "value", None),
    }
    state.conversation_log.append(event)
    return event
