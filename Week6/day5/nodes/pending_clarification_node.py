import re

from state import AgentState


def _extract_date(text: str):
    m = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text.strip()
    )

    return m.group(1) if m else None


def pending_clarification_node(
    state: AgentState
) -> AgentState:

    needed = state.get("clarification_needed")
    query = state.get("user_query", "").strip()

    # =========================================================
    # DATE CLARIFICATION
    # =========================================================

    if needed == "date":

        date_value = _extract_date(query)

        if not date_value:

            return {
                **state,

                "intent": "prediction",

                "validation_status":
                    "needs_clarification",

                "validation_error":
                    "Please provide the date in "
                    "YYYY-MM-DD format.",
            }

        tool_input = dict(
            state.get("tool_input") or {}
        )

        # -----------------------------------------------------
        # MATCH WINNER
        # -----------------------------------------------------

        if (
            state.get("pending_tool_name")
            == "match_winner_prediction"
        ):

            home_team = (
                state.get("team_a")
                or tool_input.get("home_team")
            )

            away_team = (
                state.get("team_b")
                or tool_input.get("away_team")
            )

            if not home_team or not away_team:

                return {
                    **state,

                    "intent": "prediction",

                    "validation_status":
                        "invalid",

                    "validation_error":
                        "I could not recover both teams "
                        "from the previous request.",
                }

            tool_input = {
                "home_team": home_team,
                "away_team": away_team,
                "date": date_value,
            }

            return {
                **state,

                "intent": "prediction",

                "team_a": home_team,
                "team_b": away_team,

                "date": date_value,

                "tool_input": tool_input,

                "pending_tool_name":
                    "match_winner_prediction",

                "clarification_needed":
                    None,

                "validation_status":
                    "valid",

                "validation_error":
                    "",
            }

        # -----------------------------------------------------
        # TOP PLAYER
        # -----------------------------------------------------

        if (
            state.get("pending_tool_name")
            == "top_player_prediction"
        ):

            team = (
                state.get("team_a")
                or tool_input.get("team")
            )

            if not team:

                return {
                    **state,

                    "intent": "prediction",

                    "validation_status":
                        "invalid",

                    "validation_error":
                        "I could not recover the team "
                        "from the previous request.",
                }

            tool_input = {
                "team": team,
                "date": date_value,
                "top_n": tool_input.get(
                    "top_n",
                    5
                ),
            }

            return {
                **state,

                "intent": "prediction",

                "team_a": team,

                "date": date_value,

                "tool_input": tool_input,

                "pending_tool_name":
                    "top_player_prediction",

                "clarification_needed":
                    None,

                "validation_status":
                    "valid",

                "validation_error":
                    "",
            }

        # -----------------------------------------------------
        # Unknown pending tool
        # -----------------------------------------------------

        return {
            **state,

            "validation_status":
                "invalid",

            "validation_error":
                "Unknown pending clarification.",
        }

    return state