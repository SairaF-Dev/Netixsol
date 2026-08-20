from __future__ import annotations

import re

from state import AgentState

from tools.prediction_tools import (
    match_winner_prediction,
    top_player_prediction,
)

from tools.team_resolver import extract_team_mentions

from predict import VALID_TEAMS


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _explicit_date(text: str) -> str | None:
    """Extract an explicit YYYY-MM-DD date."""

    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text,
    )

    return match.group(1) if match else None


def _resolve_date(query: str) -> str | None:
    """
    Resolve explicit dates only.

    We intentionally do not guess dates such as 'this week'
    or 'next week' because the supplied Day 2 artifacts do
    not contain a live fixture resolver.
    """

    return _explicit_date(query)


# ---------------------------------------------------------------------------
# Resume pending prediction
# ---------------------------------------------------------------------------

def _resume_pending_prediction(
    state: AgentState,
) -> AgentState | None:
    """
    Resume a prediction that was waiting for clarification.

    Example:

        User:
            Who will win Pies vs Cats?

        Assistant:
            Please provide the match date.

        User:
            2026-08-22

    The second message contains only the date, so we must use
    the teams saved from the first request.
    """

    pending_tool = state.get("pending_tool_name")

    if not pending_tool:
        return None

    tool_input = dict(
        state.get("tool_input") or {}
    )

    # ================================================================
    # MATCH WINNER
    # ================================================================

    if pending_tool == "match_winner_prediction":

        home_team = (
            tool_input.get("home_team")
            or state.get("team_a")
        )

        away_team = (
            tool_input.get("away_team")
            or state.get("team_b")
        )

        # IMPORTANT:
        # The new user message may contain the missing date.
        new_date = _explicit_date(
            state.get("user_query", "")
        )

        prediction_date = (
            new_date
            or tool_input.get("date")
            or state.get("date")
        )

        if not home_team or not away_team:
            return {
                **state,
                "validation_status": "needs_clarification",
                "clarification_needed": "",
                "pending_tool_name": "",
                "validation_error": (
                    "I lost the teams from the previous prediction "
                    "request. Please ask the match prediction again."
                ),
            }

        if not prediction_date:
            return {
                **state,
                "validation_status": "needs_clarification",
                "clarification_needed": "date",
                "pending_tool_name": "match_winner_prediction",
                "validation_error": (
                    "Please provide the match date in "
                    "YYYY-MM-DD format."
                ),
            }

        raw = match_winner_prediction.invoke(
            {
                "home_team": home_team,
                "away_team": away_team,
                "date": prediction_date,
            }
        )

        return {
            **state,

            "team_a": home_team,
            "team_b": away_team,
            "date": prediction_date,

            "tool_name": "match_winner_prediction",

            "tool_input": {
                "home_team": home_team,
                "away_team": away_team,
                "date": prediction_date,
            },

            "tool_result": raw,

            "validation_status": "valid",

            "clarification_needed": "",
            "pending_tool_name": "",
            "validation_error": "",
        }

    # ================================================================
    # TOP PLAYER
    # ================================================================

    if pending_tool == "top_player_prediction":

        team = (
            tool_input.get("team")
            or state.get("team_a")
        )

        new_date = _explicit_date(
            state.get("user_query", "")
        )

        prediction_date = (
            new_date
            or tool_input.get("date")
            or state.get("date")
        )

        top_n = tool_input.get(
            "top_n",
            5,
        )

        if not team:
            return {
                **state,
                "validation_status": "needs_clarification",
                "clarification_needed": "team",
                "pending_tool_name": "top_player_prediction",
                "validation_error": (
                    "Which AFL team should I predict "
                    "the top player for?"
                ),
            }

        if not prediction_date:
            return {
                **state,
                "validation_status": "needs_clarification",
                "clarification_needed": "date",
                "pending_tool_name": "top_player_prediction",
                "validation_error": (
                    "Please provide the prediction date in "
                    "YYYY-MM-DD format."
                ),
            }

        raw = top_player_prediction.invoke(
            {
                "team": team,
                "date": prediction_date,
                "top_n": top_n,
            }
        )

        return {
            **state,

            "team_a": team,
            "date": prediction_date,

            "tool_name": "top_player_prediction",

            "tool_input": {
                "team": team,
                "date": prediction_date,
                "top_n": top_n,
            },

            "tool_result": raw,

            "validation_status": "valid",

            "clarification_needed": "",
            "pending_tool_name": "",
            "validation_error": "",
        }

    return None


# ---------------------------------------------------------------------------
# Main prediction node
# ---------------------------------------------------------------------------

def prediction_node(
    state: AgentState,
) -> AgentState:

    # ================================================================
    # FIRST: RESUME PENDING PREDICTION
    # ================================================================

    if state.get("pending_tool_name"):

        resumed = _resume_pending_prediction(state)

        if resumed is not None:
            return resumed

    # ================================================================
    # NORMAL NEW PREDICTION REQUEST
    # ================================================================

    query = state["user_query"]
    query_lower = query.lower()

    teams = extract_team_mentions(
        query,
        VALID_TEAMS,
    )

    prediction_date = _resolve_date(query)

    # ================================================================
    # UNSUPPORTED SCORE / MARGIN PREDICTIONS
    # ================================================================

    unsupported_prediction_words = (
        "exact score",
        "score prediction",
        "final score",
        "winning margin",
        "exact margin",
        "number of goals",
        "number of points",
    )

    if any(
        word in query_lower
        for word in unsupported_prediction_words
    ):
        return {
            **state,
            "tool_name": "prediction",
            "validation_status": "needs_clarification",
            "validation_error": (
                "I can currently predict AFL match winners and "
                "top players, but I do not have a model for "
                "exact scores or winning margins."
            ),
        }

    # ================================================================
    # MATCH WINNER
    # ================================================================

    winner_words = (
        "who will win",
        "will ",
        "winner",
        "beat ",
        "defeat ",
        "match prediction",
        "predict",
    )

    is_match = (
        len(teams) >= 2
        and any(
            word in query_lower
            for word in winner_words
        )
    )

    if is_match:

        home, away = teams[0], teams[1]

        # ------------------------------------------------------------
        # DATE MISSING
        # ------------------------------------------------------------

        if not prediction_date:

            return {
                **state,

                "team_a": home,
                "team_b": away,

                "tool_name": "match_winner_prediction",

                "tool_input": {
                    "home_team": home,
                    "away_team": away,
                },

                "validation_status": "needs_clarification",

                "clarification_needed": "date",

                "pending_tool_name": (
                    "match_winner_prediction"
                ),

                "validation_error": (
                    "I resolved the teams, but I do not have a "
                    "live fixture/date resolver in the supplied "
                    "Day 2 artifacts. Please provide the match "
                    "date in YYYY-MM-DD format."
                ),
            }

        # ------------------------------------------------------------
        # DATE AVAILABLE
        # ------------------------------------------------------------

        raw = match_winner_prediction.invoke(
            {
                "home_team": home,
                "away_team": away,
                "date": prediction_date,
            }
        )

        return {
            **state,

            "team_a": home,
            "team_b": away,
            "date": prediction_date,

            "tool_name": "match_winner_prediction",

            "tool_input": {
                "home_team": home,
                "away_team": away,
                "date": prediction_date,
            },

            "tool_result": raw,

            "validation_status": "valid",

            "clarification_needed": "",
            "pending_tool_name": "",
            "validation_error": "",
        }

    # ================================================================
    # TOP PLAYER
    # ================================================================

    top_player_words = (
        "top player",
        "best player",
        "top performer",
        "top scorer",
    )

    if any(
        word in query_lower
        for word in top_player_words
    ):

        # ------------------------------------------------------------
        # TEAM MISSING
        # ------------------------------------------------------------

        if not teams:

            return {
                **state,

                "tool_name": "top_player_prediction",

                "validation_status": "needs_clarification",

                "clarification_needed": "team",

                "pending_tool_name": (
                    "top_player_prediction"
                ),

                "validation_error": (
                    "Which AFL team should I predict "
                    "the top player for?"
                ),
            }

        team = teams[0]

        # ------------------------------------------------------------
        # DATE MISSING
        # ------------------------------------------------------------

        if not prediction_date:

            return {
                **state,

                "team_a": team,

                "tool_name": "top_player_prediction",

                "tool_input": {
                    "team": team,
                    "top_n": 5,
                },

                "validation_status": "needs_clarification",

                "clarification_needed": "date",

                "pending_tool_name": (
                    "top_player_prediction"
                ),

                "validation_error": (
                    "Please provide the prediction date in "
                    "YYYY-MM-DD format. The supplied Day 2 "
                    "artifacts do not include a live fixture feed."
                ),
            }

        # ------------------------------------------------------------
        # DATE AVAILABLE
        # ------------------------------------------------------------

        raw = top_player_prediction.invoke(
            {
                "team": team,
                "date": prediction_date,
                "top_n": 5,
            }
        )

        return {
            **state,

            "team_a": team,
            "date": prediction_date,

            "tool_name": "top_player_prediction",

            "tool_input": {
                "team": team,
                "date": prediction_date,
                "top_n": 5,
            },

            "tool_result": raw,

            "validation_status": "valid",

            "clarification_needed": "",
            "pending_tool_name": "",
            "validation_error": "",
        }

    # ================================================================
    # UNSUPPORTED PREDICTION
    # ================================================================

    return {
        **state,

        "tool_name": "prediction",

        "validation_status": "needs_clarification",

        "validation_error": (
            "I can currently predict match winners and "
            "top players. I do not have a model for that "
            "requested prediction type."
        ),
    }