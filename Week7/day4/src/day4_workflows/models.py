"""Validated data contracts shared by Calendar, email, CRM and the API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


class AppointmentRequest(BaseModel):
    """Information that must be resolved before a visit can be booked."""

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: UUID = Field(default_factory=uuid4)
    client_name: str = Field(min_length=2, max_length=120)
    client_phone: str = Field(min_length=7, max_length=24)
    client_email: str | None = None
    employee_name: str = Field(min_length=2, max_length=120)
    employee_email: str
    employee_calendar_id: str = Field(default="primary", min_length=1, max_length=255)
    # Property inventory uses stable IDs such as LHR-DHA-APT-001. Keep int
    # compatibility for older callers and persisted appointments.
    property_id: str | int
    property_name: str = Field(min_length=2, max_length=255)
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)
    meeting_notes: str = Field(default="", max_length=2000)

    @field_validator("client_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        allowed = set("+0123456789- ()")
        if any(char not in allowed for char in value):
            raise ValueError("phone contains unsupported characters")
        digits = "".join(char for char in value if char.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValueError("phone must contain 7 to 15 digits")
        return value

    @field_validator("client_email", "employee_email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        local, separator, domain = value.rpartition("@")
        if not separator or not local or "." not in domain or any(char.isspace() for char in value):
            raise ValueError("invalid email address")
        return value

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class Appointment(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    appointment_id: UUID = Field(default_factory=uuid4)
    request: AppointmentRequest
    status: AppointmentStatus = AppointmentStatus.PENDING
    calendar_event_id: str | None = None
    calendar_link: str | None = None
    created_at: datetime
    updated_at: datetime
    previous_starts_at: datetime | None = None


class WorkflowResult(BaseModel):
    appointment: Appointment
    notification_sent: bool
    workflow_event_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Day3PendingAction(BaseModel):
    """Boundary contract accepted from Day 3's ``memory.pending_action``."""

    type: str
    property: dict[str, Any] | None = None
