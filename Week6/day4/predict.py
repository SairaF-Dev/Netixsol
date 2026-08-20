"""
predict.py -- callable prediction functions for the AFL
match-winner and top-player models.

These functions wrap the models trained in Week 6 Day 2.

Designed to be imported directly as LangChain/LangGraph tools.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

import sklearn.compose._column_transformer as _ct


# ============================================================================
# scikit-learn compatibility shim
# ============================================================================

if not hasattr(_ct, "_RemainderColsList"):

    class _RemainderColsList:
        pass

    _ct._RemainderColsList = _RemainderColsList


# ============================================================================
# Paths
# ============================================================================

_ARTIFACT_DIR = Path(__file__).resolve().parent


# ============================================================================
# Load trained artifacts
# ============================================================================

_match_model = joblib.load(
    _ARTIFACT_DIR / "match_winner_model.joblib"
)

_top_player_model = joblib.load(
    _ARTIFACT_DIR / "top_player_model.joblib"
)

_team_snapshots = pd.read_parquet(
    _ARTIFACT_DIR / "team_snapshots.parquet"
)

_player_snapshots = pd.read_parquet(
    _ARTIFACT_DIR / "player_snapshots.parquet"
)


# ============================================================================
# Basic dataset information
# ============================================================================

VALID_TEAMS = sorted(
    _team_snapshots["team_name"]
    .dropna()
    .unique()
)

DATA_MIN_DATE = pd.Timestamp(
    _team_snapshots["match_date"].min()
)

DATA_MAX_DATE = pd.Timestamp(
    _team_snapshots["match_date"].max()
)


# ============================================================================
# IMPORTANT:
# These are the feature names used by the TRAINED MATCH-WINNER MODEL.
#
# They must match the names used during Day 2 training.
# ============================================================================

_MATCH_FEATURES = [
    "form_win_rate_last5_home",
    "avg_score_last5_home",
    "win_streak_home",
    "rest_days_home",
    "ladder_rank_prior_home",
    "h2h_win_rate_prior_home",

    "form_win_rate_last5_away",
    "avg_score_last5_away",
    "win_streak_away",
    "rest_days_away",
    "ladder_rank_prior_away",
    "h2h_win_rate_prior_away",

    "venue",
]


# ============================================================================
# Top-player model features
# ============================================================================

_PLAYER_FEATURES = [
    "last5_avg_disposals",
    "last5_avg_goals",
    "last5_avg_fantasy_points",
    "games_played_prior",
]


# ============================================================================
# Custom validation error
# ============================================================================

class PredictionInputError(ValueError):
    """Raised for invalid prediction inputs."""


# ============================================================================
# Validation helpers
# ============================================================================

def _validate_team(team_name: str) -> None:
    """
    Validate that the supplied team exists in the snapshot dataset.
    """

    if team_name not in VALID_TEAMS:

        raise PredictionInputError(
            f"Unknown team '{team_name}'. "
            f"Valid teams: {', '.join(VALID_TEAMS)}"
        )


def _validate_date(date: str | pd.Timestamp) -> pd.Timestamp:
    """
    Validate and normalize the prediction date.
    """

    try:
        date = pd.Timestamp(date)

    except Exception as exc:

        raise PredictionInputError(
            f"Invalid date '{date}'. "
            "Use YYYY-MM-DD format."
        ) from exc

    if pd.isna(date):

        raise PredictionInputError(
            "Prediction date cannot be empty."
        )

    # Historical model data + one year forward.
    if (
        date < DATA_MIN_DATE
        or date > DATA_MAX_DATE + pd.Timedelta(days=365)
    ):

        raise PredictionInputError(
            f"Date {date.date()} is well outside the data range "
            f"({DATA_MIN_DATE.date()} to "
            f"{DATA_MAX_DATE.date()}); "
            "prediction would be unreliable."
        )

    return date


# ============================================================================
# Team snapshot helpers
# ============================================================================

def _latest_team_snapshot(
    team_name: str,
    as_of_date: pd.Timestamp,
) -> pd.Series:
    """
    Return the most recent historical team snapshot before
    the prediction date.
    """

    hist = _team_snapshots[
        (
            _team_snapshots["team_name"]
            == team_name
        )
        &
        (
            _team_snapshots["match_date"]
            < as_of_date
        )
    ]

    if hist.empty:

        raise PredictionInputError(
            f"No historical data for "
            f"'{team_name}' before "
            f"{as_of_date.date()}."
        )

    return (
        hist
        .sort_values("match_date")
        .iloc[-1]
    )


def _h2h_snapshot(
    team_name: str,
    opponent_name: str,
    as_of_date: pd.Timestamp,
):
    """
    Get the most recent historical H2H win rate for
    team_name against opponent_name.

    Returns None if no historical H2H exists.
    """

    hist = _team_snapshots[
        (
            _team_snapshots["team_name"]
            == team_name
        )
        &
        (
            _team_snapshots["opponent"]
            == opponent_name
        )
        &
        (
            _team_snapshots["match_date"]
            < as_of_date
        )
    ]

    if hist.empty:
        return None

    return (
        hist
        .sort_values("match_date")
        .iloc[-1]["h2h_win_rate"]
    )


def _safe_numeric(
    value,
    default: float = 0.0,
) -> float:
    """
    Convert a snapshot value to a numeric value.

    NaN/None values are replaced with a safe default.
    """

    try:

        value = float(value)

        if pd.isna(value):
            return default

        return value

    except (TypeError, ValueError):

        return default


# ============================================================================
# MATCH-WINNER PREDICTION
# ============================================================================

def predict_match_winner(
    team_a: str,
    team_b: str,
    date: str,
    venue: str = "unknown",
) -> dict:
    """
    Predict the winner of an AFL match.

    Parameters
    ----------
    team_a:
        Home team.

    team_b:
        Away team.

    date:
        Prediction/match date in YYYY-MM-DD format.

    venue:
        Venue string. Defaults to "unknown".

    Returns
    -------
    dict
        Prediction result containing winner and probability.
    """

    # ------------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------------

    _validate_team(team_a)
    _validate_team(team_b)

    if team_a == team_b:

        raise PredictionInputError(
            "Home and away teams must be different."
        )

    as_of = _validate_date(date)

    # ------------------------------------------------------------------------
    # Get historical snapshots
    # ------------------------------------------------------------------------

    home_snap = _latest_team_snapshot(
        team_a,
        as_of,
    )

    away_snap = _latest_team_snapshot(
        team_b,
        as_of,
    )

    # ------------------------------------------------------------------------
    # Get H2H information
    # ------------------------------------------------------------------------

    home_h2h = _h2h_snapshot(
        team_a,
        team_b,
        as_of,
    )

    away_h2h = _h2h_snapshot(
        team_b,
        team_a,
        as_of,
    )

    # ------------------------------------------------------------------------
    # Build EXACT feature names expected by Day 2 model
    # ------------------------------------------------------------------------

    row = pd.DataFrame(
        [
            {

                # ============================================================
                # HOME TEAM
                # ============================================================

                "form_win_rate_last5_home":
                    _safe_numeric(
                        home_snap["last5_win_rate"]
                    ),

                "avg_score_last5_home":
                    _safe_numeric(
                        home_snap["last5_avg_score"]
                    ),

                "win_streak_home":
                    _safe_numeric(
                        home_snap.get(
                            "win_streak",
                            0
                        )
                    ),

                "rest_days_home":
                    max(
                        0,
                        int(
                            (
                                as_of
                                - pd.Timestamp(
                                    home_snap["match_date"]
                                )
                            ).days
                        ),
                    ),

                "ladder_rank_prior_home":
                    _safe_numeric(
                        home_snap["ladder_rank"]
                    ),

                "h2h_win_rate_prior_home":
                    _safe_numeric(
                        home_h2h,
                        default=0.5,
                    ),

                # ============================================================
                # AWAY TEAM
                # ============================================================

                "form_win_rate_last5_away":
                    _safe_numeric(
                        away_snap["last5_win_rate"]
                    ),

                "avg_score_last5_away":
                    _safe_numeric(
                        away_snap["last5_avg_score"]
                    ),

                "win_streak_away":
                    _safe_numeric(
                        away_snap.get(
                            "win_streak",
                            0
                        )
                    ),

                "rest_days_away":
                    max(
                        0,
                        int(
                            (
                                as_of
                                - pd.Timestamp(
                                    away_snap["match_date"]
                                )
                            ).days
                        ),
                    ),

                "ladder_rank_prior_away":
                    _safe_numeric(
                        away_snap["ladder_rank"]
                    ),

                "h2h_win_rate_prior_away":
                    _safe_numeric(
                        away_h2h,
                        default=0.5,
                    ),

                # ============================================================
                # VENUE
                # ============================================================

                "venue":
                    venue or "unknown",
            }
        ]
    )

    # ------------------------------------------------------------------------
    # Force exact feature order
    # ------------------------------------------------------------------------

    row = row[_MATCH_FEATURES]

    # ------------------------------------------------------------------------
    # Model prediction
    # ------------------------------------------------------------------------

    try:

        proba = float(
            _match_model
            .predict_proba(row)[0, 1]
        )

    except Exception as exc:

        raise PredictionInputError(
            f"Match winner model prediction failed: {exc}"
        ) from exc

    # ------------------------------------------------------------------------
    # Determine winner
    # ------------------------------------------------------------------------

    predicted_winner = (
        team_a
        if proba >= 0.5
        else team_b
    )

    # ------------------------------------------------------------------------
    # Return structured result
    # ------------------------------------------------------------------------

    return {

        "home_team":
            team_a,

        "away_team":
            team_b,

        "predicted_winner":
            predicted_winner,

        "home_win_probability":
            round(proba, 3),

        "as_of_date":
            str(as_of.date()),
    }


# ============================================================================
# TOP PLAYER PREDICTION
# ============================================================================

def predict_top_player(
    team: str,
    date: str,
    top_n: int = 5,
) -> list:
    """
    Predict the top players for an AFL team based on expected
    fantasy points.
    """

    _validate_team(team)

    as_of = _validate_date(date)

    if top_n < 1:

        raise PredictionInputError(
            "top_n must be at least 1."
        )

    # ------------------------------------------------------------------------
    # Get player history before prediction date
    # ------------------------------------------------------------------------

    roster = _player_snapshots[
        (
            _player_snapshots["team"]
            == team
        )
        &
        (
            _player_snapshots["match_date"]
            < as_of
        )
    ]

    if roster.empty:

        raise PredictionInputError(
            f"No player history for "
            f"'{team}' before "
            f"{as_of.date()}."
        )

    # ------------------------------------------------------------------------
    # Latest snapshot per player
    # ------------------------------------------------------------------------

    latest_per_player = (
        roster
        .sort_values("match_date")
        .groupby("player_id")
        .tail(1)
        .dropna(subset=_PLAYER_FEATURES)
    )

    if latest_per_player.empty:

        raise PredictionInputError(
            f"No players with complete recent-form "
            f"data for '{team}' before "
            f"{as_of.date()}."
        )

    # ------------------------------------------------------------------------
    # Predict fantasy points
    # ------------------------------------------------------------------------

    try:

        preds = _top_player_model.predict(
            latest_per_player[_PLAYER_FEATURES]
        )

    except Exception as exc:

        raise PredictionInputError(
            f"Top-player model prediction failed: {exc}"
        ) from exc

    # ------------------------------------------------------------------------
    # Attach predictions
    # ------------------------------------------------------------------------

    latest_per_player = (
        latest_per_player
        .assign(
            predicted_fantasy_points=preds
        )
    )

    top = (
        latest_per_player
        .nlargest(
            top_n,
            "predicted_fantasy_points",
        )
    )

    # ------------------------------------------------------------------------
    # Return structured result
    # ------------------------------------------------------------------------

    return [
        {
            "player_id":
                int(row.player_id),

            "predicted_fantasy_points":
                round(
                    float(
                        row.predicted_fantasy_points
                    ),
                    1,
                ),
        }
        for row in top.itertuples()
    ]