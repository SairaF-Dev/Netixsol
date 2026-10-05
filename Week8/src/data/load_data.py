"""
load_data.py
------------
Utility functions for loading raw datasets.

Provenance: Original raw data loading — no transformation applied here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

RAW_PROPERTY_PATH = RAW_DIR / "Property.csv"
RAW_LEADS_PATH = RAW_DIR / "leads_raw.csv"


def load_property_raw(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load the raw Zameen.com property dataset WITHOUT any transformation.

    Returns
    -------
    pd.DataFrame
        Raw dataframe — 190,904 rows x 31 columns (including 14 Unnamed cols).
    """
    fp = Path(path) if path else RAW_PROPERTY_PATH
    if not fp.exists():
        raise FileNotFoundError(f"Property.csv not found at: {fp}")

    df = pd.read_csv(fp, low_memory=False)
    logger.info("Loaded raw property data: %s rows x %s cols from %s", *df.shape, fp)
    _assert_property_raw_integrity(df)
    return df


def load_leads_raw(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load the synthetic leads dataset.

    Returns
    -------
    pd.DataFrame
        Raw dataframe — 5,000 rows x 16 cols.
    """
    fp = Path(path) if path else RAW_LEADS_PATH
    if not fp.exists():
        raise FileNotFoundError(f"leads_raw.csv not found at: {fp}. Run src/data/generate_leads.py first.")

    df = pd.read_csv(fp)
    logger.info("Loaded raw leads data: %s rows x %s cols from %s", *df.shape, fp)
    return df


def _assert_property_raw_integrity(df: pd.DataFrame) -> None:
    """Sanity checks on raw property data."""
    required_cols = [
        "property_id", "location_id", "page_url", "property_type",
        "price", "location", "city", "province_name", "latitude",
        "longitude", "baths", "area", "purpose", "bedrooms",
        "date_added", "agency", "agent",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Raw property data is missing expected columns: {missing}")

    if len(df) < 5000:
        raise ValueError(f"Property dataset has only {len(df)} rows; expected >= 5,000.")
    if df["property_id"].duplicated().any():
        logger.warning(
            "Duplicate property_id found in raw data: %d duplicates",
            df["property_id"].duplicated().sum(),
        )
    logger.info("Raw property integrity checks passed.")
