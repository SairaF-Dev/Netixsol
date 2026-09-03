"""Tests for agent state management."""

import pytest
from uuid import UUID

from day5_langgraph.state import (
    AgentState,
    ConversationStage,
    UserIntent,
    UserProfile,
    Message,
    create_initial_state,
    get_conversation_summary,
)


def test_create_initial_state():
    """Test creating initial agent state."""
    state = create_initial_state()

    assert isinstance(state, AgentState)
    assert isinstance(state.session_id, UUID)
    assert state.conversation_stage == ConversationStage.GREETING
    assert state.messages == []
    assert state.current_intent is None


def test_user_profile_creation():
    """Test user profile creation."""
    profile = UserProfile(name="Ali Khan", phone="+923001234567")

    assert profile.name == "Ali Khan"
    assert profile.phone == "+923001234567"
    assert profile.budget_min is None
    assert profile.budget_max is None


def test_message_creation():
    """Test message creation."""
    msg = Message(role="user", content="I want to buy a property")

    assert msg.role == "user"
    assert msg.content == "I want to buy a property"
    assert msg.timestamp is not None


def test_conversation_summary():
    """Test generating conversation summary."""
    state = create_initial_state()
    state.user_profile.name = "Ali Khan"
    state.current_intent = UserIntent.BUYER_INQUIRY

    summary = get_conversation_summary(state)

    assert "Ali Khan" in summary
    assert "buyer_inquiry" in summary


def test_state_transitions():
    """Test conversation stage transitions."""
    state = create_initial_state()

    assert state.conversation_stage == ConversationStage.GREETING

    state.conversation_stage = ConversationStage.INTENT_DETECTION
    assert state.conversation_stage == ConversationStage.INTENT_DETECTION

    state.conversation_stage = ConversationStage.BOOKING
    assert state.conversation_stage == ConversationStage.BOOKING


def test_intent_enum_values():
    """Test user intent enum values."""
    assert UserIntent.BUYER_INQUIRY.value == "buyer_inquiry"
    assert UserIntent.RENTAL_INQUIRY.value == "rental_inquiry"
    assert UserIntent.INVESTMENT_INQUIRY.value == "investment_inquiry"
    assert UserIntent.RESCHEDULE_VISIT.value == "reschedule_visit"
