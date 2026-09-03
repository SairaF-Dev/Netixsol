"""Business validation at LangGraph-to-tool boundaries."""

from __future__ import annotations

from .state import AgentState


class StateValidationError(ValueError):
    pass


def validate_search(state: AgentState) -> None:
    if not state.user_profile.location:
        raise StateValidationError("location is required before property search")


def validate_booking(state: AgentState) -> None:
    if state.selected_property is None:
        raise StateValidationError("a verified property must be selected")
    if not state.proposed_datetime:
        raise StateValidationError("appointment date and time must be confirmed")
    if not state.user_profile.name or not state.user_profile.phone:
        raise StateValidationError("customer name and phone are required")
