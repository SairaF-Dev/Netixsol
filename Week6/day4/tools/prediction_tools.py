"""LangChain tools around the Week 6 Day 2 prediction functions."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from predict import (
    PredictionInputError,
    VALID_TEAMS,
    predict_match_winner as _predict_match_winner,
    predict_top_player as _predict_top_player,
)

from .team_resolver import resolve_team


def _json(data: Any) -> str:
    return json.dumps(data, default=str)


@tool
def match_winner_prediction(
    home_team: str,
    away_team: str,
    date: str,
    venue: str = "unknown",
) -> str:
    """Predict the winner of a future AFL match.

    Resolve team aliases before calling this tool. The date must be an explicit
    ISO date. Returns predicted winner, home-win probability, and the historical
    as-of date used by the model.
    """
    try:
        home = resolve_team(home_team, VALID_TEAMS)
        away = resolve_team(away_team, VALID_TEAMS)

        if not home:
            return _json({"error": f"Could not resolve home team '{home_team}'."})
        if not away:
            return _json({"error": f"Could not resolve away team '{away_team}'."})

        result = _predict_match_winner(home, away, date, venue)
        return _json(result)
    except (PredictionInputError, ValueError, TypeError) as exc:
        return _json({"error": str(exc)})


@tool
def top_player_prediction(
    team: str,
    date: str,
    top_n: int = 5,
) -> str:
    """Predict the top AFL players by expected fantasy points for a team.

    The date is the prediction as-of date. Returns ranked player IDs and
    predicted fantasy points.
    """
    try:
        resolved = resolve_team(team, VALID_TEAMS)
        if not resolved:
            return _json({"error": f"Could not resolve team '{team}'."})

        result = _predict_top_player(resolved, date, top_n)
        return _json({
            "team": resolved,
            "as_of_date": date,
            "predictions": result,
        })
    except (PredictionInputError, ValueError, TypeError) as exc:
        return _json({"error": str(exc)})


PREDICTION_TOOLS = [match_winner_prediction, top_player_prediction]
