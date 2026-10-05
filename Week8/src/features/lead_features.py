"""
lead_features.py
----------------
Feature engineering and preprocessing pipeline for Dataset B (lead scoring).

Target: converted (binary 0/1)
Split: 70% train / 15% val / 15% test — STRATIFIED on 'converted'.
RANDOM_STATE = 42
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, RobustScaler

logger = logging.getLogger(__name__)

RANDOM_STATE: int = 42
TARGET: str = "converted"

EXCLUDE_COLS = {"lead_id", "converted"}

CAT_COLS = [
    "lead_source", "preferred_city", "property_type",
    "purpose", "objection_raised", "lead_age_bucket",
    "response_speed_category",
]

NUMERIC_COLS = [
    "budget_pkr", "number_of_calls", "total_call_duration_min",
    "response_time_minutes", "visit_booked", "days_since_first_contact",
    "follow_up_count", "budget_match_ratio",
    "engagement_score", "avg_call_duration_min", "lead_age_bucket_num",
    "follow_up_intensity", "location_frequency",
]


def add_lead_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute domain-engineered features for sales lead scoring."""
    df = df.copy()

    # engagement_score: composite index (0-12)
    call_score = np.minimum(df["number_of_calls"], 10) / 10.0 * 4.0
    dur_score = np.minimum(df["total_call_duration_min"], 60) / 60.0 * 3.0
    followup_score = np.minimum(df["follow_up_count"], 10) / 10.0 * 2.0
    visit_bonus = df["visit_booked"] * 3.0
    df["engagement_score"] = (call_score + dur_score + followup_score + visit_bonus).round(2)

    # avg_call_duration_min
    safe_calls = df["number_of_calls"].replace(0, 1)
    df["avg_call_duration_min"] = (df["total_call_duration_min"] / safe_calls).round(2)

    # lead_age_bucket & lead_age_bucket_num
    bins = [0, 7, 30, 90, 180, 999]
    labels_cat = ["<1w", "1w-1m", "1m-3m", "3m-6m", "6m+"]
    labels_num = [1, 2, 3, 4, 5]
    df["lead_age_bucket"] = pd.cut(df["days_since_first_contact"], bins=bins, labels=labels_cat).astype(str)
    df["lead_age_bucket_num"] = pd.cut(df["days_since_first_contact"], bins=bins, labels=labels_num).astype(float)

    # response_speed_category
    df["response_speed_category"] = np.where(
        df["response_time_minutes"] <= 30, "Fast (<30m)",
        np.where(df["response_time_minutes"] <= 180, "Moderate (30m-3h)", "Slow (>3h)")
    )

    # follow_up_intensity
    safe_days = df["days_since_first_contact"].replace(0, 1)
    df["follow_up_intensity"] = (df["follow_up_count"] / safe_days).clip(0, 1.0).round(4)

    logger.info("Added lead features: engagement_score, avg_call_duration_min, lead_age_bucket, response_speed_category, follow_up_intensity.")
    return df


def apply_location_frequency_lead(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Frequency-encode preferred_location using training split only."""
    freq = df_train["preferred_location"].value_counts(normalize=True)
    for split_df in [df_train, df_val, df_test]:
        split_df["location_frequency"] = split_df["preferred_location"].map(freq).fillna(0.0)
    return df_train, df_val, df_test


def build_lead_pipeline(scaler: str = "standard") -> ColumnTransformer:
    """Build reusable Scikit-learn preprocessing ColumnTransformer for leads."""
    scaler_obj = StandardScaler() if scaler == "standard" else RobustScaler()
    num_pipe = Pipeline([("scaler", scaler_obj)])
    cat_pipe = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop="if_binary"))])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipe, NUMERIC_COLS),
            ("cat", cat_pipe, CAT_COLS),
        ],
        remainder="drop",
    )
    return preprocessor


def split_leads_data(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train/val/test split (70/15/15) preserving class balance of 'converted'."""
    df_trainval, df_test = train_test_split(df, test_size=test_size, random_state=seed, stratify=df[TARGET])
    rel_val = val_size / (1.0 - test_size)
    df_train, df_val = train_test_split(df_trainval, test_size=rel_val, random_state=seed, stratify=df_trainval[TARGET])

    logger.info(
        "Lead Split: Train=%d (%.1f%%), Val=%d (%.1f%%), Test=%d (%.1f%%)",
        len(df_train), df_train[TARGET].mean() * 100,
        len(df_val), df_val[TARGET].mean() * 100,
        len(df_test), df_test[TARGET].mean() * 100,
    )
    return df_train.copy(), df_val.copy(), df_test.copy()
