"""Opt-in, redacted conversation records for offline agent improvement."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vapi_integration.customer_learning import customer_key_for_phone

_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def _redact(value: str) -> str:
    value = _EMAIL_RE.sub("[EMAIL]", value)
    return _PHONE_RE.sub("[PHONE]", value)


def build_learning_record(
    *,
    call_id: str,
    caller_phone: str,
    created_at: datetime,
    turn_count: int,
    messages: list[dict[str, Any]],
    summary: str = "",
    transcript: str = "",
) -> dict[str, Any]:
    """Build a review record without storing caller contact details."""
    safe_messages = [
        {
            "role": str(message.get("role", "unknown")),
            "content": _redact(str(message.get("content", ""))),
        }
        for message in messages
        if message.get("content")
    ]
    safe_transcript = _redact(transcript) if transcript else ""
    customer_key = ""
    if caller_phone and caller_phone != "unknown":
        salt = os.getenv("SARA_CUSTOMER_HASH_SALT", "")
        if salt:
            customer_key = customer_key_for_phone(caller_phone, salt=salt)
    return {
        "record_type": "conversation_learning",
        "call_id": call_id,
        "caller_phone": "[REDACTED]" if caller_phone else "",
        "customer_key": customer_key,
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
        "turn_count": turn_count,
        "messages": safe_messages,
        "summary": _redact(summary),
        "transcript": safe_transcript,
        "label": None,
        "review_status": "unreviewed",
    }


class LearningRecordStore:
    """Append-only local store used to create an offline review dataset."""

    def __init__(self, path: str | None = None, enabled: bool | None = None) -> None:
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("SARA_LEARNING_ENABLED", "0").strip() == "1"
        )
        self.path = Path(
            path or os.getenv(
                "SARA_LEARNING_DATA_PATH",
                "data/learning/conversations.jsonl",
            )
        )

    def record(self, **kwargs: Any) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = build_learning_record(**kwargs)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(payload, ensure_ascii=True) + "\n")
