"""
generate_leads.py
-----------------
Generates a realistic synthetic lead-scoring dataset (Dataset B).

Design principles:
  - 5,000 records (exceeds assignment minimum of 3,000).
  - Conversion probability is driven by realistic business logic — NOT random.
  - Target 'converted' is imbalanced: ~20–25% positive rate.
  - All columns represent information available BEFORE conversion.
  - No target-derived features (no leakage).
  - Fixed RANDOM_STATE = 42 for reproducibility.
  - Column provenance: entirely Synthetic.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

logger = logging.getLogger(__name__)

RANDOM_STATE: int = 42
N_LEADS: int = 5000

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

LEAD_SOURCES = ["Call", "WhatsApp", "Facebook", "Website"]
CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]
PROPERTY_TYPES = ["House", "Flat", "Upper Portion", "Lower Portion", "Penthouse"]
PURPOSES = ["Buy", "Rent", "Invest"]
OBJECTIONS = ["None", "Budget", "Price", "Location", "Timing", "Financing"]

CITY_BUDGET_RANGE = {
    "Lahore":      (8_000_000,  30_000_000),
    "Karachi":     (7_000_000,  25_000_000),
    "Islamabad":   (12_000_000, 50_000_000),
    "Rawalpindi":  (5_000_000,  20_000_000),
    "Faisalabad":  (4_000_000,  15_000_000),
}

CITY_MARKET_MEDIAN = {
    "Lahore":     14_000_000,
    "Karachi":    13_000_000,
    "Islamabad":  22_000_000,
    "Rawalpindi": 10_000_000,
    "Faisalabad":  8_000_000,
}


def generate_leads(n: int = N_LEADS, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """Generate synthetic lead dataset with realistic conversion probability."""
    rng = np.random.default_rng(seed)

    lead_source = rng.choice(LEAD_SOURCES, n, p=[0.25, 0.30, 0.25, 0.20])
    preferred_city = rng.choice(CITIES, n, p=[0.28, 0.28, 0.22, 0.14, 0.08])
    property_type = rng.choice(PROPERTY_TYPES, n, p=[0.50, 0.25, 0.12, 0.10, 0.03])
    purpose = rng.choice(PURPOSES, n, p=[0.55, 0.30, 0.15])
    objection = rng.choice(OBJECTIONS, n, p=[0.40, 0.15, 0.15, 0.12, 0.10, 0.08])

    budget_pkr = np.array([
        int(rng.integers(
            CITY_BUDGET_RANGE[city][0],
            CITY_BUDGET_RANGE[city][1]
        ))
        for city in preferred_city
    ])

    market_price = np.array([CITY_MARKET_MEDIAN[c] for c in preferred_city])
    budget_match_ratio = np.clip(budget_pkr / market_price, 0.1, 3.0).round(3)

    number_of_calls = rng.integers(1, 15, n)
    total_call_duration_min = np.round(
        rng.gamma(shape=2.5, scale=number_of_calls * 3.0 / 2.5), 1
    ).clip(1, 300)

    response_time_minutes = np.round(
        rng.exponential(scale=120, size=n)
    ).clip(1, 4320).astype(int)

    visit_base_prob = np.clip(
        0.10
        + 0.05 * (number_of_calls - 1)
        + 0.25 * (budget_match_ratio > 0.75)
        - 0.15 * (response_time_minutes > 1440),
        0.02,
        0.75,
    )
    visit_booked = rng.random(n) < visit_base_prob

    days_since_first_contact = rng.integers(1, 180, n)
    follow_up_count = np.clip(
        (number_of_calls - 1) + rng.integers(0, 4, n), 0, 20
    )

    location_pool = [
        "DHA Phase 1", "DHA Phase 5", "Bahria Town", "Gulberg", "Johar Town",
        "F-7", "F-10", "G-11", "Blue Area", "Clifton", "PECHS", "Gulshan-e-Iqbal",
        "Model Town", "Garden Town", "Wapda Town", "Bahria Enclave", "Lake City",
        "Defence", "Askari", "Punjab Cooperative",
    ]
    preferred_location = rng.choice(location_pool, n)

    # Calibrated logit formulation
    logit = (
        -6.0
        + 2.5 * visit_booked.astype(float)
        + 0.15 * number_of_calls
        + 1.5 * (budget_match_ratio > 0.80).astype(float)
        + 1.0 * (budget_match_ratio > 1.00).astype(float)
        - 0.5 * (budget_match_ratio < 0.50).astype(float)
        - 0.003 * response_time_minutes
        + 0.05 * follow_up_count
        - 0.008 * days_since_first_contact
        - 0.5 * (objection != "None").astype(float)
        + 0.3 * (lead_source == "Call").astype(float)
        + 0.15 * (lead_source == "WhatsApp").astype(float)
        - 0.1 * (lead_source == "Facebook").astype(float)
        + 0.2 * (purpose == "Buy").astype(float)
        + 0.4 * (purpose == "Invest").astype(float)
    )

    prob = expit(logit + rng.normal(0, 0.3, n))
    converted = (rng.random(n) < prob).astype(int)

    df = pd.DataFrame({
        "lead_id":                   [f"L{str(i+1).zfill(5)}" for i in range(n)],
        "lead_source":               lead_source,
        "budget_pkr":                budget_pkr,
        "preferred_city":            preferred_city,
        "preferred_location":        preferred_location,
        "property_type":             property_type,
        "purpose":                   purpose,
        "number_of_calls":           number_of_calls,
        "total_call_duration_min":   total_call_duration_min,
        "response_time_minutes":     response_time_minutes,
        "visit_booked":              visit_booked.astype(int),
        "days_since_first_contact":  days_since_first_contact,
        "objection_raised":          objection,
        "follow_up_count":           follow_up_count,
        "budget_match_ratio":        budget_match_ratio,
        "converted":                 converted,
    })

    conversion_rate = converted.mean()
    logger.info("Generated %d lead records. Conversion rate: %.1f%%.", n, conversion_rate * 100)
    return df


def save_leads(df: pd.DataFrame, path: Path | None = None) -> Path:
    out = path or (RAW_DIR / "leads_raw.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    logger.info("Saved %d leads to %s.", len(df), out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = generate_leads()
    path = save_leads(df)
    print(f"Leads saved to: {path}")
    print(f"Shape: {df.shape}")
    print(f"Conversion rate: {df['converted'].mean():.1%}")
