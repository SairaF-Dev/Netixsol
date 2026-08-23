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
# Player ID -> Player Name lookup
# ============================================================================
_player_lookup = pd.read_csv(
    _ARTIFACT_DIR / "merged_players.csv"
)

_PLAYER_NAME_MAP = (
    _player_lookup[
        ["player_id", "player_name", "player_full_name"]
    ]
    .dropna(subset=["player_id"])
    .drop_duplicates("player_id")
    .set_index("player_id")
    .to_dict("index")
)

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


from datetime import date as dt_date


def _validate_date(
    date: str | pd.Timestamp | None
) -> pd.Timestamp:
    """
    Validate and normalize prediction date.

    If no date is supplied, today's date is used.

    Future dates are allowed because the model uses only
    historical snapshots available before the prediction date.

    Example:
        Dataset cutoff = 2025
        Prediction date = 2027
        Features = latest available historical data before 2027
                 = 2025 data in the current dataset.
    """

    # ------------------------------------------------------------------
    # No date supplied -> use today's actual date.
    # ------------------------------------------------------------------

    if date is None or str(date).strip() == "":
        parsed_date = pd.Timestamp(dt_date.today())

    else:
        try:
            parsed_date = pd.Timestamp(date)

        except Exception as exc:
            raise PredictionInputError(
                f"Invalid date '{date}'. "
                "Use YYYY-MM-DD format."
            ) from exc

        if pd.isna(parsed_date):
            raise PredictionInputError(
                "Prediction date cannot be empty."
            )

    # ------------------------------------------------------------------
    # Do not allow dates before the historical dataset begins.
    # ------------------------------------------------------------------

    if parsed_date < DATA_MIN_DATE:
        raise PredictionInputError(
            f"Date {parsed_date.date()} is before the "
            f"available historical data range "
            f"({DATA_MIN_DATE.date()} to "
            f"{DATA_MAX_DATE.date()})."
        )

    return parsed_date

def _data_recency_warning(
    prediction_date: pd.Timestamp,
) -> str | None:
    """
    Return a warning when prediction date is newer than
    the latest available historical data.
    """

    if prediction_date <= DATA_MAX_DATE:
        return None

    days_stale = (
        prediction_date - DATA_MAX_DATE
    ).days

    return (
        f"The prediction date is {days_stale} days after "
        f"the latest available historical data "
        f"({DATA_MAX_DATE.date()}). "
        "The model does not include newer match results "
        "or current-season form."
    )

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
    home_team: str,
    away_team: str,
    date: str | None = None,
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


    _validate_team(home_team)
    _validate_team(away_team)

    if home_team == away_team:

        raise PredictionInputError(
            "Home and away teams must be different."
        )

    as_of = _validate_date(date)

    # ------------------------------------------------------------------------
    # Get historical snapshots
    # ------------------------------------------------------------------------

 


    home_snap = _latest_team_snapshot(
    home_team,
    as_of,
)

    away_snap = _latest_team_snapshot(
    away_team,
    as_of,
)

    # ------------------------------------------------------------------------
    # Get H2H information
    # ------------------------------------------------------------------------

 

    home_h2h = _h2h_snapshot(
    home_team,
    away_team,
    as_of,
)

    away_h2h = _h2h_snapshot(
    away_team,
    home_team,
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
    home_team
    if proba >= 0.5
    else away_team
)

    # ------------------------------------------------------------------------
    # Return structured result
    # ------------------------------------------------------------------------

    return {
    "home_team": home_team,
    "away_team": away_team,
    "predicted_winner": predicted_winner,
    "home_win_probability": round(proba, 3),

    "prediction_date": str(as_of.date()),

    "data_cutoff": str(DATA_MAX_DATE.date()),

    "data_recency_warning": _data_recency_warning(as_of),

    "disclaimer": (
        "Predicted probability, not a certainty. "
        "This prediction is based on historical AFL data "
        f"available through {DATA_MAX_DATE.date()}."
    ),
}

# ============================================================================
# TOP PLAYER PREDICTION
# ============================================================================

def predict_top_player(
    team: str,
    date: str,
    top_n: int = 5,
) -> dict:
    """
    Predict the top AFL players for a team based on expected fantasy points.

    Eligibility:
        A player must have appeared for the requested team during either
        of the latest 2 seasons available in the dataset.

    Player form:
        Uses the player's latest available snapshot before the prediction
        date.

    Forecast horizon:
        Shows how far the requested prediction date is from the latest
        available dataset date.

    Important:
        No season/year is hard-coded. The latest 2 seasons are detected
        dynamically from the available dataset.
    """

    # ----------------------------------------------------------------------
    # Validate inputs
    # ----------------------------------------------------------------------

    _validate_team(team)

    as_of = _validate_date(date)

    if top_n < 1:
        raise PredictionInputError(
            "top_n must be at least 1."
        )

    # ----------------------------------------------------------------------
    # Validate dataset
    # ----------------------------------------------------------------------

    if _player_snapshots.empty:
        raise PredictionInputError(
            "Player snapshot dataset is empty."
        )

    valid_dates = (
        _player_snapshots["match_date"]
        .dropna()
    )

    if valid_dates.empty:
        raise PredictionInputError(
            "Player snapshot dataset contains no valid dates."
        )

    # ----------------------------------------------------------------------
    # Latest available dataset date
    # ----------------------------------------------------------------------

    data_through = valid_dates.max()

    # ----------------------------------------------------------------------
    # Dynamically detect latest 2 available seasons
    # ----------------------------------------------------------------------

    available_seasons = sorted(
        valid_dates
        .dt.year
        .astype(int)
        .unique()
    )

    if len(available_seasons) < 2:
        raise PredictionInputError(
            "At least 2 seasons are required for player eligibility."
        )

    latest_two_seasons = available_seasons[-2:]

    # ----------------------------------------------------------------------
    # Get requested team's player history before prediction date
    # ----------------------------------------------------------------------

    roster = _player_snapshots[
        (
            _player_snapshots["team"] == team
        )
        &
        (
            _player_snapshots["match_date"] < as_of
        )
    ].copy()

    if roster.empty:
        raise PredictionInputError(
            f"No player history for '{team}' before "
            f"{as_of.date()}."
        )

    # ----------------------------------------------------------------------
    # Dynamic player eligibility
    #
    # Player must have appeared for this team in either of the
    # latest 2 seasons available in the dataset.
    # ----------------------------------------------------------------------

    eligible_players = (
        _player_snapshots[
            (
                _player_snapshots["team"] == team
            )
            &
            (
                _player_snapshots["match_date"]
                .dt.year
                .isin(latest_two_seasons)
            )
        ]["player_id"]
        .dropna()
        .unique()
    )

    if len(eligible_players) == 0:
        raise PredictionInputError(
            f"No eligible players found for '{team}' "
            f"in the latest 2 available seasons."
        )

    # Keep only eligible players
    roster = roster[
        roster["player_id"].isin(eligible_players)
    ].copy()

    if roster.empty:
        raise PredictionInputError(
            f"No eligible player history found for '{team}'."
        )

    # ----------------------------------------------------------------------
    # Latest form snapshot per player
    # ----------------------------------------------------------------------

    latest_per_player = (
        roster
        .sort_values("match_date")
        .groupby("player_id")
        .tail(1)
        .dropna(subset=_PLAYER_FEATURES)
        .copy()
    )

    if latest_per_player.empty:
        raise PredictionInputError(
            f"No eligible players with complete recent-form "
            f"data for '{team}'."
        )

    # ----------------------------------------------------------------------
    # Predict fantasy points
    # ----------------------------------------------------------------------

    try:

        predictions = _top_player_model.predict(
            latest_per_player[_PLAYER_FEATURES]
        )

    except Exception as exc:

        raise PredictionInputError(
            f"Top-player model prediction failed: {exc}"
        ) from exc

    # ----------------------------------------------------------------------
    # Attach predictions
    # ----------------------------------------------------------------------

    latest_per_player[
        "predicted_fantasy_points"
    ] = predictions

    # ----------------------------------------------------------------------
    # Select Top N
    # ----------------------------------------------------------------------

    top = (
        latest_per_player
        .nlargest(
            top_n,
            "predicted_fantasy_points",
        )
    )

    # ----------------------------------------------------------------------
    # Calculate forecast horizon
    #
    # Example:
    # Dataset ends: 2025-09-27
    # Prediction:   2026-09-28
    #
    # Approximately 1 year into the future.
    # ----------------------------------------------------------------------

    forecast_days = (
        as_of - data_through
    ).days

    forecast_years = (
        forecast_days / 365.25
    )

    # ----------------------------------------------------------------------
    # Determine prediction type
    # ----------------------------------------------------------------------

    if forecast_days > 0:

        prediction_type = "future_forecast"

    elif forecast_days == 0:

        prediction_type = "same_date_as_latest_data"

    else:

        prediction_type = "historical_prediction"

    # ----------------------------------------------------------------------
    # Build player results
    # ----------------------------------------------------------------------

    players = []

    for row in top.itertuples():

        player_id = int(row.player_id)

        player_info = _PLAYER_NAME_MAP.get(
            player_id,
            {},
        )

        player_name = (
            player_info.get("player_name")
            or
            player_info.get("player_full_name")
            or
            f"Player {player_id}"
        )

        players.append(
            {
                "player_id": player_id,

                "player_name": player_name,

                "predicted_fantasy_points": round(
                    float(row.predicted_fantasy_points),
                    1,
                ),
            }
        )

    # ----------------------------------------------------------------------
    # Return structured result
    # ----------------------------------------------------------------------

    return {
        "prediction_date": as_of.strftime(
            "%Y-%m-%d"
        ),

        "data_through": data_through.strftime(
            "%Y-%m-%d"
        ),

        "prediction_type": prediction_type,

        "forecast_horizon": {
            "days": forecast_days,
            "years": round(
                forecast_years,
                1,
            ),
        },

        "eligibility_seasons": [
            int(year)
            for year in latest_two_seasons
        ],

        "prediction_basis": (
            f"Player eligibility is based on the latest 2 "
            f"available seasons "
            f"({latest_two_seasons[0]}-"
            f"{latest_two_seasons[1]}). "
            f"Player form uses each player's latest available "
            f"snapshot before the requested prediction date."
        ),

        "data_limitation": (
            f"The available player data ends on "
            f"{data_through.strftime('%Y-%m-%d')}. "
            f"Predictions after this date are forecasts based "
            f"on historical data and do not include future "
            f"player transfers, retirements, injuries, or "
            f"team-list changes."
        ),

        "players": players,
    }