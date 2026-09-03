from __future__ import annotations

from uuid import uuid4

import pytest

from day5_langgraph.graph import build_graph
from day5_langgraph.nodes import AgentNodes
from day5_langgraph.state import Appointment, Message, PropertyMatch, create_initial_state


class Tools:
    async def search_properties(self, **kwargs):
        return {"properties": [{
            "property_id": "P-1", "property_name": "Pearl Apartments",
            "area": "DHA", "city": "Lahore", "price": 25_000_000,
            "bedrooms": 3, "bathrooms": 3, "covered_area": 1800,
            "amenities": ["parking"],
        }]}

    async def book_appointment(self, **kwargs):
        return {"appointment": {
            "appointment_id": str(uuid4()), "property_id": kwargs["property_id"],
            "property_name": kwargs["property_name"], "starts_at": kwargs["starts_at"],
            "status": "confirmed",
        }}

    async def reschedule_appointment(self, **kwargs):
        return {"appointment": {
            "appointment_id": kwargs["appointment_id"], "property_id": "P-1",
            "property_name": "Pearl", "starts_at": kwargs["starts_at"],
            "status": "rescheduled",
        }}

    async def cancel_appointment(self, **kwargs):
        return {"appointment": {
            "appointment_id": kwargs["appointment_id"], "property_id": "P-1",
            "property_name": "Pearl", "starts_at": "2026-09-10T10:00:00+05:00",
            "status": "cancelled",
        }}


def graph():
    return build_graph(AgentNodes(Tools(), None))


@pytest.mark.asyncio
async def test_buyer_routes_through_search_and_recommendation():
    state = create_initial_state()
    state.messages.append(Message(role="user", content="I want to buy a house"))
    state.user_profile.name = "Ali"
    state.user_profile.phone = "+923001234567"
    state.user_profile.location = "Lahore"
    state.user_profile.budget_max = 30_000_000
    result = await graph().ainvoke(state)
    assert result["selected_property"]["property_id"] == "P-1"
    assert [event["node"] for event in result["conversation_log"]] == [
        "intent_detection", "clarification", "rag_retrieval", "recommendation"
    ]


@pytest.mark.asyncio
async def test_booking_calls_day4_adapter():
    state = create_initial_state()
    state.messages.append(Message(role="user", content="Book appointment"))
    state.user_profile.name = "Ali"
    state.user_profile.phone = "+923001234567"
    state.proposed_datetime = "2026-09-10T10:00:00+05:00"
    state.selected_property = PropertyMatch(
        property_id="P-1", name="Pearl", location="Lahore", price=25_000_000,
        bedrooms=3, bathrooms=3, area_sqft=1800, score=1, reason="verified",
    )
    result = await graph().ainvoke(state)
    assert result["booking_status"] == "confirmed"
    assert result["appointment"].status == "confirmed"


@pytest.mark.asyncio
@pytest.mark.parametrize("message,status", [("Reschedule visit", "rescheduled"), ("Cancel visit", "cancelled")])
async def test_appointment_management_routes(message, status):
    state = create_initial_state()
    state.messages.append(Message(role="user", content=message))
    state.proposed_datetime = "2026-09-11T11:00:00+05:00"
    state.appointment = Appointment(
        appointment_id=uuid4(), property_id="P-1", property_name="Pearl",
        starts_at="2026-09-10T10:00:00+05:00", status="confirmed",
    )
    result = await graph().ainvoke(state)
    assert result["booking_status"] == status


@pytest.mark.asyncio
async def test_validation_failure_is_traced_and_fails_safely():
    state = create_initial_state()
    state.messages.append(Message(role="user", content="Book appointment"))
    result = await graph().ainvoke(state)
    assert result["errors"]
    assert result["conversation_log"][-1]["outcome"] == "error"
