from __future__ import annotations

import re
import time

from state import AgentState

from tools.prediction_tools import (
    match_winner_prediction,
    top_player_prediction,
)

from tools.team_resolver import extract_team_mentions
from predict import VALID_TEAMS


# ============================================================================
# DATE HELPERS
# ============================================================================

def _explicit_date(text: str) -> str | None:
    """
    Extract a YYYY-MM-DD date from text.
    """

    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text,
    )

    return match.group(1) if match else None


def _is_date_only_query(text: str) -> bool:
    """
    True only when the complete user message is a date.

    Example:
        2025-08-30
    """

    return bool(
        re.fullmatch(
            r"20\d{2}-\d{2}-\d{2}",
            text.strip(),
        )
    )


# ============================================================================
# SAFE TOOL INVOCATION
# ============================================================================

def _safe_invoke(
    tool,
    payload: dict,
    state: AgentState,
) -> AgentState:

    started = time.perf_counter()

    tool_name = state.get(
        "tool_name",
        "prediction",
    )

    try:

        print(
            "[DEBUG prediction_node] invoking tool"
        )

        print(
            {
                "intent": state.get("intent"),
                "tool_name": tool_name,
                "tool_input": payload,
            }
        )

        raw = tool.invoke(payload)

        print(
            "[DEBUG prediction_node] tool_result:"
        )

        print(raw)

        return {
            **state,

            "intent": "prediction",

            "tool_result": raw,

            "validation_status": "valid",

            "validation_error": "",

            "tools_called": (
                state.get("tools_called", [])
                + [tool_name]
            ),

            "latency_ms": round(
                (
                    time.perf_counter()
                    - started
                ) * 1000,
                2,
            ),

            "error": "",

            # Prediction completed.
            "clarification_needed": None,

            "pending_tool_name": None,
        }

    except Exception as exc:

        print(
            "[DEBUG prediction_node] tool_error:"
        )

        print(str(exc))

        return {
            **state,

            "intent": "prediction",

            "tool_result": None,

            "validation_status": "invalid",

            "validation_error":
                "The prediction tool could not "
                "complete safely.",

            "tools_called": (
                state.get("tools_called", [])
                + [tool_name]
            ),

            "latency_ms": round(
                (
                    time.perf_counter()
                    - started
                ) * 1000,
                2,
            ),

            "error": str(exc),
        }


# ============================================================================
# MAIN NODE
# ============================================================================

def prediction_node(
    state: AgentState,
) -> AgentState:

    query = (
        state.get("user_query", "")
        .strip()
    )

    q = query.lower()

    # ------------------------------------------------------------------------
    # Prediction node owns prediction intent.
    # ------------------------------------------------------------------------

    state = {
        **state,
        "intent": "prediction",
    }

    # ------------------------------------------------------------------------
    # Existing tool input
    # ------------------------------------------------------------------------

    existing_tool_input = dict(
        state.get("tool_input") or {}
    )

    pending_tool = state.get(
        "pending_tool_name"
    )

    # =========================================================================
    # 1. CONTINUE MATCH-WINNER PREDICTION
    # =========================================================================
    #
    # Previous:
    #
    #   Who will win Collingwood vs Geelong?
    #
    # Current:
    #
    #   2025-08-30
    #
    # pending_clarification_node should produce:
    #
    # {
    #     "home_team": "...",
    #     "away_team": "...",
    #     "date": "..."
    # }
    #
    # =========================================================================

    if (
        pending_tool
        == "match_winner_prediction"
        and existing_tool_input.get("home_team")
        and existing_tool_input.get("away_team")
        and existing_tool_input.get("date")
    ):

        return _safe_invoke(
            match_winner_prediction,
            existing_tool_input,
            {
                **state,

                "intent": "prediction",

                "tool_name":
                    "match_winner_prediction",

                "tool_input":
                    existing_tool_input,

                "team_a":
                    existing_tool_input["home_team"],

                "team_b":
                    existing_tool_input["away_team"],

                "date":
                    existing_tool_input["date"],
            },
        )

    # =========================================================================
    # 2. CONTINUE TOP-PLAYER PREDICTION
    # =========================================================================
    #
    # Previous:
    #
    #   Who is the top player for Collingwood?
    #
    # Current:
    #
    #   2025-08-30
    #
    # =========================================================================

    if (
        pending_tool
        == "top_player_prediction"
        and existing_tool_input.get("team")
        and existing_tool_input.get("date")
    ):

        payload = {
            "team":
                existing_tool_input["team"],

            "date":
                existing_tool_input["date"],

            "top_n":
                existing_tool_input.get(
                    "top_n",
                    5,
                ),
        }

        return _safe_invoke(
            top_player_prediction,
            payload,
            {
                **state,

                "intent": "prediction",

                "tool_name":
                    "top_player_prediction",

                "tool_input":
                    payload,

                "team_a":
                    existing_tool_input["team"],

                "date":
                    existing_tool_input["date"],
            },
        )

    # =========================================================================
    # 3. RECOVER PREVIOUS TEAMS
    # =========================================================================

    team_a = state.get("team_a")
    team_b = state.get("team_b")

    # =========================================================================
    # 4. EXTRACT TEAMS FROM CURRENT QUERY
    # =========================================================================

    teams = extract_team_mentions(
        query,
        VALID_TEAMS,
    )

    if len(teams) >= 2:

        team_a, team_b = teams[:2]

    elif team_a and team_b:

        teams = [
            team_a,
            team_b,
        ]

    # =========================================================================
    # 5. EXTRACT DATE
    # =========================================================================

    date = _explicit_date(query)

    if not date:

        date = state.get("date")

    # =========================================================================
    # 6. STANDALONE DATE
    # =========================================================================
    #
    # If there is NO pending prediction, do not run a model just because
    # the user typed a date.
    #
    # Normally the router should handle this before reaching this node,
    # but this protects the prediction node as well.
    # =========================================================================

    if _is_date_only_query(query):

        if pending_tool not in {
            "match_winner_prediction",
            "top_player_prediction",
        }:

            return {
                **state,

                "intent":
                    "prediction",

                "tool_name":
                    "prediction",

                "validation_status":
                    "needs_clarification",

                "clarification_needed":
                    None,

                "pending_tool_name":
                    None,

                "validation_error":
                    "Please provide an AFL prediction "
                    "question with the team or teams "
                    "you want me to predict.",
            }

    # =========================================================================
    # 7. UNSUPPORTED PREDICTIONS
    # =========================================================================

    unsupported_phrases = (
        "exact score",
        "score prediction",
        "final score",
        "winning margin",
        "exact margin",
        "number of goals",
        "number of points",
    )

    if any(
        phrase in q
        for phrase in unsupported_phrases
    ):

        return {
            **state,

            "intent":
                "prediction",

            "tool_name":
                "prediction",

            "validation_status":
                "needs_clarification",

            "validation_error":
                "I can currently predict AFL "
                "match winners and top players, "
                "but I do not have a model for "
                "exact scores or winning margins.",
        }

    # =========================================================================
    # 8. MATCH-WINNER KEYWORDS
    # =========================================================================

    winner_words = (
        "who will win",
        "will win",
        "winner",
        "beat ",
        "defeat ",
        "match prediction",
        "predict",
    )

    # =========================================================================
    # 9. MATCH-WINNER PREDICTION
    # =========================================================================

    if (
        len(teams) >= 2
        and any(
            word in q
            for word in winner_words
        )
    ):

        home, away = teams[:2]

        # ---------------------------------------------------------------------
        # Date missing -> ask for date
        # ---------------------------------------------------------------------

        if not date:

            return {
                **state,

                "intent":
                    "prediction",

                "team_a":
                    home,

                "team_b":
                    away,

                "tool_name":
                    "match_winner_prediction",

                # IMPORTANT:
                # Must match MatchInput exactly.
                "tool_input": {
                    "home_team":
                        home,

                    "away_team":
                        away,
                },

                "validation_status":
                    "needs_clarification",

                "clarification_needed":
                    "date",

                "pending_tool_name":
                    "match_winner_prediction",

                "validation_error":
                    "I resolved the teams, but I do "
                    "not have a live fixture/date "
                    "resolver. Please provide the "
                    "match date in YYYY-MM-DD format.",
            }

        # ---------------------------------------------------------------------
        # Date exists -> run prediction
        # ---------------------------------------------------------------------

        payload = {
            "home_team":
                home,

            "away_team":
                away,

            "date":
                date,
        }

        return _safe_invoke(
            match_winner_prediction,
            payload,
            {
                **state,

                "intent":
                    "prediction",

                "team_a":
                    home,

                "team_b":
                    away,

                "date":
                    date,

                "tool_name":
                    "match_winner_prediction",

                "tool_input":
                    payload,
            },
        )

    # =========================================================================
    # 10. TOP-PLAYER PREDICTION
    # =========================================================================

    top_words = (
        "top player",
        "best player",
        "top performer",
        "top scorer",
    )

    if any(
        word in q
        for word in top_words
    ):

        # ---------------------------------------------------------------------
        # Team missing
        # ---------------------------------------------------------------------

        if not teams:

            return {
                **state,

                "intent":
                    "prediction",

                "tool_name":
                    "top_player_prediction",

                "validation_status":
                    "needs_clarification",

                "clarification_needed":
                    "team",

                "pending_tool_name":
                    "top_player_prediction",

                "validation_error":
                    "Which AFL team should I "
                    "predict the top player for?",
            }

        team = teams[0]

        # ---------------------------------------------------------------------
        # Date missing
        # ---------------------------------------------------------------------

        if not date:

            return {
                **state,

                "intent":
                    "prediction",

                "team_a":
                    team,

                "tool_name":
                    "top_player_prediction",

                "tool_input": {
                    "team":
                        team,

                    "top_n":
                        5,
                },

                "validation_status":
                    "needs_clarification",

                "clarification_needed":
                    "date",

                "pending_tool_name":
                    "top_player_prediction",

                "validation_error":
                    "Please provide the prediction "
                    "date in YYYY-MM-DD format.",
            }

        # ---------------------------------------------------------------------
        # Run model
        # ---------------------------------------------------------------------

        payload = {
            "team":
                team,

            "date":
                date,

            "top_n":
                5,
        }

        return _safe_invoke(
            top_player_prediction,
            payload,
            {
                **state,

                "intent":
                    "prediction",

                "team_a":
                    team,

                "date":
                    date,

                "tool_name":
                    "top_player_prediction",

                "tool_input":
                    payload,
            },
        )

    # =========================================================================
    # 11. FALLBACK
    # =========================================================================

    return {
        **state,

        "intent":
            "prediction",

        "tool_name":
            "prediction",

        "validation_status":
            "needs_clarification",

        "clarification_needed":
            None,

        "validation_error":
            "I can currently predict AFL match "
            "winners and top players. I do not "
            "have a model for that requested "
            "prediction type.",
    }