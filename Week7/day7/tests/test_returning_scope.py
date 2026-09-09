from copy import deepcopy
from unittest.mock import Mock

import pytest

from sara_agent.models import UserUnderstanding
from test_phase9_chat import chat, setup


def returning_customer():
    web, svc, nlu = setup()
    nlu.test_returning = True
    nlu.result = UserUnderstanding(intent="greeting")
    response = chat(web, message="hi")
    assert response.status_code == 200
    assert "welcome back" in response.json()["message"]
    cid = response.json()["conversation_id"]
    nlu.result = UserUnderstanding(intent="unknown")
    return web, svc, nlu, cid


@pytest.mark.parametrize("message", [
    "aur options dekhna chahungi", "aor options dekhna chahu gi",
    "different options dekhna hai", "options dekhna chahiye",
])
def test_other_options_asks_scope_and_preserves_preferences(message):
    web, svc, nlu, cid = returning_customer()
    before = deepcopy(svc.customers.preferences)
    svc.chat.store.rows[cid][2]["flexible"] = ["bedrooms"]
    response = chat(web, cid, message)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == (
        "Ji zaroor! Kya ap Lahore mein hi doosre areas ke options dekhna chahengi, "
        "ya kisi aur city mein dekhna chahengi?"
    )
    assert data["requires_clarification"]
    saved = svc.chat.store.rows[cid][2]
    assert saved["pending_scope_confirm"] == {"city": "Lahore"}
    assert not saved["pending_returning_confirm"]
    assert saved["flexible"] == ["bedrooms"]
    assert svc.customers.preferences == before
    assert nlu.result.intent == "unknown"
    assert not svc.properties.search_calls


@pytest.mark.parametrize("reply,method,inventory,expected,kwargs", [
    ("isi city mein", "list_available_areas", ["Area A", "Area B"], "Area A, Area B", {"city": "Lahore", "limit": 6}),
    ("kisi aur city", "list_available_cities", ["City A", "City B"], "City A, City B", {}),
    ("isi city mein", "list_available_areas", [], "koi aur verified area available nahi", {"city": "Lahore", "limit": 6}),
    ("kisi aur city", "list_available_cities", [], "koi aur city available nahi", {}),
])
def test_scope_reply_lists_inventory(reply, method, inventory, expected, kwargs):
    web, svc, nlu, cid = returning_customer()
    chat(web, cid, "aur options dekhna chahungi")
    lookup = Mock(return_value=inventory)
    setattr(svc.properties, method, lookup)
    response = chat(web, cid, reply)
    assert response.status_code == 200
    assert expected in response.json()["message"]
    assert response.json()["requires_clarification"]
    lookup.assert_called_once_with(**kwargs)
    assert "pending_scope_confirm" not in svc.chat.store.rows[cid][2]
    assert not svc.properties.search_calls


def test_ambiguous_reply_keeps_scope_city_for_next_turn():
    web, svc, nlu, cid = returning_customer()
    chat(web, cid, "aur options dekhna chahungi")
    for reply in ("hmm", "samajh nahi aya", "haan theek hai"):
        response = chat(web, cid, reply)
        assert response.status_code == 200
        assert "Lahore mein hi doosre areas" in response.json()["message"]
        assert response.json()["requires_clarification"]
        assert svc.chat.store.rows[cid][2]["pending_scope_confirm"] == {"city": "Lahore"}
    svc.properties.list_available_areas = Mock(return_value=["Area A"])
    assert "Area A" in chat(web, cid, "isi city mein").json()["message"]
    svc.properties.list_available_areas.assert_called_once_with(city="Lahore", limit=6)


@pytest.mark.parametrize("saved_city,reply,target_city", [
    ("Lahore", "Lahore mein hi", "Lahore"),
    ("Lahore", "Lahore mein hi areas k options dekhna chahu gi", "Lahore"),
    ("Lahore", "LAHORE hi theek hai", "Lahore"),
    ("Lahore", "Karachi mein dekhna hai", "Karachi"),
    ("Lahore", "karachi mein hi", "Karachi"),
    ("City A", "City A mein hi", "City A"),
    ("City A", "City B mein dekhna hai", "City B"),
])
def test_named_city_lists_target_areas(saved_city, reply, target_city):
    web, svc, nlu, cid = returning_customer()
    svc.customers.preferences.city = saved_city
    chat(web, cid, "aur options dekhna chahungi")
    svc.properties.list_available_cities = Mock(return_value=[saved_city, target_city])
    svc.properties.list_available_areas = Mock(return_value=["Area A", "Area B"])

    response = chat(web, cid, reply)

    assert response.status_code == 200
    assert response.json()["message"] == (
        f"Ji! {target_city} mein in areas mein verified options available hain: Area A, Area B. "
        "Kis area ke options dekhna chahengi?"
    )
    assert response.json()["requires_clarification"]
    svc.properties.list_available_cities.assert_called_once_with()
    svc.properties.list_available_areas.assert_called_once_with(city=target_city, limit=6)
    assert "pending_scope_confirm" not in svc.chat.store.rows[cid][2]
    assert not svc.properties.search_calls


@pytest.mark.parametrize("reply", ["haan aur options", "nahi aur options"])
def test_original_confirmation_and_decline_take_precedence(reply):
    web, svc, nlu, cid = returning_customer()
    response = chat(web, cid, reply)
    assert response.status_code == 200
    assert "pending_scope_confirm" not in svc.chat.store.rows[cid][2]
    assert nlu.result.intent == "property_search"

