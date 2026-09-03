"""Pydantic models for VAPI webhook payloads and responses."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class VapiCall(BaseModel):
    id: str
    type: str = "inboundPhoneCall"
    customer: dict = Field(default_factory=dict)


class VapiMessage(BaseModel):
    type: str
    call: Optional[VapiCall] = None
    transcript: Optional[str] = None
    role: Optional[str] = None
    toolCalls: list[dict] = Field(default_factory=list)
    summary: Optional[str] = None
    recordingUrl: Optional[str] = None


class VapiWebhookPayload(BaseModel):
    message: VapiMessage


class VapiMessageResponse(BaseModel):
    """Response for transcript events — VAPI speaks the 'content' field."""
    type: str = "text"
    content: str


class VapiToolCallResult(BaseModel):
    """Result of a single tool call."""
    toolCallId: str
    result: Any

