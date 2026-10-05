"""
clean_properties.py
-------------------
Cleaning pipeline for the Zameen.com property dataset supporting BOTH
'For Sale' and 'For Rent' listings.

Raw data is NEVER modified — only returned DataFrames are cleaned.

Provenance convention:
  - Original  : columns present in raw Property.csv
  - Derived   : computed from original columns
  - Synthetic : generated via documented rules (see property_features.py)
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Conversion constants
KANAL_TO_MARLA: float = 20.0

# Pakistan geographic bounding box
LAT_MIN, LAT_MAX = 20.0, 38.0
LON_MIN, LON_MAX = 58.0, 80.0

# Purpose-specific price validation floors
# For Sale: anything under PKR 50k is an entry typo / test listing (median is 13.5M PKR)
SALE_PRICE_FLOOR: float = 50_000.0

# For Rent: anything under PKR 1,000 is an entry typo (e.g. 0, 27, 40, 54 PKR).
# Legitimate hostel rooms and sub-portions rent for 3,000 to 8,000 PKR.
RENT_PRICE_FLOOR: float = 1_000.0

# IQR fence multiplier for flagging luxury outliers (retained in training data)
IQR_FENCE: float = 3.0


def clean_properties(
    df_raw: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Full cleaning pipeline for property data supporting both Sale and Rent.

    Parameters
    ----------
    df_raw : pd.DataFrame
        Raw property dataframe loaded by load_data.load_property_raw().

    Returns
    -------
    df_interim : pd.DataFrame
        Structural cleaning applied (14 Unnamed columns dropped, 17 missing purpose dropped).
    df_clean : pd.DataFrame
        Complete cleaned dataset containing both For Sale and For Rent listings.
    df_sale : pd.DataFrame
        For Sale subset after sale price validation (126,666 rows).
    df_rent : pd.DataFrame
        For Rent subset after rental price validation (64,161 rows).
    """
    df = df_raw.copy()

    df = _drop_unnamed_columns(df)
    df = _clean_purpose(df)
    df = _parse_dates(df)
    df = _parse_area(df)
    df = _clean_coordinates(df)
    df = _clean_bedrooms_baths(df)
    df = _normalise_location(df)
    df = _add_derived_temporal_features(df)

    df_interim = df.copy()

    # Separate purpose-specific price cleaning
    df_sale = _clean_sale_listings(df_interim)
    df_rent = _clean_rental_listings(df_interim)

    # Combine into unified canonical cleaned dataset
    df_clean = pd.concat([df_sale, df_rent], ignore_index=True)

    logger.info(
        "Cleaning complete: Interim=%d | Clean Total=%d (Sale=%d, Rent=%d)",
        len(df_interim), len(df_clean), len(df_sale), len(df_rent)
    )
    return df_interim, df_clean, df_sale, df_rent


def _drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop 14 empty Unnamed export artifact columns."""
    unnamed = [c for c in df.columns if c.startswith("Unnamed:")]
    df = df.drop(columns=unnamed)
    logger.info("Dropped %d Unnamed columns.", len(unnamed))
    return df


def _clean_purpose(df: pd.DataFrame) -> pd.DataFrame:
    """Drop 17 rows with missing purpose (<0.01% of data)."""
    before = len(df)
    df = df.dropna(subset=["purpose"])
    removed = before - len(df)
    logger.info("Removed %d rows with missing 'purpose'.", removed)
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date_added into datetime with mixed-format handling."""
    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce", dayfirst=False)
    unparsed = df["date_added"].isna().sum()
    if unparsed:
        logger.warning("%d date_added values could not be parsed -> NaT.", unparsed)
    return df


def _parse_area(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize 'area' into numeric 'area_marla'.
    Conversion: 1 Kanal = 20 Marla. Original 'area' is retained for traceability.
    """
    def _parse_one(val: str) -> Optional[float]:
        if pd.isna(val):
            return np.nan
        val = str(val).strip()
        m = re.match(r"^([\d.]+)\s*(Kanal|Marla)$", val, re.IGNORECASE)
        if not m:
            return np.nan
        number = float(m.group(1))
        unit = m.group(2).lower()
        return number * KANAL_TO_MARLA if unit == "kanal" else number

    df["area_marla"] = df["area"].apply(_parse_one)
    invalid_area = df["area_marla"] <= 0
    df.loc[invalid_area, "area_marla"] = np.nan
    logger.info(
        "area_marla parsed. Valid: %d, NaN: %d",
        df["area_marla"].notna().sum(),
        df["area_marla"].isna().sum(),
    )
    return df


def _clean_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Validate lat/lon against Pakistan bounding box; out-of-bounds -> NaN."""
    df["coord_valid"] = (
        df["latitude"].between(LAT_MIN, LAT_MAX)
        & df["longitude"].between(LON_MIN, LON_MAX)
    )
    n_invalid = (~df["coord_valid"]).sum()
    df.loc[~df["coord_valid"], ["latitude", "longitude"]] = np.nan
    logger.info("%d coordinate pairs flagged as out-of-bounds -> set to NaN.", n_invalid)
    return df


def _clean_bedrooms_baths(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle zero bedrooms and baths across both Sale and Rent properties.
    For residential types (House, Flat, Portion, Penthouse), zeros are treated
    as unreported missing values and imputed via (property_type, city) group medians.
    """
    residential = {"House", "Flat", "Upper Portion", "Lower Portion", "Penthouse"}

    mask_residential = df["property_type"].isin(residential)
    mask_zero_bed = df["bedrooms"] == 0
    mask_zero_bath = df["baths"] == 0

    df.loc[mask_residential & mask_zero_bed, "bedrooms"] = np.nan
    df.loc[mask_zero_bath, "baths"] = np.nan

    logger.info(
        "bedrooms NaN after zero-cleaning: %d. baths NaN: %d.",
        df["bedrooms"].isna().sum(),
        df["baths"].isna().sum(),
    )

    for col in ["bedrooms", "baths"]:
        group_median = df.groupby(["property_type", "city"])[col].transform("median")
        df[col] = df[col].fillna(group_median)
        df[col] = df[col].fillna(df[col].median())

    logger.info("bedrooms / baths imputation complete.")
    return df


def _normalise_location(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and title-case location, city, and province."""
    df["location"] = df["location"].astype(str).str.strip().str.title()
    df["city"] = df["city"].astype(str).str.strip().str.title()
    df["province_name"] = df["province_name"].astype(str).str.strip().str.title()
    logger.info("Location strings normalised.")
    return df


def _add_derived_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract calendar year, month, and quarter from date_added."""
    df["listing_year"] = df["date_added"].dt.year.astype("Int64")
    df["listing_month"] = df["date_added"].dt.month.astype("Int64")
    df["listing_quarter"] = df["date_added"].dt.quarter.astype("Int64")
    logger.info("Derived temporal features added.")
    return df


def _clean_sale_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean For Sale listings:
      - Filter purpose == 'For Sale'
      - Enforce SALE_PRICE_FLOOR (PKR 50,000)
      - Flag luxury outliers (price > Q3 + 3*IQR ~ 81.5M PKR)
      - Calculate price_per_marla (EDA ONLY)
    """
    df_sale = df[df["purpose"] == "For Sale"].copy()
    before = len(df_sale)
    df_sale = df_sale[df_sale["price"] >= SALE_PRICE_FLOOR]
    removed = before - len(df_sale)
    logger.info("Sale cleaning: removed %d listings with price < PKR %s.", removed, f"{SALE_PRICE_FLOOR:,.0f}")

    q1 = df_sale["price"].quantile(0.25)
    q3 = df_sale["price"].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + IQR_FENCE * iqr
    df_sale["price_outlier_flag"] = (df_sale["price"] > upper_fence).astype(int)

    valid_area = df_sale["area_marla"].notna() & (df_sale["area_marla"] > 0)
    df_sale["price_per_marla"] = np.nan
    df_sale.loc[valid_area, "price_per_marla"] = (
        df_sale.loc[valid_area, "price"] / df_sale.loc[valid_area, "area_marla"]
    )
    return df_sale.reset_index(drop=True)


def _clean_rental_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean For Rent listings:
      - Filter purpose == 'For Rent'
      - Enforce RENT_PRICE_FLOOR (PKR 1,000)
      - Flag luxury rental outliers (price > Q3 + 3*IQR ~ 250,000 PKR)
      - Calculate price_per_marla (EDA ONLY)
    """
    df_rent = df[df["purpose"] == "For Rent"].copy()
    before = len(df_rent)
    df_rent = df_rent[df_rent["price"] >= RENT_PRICE_FLOOR]
    removed = before - len(df_rent)
    logger.info("Rent cleaning: removed %d listings with price < PKR %s.", removed, f"{RENT_PRICE_FLOOR:,.0f}")

    q1 = df_rent["price"].quantile(0.25)
    q3 = df_rent["price"].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + IQR_FENCE * iqr
    df_rent["price_outlier_flag"] = (df_rent["price"] > upper_fence).astype(int)

    valid_area = df_rent["area_marla"].notna() & (df_rent["area_marla"] > 0)
    df_rent["price_per_marla"] = np.nan
    df_rent.loc[valid_area, "price_per_marla"] = (
        df_rent.loc[valid_area, "price"] / df_rent.loc[valid_area, "area_marla"]
    )
    return df_rent.reset_index(drop=True)
