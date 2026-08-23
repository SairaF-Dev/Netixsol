from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from state import AgentState


# ============================================================================
# CONSTANTS
# ============================================================================

PREDICTION_DISCLAIMER = (
    "Prediction, not a certainty."
)

PLAYER_LOOKUP_FILE = Path(
    "merged_players.csv"
)


# ============================================================================
# PLAYER LOOKUP
# ============================================================================

@lru_cache(maxsize=1)
def _load_player_lookup() -> dict[int, str]:

    if not PLAYER_LOOKUP_FILE.exists():

        print(
            "[WARNING formatter] "
            f"{PLAYER_LOOKUP_FILE} not found."
        )

        return {}

    try:

        df = pd.read_csv(
            PLAYER_LOOKUP_FILE,
            usecols=[
                "player_id",
                "player_name",
                "player_full_name",
            ],
        )

    except ValueError:

        try:

            df = pd.read_csv(
                PLAYER_LOOKUP_FILE,
                usecols=[
                    "player_id",
                    "player_name",
                ],
            )

        except Exception as exc:

            print(
                "[WARNING formatter] "
                f"Could not load player lookup: {exc}"
            )

            return {}

    except Exception as exc:

        print(
            "[WARNING formatter] "
            f"Could not load player lookup: {exc}"
        )

        return {}

    if "player_id" not in df.columns:
        return {}

    df = df.dropna(
        subset=["player_id"]
    )

    df["player_id"] = pd.to_numeric(
        df["player_id"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["player_id"]
    )

    df["player_id"] = (
        df["player_id"]
        .astype(int)
    )

    # ------------------------------------------------------------------------
    # Player name
    # ------------------------------------------------------------------------

    if "player_name" in df.columns:

        player_name = (
            df["player_name"]
            .astype("string")
            .str.strip()
        )

    else:

        player_name = pd.Series(
            pd.NA,
            index=df.index,
            dtype="string",
        )

    # ------------------------------------------------------------------------
    # Full name
    # ------------------------------------------------------------------------

    if "player_full_name" in df.columns:

        full_name = (
            df["player_full_name"]
            .astype("string")
            .str.strip()
        )

    else:

        full_name = pd.Series(
            pd.NA,
            index=df.index,
            dtype="string",
        )

    # Prefer player_name.
    df["display_name"] = (
        player_name
        .fillna(full_name)
    )

    df["display_name"] = (
        df["display_name"]
        .replace("", pd.NA)
    )

    df = df.dropna(
        subset=["display_name"]
    )

    df = df.drop_duplicates(
        subset=["player_id"],
        keep="first",
    )

    return dict(
        zip(
            df["player_id"],
            df["display_name"],
        )
    )


def _player_name(
    player_id,
) -> str:

    try:

        pid = int(player_id)

    except (
        TypeError,
        ValueError,
    ):

        return f"Player {player_id}"

    lookup = _load_player_lookup()

    return lookup.get(
        pid,
        f"Player {pid}",
    )


# ============================================================================
# RESULT PARSER
# ============================================================================

def _parse_result(result):

    if isinstance(
        result,
        str,
    ):

        try:

            return json.loads(
                result
            )

        except json.JSONDecodeError:

            return result

    return result


# ============================================================================
# FORMAT MATCH WINNER
# ============================================================================

def _format_match_winner(
    result: dict,
    state: AgentState,
) -> AgentState:

    try:

        probability = float(
            result["home_win_probability"]
        )

        winner = str(
            result["predicted_winner"]
        )

        home = str(
            result["home_team"]
        )

        away = str(
            result["away_team"]
        )

        as_of_date = result.get(
            "as_of_date",
            "unknown",
        )

        if winner == home:

            confidence = probability
            opponent = away

        else:

            confidence = (
                1.0 - probability
            )

            opponent = home

        response = (
            f"Model prediction: **{winner}** has a "
            f"{confidence:.1%} predicted probability "
            f"of winning against **{opponent}**.\n\n"
            f"Grounding: the model used historical "
            f"AFL features from data available as of "
            f"**{as_of_date}**.\n\n"
            f"**{PREDICTION_DISCLAIMER}**"
        )

        return {
            **state,
            "final_response": response,
            "prediction_metadata": {
                "type": "match_winner",
                "winner": winner,
                "probability": confidence,
                "as_of_date": as_of_date,
            },
        }

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return {
            **state,
            "final_response": (
                "The match-winner model returned "
                "an invalid result. "
                "I won't invent a prediction."
            ),
        }


# ============================================================================
# FORMAT TOP PLAYERS — CURRENT RESULT FORMAT
# ============================================================================

def _format_top_players_result(
    result: dict,
    state: AgentState,
) -> AgentState:

    players = result.get(
        "players"
    )

    if (
        not isinstance(
            players,
            list,
        )
        or not players
    ):

        return {
            **state,
            "final_response":
                "No top-player predictions were returned.",
        }

    valid_rows = []

    for row in players:

        if not isinstance(
            row,
            dict,
        ):
            continue

        try:

            player_id = int(
                row["player_id"]
            )

            player_name = (
                row.get("player_name")
                or
                _player_name(
                    player_id
                )
            )

            points = float(
                row[
                    "predicted_fantasy_points"
                ]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            continue

        valid_rows.append(
            {
                "player_id": player_id,
                "player_name": str(
                    player_name
                ).strip(),
                "points": points,
            }
        )

    if not valid_rows:

        return {
            **state,
            "final_response": (
                "The top-player model returned "
                "an invalid result. "
                "I won't invent a prediction."
            ),
        }

    # =========================================================================
    # TEAM
    # =========================================================================

    tool_input = (
        state.get(
            "tool_input"
        )
        or {}
    )

    team = (
        tool_input.get("team")
        or state.get("team_a")
        or "the selected team"
    )

    # =========================================================================
    # METADATA
    # =========================================================================

    prediction_date = result.get(
        "prediction_date"
    )

    data_through = result.get(
        "data_through"
    )

    prediction_type = result.get(
        "prediction_type"
    )

    forecast_horizon = (
        result.get(
            "forecast_horizon"
        )
        or {}
    )

    forecast_years = (
        forecast_horizon.get(
            "years"
        )
    )

    forecast_days = (
        forecast_horizon.get(
            "days"
        )
    )

    eligibility_seasons = (
        result.get(
            "eligibility_seasons"
        )
        or []
    )

    prediction_basis = result.get(
        "prediction_basis"
    )

    data_limitation = result.get(
        "data_limitation"
    )

    # =========================================================================
    # PLAYER LIST
    # =========================================================================

    lines = []

    for index, row in enumerate(
        valid_rows,
        start=1,
    ):

        lines.append(
            f"{index}. **{row['player_name']}** — "
            f"{row['points']:.1f} predicted fantasy points"
        )

    # =========================================================================
    # RESPONSE
    # =========================================================================

    response = (
        f"Top-player prediction for "
        f"**{team}**"
    )

    if prediction_date:

        response += (
            f" on **{prediction_date}**"
        )

    response += (
        ":\n\n"
        +
        "\n".join(lines)
    )

    # =========================================================================
    # FUTURE FORECAST CONTEXT
    # =========================================================================

    if prediction_type == "future_forecast":

        response += "\n\n"

        if forecast_years is not None:

            response += (
                f"This is a **future forecast** "
                f"approximately **{forecast_years:.1f} "
                f"years** ahead"
            )

            if forecast_days is not None:

                response += (
                    f" ({int(forecast_days):,} days)"
                )

            response += "."

        if data_through:

            response += (
                f"\n\nAvailable data through: "
                f"**{data_through}**."
            )

    # =========================================================================
    # PREDICTION BASIS
    # =========================================================================

    if prediction_basis:

        response += (
            "\n\n**Prediction basis:** "
            f"{prediction_basis}"
        )

    # =========================================================================
    # ELIGIBILITY
    # =========================================================================

    if eligibility_seasons:

        seasons_text = ", ".join(
            str(year)
            for year in eligibility_seasons
        )

        response += (
            f"\n\n**Eligibility seasons:** "
            f"{seasons_text}"
        )

    # =========================================================================
    # LIMITATION
    # =========================================================================

    if data_limitation:

        response += (
            "\n\n**Data limitation:** "
            f"{data_limitation}"
        )

    # =========================================================================
    # DISCLAIMER
    # =========================================================================

    response += (
        f"\n\n**{PREDICTION_DISCLAIMER}**"
    )

    return {
        **state,
        "final_response": response,
        "prediction_metadata": {
            "type": "top_player",
            "team": team,
            "prediction_date": prediction_date,
            "data_through": data_through,
            "prediction_type": prediction_type,
            "forecast_horizon": forecast_horizon,
            "eligibility_seasons": eligibility_seasons,
            "count": len(valid_rows),
            "top_player_id": valid_rows[0]["player_id"],
            "top_player_name": valid_rows[0]["player_name"],
            "top_player_predicted_points":
                valid_rows[0]["points"],
        },
    }


# ============================================================================
# LEGACY TOP PLAYER FORMAT
# ============================================================================

def _format_legacy_top_players(
    result: dict,
    state: AgentState,
) -> AgentState:

    rows = result.get(
        "predictions"
    )

    if (
        not isinstance(
            rows,
            list,
        )
        or not rows
    ):

        return {
            **state,
            "final_response":
                "No top-player predictions were returned.",
        }

    valid_rows = []

    for row in rows:

        if not isinstance(
            row,
            dict,
        ):
            continue

        try:

            player_id = int(
                row["player_id"]
            )

            points = float(
                row[
                    "predicted_fantasy_points"
                ]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            continue

        valid_rows.append(
            (
                player_id,
                points,
            )
        )

    if not valid_rows:

        return {
            **state,
            "final_response": (
                "The top-player model returned "
                "an invalid result."
            ),
        }

    tool_input = (
        state.get(
            "tool_input"
        )
        or {}
    )

    team = (
        result.get("team")
        or state.get("team_a")
        or tool_input.get(
            "team",
            "the selected team",
        )
    )

    lines = []

    for index, (
        player_id,
        points,
    ) in enumerate(
        valid_rows,
        start=1,
    ):

        player_name = _player_name(
            player_id
        )

        lines.append(
            f"{index}. **{player_name}** — "
            f"{points:.1f} predicted fantasy points"
        )

    response = (
        f"Top-player prediction for "
        f"**{team}**:\n\n"
        +
        "\n".join(lines)
        +
        f"\n\n**{PREDICTION_DISCLAIMER}**"
    )

    return {
        **state,
        "final_response": response,
        "prediction_metadata": {
            "type": "top_player",
            "team": team,
            "count": len(valid_rows),
            "top_player_id":
                valid_rows[0][0],
            "top_player_name":
                _player_name(
                    valid_rows[0][0]
                ),
            "top_player_predicted_points":
                valid_rows[0][1],
        },
    }


# ============================================================================
# PREDICTION ERROR / UNSUPPORTED FORMAT
# ============================================================================

def _format_prediction_error(
    result,
    state: AgentState,
) -> AgentState:

    if isinstance(
        result,
        dict,
    ):

        message = (
            result.get("message")
            or result.get("error")
        )

        if message:

            return {
                **state,
                "final_response": str(
                    message
                ),
            }

    return {
        **state,
        "final_response": (
            "I couldn't produce a prediction "
            "from the available models. "
            "I won't guess."
        ),
    }


# ============================================================================
# FORMATTER NODE
# ============================================================================

def formatter_node(
    state: AgentState,
) -> AgentState:

    intent = state.get(
        "intent"
    )

    result = _parse_result(
        state.get(
            "tool_result"
        )
    )

    # =========================================================================
    # OFF TOPIC
    # =========================================================================

    if intent == "off_topic":

        return {
            **state,
            "final_response":
                state.get(
                    "final_response"
                )
                or
                (
                    "I can only help with AFL-related "
                    "questions. You can ask me about "
                    "an AFL team, player, match, statistic, "
                    "history, or rule."
                ),
        }

    # =========================================================================
    # FACTUAL
    # =========================================================================

    if intent == "factual":

        return {
            **state,
            "final_response":
                state.get(
                    "final_response"
                )
                or
                (
                    "I can answer general AFL rules, "
                    "history, and competition-structure "
                    "questions."
                ),
        }

    # =========================================================================
    # RETRIEVAL
    # =========================================================================

    if intent == "retrieval":

        if result is None:

            return {
                **state,
                "final_response":
                    "No matching AFL data was found.",
            }

        if (
            state.get(
                "tool_name"
            )
            == "player_statistics"
            and
            isinstance(
                result,
                dict,
            )
            and
            not result.get("error")
        ):

            period = (
                f" in {result['year']}"
                if result.get("year")
                else ""
            )

            totals = (
                result.get(
                    "totals"
                )
                or {}
            )

            total_text = ", ".join(
                f"{value} "
                f"{key.replace('_', ' ')}"
                for key, value
                in totals.items()
            )

            return {
                **state,
                "final_response": (
                    f"{result.get('player', 'That player')}"
                    f"{period} played "
                    f"{result.get('match_count', 0)} "
                    f"recorded matches. "
                    f"Totals across those matches: "
                    f"{total_text or 'no supported totals available'}."
                ),
            }

        return {
            **state,
            "final_response":
                (
                    "According to the available "
                    "AFL dataset:\n"
                    +
                    json.dumps(
                        result,
                        indent=2,
                        default=str,
                    )
                ),
        }

    # =========================================================================
    # PREDICTION
    # =========================================================================

    if intent == "prediction":

        # ---------------------------------------------------------------------
        # Existing final response from validation node
        # ---------------------------------------------------------------------

        if (
            state.get("final_response")
            and
            isinstance(result, dict)
            and
            result.get("unsupported") is True
        ):

            return {
                **state,
                "final_response":
                    state["final_response"],
            }

        # ---------------------------------------------------------------------
        # No result
        # ---------------------------------------------------------------------

        if result is None:

            return {
                **state,
                "final_response":
                    state.get(
                        "validation_error"
                    )
                    or
                    (
                        "I couldn't produce a prediction "
                        "from the available models. "
                        "I won't guess."
                    ),
            }

        # ---------------------------------------------------------------------
        # Unsupported prediction
        # ---------------------------------------------------------------------

        if (
            isinstance(
                result,
                dict,
            )
            and
            result.get(
                "unsupported"
            ) is True
        ):

            return _format_prediction_error(
                result,
                state,
            )

        # ---------------------------------------------------------------------
        # Explicit error
        # ---------------------------------------------------------------------

        if (
            isinstance(
                result,
                dict,
            )
            and
            result.get("error")
            and
            "predicted_winner"
            not in result
        ):

            return _format_prediction_error(
                result,
                state,
            )

        # ---------------------------------------------------------------------
        # Match winner
        # ---------------------------------------------------------------------

        if (
            isinstance(
                result,
                dict,
            )
            and
            "predicted_winner"
            in result
        ):

            return _format_match_winner(
                result,
                state,
            )

        # ---------------------------------------------------------------------
        # Current top-player result
        # ---------------------------------------------------------------------

        if (
            isinstance(
                result,
                dict,
            )
            and
            "players"
            in result
        ):

            return _format_top_players_result(
                result,
                state,
            )

        # ---------------------------------------------------------------------
        # Legacy list
        # ---------------------------------------------------------------------

        if isinstance(
            result,
            list,
        ):

            return _format_top_players_result(
                {
                    "players": result,
                },
                state,
            )

        # ---------------------------------------------------------------------
        # Legacy dictionary
        # ---------------------------------------------------------------------

        if (
            isinstance(
                result,
                dict,
            )
            and
            "predictions"
            in result
        ):

            return _format_legacy_top_players(
                result,
                state,
            )

        # ---------------------------------------------------------------------
        # Unknown result
        # ---------------------------------------------------------------------

        return {
            **state,
            "final_response": (
                "The prediction model returned an "
                "unsupported result format. "
                "I won't invent a prediction."
            ),
        }

    # =========================================================================
    # UNKNOWN INTENT
    # =========================================================================

    return {
        **state,
        "final_response":
            "I couldn't determine how to answer that safely.",
    }