from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from predict import predict_match_winner, predict_top_player


# ============================================================================
# CONSTANTS
# ============================================================================

PLAYER_DATA_FILE = Path("merged_players.csv")

DEFAULT_TOP_N = 5

# We use the latest two available seasons to forecast
# the immediately following season.
TRAINING_SEASONS = 2
FORECAST_HORIZON_SEASONS = 1


# ============================================================================
# DATASET YEAR HELPERS
# ============================================================================

@lru_cache(maxsize=1)
def get_latest_data_year() -> int:
    """
    Return the latest season/year available in the player dataset.

    Example:
        Dataset ends at 2025
        -> returns 2025

    The value is cached because the dataset does not normally
    change while the application is running.
    """

    if not PLAYER_DATA_FILE.exists():
        # Fallback to the known project data boundary.
        return 2025

    try:
        # Read only the year column.
        df = pd.read_csv(
            PLAYER_DATA_FILE,
            usecols=["year"],
        )

    except ValueError:
        # Some datasets may use "season" instead of "year".
        try:
            df = pd.read_csv(
                PLAYER_DATA_FILE,
                usecols=["season"],
            )

            year_column = "season"

        except Exception as exc:
            print(
                "[WARNING prediction_tools] "
                f"Could not determine latest season: {exc}"
            )

            return 2025

    except Exception as exc:
        print(
            "[WARNING prediction_tools] "
            f"Could not determine latest season: {exc}"
        )

        return 2025

    else:
        year_column = "year"

    if year_column not in df.columns:
        return 2025

    years = pd.to_numeric(
        df[year_column],
        errors="coerce",
    ).dropna()

    if years.empty:
        return 2025

    return int(years.max())


def get_forecast_year() -> int:
    """
    Return the only future season that the current model
    is designed to forecast.

    Example:

        Latest data = 2025
        Forecast year = 2026
    """

    return (
        get_latest_data_year()
        + FORECAST_HORIZON_SEASONS
    )


def get_training_seasons() -> list[int]:
    """
    Return the latest two available seasons.

    Example:

        Latest year = 2025
        -> [2024, 2025]
    """

    latest_year = get_latest_data_year()

    return [
        latest_year - 1,
        latest_year,
    ]


def validate_forecast_date(
    date: str | None,
) -> tuple[bool, str | None]:
    """
    Validate whether a requested prediction date falls
    within the supported one-season forecast horizon.

    Returns:

        (True, None)
            when prediction is supported.

        (False, error_message)
            when prediction is outside the supported horizon.
    """

    latest_year = get_latest_data_year()
    forecast_year = get_forecast_year()
    training_seasons = get_training_seasons()

    # ------------------------------------------------------------------------
    # No date supplied
    #
    # Let the underlying model use its normal latest-data behavior.
    # ------------------------------------------------------------------------

    if not date:
        return True, None

    # ------------------------------------------------------------------------
    # Extract year safely.
    # ------------------------------------------------------------------------

    try:
        requested_year = int(
            str(date).strip()[:4]
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            False,
            (
                "Invalid prediction date. "
                "Please use YYYY-MM-DD format."
            ),
        )

    # ------------------------------------------------------------------------
    # Future prediction
    # ------------------------------------------------------------------------

    if requested_year > latest_year:

        if requested_year > forecast_year:

            return (
                False,
                (
                    f"My current AFL prediction model uses the "
                    f"latest two available seasons "
                    f"({training_seasons[0]}-{training_seasons[1]}) "
                    f"and is designed to forecast only the "
                    f"immediately following season ({forecast_year}). "
                    f"I cannot provide a reliable forecast for "
                    f"{requested_year} from the available data."
                ),
            )

        # requested_year == forecast_year
        return True, None

    # ------------------------------------------------------------------------
    # Historical/current dates are allowed.
    #
    # These are not treated as future forecasts.
    # ------------------------------------------------------------------------

    return True, None


# ============================================================================
# MATCH-WINNER INPUT
# ============================================================================

class MatchInput(BaseModel):

    home_team: str = Field(
        ...,
        description="Home AFL team.",
    )

    away_team: str = Field(
        ...,
        description="Away AFL team.",
    )

    date: str | None = Field(
        default=None,
        description=(
            "Optional prediction date in YYYY-MM-DD format. "
            "Future forecasts are supported only for the "
            "immediately following season after the latest "
            "available data."
        ),
    )


# ============================================================================
# TOP-PLAYER INPUT
# ============================================================================

class PlayerInput(BaseModel):

    team: str = Field(
        ...,
        description="AFL team for the top-player prediction.",
    )

    date: str | None = Field(
        default=None,
        description=(
            "Optional prediction date in YYYY-MM-DD format. "
            "Future forecasts are supported only for the "
            "immediately following season after the latest "
            "available data."
        ),
    )

    top_n: int = Field(
        default=DEFAULT_TOP_N,
        ge=1,
        le=20,
    )


# ============================================================================
# SAFE MATCH-WINNER WRAPPER
# ============================================================================

def _run_match_winner_prediction(
    home_team: str,
    away_team: str,
    date: str | None = None,
) -> Any:
    """
    Validate forecast horizon before calling the actual model.
    """

    valid, error = validate_forecast_date(date)

    if not valid:
        return {
            "error": error,
            "unsupported": True,
            "prediction_type": "unsupported_future_horizon",
        }

    return predict_match_winner(
        home_team,
        away_team,
        date,
    )


# ============================================================================
# SAFE TOP-PLAYER WRAPPER
# ============================================================================

def _run_top_player_prediction(
    team: str,
    date: str | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> Any:
    """
    Validate forecast horizon before calling the actual model.
    """

    valid, error = validate_forecast_date(date)

    if not valid:
        return {
            "error": error,
            "unsupported": True,
            "prediction_type": "unsupported_future_horizon",
        }

    return predict_top_player(
        team,
        date,
        top_n,
    )


# ============================================================================
# LANGCHAIN TOOLS
# ============================================================================

match_winner_prediction = StructuredTool.from_function(
    func=_run_match_winner_prediction,
    name="match_winner_prediction",
    description=(
        "Predict an AFL match winner using historical model features. "
        "The model uses historical data and supports future forecasting "
        "only for the immediately following season after the latest "
        "available data."
    ),
    args_schema=MatchInput,
)


top_player_prediction = StructuredTool.from_function(
    func=_run_top_player_prediction,
    name="top_player_prediction",
    description=(
        "Predict the top AFL players for a team. "
        "The model uses the latest two available seasons and supports "
        "future forecasting only for the immediately following season."
    ),
    args_schema=PlayerInput,
)