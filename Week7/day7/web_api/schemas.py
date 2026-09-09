from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ChatRequest(APIModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(APIModel):
    conversation_id: UUID
    message: str
    recommendation_session_id: UUID | None = None
    properties: list["PropertyResponse"] | None = None
    appointment: dict | None = None
    requires_clarification: bool = False


class CustomerCreate(APIModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str = Field(min_length=7, max_length=24)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("invalid email address")
        return value.casefold()


class RegisterRequest(CustomerCreate):
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("password must include a letter and a number")
        return value


class LoginRequest(APIModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("invalid email address")
        return value.casefold()


class AuthMeResponse(APIModel):
    customer_id: UUID
    full_name: str | None = None
    email: str
    phone: str | None = None


class MeInteractionCreate(APIModel):
    property_id: str = Field(min_length=1, max_length=100)
    action: Literal["liked", "rejected", "shortlisted"]
    recommendation_session_id: UUID


class MeAppointmentBook(APIModel):
    property_id: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)
    meeting_notes: str = Field(default="", max_length=2000)

    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class CustomerResponse(APIModel):
    customer_id: UUID
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None


class PreferencesUpdate(APIModel):
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=150)
    budget_min: int | None = Field(default=None, gt=0)
    budget_max: int | None = Field(default=None, gt=0)
    bedrooms: int | None = Field(default=None, ge=0, le=30)
    property_type: Literal["Apartment", "House", "Villa", "Plot", "Commercial"] | None = None
    purpose: Literal["purchase", "rental", "investment", "commercial"] | None = None
    amenities: list[str] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def budget_order(self):
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("budget_min cannot exceed budget_max")
        return self


class PreferencesResponse(APIModel):
    customer_id: UUID
    city: str | None = None
    area: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    bedrooms: int | None = None
    property_type: str | None = None
    purpose: str | None = None
    amenities: list[str] = Field(default_factory=list)


class PropertySearchRequest(APIModel):
    customer_id: UUID | None = None
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=150)
    budget_max: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=30)
    property_type: Literal["Apartment", "House", "Villa", "Plot", "Commercial"] | None = None
    purpose: Literal["purchase", "rental", "investment", "commercial"] | None = None
    amenities: list[str] | None = Field(default=None, max_length=50)
    limit: int = Field(default=20, ge=1, le=100)


class PropertyResponse(APIModel):
    property_id: str
    property_name: str
    city: str
    area: str
    price: float
    currency: str = "PKR"
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: str
    purpose: str
    amenities: list[str] = Field(default_factory=list)
    available: bool
    status: str | None = None


class RecommendationRequest(APIModel):
    recommendation_session_id: UUID | None = None
    limit: int = Field(default=10, ge=1, le=100)


class RecommendationResponse(APIModel):
    recommendation_session_id: UUID
    ml_mode: Literal["off", "shadow", "active_dev"]
    properties: list[PropertyResponse]


class InteractionCreate(APIModel):
    customer_id: UUID
    property_id: str = Field(min_length=1, max_length=100)
    action: Literal["liked", "rejected", "shortlisted"]
    recommendation_session_id: UUID


class InteractionResponse(APIModel):
    interaction_id: UUID
    customer_id: UUID
    property_id: str
    action: str


class AppointmentBook(APIModel):
    customer_id: UUID
    property_id: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)
    meeting_notes: str = Field(default="", max_length=2000)

    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class AppointmentReschedule(APIModel):
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value
