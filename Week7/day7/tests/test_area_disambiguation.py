from unittest.mock import MagicMock

import pytest

from sara_agent.models import UserUnderstanding
from test_phase9_chat import chat, setup


@pytest.mark.parametrize("intent", ["property_search", "recommendation"])
@pytest.mark.parametrize("area_source", ["required", "preferred", "saved"])
def test_parent_area_lists_all_matching_phases(intent, area_source):
    web, svc, nlu = setup()
    phases = ["DHA Phase 5", "DHA Phase 6", "DHA Phase 8"]
    svc.properties.list_available_areas = MagicMock(return_value=phases + ["Gulberg"])
    nlu.result = UserUnderstanding(
        intent=intent, needs_clarification=True,
        clarification_reason="selected_area_not_available",
        **({area_source: {"area": "dha"}} if area_source != "saved" else {}),
    )

    response = chat(web, message="dha mein")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["requires_clarification"]
    assert all(phase in data["message"] for phase in phases)
    assert "kis phase" in data["message"]
    assert "Gulberg" not in data["message"]
    assert "bedrooms" not in data["message"]
    assert not data.get("properties")
    assert not svc.properties.search_calls
    svc.properties.list_available_areas.assert_called_once_with(
        city="Lahore", property_type="Apartment", purpose="purchase",
        budget=20_000_000, limit=20,
    )


@pytest.mark.parametrize("intent", ["property_search", "recommendation"])
def test_exact_area_proceeds_to_recommendations(intent):
    web, svc, nlu = setup()
    svc.properties.list_available_areas = lambda **kw: [
        "DHA Phase 5", "DHA Phase 6", "DHA Phase 6 Extension", "DHA Phase 8"]
    nlu.result = UserUnderstanding(intent=intent, required={"area": "DHA Phase 6"})

    response = chat(web, message="DHA Phase 6 mein")

    assert response.status_code == 200, response.text
    data = response.json()
    assert not data["requires_clarification"]
    assert data["properties"]
    assert svc.customers.preferences.area == "DHA Phase 6"
    assert svc.properties.search_calls[-1]["area"] == "DHA Phase 6"


@pytest.mark.parametrize("intent", ["property_search", "recommendation"])
@pytest.mark.parametrize("area_source", ["required", "preferred"])
def test_single_matching_phase_resolves_without_reasking(intent, area_source):
    web, svc, nlu = setup()
    svc.customers.preferences.area = None
    svc.properties.list_available_areas = lambda **kw: ["Garden Town Phase 2", "Gulberg"]
    nlu.result = UserUnderstanding(
        intent=intent, needs_clarification=True,
        clarification_reason="selected_area_not_available",
        **{area_source: {"area": "Garden Town"}},
    )

    response = chat(web, message="Garden Town mein")

    assert response.status_code == 200, response.text
    data = response.json()
    assert not data["requires_clarification"]
    assert data["properties"]
    assert svc.customers.preferences.area == "Garden Town Phase 2"
    assert all(call["area"] == "Garden Town Phase 2" for call in svc.properties.search_calls)
    saved = svc.chat.store.rows[data["conversation_id"]][2]
    assert "area" not in saved["flexible"]


def test_returning_customer_phase_disambiguation_flow():
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences.city = "Lahore"
    svc.customers.preferences.area = "DHA"
    svc.customers.preferences.budget_max = 28_500_000
    phases = ["DHA Phase 6", "DHA Phase 8"]
    svc.properties.list_available_areas = MagicMock(return_value=phases)

    # Turn 1: User greets
    nlu.result = UserUnderstanding(intent="greeting")
    res1 = chat(web, message="Aoa")
    assert res1.status_code == 200
    cid = res1.json()["conversation_id"]

    # Turn 2: User says "wahi hai" (continue saved requirements)
    nlu.result = UserUnderstanding(intent="SAME_REQUIREMENTS")
    res2 = chat(web, cid=cid, message="wahi hai")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["requires_clarification"]
    assert "kis phase" in data2["message"]

    # Turn 3: User says "Dha phase 6"
    nlu.result = UserUnderstanding(intent="property_search", required={"area": "DHA Phase 6"})
    res3 = chat(web, cid=cid, message="Dha phase 6")
    assert res3.status_code == 200
    data3 = res3.json()
    assert not data3["requires_clarification"]
    assert data3.get("properties")
    assert "DHA Phase 6" in data3["message"]
    # Verify preferences updated to selected phase
    assert svc.customers.preferences.area == "DHA Phase 6"


def test_returning_customer_any_phase_selection():
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences.city = "Lahore"
    svc.customers.preferences.area = "DHA"
    phases = ["DHA Phase 6", "DHA Phase 8"]
    svc.properties.list_available_areas = MagicMock(return_value=phases)

    # Turn 1: User greets
    nlu.result = UserUnderstanding(intent="greeting")
    res1 = chat(web, message="Aoa")
    cid = res1.json()["conversation_id"]

    # Turn 2: User says "wahi hai"
    nlu.result = UserUnderstanding(intent="SAME_REQUIREMENTS")
    res2 = chat(web, cid=cid, message="wahi hai")
    assert "kis phase" in res2.json()["message"]

    # Turn 3: User says "kisi b phase mein"
    nlu.result = UserUnderstanding(intent="property_search")
    res3 = chat(web, cid=cid, message="kisi b phase mein dikhayein")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3.get("properties")


def test_pending_explore_area_response():
    web, svc, nlu = setup()
    # Simulate pending_explore_area state
    res1 = chat(web, message="hello")
    cid = res1.json()["conversation_id"]
    svc.chat.store.rows[cid][2]["pending_explore_area"] = "DHA Phase 6"

    nlu.result = UserUnderstanding(intent="unknown")
    res2 = chat(web, cid=cid, message="options dikhaye")
    assert res2.status_code == 200
    data2 = res2.json()
    assert not data2["requires_clarification"]
    assert data2.get("properties")
    assert "DHA Phase 6" in data2["message"]


