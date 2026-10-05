"""
property_features.py
--------------------
Feature engineering and preprocessing pipeline for the property valuation dataset
supporting BOTH 'For Sale' and 'For Rent' listings.

Features:
1. Synthetic augmentation (documented domain assumptions for structure & amenities)
2. Derived feature calculations (ratios, society tiers, buckets)
3. Preprocessing pipelines (Scikit-learn) with purpose-stratified 70/15/15 splits
4. High-cardinality location encoding (Frequency Encoding vs Target Encoding)
5. Production Huber Preprocessor (37 Numeric + 6 Categorical)
"""

from __future__ import annotations

import logging
from typing import Tuple, Dict, Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
    RobustScaler,
    TargetEncoder,
)

logger = logging.getLogger(__name__)

RANDOM_STATE: int = 42
TARGET: str = "price"


# ==============================================================================
# 1. Synthetic Augmentation (Documented Domain Assumptions)
# ==============================================================================

def add_synthetic_features(df: pd.DataFrame, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """
    Augment property listings with realistic synthetic valuation features.

    Documented Assumptions:
    - property_age_years: Gamma distribution (shape=2.0, scale=5.0) reflecting Pakistani
      housing stock. Conditioned by property type (flats newer; farmhouses older).
    - floors: Storey count conditioned on type (Houses: 1-3 storeys; Flats: 1-20 storeys).
    - corner: ~18% base probability (22% for detached houses, 12% for flats/portions).
    - park_facing: ~10% overall; higher (~20%) for corner properties.
    - covered_area_sqft: Structural footprint derived from plot size (Marla x 272 sqft)
      multiplied by plausible structural coverage ratios by type (Houses: 55-85%, Flats: 85-110%).
    - Individual amenities: parking, security, electricity_backup, gas, water_supply, park_nearby.
      Calibrated with an empirical premium boost for Islamabad and prime Lahore schemes.
    - amenity_score: Sum of active amenities (0 to 6).
    - Distance features: Exponential distributions reflecting urban transit access to main roads,
      schools, and hospitals in km, parameterized per metropolitan city infrastructure.
    """
    rng = np.random.default_rng(seed)
    n = len(df)
    df = df.copy()

    # property_age_years
    age_base = rng.gamma(shape=2.0, scale=5.0, size=n).clip(0, 50).astype(int)
    age_adj = np.where(
        df["property_type"].isin(["Farm House"]), rng.integers(5, 20, n), 0
    ) + np.where(
        df["property_type"].isin(["Flat", "Penthouse"]), -rng.integers(0, 5, n), 0
    )
    df["property_age_years"] = np.clip(age_base + age_adj, 0, 60).astype(int)

    # floors
    type_floors_map = {
        "House":          lambda s: rng.choice([1, 2, 3], s, p=[0.25, 0.55, 0.20]),
        "Flat":           lambda s: rng.integers(1, 21, s),
        "Upper Portion":  lambda s: rng.choice([1, 2], s, p=[0.40, 0.60]),
        "Lower Portion":  lambda s: np.ones(s, dtype=int),
        "Room":           lambda s: np.ones(s, dtype=int),
        "Penthouse":      lambda s: rng.integers(5, 21, s),
        "Farm House":     lambda s: rng.choice([1, 2], s, p=[0.70, 0.30]),
    }
    floors = np.ones(n, dtype=int)
    for ptype, fn in type_floors_map.items():
        mask = df["property_type"] == ptype
        if mask.any():
            floors[mask] = fn(mask.sum())
    df["floors"] = floors

    # corner & park_facing
    corner_prob = np.where(df["property_type"].isin(["House", "Farm House"]), 0.22, 0.12)
    df["corner"] = (rng.random(n) < corner_prob).astype(int)
    pf_prob = np.where(df["corner"] == 1, 0.20, 0.08)
    df["park_facing"] = (rng.random(n) < pf_prob).astype(int)

    # covered_area_sqft
    marla_to_sqft = 272.0
    plot_sqft = df["area_marla"].fillna(df["area_marla"].median()) * marla_to_sqft
    coverage_ratio = np.where(
        df["property_type"] == "House", rng.uniform(0.55, 0.85, n),
        np.where(df["property_type"] == "Flat", rng.uniform(0.85, 1.10, n),
        np.where(df["property_type"] == "Penthouse", rng.uniform(0.90, 1.20, n),
        np.where(df["property_type"].isin(["Upper Portion", "Lower Portion"]), rng.uniform(0.40, 0.60, n),
        np.where(df["property_type"] == "Farm House", rng.uniform(0.20, 0.45, n),
        rng.uniform(0.50, 0.80, n)))))
    )
    df["covered_area_sqft"] = (plot_sqft * coverage_ratio).round(0).clip(lower=100).astype(int)

    # Individual amenities
    city_boost = np.where(df["city"] == "Islamabad", 0.12, np.where(df["city"] == "Lahore", 0.06, 0.0))
    amenities = {
        "parking": 0.60, "security": 0.40, "electricity_backup": 0.35,
        "gas": 0.75, "water_supply": 0.70, "park_nearby": 0.25
    }
    for col, base_p in amenities.items():
        p = np.clip(base_p + city_boost, 0.0, 1.0)
        df[col] = (rng.random(n) < p).astype(int)

    # amenity_score
    df["amenity_score"] = df[list(amenities.keys())].sum(axis=1)

    # Distances
    city_dist = {
        "Islamabad":  {"road": 0.8, "school": 1.0, "hospital": 2.0},
        "Lahore":     {"road": 1.0, "school": 1.5, "hospital": 2.5},
        "Karachi":    {"road": 1.2, "school": 2.0, "hospital": 3.0},
        "Rawalpindi": {"road": 1.0, "school": 1.5, "hospital": 2.5},
        "Faisalabad": {"road": 1.1, "school": 1.8, "hospital": 2.8},
    }
    road_km, school_km, hospital_km = np.zeros(n), np.zeros(n), np.zeros(n)
    for city, scales in city_dist.items():
        m = df["city"] == city
        if m.any():
            road_km[m] = rng.exponential(scales["road"], m.sum()).clip(0.1, 10)
            school_km[m] = rng.exponential(scales["school"], m.sum()).clip(0.2, 15)
            hospital_km[m] = rng.exponential(scales["hospital"], m.sum()).clip(0.3, 20)

    unmapped = road_km == 0
    if unmapped.any():
        road_km[unmapped] = rng.exponential(1.0, unmapped.sum())
        school_km[unmapped] = rng.exponential(1.5, unmapped.sum())
        hospital_km[unmapped] = rng.exponential(2.5, unmapped.sum())

    df["distance_main_road_km"] = road_km.round(2)
    df["distance_school_km"] = school_km.round(2)
    df["distance_hospital_km"] = hospital_km.round(2)

    logger.info("Added 15 synthetic features across %d records.", n)
    return df


# ==============================================================================
# 2. Derived Feature Engineering
# ==============================================================================

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived features applicable to both Sale and Rental models.
    """
    df = df.copy()

    bins = [-1, 0, 5, 10, 20, 60]
    labels = ["New", "0-5yr", "6-10yr", "11-20yr", "20+yr"]
    df["property_age_bucket"] = pd.cut(df["property_age_years"], bins=bins, labels=labels).astype(str)

    safe_baths = df["baths"].replace(0, np.nan).fillna(1)
    df["bed_bath_ratio"] = (df["bedrooms"] / safe_baths).round(2)

    plot_sqft = df["area_marla"] * 272.0
    df["covered_area_ratio"] = (df["covered_area_sqft"] / plot_sqft).clip(0, 2.0).round(3)

    season_map = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Autumn"}
    df["listing_season"] = df["listing_quarter"].map(season_map).fillna("Unknown")

    loc_lower = df["location"].astype(str).str.lower()
    premium_kw = ["dha", "bahria", "f-6", "f-7", "f-8", "e-7", "clifton", "cantt", "gulberg", "askari", "model town"]
    budget_kw = ["scheme 33", "korangi", "surjani", "north karachi", "shadman", "chungi", "rehman", "badami"]

    df["society_tier"] = np.where(
        loc_lower.str.contains("|".join(premium_kw)), "Premium",
        np.where(loc_lower.str.contains("|".join(budget_kw)), "Budget", "Mid")
    )

    logger.info("Added engineered features: property_age_bucket, bed_bath_ratio, covered_area_ratio, listing_season, society_tier.")
    return df


# ==============================================================================
# 3. High-Cardinality Encoding (Train-Only Fitting)
# ==============================================================================

def apply_location_frequency_encoding(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Apply frequency encoding to high-cardinality 'location'.
    Fitted STRICTLY on training split. Unseen locations map to 0.0.
    """
    freq = df_train["location"].value_counts(normalize=True)
    for split_df in [df_train, df_val, df_test]:
        split_df["location_frequency"] = split_df["location"].map(freq).fillna(0.0)
    return df_train, df_val, df_test


def apply_location_target_encoding(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    target_col: str = TARGET,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Apply out-of-fold target encoding to 'location'.
    Fitted STRICTLY on training split using Scikit-Learn TargetEncoder.
    """
    te = TargetEncoder(smooth="auto", cv=5, random_state=RANDOM_STATE)
    X_train_loc = df_train[["location"]]
    y_train = np.log1p(df_train[target_col])

    df_train["location_target_enc"] = te.fit_transform(X_train_loc, y_train)
    df_val["location_target_enc"] = te.transform(df_val[["location"]])
    df_test["location_target_enc"] = te.transform(df_test[["location"]])
    return df_train, df_val, df_test


# ==============================================================================
# 4. Preprocessing Pipelines & Splitting
# ==============================================================================

ML_NUMERIC_COLS = [
    "baths", "bedrooms", "latitude", "longitude",
    "area_marla", "listing_year", "listing_month", "listing_quarter",
    "property_age_years", "floors", "corner", "park_facing",
    "covered_area_sqft", "parking", "security", "electricity_backup",
    "gas", "water_supply", "park_nearby", "amenity_score",
    "distance_main_road_km", "distance_school_km", "distance_hospital_km",
    "bed_bath_ratio", "covered_area_ratio", "location_frequency",
]

ML_LOW_CARD_CATS = [
    "property_type", "city", "province_name",
    "listing_season", "property_age_bucket", "society_tier"
]

EXCLUDED_ML_COLS = [
    "property_id", "location_id", "page_url", "agency", "agent",
    "price_per_marla",  # TARGET LEAKAGE
    "price_outlier_flag", "coord_valid", "purpose", "price"
]


def build_property_pipeline(purpose: str = "sale", scaler: str = "robust") -> ColumnTransformer:
    """
    Build reusable Scikit-learn preprocessing ColumnTransformer.

    Parameters
    ----------
    purpose : str
        'sale' -> For Sale model pipeline
        'rent' -> For Rent model pipeline
        'all'  -> Unified model with purpose one-hot encoded
    scaler : str
        'robust' or 'standard'
    """
    scaler_obj = RobustScaler() if scaler == "robust" else StandardScaler()
    num_pipe = Pipeline([("scaler", scaler_obj)])
    cat_pipe = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop="if_binary"))])

    cat_cols = list(ML_LOW_CARD_CATS)
    if purpose == "all":
        cat_cols.append("purpose")

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipe, ML_NUMERIC_COLS),
            ("cat", cat_pipe, cat_cols),
        ],
        remainder="drop",
    )
    return preprocessor


def split_property_data(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split property dataset into 70% train / 15% validation / 15% test
    STRATIFIED on 'purpose' so that both Sale and Rent listings are
    proportionally represented across all three folds.
    """
    df_trainval, df_test = train_test_split(
        df, test_size=test_size, random_state=seed, stratify=df["purpose"]
    )
    rel_val = val_size / (1.0 - test_size)
    df_train, df_val = train_test_split(
        df_trainval, test_size=rel_val, random_state=seed, stratify=df_trainval["purpose"]
    )

    logger.info(
        "Property Stratified Split: Train=%d (Sale=%d, Rent=%d), Val=%d (Sale=%d, Rent=%d), Test=%d (Sale=%d, Rent=%d)",
        len(df_train), (df_train["purpose"]=="For Sale").sum(), (df_train["purpose"]=="For Rent").sum(),
        len(df_val), (df_val["purpose"]=="For Sale").sum(), (df_val["purpose"]=="For Rent").sum(),
        len(df_test), (df_test["purpose"]=="For Sale").sum(), (df_test["purpose"]=="For Rent").sum(),
    )
    return df_train.copy(), df_val.copy(), df_test.copy()


def extract_purpose_splits(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
) -> Tuple[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame], Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """
    Extract dedicated (train, val, test) subsets for For Sale and For Rent.
    """
    sale_splits = (
        df_train[df_train["purpose"] == "For Sale"].copy(),
        df_val[df_val["purpose"] == "For Sale"].copy(),
        df_test[df_test["purpose"] == "For Sale"].copy(),
    )
    rent_splits = (
        df_train[df_train["purpose"] == "For Rent"].copy(),
        df_val[df_val["purpose"] == "For Rent"].copy(),
        df_test[df_test["purpose"] == "For Rent"].copy(),
    )
    return sale_splits, rent_splits


# ==============================================================================
# 5. Production Huber Preprocessor (37 Numeric + 6 Categorical)
# ==============================================================================

class HuberPropertyPreprocessor:
    """
    Production feature preprocessor for the Huber Property Valuation model.
    Encapsulates safe physical features, domain interactions, out-of-fold location
    target encoding, median imputation, and robust scaling.
    """

    def __init__(self, random_state: int = RANDOM_STATE):
        self.random_state = random_state
        self.target_encoder: Any = None
        self.column_transformer: Any = None
        self.numeric_cols = [
            "baths", "bedrooms", "latitude", "longitude",
            "area_marla", "listing_year", "listing_month", "listing_quarter",
            "property_age_years", "floors", "corner", "park_facing",
            "covered_area_sqft", "parking", "security", "electricity_backup",
            "gas", "water_supply", "park_nearby", "amenity_score",
            "distance_main_road_km", "distance_school_km", "distance_hospital_km",
            "bed_bath_ratio", "covered_area_ratio", "location_frequency",
            "is_furnished", "is_brand_new", "is_corner", "is_park_facing", "is_main_road",
            "loc_te", "log_area_marla", "total_rooms", "bed_bath_prod", "is_prime_city", "area_per_bed"
        ]
        self.categorical_cols = [
            "property_type", "city", "province_name",
            "listing_season", "property_age_bucket", "society_tier"
        ]

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        if "is_furnished" not in d.columns:
            u = d["page_url"].astype(str).str.lower() if "page_url" in d.columns else pd.Series("", index=d.index)
            d["is_furnished"] = (u.str.contains("furnished", na=False) & (~u.str.contains("unfurnished", na=False))).astype(int)
            d["is_brand_new"] = u.str.contains(r"brand_new|brand-new|newly_built|newly-built", na=False).astype(int)
            d["is_main_road"] = u.str.contains(r"main_road|main_boulevard|main-boulevard", na=False).astype(int)
            c_url = u.str.contains("corner", na=False).astype(int)
            d["is_corner"] = np.where(d["corner"].fillna(0) == 1, 1, c_url) if "corner" in d.columns else c_url
            pf_url = u.str.contains("park_facing|park-facing", na=False).astype(int)
            d["is_park_facing"] = np.where(d["park_facing"].fillna(0) == 1, 1, pf_url) if "park_facing" in d.columns else pf_url

        area_m = d["area_marla"].fillna(5.0)
        beds_safe = d["bedrooms"].fillna(3.0)
        baths_safe = d["baths"].fillna(3.0)

        d["log_area_marla"] = np.log1p(np.maximum(area_m, 0.1))
        d["total_rooms"] = beds_safe + baths_safe
        d["bed_bath_prod"] = beds_safe * baths_safe
        d["is_prime_city"] = d["city"].astype(str).isin(["Islamabad", "Lahore"]).astype(int)
        d["area_per_bed"] = (area_m / np.maximum(beds_safe, 1.0)).clip(0.0, 50.0)

        if "location" not in d.columns:
            d["location"] = "Unknown"
        return d

    def fit(self, df: pd.DataFrame, y: np.ndarray = None) -> "HuberPropertyPreprocessor":
        d = self._enrich(df)
        y_vals = y if y is not None else d["price"].values
        y_log = np.log1p(y_vals)

        self.target_encoder = TargetEncoder(smooth="auto", cv=5, random_state=self.random_state)
        d["loc_te"] = self.target_encoder.fit_transform(d[["location"]], y_log)

        num_pipe = Pipeline([("imp", SimpleImputer(strategy="median")), ("scl", RobustScaler())])
        cat_pipe = Pipeline([
            ("imp", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])

        self.column_transformer = ColumnTransformer([
            ("num", num_pipe, self.numeric_cols),
            ("cat", cat_pipe, self.categorical_cols),
        ])
        self.column_transformer.fit(d)
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        d = self._enrich(df)
        d["loc_te"] = self.target_encoder.transform(d[["location"]])
        return self.column_transformer.transform(d)

    def fit_transform(self, df: pd.DataFrame, y: np.ndarray = None) -> np.ndarray:
        self.fit(df, y)
        d = self._enrich(df)
        y_vals = y if y is not None else d["price"].values
        y_log = np.log1p(y_vals)
        d["loc_te"] = self.target_encoder.fit_transform(d[["location"]], y_log)
        return self.column_transformer.transform(d)
