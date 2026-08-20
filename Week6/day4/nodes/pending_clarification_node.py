from __future__ import annotations

import re

from state import AgentState


def _extract_date(text: str) -> str | None:
    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text.strip(),
    )

    return match.group(1) if match else None


def pending_clarification_node(
    state: AgentState,
) -> AgentState:
    """
    Complete a previously requested clarification.

    Example:

        Turn 1:
            Who will win Pies vs Cats?

        Turn 2:
            2026-08-22
    """

    clarification_needed = state.get(
        "clarification_needed"
    )

    query = state.get(
        "user_query",
        "",
    ).strip()

    # ---------------------------------------------------------------
    # Date clarification
    # ---------------------------------------------------------------

    if clarification_needed == "date":

        date_value = _extract_date(query)

        if not date_value:
            return {
                **state,
                "validation_status": "needs_clarification",
                "validation_error": (
                    "Please provide the date in "
                    "YYYY-MM-DD format."
                ),
            }

        tool_input = dict(
            state.get("tool_input") or {}
        )

        tool_input["date"] = date_value

        return {
            **state,
            "date": date_value,
            "tool_input": tool_input,
            "validation_status": "valid",
            "clarification_needed": "",
            "validation_error": "",
        }

    return state