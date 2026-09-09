"""Returning-customer regressions using real NLU, HTTP and voice orchestration."""
import asyncio
from copy import deepcopy
from unittest.mock import Mock

import pytest

from sara_agent.models import UserUnderstanding
from sara_agent.understanding import UserUnderstandingService
from test_phase9_chat import setup, chat


@pytest.fixture
def returning(monkeypatch):
    # Exercise production extraction with provider failure, without network calls.
    monkeypatch.setattr(UserUnderstandingService, "_call_llm", Mock(side_effect=RuntimeError("offline test")))
    web, svc, _ = setup()
    svc.chat.sara.understanding = UserUnderstandingService(deterministic_first=True)
    prefs = svc.customers.preferences
    prefs.city, prefs.area, prefs.budget_max = "Karachi", None, 190_000_000
    prefs.property_type, prefs.purpose, prefs.bedrooms = "House", "purchase", 4
    first = chat(web, message="hi").json()
    assert "welcome back" in first["message"]
    return web, svc, first["conversation_id"]


@pytest.mark.parametrize("message", ["change krni hai", "preference change krni hai", "preferences change karni hain"])
def test_change_selects_field(returning, message):
    web, svc, cid = returning
    before = deepcopy(svc.customers.preferences)
    response = chat(web, cid, message)
    assert response.status_code == 200, response.text
    assert "kis preference" in response.json()["message"]
    assert "continue karni hai ya koi preference change" not in response.json()["message"]
    assert svc.chat.store.rows[cid][2]["preference_state"] == "selecting_preference_field"
    assert svc.customers.preferences == before


@pytest.mark.parametrize("message,field,reply,value", [
    ("city change karni hai", "city", "Lahore", "Lahore"),
    ("budget change krna hai", "budget_max", "5 crore", 50_000_000),
    ("location badalni hai", "area", "DHA", "DHA"),
])
def test_field_then_value(returning, message, field, reply, value):
    web, svc, cid = returning
    question = chat(web, cid, message).json()["message"]
    assert "kis preference" not in question
    assert svc.chat.store.rows[cid][2]["preference_state"] == "providing_preference_value"
    response = chat(web, cid, reply)
    assert response.status_code == 200, response.text
    assert getattr(svc.customers.preferences, field) == value
    assert svc.chat.store.rows[cid][2]["preference_state"] == "ready_for_search"


@pytest.mark.parametrize("message,expected", [
    ("city Lahore kar do", {"city": "Lahore"}),
    ("Lahore kar do", {"city": "Lahore"}),
    ("budget 5 crore kar do", {"budget_max": 50_000_000}),
    ("Karachi ki jagah Lahore aur budget 10 crore kar do", {"city": "Lahore", "budget_max": 100_000_000}),
    ("house ki jagah apartment chahiye", {"property_type": "Apartment"}),
    ("buy ki jagah rent chahiye", {"purpose": "rental", "budget_max": None}),
])
def test_direct_updates_and_persistence(returning, message, expected):
    web, svc, cid = returning
    before = deepcopy(svc.customers.preferences)
    response = chat(web, cid, message)
    assert response.status_code == 200, response.text
    assert "update ho gayi" in response.json()["message"]
    fresh = svc.customers.resolve_for_customer_id(before.customer_id).preferences
    for field in ("city", "budget_max", "property_type", "purpose", "bedrooms"):
        assert getattr(fresh, field) == expected.get(field, getattr(before, field))
    # A fresh conversation hydrates the newly stored preference.
    new = chat(web, message="hi").json()
    assert new["conversation_id"] != cid
    assert "welcome back" in new["message"]


def test_repeated_change_does_not_loop(returning):
    web, svc, cid = returning
    for message in ("change krni hai", "preference change krni hai"):
        assert "kis preference" in chat(web, cid, message).json()["message"]
        assert not svc.chat.store.rows[cid][2]["pending_returning_confirm"]


def test_continue_searches_saved_preferences(returning):
    web, svc, cid = returning
    before = deepcopy(svc.customers.preferences)
    assert chat(web, cid, "continue").status_code == 200
    assert svc.customers.preferences == before
    assert svc.chat.store.rows[cid][2]["preference_state"] == "ready_for_search"


def test_cancel_edit_preserves_profile(returning):
    web, svc, cid = returning
    before = deepcopy(svc.customers.preferences)
    chat(web, cid, "city change karni hai")
    response = chat(web, cid, "cancel edit")
    assert response.status_code == 200
    assert svc.customers.preferences == before
    assert svc.chat.store.rows[cid][2]["preference_state"] == "ready_for_search"


def test_invalid_value_is_not_saved(returning):
    web, svc, cid = returning
    svc.chat.sara.understanding = Mock(understand=Mock(return_value=UserUnderstanding(
        preference_action="edit", preference_fields=["bedrooms"], required={"bedrooms": 100})))
    response = chat(web, cid, "bedrooms 100 kar do")
    assert response.status_code == 200
    assert "valid nahi" in response.json()["message"]
    assert svc.customers.preferences.bedrooms == 4
    assert svc.chat.store.rows[cid][2]["preference_state"] == "providing_preference_value"


def test_budget_conflict_asks_only_for_budget_and_keeps_edit_active(returning):
    web, svc, cid = returning
    svc.customers.preferences.budget_min = 60_000_000
    response = chat(web, cid, "budget 5 crore kar do")
    assert response.status_code == 200
    assert "minimum budget" in response.json()["message"]
    assert svc.customers.preferences.budget_max == 190_000_000
    assert svc.chat.store.rows[cid][2]["preference_fields"] == ["budget"]
    assert chat(web, cid, "10 crore").status_code == 200
    assert svc.customers.preferences.budget_max == 100_000_000


def test_karachi_is_not_mistaken_for_change_command(returning):
    web, svc, cid = returning
    svc.customers.preferences.city = "Lahore"
    response = chat(web, cid, "city Karachi change karni hai")
    assert response.status_code == 200
    assert svc.customers.preferences.city == "Karachi"


def test_partial_multi_field_edit_keeps_missing_field(returning):
    web, svc, cid = returning
    svc.chat.sara.understanding = Mock(understand=Mock(return_value=UserUnderstanding(
        preference_action="edit", preference_fields=["city", "budget"], required={"city": "Lahore"})))
    response = chat(web, cid, "city Lahore kar do aur budget change karna hai")
    assert "naya budget" in response.json()["message"]
    assert svc.customers.preferences.city == "Lahore"
    assert svc.chat.store.rows[cid][2]["preference_fields"] == ["budget"]


def test_edit_does_not_capture_appointment_commands(returning):
    web, svc, cid = returning
    before = deepcopy(svc.customers.preferences)
    svc.chat.sara.understanding = Mock(understand=Mock(return_value=UserUnderstanding(intent="schedule_visit")))
    response = chat(web, cid, "visit book kar do")
    assert response.status_code == 200
    assert "kis preference" not in response.json()["message"]
    assert svc.customers.preferences == before


def test_browser_voice_transcripts_persist_edit_state(returning, monkeypatch):
    from test_browser_voice import voice_setup
    web, svc, _ = voice_setup(monkeypatch)
    svc.chat.sara.understanding = UserUnderstandingService(deterministic_first=True)
    for text in ("hi", "change krni hai", "budget change krna hai", "5 crore"):
        response = web.post('/api/internal/voice/webhook', headers={'x-vapi-secret': 'test-secret'}, json={
            'message': {'type': 'transcript', 'role': 'user', 'transcriptType': 'final',
                        'transcript': text, 'call': {'type': 'webCall', 'id': 'call'}}})
        assert response.status_code == 200, response.text
    assert svc.customers.preferences.budget_max == 50_000_000
    saved = next(iter(svc.chat.store.rows.values()))[2]
    assert saved["preference_state"] == "ready_for_search"


def test_semantic_edit_not_keyword_only(returning):
    web, svc, cid = returning
    svc.chat.sara.understanding = Mock(understand=Mock(return_value=UserUnderstanding(
        preference_action="edit", preference_fields=["budget"])))
    assert "naya budget" in chat(web, cid, "I'd like to revise what I can afford").json()["message"]


def test_voice_uses_same_edit_flow(returning, monkeypatch):
    from vapi_integration.session_manager import VapiSessionManager
    from vapi_integration.tests.test_preference_persistence import RecordingCustomerService, make_context
    import vapi_integration.session_manager as module
    parser = UserUnderstandingService(deterministic_first=True)
    monkeypatch.setattr(module, "UserUnderstandingService", lambda: parser)
    phone = "+923001234567"
    customer = make_context()
    service = RecordingCustomerService({phone: customer})
    manager = VapiSessionManager(customer_service=service)

    async def run():
        session = await manager.create_session("edit-voice", caller_phone=phone)
        await manager.process_turn(session.call_id, "hi")
        for message in ("change krni hai", "preference change krni hai"):
            assert "kis preference" in await manager.process_turn(session.call_id, message)
        assert "naya budget" in await manager.process_turn(session.call_id, "budget change krna hai")
        assert "update ho gayi" in await manager.process_turn(session.call_id, "5 crore")
        assert customer.preferences.budget_max == 50_000_000
        assert customer.preferences.city == "Lahore"
        assert session.preference_flow["preference_state"] == "ready_for_search"
        fresh = await manager.create_session("edit-voice-new", caller_phone=phone)
        assert fresh.sara_state.user_profile.budget == 50_000_000
    asyncio.run(run())


@pytest.mark.parametrize("message,expected", [
    ("city Karachi kar do", {"city": "Karachi", "area": None}),
    ("Lahore ki jagah Karachi aur budget 10 crore kar do", {"city": "Karachi", "area": None, "budget_max": 100_000_000}),
    ("house ki jagah apartment chahiye", {"property_type": "Apartment"}),
    ("buy ki jagah rent chahiye", {"purpose": "rental", "budget_max": None}),
])
def test_voice_direct_edits_preserve_other_fields(returning, monkeypatch, message, expected):
    from vapi_integration.session_manager import VapiSessionManager
    from vapi_integration.tests.test_preference_persistence import RecordingCustomerService, make_context
    import vapi_integration.session_manager as module
    parser = UserUnderstandingService(deterministic_first=True)
    monkeypatch.setattr(module, "UserUnderstandingService", lambda: parser)
    phone = "+923001234567"
    customer = make_context()
    customer.preferences.purpose = "purchase"
    customer.preferences.property_type = "House"
    before = deepcopy(customer.preferences)
    service = RecordingCustomerService({phone: customer})
    manager = VapiSessionManager(customer_service=service)

    async def run():
        session = await manager.create_session("direct-voice", caller_phone=phone)
        response = await manager.process_turn(session.call_id, message)
        assert "update ho gayi" in response
        for field in ("city", "area", "budget_max", "property_type", "purpose", "bedrooms"):
            assert getattr(customer.preferences, field) == expected.get(field, getattr(before, field))
    asyncio.run(run())


def test_voice_save_failure_does_not_acknowledge_success(returning, monkeypatch):
    from vapi_integration.session_manager import VapiSessionManager
    from vapi_integration.tests.test_preference_persistence import RecordingCustomerService, make_context
    import vapi_integration.session_manager as module
    parser = UserUnderstandingService(deterministic_first=True)
    monkeypatch.setattr(module, "UserUnderstandingService", lambda: parser)
    phone = "+923001234567"
    customer = make_context()
    service = RecordingCustomerService({phone: customer}, fail_updates=True)
    manager = VapiSessionManager(customer_service=service)

    async def run():
        session = await manager.create_session("failed-voice", caller_phone=phone)
        response = await manager.process_turn(session.call_id, "budget 5 crore kar do")
        assert "save nahi ho saki" in response
        assert "update ho gayi" not in response
        assert session.sara_state.user_profile.budget == 30_000_000
        assert customer.preferences.budget_max == 30_000_000
        assert session.preference_flow["preference_state"] == "editing_preferences"
    asyncio.run(run())
