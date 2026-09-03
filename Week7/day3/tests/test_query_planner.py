from decimal import Decimal
from sara_agent.memory import ConversationState
from sara_agent.models import UserUnderstanding,ComparisonRequest
from sara_agent.query_planner import QueryPlanner

def test_selected_second_result():
    s=ConversationState(last_results=[{"property_id":"1"},{"property_id":"2"}])
    p=QueryPlanner().build_plan(UserUnderstanding(intent="property_selection",selected_index=1),s)
    assert s.selected_property["property_id"]=="2"
    assert not p.needs_clarification

def test_comparison_uses_verified_decimal():
    s=ConversationState(selected_property={"price":Decimal("110000")})
    u=UserUnderstanding(intent="property_search",reference_type="selected_property",
        comparison=ComparisonRequest("price","lt","selected_property",None))
    p=QueryPlanner().build_plan(u,s)
    assert p.comparison_value==Decimal("110000")


def test_ambiguous_area_is_not_committed_before_clarification():
    s = ConversationState(required={"city": "Lahore"})
    u = UserUnderstanding(
        intent="property_search",
        required={"area": "Wrong Area"},
        needs_clarification=True,
        clarification_reason="selected_area_not_available",
    )

    p = QueryPlanner().build_plan(u, s)

    assert "area" not in s.required
    assert p.needs_clarification
