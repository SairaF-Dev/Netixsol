from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sara_agent.conversation_policy import ConversationPolicy
from sara_agent.memory import ConversationState
from sara_agent.understanding import UserUnderstandingService
from postgres_repository import PostgresPropertyRepository


@pytest.mark.parametrize("required,field", [
    ({}, "purpose"),
    ({"purpose": "Purchase"}, "city"),
    ({"purpose": "Purchase", "city": "Lahore"}, "budget"),
    ({"purpose": "Purchase", "city": "Lahore", "area": "DHA"}, "budget"),
])
def test_order(required, field):
    assert ConversationPolicy().next_tier1_requirement(state=ConversationState(required=required)).field == field


def test_purpose_change_invalidates_budget_and_results():
    state = ConversationState(required={"purpose": "Purchase", "budget": 40000000, "city": "Lahore"},
                              pending_action={"type": "choose_verified_area"}, last_results=[{"property_id": "old"}])
    state.apply(required={"purpose": "Rental"})
    assert "budget" not in state.required
    assert state.required["city"] == "Lahore"
    assert not state.last_results and not state.pending_action
    state.apply(required={"purpose": "Purchase", "budget": 30000000})
    assert state.required["budget"] == 30000000


@pytest.mark.parametrize("message,field", [("budget koi masla nahi", "budget"), ("budget flexible hai", "budget"),
                                            ("sab areas dikha do", "area"), ("sab suggest kiye hue areas dikha do", "area")])
def test_explicit_flexibility(message, field):
    parsed = UserUnderstandingService()._deterministic_understanding(message, {})
    assert field in parsed.relax


def test_aggregate_query_ranks_all_affordable_areas_and_verifies_prices():
    repo = object.__new__(PostgresPropertyRepository)
    cursor = MagicMock()
    repo._connect = MagicMock()
    repo._connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
    repo._rows_to_dicts = lambda cur, rows: [
        {"area": "Cheap", "min_price": Decimal(100), "max_price": Decimal(100), "match_price": Decimal(100)},
        {"area": "Close", "min_price": Decimal(390), "max_price": Decimal(390), "match_price": Decimal(390)},
        {"area": "Expensive", "min_price": Decimal(800), "max_price": Decimal(800), "match_price": None},
    ]
    result = repo.budget_area_options(city="Lahore", purpose="Purchase", budget=400)
    assert [row["area"] for row in result["areas"]] == ["Close", "Cheap"]
    assert result["cheapest"]["area"] == "Cheap"
    sql, params = cursor.execute.call_args.args
    assert "verification_status = 'Verified'" in sql and "p.available = TRUE" in sql
    assert "LIMIT" not in sql and params["purpose"] == "Purchase"


def test_unaffordable_inventory_never_becomes_generic_area_list():
    knowledge = SimpleNamespace(budget_area_options=lambda **kw: {
        "areas": [], "cheapest": {"area": "Verified Area", "min_price": 5000000}})
    state = ConversationState(required={"city": "Lahore", "purpose": "Purchase", "budget": 100000})
    result = ConversationPolicy().next_tier1_requirement(state=state, knowledge=knowledge)
    assert "5,000,000" in result.message and "Verified Area" in result.message
    assert result.field == "budget" and state.required["budget"] == 100000


def test_all_details_skip_questions_and_tier2_threshold():
    policy = ConversationPolicy()
    state = ConversationState(required={"purpose": "Purchase", "city": "Lahore", "budget": 30000000, "area": "DHA", "property_type": "House"})
    assert policy.next_tier1_requirement(state=state) is None
    assert policy.next_narrowing_requirement(state=state, matching_count=5, threshold=5) is None
    assert policy.next_narrowing_requirement(state=state, matching_count=6, threshold=5).field == "bedrooms"


def test_new_customer_http_flow_and_side_question():
    from test_phase9_chat import setup, chat
    from sara_agent.models import UserUnderstanding
    web, svc, nlu = setup()
    prefs = svc.customers.preferences
    for key in ("city", "area", "budget_max", "bedrooms", "property_type", "purpose"):
        setattr(prefs, key, None)
    prefs.amenities = []
    nlu.result = UserUnderstanding(intent="greeting")
    result = chat(web, message="hi").json()
    cid = result["conversation_id"]
    assert "Sara" in result["message"] and "purchase" in result["message"]
    assert "budget" not in result["message"].lower()
    nlu.result = UserUnderstanding(intent="property_search", required={"purpose": "Purchase"})
    assert "city" in chat(web, cid, "ghar khareedna hai").json()["message"]
    nlu.result = UserUnderstanding(intent="property_search", required={"city": "Lahore"})
    assert "budget" in chat(web, cid, "Lahore").json()["message"]
    nlu.result = UserUnderstanding(intent="unknown")
    answer = chat(web, cid, "aap kaun ho").json()["message"]
    assert "Sara" in answer and "budget" in answer
    assert prefs.city == "Lahore" and prefs.purpose == "purchase"


def test_returning_partial_correction_preserves_location():
    from test_phase9_chat import setup, chat
    from sara_agent.models import UserUnderstanding
    web, svc, nlu = setup()
    nlu.test_returning = True
    nlu.result = UserUnderstanding(intent="greeting")
    result = chat(web, message="hi").json()
    assert "welcome back" in result["message"]
    nlu.result = UserUnderstanding(intent="property_search", required={"budget": 15000000})
    chat(web, result["conversation_id"], "budget 1.5 crore")
    assert svc.customers.preferences.city == "Lahore"
    assert svc.customers.preferences.budget_max == 15000000
