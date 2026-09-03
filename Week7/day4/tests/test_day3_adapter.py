import pytest
from day4_workflows.day3_adapter import IncompleteHandoff, validate_pending_action

def test_day3_verified_property_handoff():
    action = validate_pending_action({"type":"schedule_visit","property":{"property_id":101,"name":"Horizon Heights"}})
    assert action.property["property_id"] == 101

def test_day3_booking_without_property_is_rejected():
    with pytest.raises(IncompleteHandoff): validate_pending_action({"type":"schedule_visit","property":None})
