from __future__ import annotations

import asyncio

from vapi_integration.customer_identity import normalize_phone
from vapi_integration.customer_repository import Customer
from vapi_integration.customer_service import CustomerContext
from vapi_integration.preference_repository import CustomerPreferences
from vapi_integration.session_manager import VapiSessionManager


def test_normalize_pakistani_mobile_phone():
    assert normalize_phone("03001234567") == "+923001234567"
    assert normalize_phone("+923001234567") == "+923001234567"
    assert normalize_phone("00923001234567") == "+923001234567"


def test_invalid_phone_is_rejected():
    assert normalize_phone("unknown") is None
    assert normalize_phone("0300123") is None
    assert normalize_phone("not-a-phone") is None


class FakeCustomerService:
    def __init__(self, contexts_by_phone: dict[str, CustomerContext]):
        self.contexts_by_phone = contexts_by_phone

    def resolve_for_phone(self, phone: str) -> CustomerContext:
        return self.contexts_by_phone.get(phone, CustomerContext())

    def resolve_for_customer_id(self, customer_id: str) -> CustomerContext:
        return CustomerContext()


def make_context(customer_id: str, phone: str, *, city: str | None = None) -> CustomerContext:
    return CustomerContext(
        customer=Customer(customer_id=customer_id, phone_normalized=phone, full_name="Ali"),
        preferences=CustomerPreferences(
            customer_id=customer_id,
            city=city,
            area="DHA" if city else None,
            budget_max=30_000_000 if city else None,
            bedrooms=3 if city else None,
            property_type="apartment" if city else None,
            purpose="buy" if city else None,
            amenities=["parking"] if city else [],
        ),
    )


def test_new_caller_gets_customer_identity_without_preferences():
    phone = "+923001234567"
    service = FakeCustomerService({phone: make_context("customer-1", phone)})
    manager = VapiSessionManager(customer_service=service)

    session = asyncio.run(manager.create_session("call-new", caller_phone="03001234567"))

    assert session.customer_id == "customer-1"
    assert session.caller_phone == phone
    assert session.sara_state.user_profile.customer_phone == phone
    assert session.sara_state.user_profile.city is None


def test_returning_caller_preferences_are_hydrated():
    phone = "+923001234567"
    service = FakeCustomerService({phone: make_context("customer-1", phone, city="Lahore")})
    manager = VapiSessionManager(customer_service=service)

    session = asyncio.run(manager.create_session("call-returning", caller_phone=phone))
    profile = session.sara_state.user_profile

    assert profile.customer_name == "Ali"
    assert profile.customer_phone == phone
    assert profile.city == "Lahore"
    assert profile.area == "DHA"
    assert profile.budget == 30_000_000
    assert profile.bedrooms == 3
    assert profile.property_type == "apartment"
    assert profile.purpose == "buy"
    assert profile.amenities_preferred == ["parking"]


def test_talk_button_without_phone_remains_unidentified():
    manager = VapiSessionManager(customer_service=FakeCustomerService({}))

    session = asyncio.run(manager.create_session("call-browser", caller_phone="unknown"))

    assert session.customer_id is None
    assert session.caller_phone == "unknown"
    assert session.sara_state.user_profile.customer_phone == "unknown"


def test_one_customer_preferences_do_not_leak_to_another_session():
    first_phone = "+923001234567"
    second_phone = "+923001234568"
    service = FakeCustomerService({
        first_phone: make_context("customer-1", first_phone, city="Lahore"),
        second_phone: make_context("customer-2", second_phone, city="Karachi"),
    })
    manager = VapiSessionManager(customer_service=service)

    first = asyncio.run(manager.create_session("call-one", caller_phone=first_phone))
    second = asyncio.run(manager.create_session("call-two", caller_phone=second_phone))

    assert first.sara_state.user_profile.city == "Lahore"
    assert second.sara_state.user_profile.city == "Karachi"
    assert second.sara_state.user_profile.area == "DHA"