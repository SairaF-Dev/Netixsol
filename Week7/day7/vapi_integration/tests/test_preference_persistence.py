from __future__ import annotations

import asyncio
from types import SimpleNamespace

from vapi_integration.customer_identity import normalize_phone
from vapi_integration.customer_repository import Customer
from vapi_integration.customer_service import CustomerContext
from vapi_integration.preference_repository import CustomerPreferences
from vapi_integration.session_manager import VapiSessionManager


class RecordingCustomerService:
    def __init__(self, contexts: dict[str, CustomerContext], fail_updates: bool = False):
        self.contexts = contexts
        self.fail_updates = fail_updates
        self.preference_updates: list[tuple[str, dict[str, object]]] = []
        self.name_updates: list[tuple[str, str]] = []

    def resolve_for_phone(self, phone: str | None) -> CustomerContext:
        return self.contexts.get(phone, CustomerContext())

    def resolve_for_customer_id(self, customer_id: str | None) -> CustomerContext:
        return CustomerContext()

    def update_preferences(self, customer_id: str, updates: dict[str, object]):
        if self.fail_updates:
            raise RuntimeError("database unavailable")
        self.preference_updates.append((customer_id, updates))
        for context in self.contexts.values():
            if context.customer and context.customer.customer_id == customer_id and context.preferences:
                for field_name, value in updates.items():
                    setattr(context.preferences, field_name, value)

    def update_name(self, customer_id: str, full_name: str):
        self.name_updates.append((customer_id, full_name))


def make_context(customer_id: str = "customer-1", phone: str = "+923001234567") -> CustomerContext:
    return CustomerContext(
        customer=Customer(customer_id=customer_id, phone_normalized=phone),
        preferences=CustomerPreferences(
            customer_id=customer_id,
            city="Lahore",
            area="DHA",
            budget_max=30_000_000,
            bedrooms=3,
        ),
    )


def understanding(**required):
    return SimpleNamespace(required=required, preferred={})


def test_structured_preferences_are_persisted_immediately():
    phone = normalize_phone("03001234567")
    service = RecordingCustomerService({phone: make_context()})
    manager = VapiSessionManager(customer_service=service)
    session = asyncio.run(manager.create_session("phase2-new", caller_phone=phone))

    asyncio.run(manager._apply_understanding(session, understanding(
        city="Lahore", area="DHA", budget=40_000_000, bedrooms=3,
        property_type="Apartment", purpose="buy", amenities=["parking", "parking"],
    )))

    profile = session.sara_state.user_profile
    assert (profile.city, profile.area, profile.budget, profile.bedrooms) == (
        "Lahore", "DHA", 40_000_000, 3
    )
    assert profile.property_type == "Apartment"
    assert profile.amenities_preferred == ["parking"]
    assert service.preference_updates == [("customer-1", {
        "city": "Lahore", "area": "DHA", "budget_max": 40_000_000,
        "bedrooms": 3, "property_type": "Apartment", "purpose": "buy",
        "amenities": ["parking"],
    })]


def test_partial_update_does_not_overwrite_existing_values():
    phone = "+923001234567"
    service = RecordingCustomerService({phone: make_context()})
    manager = VapiSessionManager(customer_service=service)
    session = asyncio.run(manager.create_session("phase2-partial", caller_phone=phone))

    asyncio.run(manager._apply_understanding(session, understanding(bedrooms=4)))

    assert session.sara_state.user_profile.bedrooms == 4
    assert service.preference_updates == [("customer-1", {"bedrooms": 4})]


def test_unidentified_session_keeps_memory_without_persistence():
    service = RecordingCustomerService({})
    manager = VapiSessionManager(customer_service=service)
    session = asyncio.run(manager.create_session("phase2-browser", caller_phone="unknown"))

    asyncio.run(manager._apply_understanding(session, understanding(city="Karachi", budget=20_000_000)))

    assert session.customer_id is None
    assert session.sara_state.user_profile.city == "Karachi"
    assert session.sara_state.user_profile.budget == 20_000_000
    assert service.preference_updates == []


def test_database_failure_does_not_break_memory_update():
    phone = "+923001234567"
    service = RecordingCustomerService({phone: make_context()}, fail_updates=True)
    manager = VapiSessionManager(customer_service=service)
    session = asyncio.run(manager.create_session("phase2-failure", caller_phone=phone))

    asyncio.run(manager._apply_understanding(session, understanding(area="Gulberg")))

    assert session.sara_state.user_profile.area == "Gulberg"


def test_structured_customer_name_is_persisted():
    phone = "+923001234567"
    service = RecordingCustomerService({phone: make_context()})
    manager = VapiSessionManager(customer_service=service)
    session = asyncio.run(manager.create_session("phase2-name", caller_phone=phone))
    name_understanding = SimpleNamespace(required={}, preferred={}, customer_name="Sara Khan")

    asyncio.run(manager._apply_understanding(session, name_understanding))

    assert session.sara_state.user_profile.customer_name == "Sara Khan"
    assert service.name_updates == [("customer-1", "Sara Khan")]


def test_returning_customer_hydrates_latest_persisted_values_and_isolation():
    first_phone = "+923001234567"
    second_phone = "+923001234568"
    service = RecordingCustomerService({
        first_phone: make_context(),
        second_phone: make_context("customer-2", second_phone),
    })
    manager = VapiSessionManager(customer_service=service)

    first = asyncio.run(manager.create_session("phase2-returning", caller_phone=first_phone))
    asyncio.run(manager._apply_understanding(first, understanding(city="Islamabad", budget=40_000_000)))
    second = asyncio.run(manager.create_session("phase2-other", caller_phone=second_phone))

    assert first.sara_state.user_profile.city == "Islamabad"
    assert first.sara_state.user_profile.budget == 40_000_000
    assert second.sara_state.user_profile.city == "Lahore"
    assert second.sara_state.user_profile.budget == 30_000_000