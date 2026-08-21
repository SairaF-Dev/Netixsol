from __future__ import annotations

import re

from state import AgentState


DATE_ONLY_RE = re.compile(
    r"^\s*20\d{2}-\d{2}-\d{2}\s*$"
)


def _is_date_only(text: str) -> bool:
    return bool(
        DATE_ONLY_RE.fullmatch(text)
    )


def guardrail_node(state: AgentState) -> AgentState:

    query = state.get(
        "user_query",
        ""
    ).strip()

    # ============================================================
    # IMPORTANT:
    # DATE-ONLY FOLLOW-UP
    # ============================================================
    #
    # Example:
    #
    # Turn 1:
    #   Who will win Collingwood vs Geelong?
    #
    # Graph asks:
    #   Please provide the match date.
    #
    # Turn 2:
    #   2025-08-30
    #
    # This is NOT off-topic.
    #
    # ============================================================

    if _is_date_only(query):

        pending_tool = state.get(
            "pending_tool_name"
        )

        clarification_needed = state.get(
            "clarification_needed"
        )

        team_a = state.get(
            "team_a"
        )

        team_b = state.get(
            "team_b"
        )

        # --------------------------------------------------------
        # Match prediction clarification
        # --------------------------------------------------------

        if (
            pending_tool
            == "match_winner_prediction"
            and clarification_needed
            == "date"
            and team_a
            and team_b
        ):

            return {
                **state,

                "intent":
                    "prediction",

                "router_reason":
                    "The user supplied the date requested "
                    "for a pending AFL match prediction.",

                # Keep clarification information.
                "clarification_needed":
                    "date",

                "pending_tool_name":
                    "match_winner_prediction",
            }

        # --------------------------------------------------------
        # Top-player prediction clarification
        # --------------------------------------------------------

        if (
            pending_tool
            == "top_player_prediction"
            and clarification_needed
            == "date"
            and team_a
        ):

            return {
                **state,

                "intent":
                    "prediction",

                "router_reason":
                    "The user supplied the date requested "
                    "for a pending AFL top-player prediction.",

                "clarification_needed":
                    "date",

                "pending_tool_name":
                    "top_player_prediction",
            }

    # ============================================================
    # NORMAL AFL QUERY
    # ============================================================

    # IMPORTANT:
    # Keep your existing AFL guardrail logic below this point.
    #
    # For example:
    #
    # if clearly_off_topic(query):
    #     return {
    #         **state,
    #         "intent": "off_topic",
    #         "router_reason": "..."
    #     }
    #
    # Otherwise:
    #
    # return {
    #     **state,
    #     "intent": state.get("intent"),
    # }

    return state