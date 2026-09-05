from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from vapi_integration.customer_identity import normalize_phone
from vapi_integration.customer_repository import Customer
from vapi_integration.customer_service import CustomerContext
from vapi_integration.interaction_repository import InteractionRepository
from vapi_integration.preference_repository import CustomerPreferences
from vapi_integration.session_manager import VapiSessionManager
from vapi_integration.tool_handler import VapiToolHandler


class RecordingInteractions:
    def __init__(self):
        self.events = []

    def record_interaction(self, **event):
        self.events.append(event)


class FakeCustomerService:
    def resolve_for_phone(self, phone):
        if phone == normalize_phone("03001234567"):
            return CustomerContext(
                customer=Customer(customer_id="customer-1", phone_normalized=phone),
                preferences=CustomerPreferences(customer_id="customer-1"),
            )
        return CustomerContext()

    def resolve_for_customer_id(self, customer_id):
        return CustomerContext()


def make_session_manager(interactions: RecordingInteractions) -> VapiSessionManager:
    return VapiSessionManager(
        customer_service=FakeCustomerService(),
        interaction_repository=interactions,
    )


def test_invalid_action_is_rejected_before_database_write():
    repository = InteractionRepository.__new__(InteractionRepository)
    repository._connect = Mock(side_effect=AssertionError("database should not be called"))

    with pytest.raises(ValueError, match="Unsupported interaction action"):
        repository.record_interaction("customer-1", "call-1", "P001", "unknown")


def test_feedback_resolves_second_shown_property_and_records_it():
    interactions = RecordingInteractions()
    manager = make_session_manager(interactions)
    session = asyncio.run(manager.create_session("call-1", caller_phone="03001234567"))
    session.shown_property_ids = ["P001", "P002"]
    session.latest_recommended_property_order = ["P001", "P002"]

    response = asyncio.run(manager._apply_feedback(session, SimpleNamespace(
        interaction_action="liked", selected_index=1, reference_type=None,
        interaction_property_id=None,
    )))

    assert "pasand" in response
    assert [event["property_id"] for event in interactions.events] == ["P002"]
    assert interactions.events[0]["action"] == "liked"


def test_ambiguous_feedback_does_not_record():
    interactions = RecordingInteractions()
    manager = make_session_manager(interactions)
    session = asyncio.run(manager.create_session("call-2", caller_phone="03001234567"))
    session.shown_property_ids = ["P001", "P002"]
    session.latest_recommended_property_order = ["P001", "P002"]

    response = asyncio.run(manager._apply_feedback(session, SimpleNamespace(
        interaction_action="shortlisted", selected_index=None,
        reference_type=None, interaction_property_id=None,
    )))

    assert "pehli" in response
    assert interactions.events == []


def test_unidentified_feedback_stays_in_memory_only():
    interactions = RecordingInteractions()
    manager = VapiSessionManager(interaction_repository=interactions)
    session = asyncio.run(manager.create_session("call-browser", caller_phone="unknown"))
    session.shown_property_ids = ["P001"]
    session.latest_recommended_property_order = ["P001"]

    asyncio.run(manager._apply_feedback(session, SimpleNamespace(
        interaction_action="rejected", selected_index=0,
        reference_type=None, interaction_property_id=None,
    )))

    assert interactions.events == []


@pytest.mark.asyncio
async def test_search_records_only_presented_properties():
    interactions = RecordingInteractions()
    handler = VapiToolHandler(interaction_repository=interactions)
    handler.repository = Mock()
    handler.preference_repository = None
    handler.repository.search = Mock(return_value=[
        {"property_id": "P001", "property_name": "One", "area": "DHA", "city": "Lahore", "price": 1},
        {"property_id": "P002", "property_name": "Two", "area": "DHA", "city": "Lahore", "price": 2},
        {"property_id": "P003", "property_name": "Three", "area": "DHA", "city": "Lahore", "price": 3},
        {"property_id": "P004", "property_name": "Four", "area": "DHA", "city": "Lahore", "price": 4},
    ])
    session = SimpleNamespace(customer_id="customer-1", call_id="call-search")

    result = await handler._search_properties({"location": "Lahore", "max_price": 10}, session=session)

    assert "Found 4 verified properties" in result
    assert [event["property_id"] for event in interactions.events] == ["P001", "P002", "P003"]
    assert all(event["action"] == "shown" for event in interactions.events)
    assert session.shown_property_ids == ["P001", "P002", "P003"]


@pytest.mark.asyncio
async def test_booking_and_cancellation_record_only_success():
    interactions = RecordingInteractions()
    handler = VapiToolHandler(interaction_repository=interactions)
    handler.day4_api_key = "test-key"
    response = SimpleNamespace(
        status_code=201,
        content=True,
        text="ok",
        json=lambda: {"appointment": {"appointment_id": "apt-1"}},
    )
    handler._appointment_request = AsyncMock(return_value=response)
    session = SimpleNamespace(
        customer_id="customer-1", call_id="call-book", appointment_id=None,
        appointment_property_id=None,
    )

    await handler._book_appointment({"property_id": "P002", "client_name": "Ali"}, session)
    assert interactions.events[0]["action"] == "appointment_booked"
    assert interactions.events[0]["property_id"] == "P002"

    cancel_response = SimpleNamespace(status_code=200, content=True, text="ok")
    handler._appointment_request = AsyncMock(return_value=cancel_response)
    await handler._cancel_appointment({"appointment_id": "apt-1"}, session)
    assert interactions.events[1]["action"] == "appointment_cancelled"
    assert interactions.events[1]["property_id"] == "P002"

    handler._appointment_request = AsyncMock(return_value=SimpleNamespace(status_code=500, content=True, text="failed"))
    await handler._book_appointment({"property_id": "P003", "client_name": "Ali"}, session)
    assert [event["action"] for event in interactions.events] == [
        "appointment_booked", "appointment_cancelled"
    ]