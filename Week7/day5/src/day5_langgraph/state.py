"""LangGraph state definition for the AI voice agent."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ConversationStage(str, Enum):
    """Stages in the conversation flow."""

    GREETING = "greeting"
    INTENT_DETECTION = "intent_detection"
    CLARIFICATION = "clarification"
    RAG_RETRIEVAL = "rag_retrieval"
    RECOMMENDATION = "recommendation"
    OBJECTION_HANDLING = "objection_handling"
    BOOKING = "booking"
    RESCHEDULE = "reschedule"
    CANCELLATION = "cancellation"
    GOODBYE = "goodbye"


class UserIntent(str, Enum):
    """User intents detected from conversation."""

    BUYER_INQUIRY = "buyer_inquiry"
    RENTAL_INQUIRY = "rental_inquiry"
    INVESTMENT_INQUIRY = "investment_inquiry"
    COMMERCIAL_INQUIRY = "commercial_inquiry"
    SCHEDULE_VISIT = "schedule_visit"
    RESCHEDULE_VISIT = "reschedule_visit"
    CANCEL_VISIT = "cancel_visit"
    RETURNING_CUSTOMER = "returning_customer"
    OFF_TOPIC = "off_topic"
    UNCLEAR = "unclear"


class UserProfile(BaseModel):
    """User profile and preferences."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: UUID = Field(default_factory=uuid4)
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    bedrooms: Optional[int] = None
    purpose: Optional[str] = None  # rent, buy, invest
    preferences: dict[str, Any] = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)


class Message(BaseModel):
    """Single message in conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PropertyMatch(BaseModel):
    """Property recommendation match."""

    property_id: str | int
    name: str
    location: str
    price: int
    bedrooms: int
    bathrooms: int
    area_sqft: int
    amenities: list[str] = Field(default_factory=list)
    score: float  # 0-1 match score
    reason: str  # Why this property matches


class Appointment(BaseModel):
    """Appointment record."""

    appointment_id: UUID
    property_id: str | int
    property_name: str
    starts_at: str  # ISO format
    status: str  # pending, confirmed, rescheduled, cancelled
    calendar_event_id: Optional[str] = None
    calendar_link: Optional[str] = None


class AgentState(BaseModel):
    """Complete state of the agent and conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Session info
    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Conversation
    messages: list[Message] = Field(default_factory=list)
    conversation_stage: ConversationStage = ConversationStage.GREETING

    # User info
    user_profile: UserProfile = Field(default_factory=UserProfile)

    # Current interaction
    current_intent: Optional[UserIntent] = None
    intent_confidence: float = 0.0
    clarification_needed: bool = False
    clarification_questions: list[str] = Field(default_factory=list)

    # Properties
    detected_properties: list[PropertyMatch] = Field(default_factory=list)
    selected_property: Optional[PropertyMatch] = None
    rag_context: Optional[str] = None
    rag_confidence: float = 0.0

    # Booking
    appointment: Optional[Appointment] = None
    proposed_datetime: Optional[str] = None
    booking_status: Optional[str] = None

    # Objections
    objections: list[str] = Field(default_factory=list)
    objection_responses: list[str] = Field(default_factory=list)

    # Metadata
    conversation_log: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def create_initial_state(session_id: Optional[UUID] = None) -> AgentState:
    """Create a new initial state for conversation."""
    return AgentState(
        session_id=session_id or uuid4(),
        conversation_stage=ConversationStage.GREETING,
        user_profile=UserProfile(),
    )


def get_conversation_summary(state: AgentState) -> str:
    """Generate conversation summary from state."""
    summary_parts = []

    if state.user_profile.name:
        summary_parts.append(f"Customer: {state.user_profile.name}")

    if state.current_intent:
        summary_parts.append(f"Intent: {state.current_intent.value}")

    if state.selected_property:
        summary_parts.append(
            f"Property: {state.selected_property.name} (₨{state.selected_property.price:,.0f})"
        )

    if state.appointment:
        summary_parts.append(f"Appointment: {state.appointment.starts_at}")

    return " | ".join(summary_parts) if summary_parts else "New conversation started"
