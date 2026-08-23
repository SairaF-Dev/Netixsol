from __future__ import annotations

import re
import time
from typing import Any

from state import AgentState

from tools.prediction_tools import (
    match_winner_prediction,
    top_player_prediction,
    get_latest_data_year,
    get_forecast_year,
    get_training_seasons,
)

from tools.team_resolver import extract_team_mentions
from predict import VALID_TEAMS


# ============================================================================
# CONSTANTS
# ============================================================================

MATCH_WINNER_TOOL = "match_winner_prediction"
TOP_PLAYER_TOOL = "top_player_prediction"
PREDICTION_TOOL = "prediction"

DEFAULT_TOP_N = 5


# ============================================================================
# DATE HELPERS
# ============================================================================

def _explicit_date(text: str) -> str | None:
    """
    Extract explicit YYYY-MM-DD date.
    """

    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text or "",
    )

    return match.group(1) if match else None


def _explicit_year(text: str) -> int | None:
    """
    Extract a standalone four-digit year.

    Examples:
        2040 -> 2040
        2026 -> 2026

    Does not treat YYYY-MM-DD as a separate year request.
    """

    text = text or ""

    date_match = _explicit_date(text)

    if date_match:
        # The date already contains the year.
        return int(date_match[:4])

    match = re.search(
        r"\b(20\d{2})\b",
        text,
    )

    return (
        int(match.group(1))
        if match
        else None
    )


def _year_to_prediction_date(
    year: int,
) -> str:
    """
    Convert a year-only request into a season-end prediction date.

    Example:
        2026 -> 2026-09-28
    """

    return f"{year}-09-28"


def _is_date_only_query(text: str) -> bool:
    """
    Return True when query consists only of YYYY-MM-DD.
    """

    return bool(
        re.fullmatch(
            r"20\d{2}-\d{2}-\d{2}",
            (text or "").strip(),
        )
    )


# ============================================================================
# FUTURE FORECAST VALIDATION
# ============================================================================

def _future_horizon_error(
    requested_year: int,
) -> str | None:
    """
    Validate requested future year.

    Current project rule:

        latest 2 seasons -> next 1 season

    Example:

        data through 2025
        training = 2024 + 2025
        forecast = 2026

        2040 -> rejected
        2060 -> rejected
    """

    latest_year = get_latest_data_year()
    forecast_year = get_forecast_year()
    training_seasons = get_training_seasons()

    if requested_year <= latest_year:
        return None

    if requested_year > forecast_year:

        return (
            f"My current AFL prediction model uses the latest "
            f"two available seasons "
            f"({training_seasons[0]}-{training_seasons[1]}) "
            f"and is designed to forecast only the immediately "
            f"following season ({forecast_year}). "
            f"I cannot provide a reliable forecast for "
            f"{requested_year} from the available data."
        )

    return None


# ============================================================================
# TEAM HELPERS
# ============================================================================

def _same_team(
    team_a: str | None,
    team_b: str | None,
) -> bool:

    if not team_a or not team_b:
        return False

    return (
        str(team_a).strip().casefold()
        ==
        str(team_b).strip().casefold()
    )


def _find_team_in_text(
    text: str,
    valid_teams: list[str],
) -> str | None:

    text = (text or "").strip()

    if not text:
        return None

    text_clean = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    text_clean = re.sub(
        r"\s+",
        " ",
        text_clean,
    ).strip().casefold()

    matches: list[str] = []

    for team in valid_teams:

        team_clean = re.sub(
            r"[^\w\s]",
            " ",
            team,
        )

        team_clean = re.sub(
            r"\s+",
            " ",
            team_clean,
        ).strip().casefold()

        # Full team name.
        if re.search(
            rf"\b{re.escape(team_clean)}\b",
            text_clean,
        ):
            matches.append(team)
            continue

        # Short team name.
        team_words = team_clean.split()

        if team_words:

            short_name = team_words[0]

            if re.search(
                rf"\b{re.escape(short_name)}\b",
                text_clean,
            ):
                matches.append(team)

    if not matches:
        return None

    matches.sort(
        key=len,
        reverse=True,
    )

    return matches[0]


def _extract_match_teams(
    query: str,
    valid_teams: list[str],
) -> list[str]:

    query = (query or "").strip()

    if not query:
        return []

    separator_pattern = re.compile(
        r"\s+(?:vs\.?|versus|against)\s+",
        flags=re.IGNORECASE,
    )

    parts = separator_pattern.split(
        query,
        maxsplit=1,
    )

    if len(parts) == 2:

        left_team = _find_team_in_text(
            parts[0],
            valid_teams,
        )

        right_team = _find_team_in_text(
            parts[1],
            valid_teams,
        )

        if left_team and right_team:

            return [
                left_team,
                right_team,
            ]

    resolved = extract_team_mentions(
        query,
        valid_teams,
    )

    if resolved:
        return list(resolved)

    return []


# ============================================================================
# STATE HELPERS
# ============================================================================

def _base_prediction_state(
    state: AgentState,
    *,
    tool_name: str,
    tool_input: dict | None = None,
) -> AgentState:

    return {
        **state,
        "intent": "prediction",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_result": None,
        "error": None,
        "clarification_needed": None,
        "pending_tool_name": None,
        "validation_status": None,
        "validation_error": None,
    }


def _needs_clarification(
    state: AgentState,
    *,
    tool_name: str,
    tool_input: dict | None,
    field: str,
    message: str,
) -> AgentState:

    return {
        **state,
        "intent": "prediction",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_result": None,
        "validation_status": "needs_clarification",
        "validation_error": message,
        "clarification_needed": field,
        "pending_tool_name": tool_name,
        "error": None,
    }


def _unsupported_prediction_state(
    state: AgentState,
    message: str,
) -> AgentState:

    return {
        **state,
        "intent": "prediction",
        "tool_name": PREDICTION_TOOL,
        "tool_input": None,
        "tool_result": {
            "unsupported": True,
            "message": message,
        },
        "validation_status": "valid",
        "validation_error": None,
        "clarification_needed": None,
        "pending_tool_name": None,
        "final_response": message,
        "error": None,
    }


def _same_team_state(
    state: AgentState,
    home: str,
    away: str,
    date: str | None = None,
) -> AgentState:

    message = (
        f"'{home}' cannot play against itself. "
        "Please provide two different AFL teams."
    )

    tool_input = {
        "home_team": home,
        "away_team": away,
    }

    if date:
        tool_input["date"] = date

    return {
        **state,
        "intent": "prediction",
        "tool_name": MATCH_WINNER_TOOL,
        "tool_input": tool_input,
        "tool_result": {
            "error": message,
            "invalid_matchup": True,
        },
        "validation_status": "needs_clarification",
        "validation_error": message,
        "clarification_needed": None,
        "pending_tool_name": None,
        "final_response": message,
        "error": None,
        "team_a": None,
        "team_b": None,
        "date": None,
    }


# ============================================================================
# SAFE TOOL INVOCATION
# ============================================================================

def _safe_invoke(
    tool: Any,
    payload: dict,
    state: AgentState,
) -> AgentState:

    started = time.perf_counter()

    tool_name = state.get(
        "tool_name",
        PREDICTION_TOOL,
    )

    try:

        raw = tool.invoke(payload)

        elapsed_ms = round(
            (
                time.perf_counter()
                - started
            )
            * 1000,
            2,
        )

        # --------------------------------------------------------------------
        # None result
        # --------------------------------------------------------------------

        if raw is None:

            message = (
                "Prediction tool returned no result."
            )

            return {
                **state,
                "intent": "prediction",
                "tool_result": {
                    "error": message,
                },
                "validation_status": "needs_clarification",
                "validation_error": message,
                "clarification_needed": None,
                "pending_tool_name": None,
                "tools_called": (
                    state.get(
                        "tools_called",
                        [],
                    )
                    + [tool_name]
                ),
                "latency_ms": elapsed_ms,
                "error": message,
            }

        # --------------------------------------------------------------------
        # Explicit unsupported prediction
        # --------------------------------------------------------------------

        if (
            isinstance(raw, dict)
            and raw.get("unsupported") is True
        ):

            message = str(
                raw.get(
                    "error"
                    or "message",
                    "This prediction is not supported.",
                )
            )

            return {
                **state,
                "intent": "prediction",
                "tool_result": raw,
                "validation_status": "valid",
                "validation_error": None,
                "clarification_needed": None,
                "pending_tool_name": None,
                "tools_called": (
                    state.get(
                        "tools_called",
                        [],
                    )
                    + [tool_name]
                ),
                "latency_ms": elapsed_ms,
                "error": None,
                "final_response": message,
            }

        # --------------------------------------------------------------------
        # Explicit tool error
        # --------------------------------------------------------------------

        if (
            isinstance(raw, dict)
            and raw.get("error")
        ):

            message = str(
                raw["error"]
            )

            return {
                **state,
                "intent": "prediction",
                "tool_result": raw,
                "validation_status": "needs_clarification",
                "validation_error": message,
                "clarification_needed": None,
                "pending_tool_name": None,
                "tools_called": (
                    state.get(
                        "tools_called",
                        [],
                    )
                    + [tool_name]
                ),
                "latency_ms": elapsed_ms,
                "error": None,
            }

        # --------------------------------------------------------------------
        # Success
        # --------------------------------------------------------------------

        return {
            **state,
            "intent": "prediction",
            "tool_result": raw,
            "validation_status": "valid",
            "validation_error": None,
            "clarification_needed": None,
            "pending_tool_name": None,
            "tools_called": (
                state.get(
                    "tools_called",
                    [],
                )
                + [tool_name]
            ),
            "latency_ms": elapsed_ms,
            "error": None,
        }

    except Exception as exc:

        print(
            f"[ERROR prediction_node] "
            f"{tool_name} failed: {exc}"
        )

        elapsed_ms = round(
            (
                time.perf_counter()
                - started
            )
            * 1000,
            2,
        )

        return {
            **state,
            "intent": "prediction",
            "tool_result": {
                "error": "Prediction service failed.",
            },
            "validation_status": "needs_clarification",
            "validation_error": (
                "The prediction service could not "
                "complete the request safely."
            ),
            "clarification_needed": None,
            "pending_tool_name": None,
            "tools_called": (
                state.get(
                    "tools_called",
                    [],
                )
                + [tool_name]
            ),
            "latency_ms": elapsed_ms,
            "error": "Prediction service failed.",
        }


# ============================================================================
# MAIN PREDICTION NODE
# ============================================================================

def prediction_node(
    state: AgentState,
) -> AgentState:
    """
    Main AFL prediction node.

    Supported:
        1. Match-winner prediction
        2. Top-player prediction
        3. Multi-turn clarification
        4. Same-team validation
        5. Future forecast horizon validation
        6. Safe tool invocation

    Forecast policy:

        Latest 2 seasons
                ↓
        immediately following season

    Example:

        Data through 2025
        Training seasons = 2024 + 2025
        Forecast = 2026

    Requests for 2027+ are rejected as unreliable.
    """

    query = (
        state.get(
            "user_query",
            "",
        )
        or ""
    ).strip()

    q = query.casefold()

    # Prediction node owns prediction intent.
    state = {
        **state,
        "intent": "prediction",
    }

    # =========================================================================
    # EXISTING STATE
    # =========================================================================

    existing_tool_input = dict(
        state.get("tool_input") or {}
    )

    pending_tool = state.get(
        "pending_tool_name"
    )

    # =========================================================================
    # CURRENT DATE / YEAR
    # =========================================================================

    current_date = _explicit_date(
        query
    )

    requested_year = _explicit_year(
        query
    )

    # If query says "in 2040", convert it to season date.
    if (
        requested_year is not None
        and current_date is None
    ):
        current_date = _year_to_prediction_date(
            requested_year
        )

    # =========================================================================
    # FUTURE HORIZON VALIDATION
    # =========================================================================

    if requested_year is not None:

        error = _future_horizon_error(
            requested_year
        )

        if error:

            return _unsupported_prediction_state(
                state,
                error,
            )

    # =========================================================================
    # CONTINUE PENDING MATCH-WINNER
    # =========================================================================

    if pending_tool == MATCH_WINNER_TOOL:

        home = (
            existing_tool_input.get(
                "home_team"
            )
            or state.get("team_a")
        )

        away = (
            existing_tool_input.get(
                "away_team"
            )
            or state.get("team_b")
        )

        date = (
            current_date
            or existing_tool_input.get("date")
            or state.get("date")
        )

        if home and away:

            home = str(home).strip()
            away = str(away).strip()

            if _same_team(
                home,
                away,
            ):

                return _same_team_state(
                    state,
                    home,
                    away,
                    date,
                )

            payload = {
                "home_team": home,
                "away_team": away,
            }

            if date:
                payload["date"] = date

            return _safe_invoke(
                match_winner_prediction,
                payload,
                {
                    **state,
                    "intent": "prediction",
                    "tool_name": MATCH_WINNER_TOOL,
                    "tool_input": payload,
                    "team_a": home,
                    "team_b": away,
                    "date": date,
                },
            )

    # =========================================================================
    # CONTINUE PENDING TOP PLAYER
    # =========================================================================

    if pending_tool == TOP_PLAYER_TOOL:

        team = (
            existing_tool_input.get(
                "team"
            )
            or state.get("team_a")
        )

        date = (
            current_date
            or existing_tool_input.get("date")
            or state.get("date")
        )

        if team:

            team = str(team).strip()

            if not date:

                forecast_year = get_forecast_year()

                date = _year_to_prediction_date(
                    forecast_year
                )

            payload = {
                "team": team,
                "date": date,
                "top_n": existing_tool_input.get(
                    "top_n",
                    DEFAULT_TOP_N,
                ),
            }

            return _safe_invoke(
                top_player_prediction,
                payload,
                {
                    **state,
                    "intent": "prediction",
                    "tool_name": TOP_PLAYER_TOOL,
                    "tool_input": payload,
                    "team_a": team,
                    "team_b": None,
                    "date": date,
                },
            )

    # =========================================================================
    # RECOVER PREVIOUS TEAMS
    # =========================================================================

    team_a = state.get("team_a")
    team_b = state.get("team_b")

    # =========================================================================
    # EXTRACT TEAMS
    # =========================================================================

    teams = _extract_match_teams(
        query,
        VALID_TEAMS,
    )

    if len(teams) >= 2:

        team_a = teams[0]
        team_b = teams[1]

    elif len(teams) == 1:

        team_a = teams[0]

    elif team_a and team_b:

        teams = [
            team_a,
            team_b,
        ]

    elif team_a:

        teams = [
            team_a,
        ]

    # =========================================================================
    # STANDALONE DATE
    # =========================================================================

    if _is_date_only_query(query):

        return {
            **state,
            "intent": "prediction",
            "tool_name": PREDICTION_TOOL,
            "tool_input": None,
            "tool_result": None,
            "validation_status": "needs_clarification",
            "validation_error": (
                "Please provide an AFL prediction "
                "question with the team or teams "
                "you want me to predict."
            ),
            "clarification_needed": None,
            "pending_tool_name": None,
            "error": None,
        }

    # =========================================================================
    # UNSUPPORTED PREDICTIONS
    # =========================================================================

    unsupported_phrases = (
        "exact score",
        "score prediction",
        "final score",
        "winning margin",
        "exact margin",
        "number of goals",
        "number of points",
        "how many goals",
        "how many points",
        "goals will",
        "points will",
    )

    if any(
        phrase in q
        for phrase in unsupported_phrases
    ):

        return _unsupported_prediction_state(
            state,
            (
                "I can currently predict AFL match winners "
                "and top players, but I do not have a model "
                "for exact scores, winning margins, or the "
                "number of goals a team will score."
            ),
        )

    # =========================================================================
    # MATCH-WINNER KEYWORDS
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
    # MATCH-WINNER
    # =========================================================================

    if (
        len(teams) >= 2
        and any(
            word in q
            for word in winner_words
        )
    ):

        home = str(
            teams[0]
        ).strip()

        away = str(
            teams[1]
        ).strip()

        if _same_team(
            home,
            away,
        ):

            return _same_team_state(
                state,
                home,
                away,
                current_date,
            )

        payload = {
            "home_team": home,
            "away_team": away,
        }

        if current_date:
            payload["date"] = current_date

        return _safe_invoke(
            match_winner_prediction,
            payload,
            {
                **state,
                "intent": "prediction",
                "team_a": home,
                "team_b": away,
                "date": current_date,
                "tool_name": MATCH_WINNER_TOOL,
                "tool_input": payload,
            },
        )

    # =========================================================================
    # TOP PLAYER
    # =========================================================================

    top_words = (
        "top player",
        "best player",
        "top performer",
        "top scorer",
        "likely to be",
    )

    if any(
        word in q
        for word in top_words
    ):

        # ---------------------------------------------------------------------
        # Missing team
        # ---------------------------------------------------------------------

        if not teams:

            return _needs_clarification(
                state,
                tool_name=TOP_PLAYER_TOOL,
                tool_input={
                    "top_n": DEFAULT_TOP_N,
                },
                field="team",
                message=(
                    "Which AFL team should I "
                    "predict the top player for?"
                ),
            )

        team = str(
            teams[0]
        ).strip()

        # ---------------------------------------------------------------------
        # Date missing
        #
        # For a future forecast, use the immediately following season.
        # ---------------------------------------------------------------------

        if not current_date:

            forecast_year = get_forecast_year()

            current_date = _year_to_prediction_date(
                forecast_year
            )

        # ---------------------------------------------------------------------
        # Run prediction
        # ---------------------------------------------------------------------

        payload = {
            "team": team,
            "date": current_date,
            "top_n": DEFAULT_TOP_N,
        }

        return _safe_invoke(
            top_player_prediction,
            payload,
            {
                **state,
                "intent": "prediction",
                "team_a": team,
                "team_b": None,
                "date": current_date,
                "tool_name": TOP_PLAYER_TOOL,
                "tool_input": payload,
            },
        )

    # =========================================================================
    # FALLBACK
    # =========================================================================

    message = (
        "I can currently predict AFL match winners "
        "and top players. I do not have a model for "
        "that requested prediction type."
    )

    return {
        **state,
        "intent": "prediction",
        "tool_name": PREDICTION_TOOL,
        "tool_input": None,
        "tool_result": {
            "error": message,
        },
        "validation_status": "needs_clarification",
        "clarification_needed": None,
        "pending_tool_name": None,
        "validation_error": message,
        "error": None,
    }