"""
clean_leads.py
--------------
Cleaning and validation pipeline for Dataset B (synthetic leads).
"""

from __future__ import annotations

import logging
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "lead_id", "lead_source", "budget_pkr", "preferred_city",
    "preferred_location", "property_type", "purpose",
    "number_of_calls", "total_call_duration_min", "response_time_minutes",
    "visit_booked", "days_since_first_contact", "objection_raised",
    "follow_up_count", "budget_match_ratio", "converted",
]


def clean_leads(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Validate and lightly clean the synthetic leads dataset."""
    df = df_raw.copy()

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Leads dataset missing required columns: {missing_cols}")

    if not set(df["converted"].unique()).issubset({0, 1}):
        raise ValueError("'converted' column contains values other than 0 and 1.")

    n_bad_budget = (df["budget_pkr"] <= 0).sum()
    if n_bad_budget:
        logger.warning("%d leads have non-positive budget -> removed.", n_bad_budget)
        df = df[df["budget_pkr"] > 0]

    df = df[df["number_of_calls"] > 0]

    if df["lead_id"].duplicated().any():
        raise ValueError("Duplicate lead_id values found.")

    df = df[(df["budget_match_ratio"] > 0) & (df["budget_match_ratio"] <= 5.0)]

    logger.info(
        "Leads cleaning complete. Final shape: %d rows x %d cols. Conversion rate: %.1f%%.",
        *df.shape,
        df["converted"].mean() * 100,
    )
    return df.reset_index(drop=True)
