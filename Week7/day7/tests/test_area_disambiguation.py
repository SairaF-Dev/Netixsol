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
