from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from state import AgentState


# ============================================================================
# CONSTANTS
# ============================================================================

PREDICTION_DISCLAIMER = "Prediction, not a certainty."

PLAYER_LOOKUP_FILE = Path("merged_players.csv")


# ============================================================================
# PLAYER LOOKUP
# ============================================================================

@lru_cache(maxsize=1)
def _load_player_lookup() -> dict[int, str]:
    """
    Load player_id -> player_name mapping.

    IMPORTANT:
    This file is used ONLY for display/lookup.
    It is NOT used by the prediction model.
    """

    if not PLAYER_LOOKUP_FILE.exists():
        print(
            f"[WARNING formatter] "
            f"{PLAYER_LOOKUP_FILE} not found."
        )
        return {}

    try:

        # Read only the columns needed for lookup.
        df = pd.read_csv(
            PLAYER_LOOKUP_FILE,
            usecols=[
                "player_id",
                "player_name",
                "player_full_name",
            ],
        )

    except ValueError:

        # Fallback in case player_full_name is unavailable.
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

    # ------------------------------------------------------------------------
    # Validate player_id
    # ------------------------------------------------------------------------

    if "player_id" not in df.columns:
        return {}

    df = df.dropna(
        subset=["player_id"]
    )

    # Convert IDs safely.
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
    # Build display name
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

    # Remove empty strings.
    df["display_name"] = (
        df["display_name"]
        .replace("", pd.NA)
    )

    df = df.dropna(
        subset=["display_name"]
    )

    # ------------------------------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------------------------------
    #
    # merged_players.csv contains many repeated rows for the same player.
    #
    # Example:
    #
    # 43668 -> Nick Daicos
    # 43668 -> Nick Daicos
    # 43668 -> Nick Daicos
    #
    # We only need one mapping.
    # ------------------------------------------------------------------------

    df = df.drop_duplicates(
        subset=["player_id"],
        keep="first",
    )

    # ------------------------------------------------------------------------
    # Create dictionary
    # ------------------------------------------------------------------------

    lookup = dict(
        zip(
            df["player_id"],
            df["display_name"],
        )
    )

    print(
        "[DEBUG formatter] "
        f"Loaded {len(lookup)} player names."
    )

    return lookup


def _player_name(player_id) -> str:
    """
    Convert a player ID to a readable player name.
    """

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

    """
    Convert JSON strings to Python objects.

    Dict/list results are returned unchanged.
    """

    if isinstance(result, str):

        try:

            return json.loads(result)

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

        # home_win_probability represents probability
        # of HOME team winning.
        #
        # Therefore if away team is predicted winner,
        # its probability is 1 - home probability.

        if winner == home:

            confidence = probability
            opponent = away

        else:

            confidence = 1.0 - probability
            opponent = home

        response = (

            f"Model prediction: **{winner}** has a "
            f"{confidence:.1%} predicted probability "
            f"of winning against **{opponent}**.\n\n"

            f"Grounding: the model used recent-form, "
            f"scoring, rest, ladder-position and "
            f"head-to-head inputs from historical "
            f"snapshots (as of {as_of_date}).\n\n"

            f"**{PREDICTION_DISCLAIMER}**"
        )

        return {
            **state,

            "final_response":
                response,

            "prediction_metadata": {

                "type":
                    "match_winner",

                "winner":
                    winner,

                "probability":
                    confidence,

                "as_of_date":
                    as_of_date,
            },
        }

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return {
            **state,

            "final_response":
                (
                    "The match-winner model returned "
                    "an invalid result. "
                    "I won't invent a prediction."
                ),
        }


# ============================================================================
# FORMAT TOP PLAYER
# ============================================================================

def _format_top_players(
    result: list,
    state: AgentState,
) -> AgentState:

    if not result:

        return {
            **state,

            "final_response":
                "No top-player predictions were returned.",
        }

    # ------------------------------------------------------------------------
    # Validate rows
    # ------------------------------------------------------------------------

    valid_rows = []

    for row in result:

        if not isinstance(row, dict):
            continue

        if (
            "player_id" not in row
            or
            "predicted_fantasy_points" not in row
        ):
            continue

        try:

            player_id = int(
                row["player_id"]
            )

            fantasy_points = float(
                row[
                    "predicted_fantasy_points"
                ]
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        valid_rows.append(
            {
                "player_id":
                    player_id,

                "predicted_fantasy_points":
                    fantasy_points,
            }
        )

    if not valid_rows:

        return {
            **state,

            "final_response":
                (
                    "The top-player model returned "
                    "an invalid result. "
                    "I won't invent a prediction."
                ),
        }

    # ------------------------------------------------------------------------
    # Get team
    # ------------------------------------------------------------------------

    tool_input = (
        state.get("tool_input")
        or {}
    )

    team = (
        state.get("team_a")
        or
        tool_input.get(
            "team",
            "the selected team",
        )
    )

    # ------------------------------------------------------------------------
# Resolve player names
# ------------------------------------------------------------------------

    lines = []

    for index, row in enumerate(
        valid_rows,
        start=1,
    ):

        player_id = row["player_id"]

        player_name = _player_name(
            player_id
        )

        # Clean accidental whitespace
        player_name = player_name.strip()

        fantasy_points = (
            row["predicted_fantasy_points"]
        )

        lines.append(
            f"{index}. **{player_name}** — "
            f"{fantasy_points:.1f} "
            f"predicted fantasy points"
        )
    # ------------------------------------------------------------------------
    # Final response
    # ------------------------------------------------------------------------

    response = (

        f"Top-player prediction for "
        f"**{team}**:\n\n"

        +
        "\n".join(lines)

        +

        "\n\n"
        f"**{PREDICTION_DISCLAIMER}**"
    )

    return {
        **state,

        "final_response":
            response,

        "prediction_metadata": {

            "type":
                "top_player",

            "team":
                team,

            "count":
                len(valid_rows),

            "top_player_id":
                valid_rows[0]["player_id"],

            "top_player_name":
                _player_name(
                    valid_rows[0]["player_id"]
                ),

            "top_player_predicted_points":
                valid_rows[0][
                    "predicted_fantasy_points"
                ],
        },
    }


# ============================================================================
# FORMAT LEGACY TOP PLAYER RESULT
# ============================================================================

def _format_legacy_top_players(
    result: dict,
    state: AgentState,
) -> AgentState:

    rows = result.get(
        "predictions"
    )

    if not isinstance(
        rows,
        list,
    ) or not rows:

        return {
            **state,

            "final_response":
                "No top-player predictions were returned.",
        }

    valid_rows = []

    for row in rows:

        if not isinstance(row, dict):
            continue

        if (
            "player_id" not in row
            or
            "predicted_fantasy_points" not in row
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

            "final_response":
                (
                    "The top-player model returned "
                    "an invalid result."
                ),
        }

    team = (
        result.get("team")
        or
        state.get("team_a")
        or
        state.get("tool_input", {}).get(
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
            f"{index}. **{player_name}** "
            f"(ID: {player_id}) — "
            f"{points:.1f} predicted fantasy points"
        )

    return {
        **state,

        "final_response":
            (
                f"Top-player prediction for "
                f"**{team}**:\n\n"
                +
                "\n".join(lines)
                +
                "\n\n"
                f"**{PREDICTION_DISCLAIMER}**"
            ),

        "prediction_metadata": {

            "type":
                "top_player",

            "team":
                team,

            "count":
                len(valid_rows),

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
# FORMATTER NODE
# ============================================================================

def formatter_node(
    state: AgentState,
) -> AgentState:

    print("🔥 FORMATTER CALLED")

    intent = state.get(
        "intent"
    )

    result = _parse_result(
        state.get("tool_result")
    )

    print(
        "🔥 intent =",
        intent,
    )

    print(
        "🔥 result type =",
        type(result),
    )

    print(
        "🔥 result =",
        result,
    )

    # ========================================================================
    # OFF TOPIC
    # ========================================================================

    if intent == "off_topic":

        return {
            **state,

            "final_response":
                state.get("final_response")
                or
                (
                    "I can only help with AFL-related questions. "
                    "You can ask me about an AFL team, player, "
                    "match, statistic, history, or rule."
                ),
        }

    # ========================================================================
    # FACTUAL
    # ========================================================================

    if intent == "factual":

        return {
            **state,

            "final_response":
                state.get("final_response")
                or
                (
                    "I can answer general AFL rules, history, "
                    "and competition-structure questions."
                ),
        }

    # ========================================================================
    # RETRIEVAL
    # ========================================================================

    if intent == "retrieval":

        if result is None:

            return {
                **state,

                "final_response":
                    "No matching AFL data was found.",
            }

        return {
            **state,

            "final_response":
                (
                    "According to the available AFL dataset:\n"
                    +
                    json.dumps(
                        result,
                        indent=2,
                        default=str,
                    )
                ),
        }

    # ========================================================================
    # PREDICTION
    # ========================================================================

    if intent == "prediction":

        # --------------------------------------------------------------------
        # No result
        # --------------------------------------------------------------------

        if result is None:

            return {
                **state,

                "final_response":
                    (
                        "I couldn't produce a prediction "
                        "from the available models. "
                        "I won't guess."
                    ),
            }

        # --------------------------------------------------------------------
        # Match winner
        # --------------------------------------------------------------------

        if (
            isinstance(result, dict)
            and
            "predicted_winner" in result
        ):

            return _format_match_winner(
                result,
                state,
            )

        # --------------------------------------------------------------------
        # Top-player list
        # --------------------------------------------------------------------

        if isinstance(
            result,
            list,
        ):

            return _format_top_players(
                result,
                state,
            )

        # --------------------------------------------------------------------
        # Legacy top-player dictionary
        # --------------------------------------------------------------------

        if (
            isinstance(result, dict)
            and
            "predictions" in result
        ):

            return _format_legacy_top_players(
                result,
                state,
            )

        # --------------------------------------------------------------------
        # Unknown format
        # --------------------------------------------------------------------

        return {
            **state,

            "final_response":
                (
                    "The prediction model returned "
                    "an unsupported result format. "
                    "I won't invent a prediction."
                ),
        }

    # ========================================================================
    # UNKNOWN INTENT
    # ========================================================================

    return {
        **state,

        "final_response":
            "I couldn't determine how to answer that safely.",
    }