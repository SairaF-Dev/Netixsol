"""Resolve Day 3 pending actions into Day 4 API operations."""
from __future__ import annotations
from .models import Day3PendingAction

class IncompleteHandoff(ValueError): pass

def validate_pending_action(raw: dict) -> Day3PendingAction:
    action = Day3PendingAction.model_validate(raw)
    if action.type not in {"schedule_visit", "reschedule_visit", "cancel_visit"}: raise IncompleteHandoff("Unsupported Day 3 action")
    if action.type != "cancel_visit" and not action.property: raise IncompleteHandoff("A verified selected property is required")
    return action
