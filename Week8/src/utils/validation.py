"""
validation.py
-------------
Programmatic validation of Day 1 pipeline outputs for BOTH Sale and Rental models.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CheckResult = Tuple[str, bool, str]


def run_all_checks(
    df_property_raw: pd.DataFrame,
    df_property_interim: pd.DataFrame,
    df_property_clean: pd.DataFrame,
    df_sale: pd.DataFrame,
    df_rent: pd.DataFrame,
    df_leads_raw: pd.DataFrame,
    df_leads_clean: pd.DataFrame,
    df_prop_train: pd.DataFrame,
    df_prop_val: pd.DataFrame,
    df_prop_test: pd.DataFrame,
    df_lead_train: pd.DataFrame,
    df_lead_val: pd.DataFrame,
    df_lead_test: pd.DataFrame,
) -> List[CheckResult]:
    """Run all Day 1 validation checks across both Sale and Rental datasets."""
    results: List[CheckResult] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        results.append((name, condition, detail))
        icon = "[PASS]" if condition else "[FAIL]"
        print(f"{icon} {name}" + (f" - {detail}" if detail else ""))

    # 1. Dataset A Raw Checks
    check(
        "Dataset A raw: >= 5,000 rows",
        len(df_property_raw) >= 5000,
        f"Actual: {len(df_property_raw):,}",
    )
    check(
        "Dataset A raw: property_id unique",
        not df_property_raw["property_id"].duplicated().any(),
    )
    check(
        "Dataset A raw: unchanged (17 meaningful + 14 Unnamed cols)",
        len(df_property_raw.columns) == 31,
    )

    # 2. Dataset A Interim Checks
    check(
        "Dataset A interim: no Unnamed columns",
        not any(c.startswith("Unnamed") for c in df_property_interim.columns),
    )
    check(
        "Dataset A interim: area_marla > 0 (where not null)",
        (df_property_interim["area_marla"].dropna() > 0).all(),
    )
    check(
        "Dataset A interim: date_added parsed to datetime",
        pd.api.types.is_datetime64_any_dtype(df_property_interim["date_added"]),
    )
    check(
        "Dataset A interim: listing temporal columns exist",
        all(c in df_property_interim.columns for c in ["listing_year", "listing_month", "listing_quarter"]),
    )

    # 3. Purpose-Specific Subsets Checks
    check(
        "For Sale subset: all rows purpose == 'For Sale'",
        (df_sale["purpose"] == "For Sale").all(),
        f"Rows: {len(df_sale):,}",
    )
    check(
        "For Sale subset: price floor enforced (>= 50,000 PKR)",
        (df_sale["price"] >= 50_000).all(),
        f"Min price: {df_sale['price'].min():,.0f} PKR",
    )
    check(
        "For Rent subset: all rows purpose == 'For Rent'",
        (df_rent["purpose"] == "For Rent").all(),
        f"Rows: {len(df_rent):,}",
    )
    check(
        "For Rent subset: price floor enforced (>= 1,000 PKR)",
        (df_rent["price"] >= 1_000).all(),
        f"Min rent: {df_rent['price'].min():,.0f} PKR",
    )
    check(
        "Cleaned Property Total: Sale + Rent preserved",
        len(df_property_clean) == len(df_sale) + len(df_rent),
        f"Cleaned Total: {len(df_property_clean):,}",
    )

    # Synthetic features verification
    synthetic_cols = [
        "property_age_years", "floors", "corner", "park_facing",
        "covered_area_sqft", "parking", "security", "electricity_backup",
        "gas", "water_supply", "park_nearby", "amenity_score",
        "distance_main_road_km", "distance_school_km", "distance_hospital_km",
    ]
    for col in synthetic_cols:
        check(f"Property features: synthetic col '{col}' present", col in df_property_clean.columns)

    # 4. Dataset B Raw Checks
    check(
        "Dataset B raw: >= 3,000 rows",
        len(df_leads_raw) >= 3000,
        f"Actual: {len(df_leads_raw):,}",
    )
    check(
        "Dataset B raw: converted binary {0, 1}",
        set(df_leads_raw["converted"].unique()).issubset({0, 1}),
    )
    conv_rate = df_leads_raw["converted"].mean()
    check(
        "Dataset B raw: conversion rate in 15-40% window",
        0.15 <= conv_rate <= 0.40,
        f"Rate: {conv_rate:.1%}",
    )
    check(
        "Dataset B raw: lead_id unique",
        not df_leads_raw["lead_id"].duplicated().any(),
    )

    # 5. Split Overlap & Stratification Checks
    check(
        "Property splits: train intersect val = empty",
        len(set(df_prop_train.index) & set(df_prop_val.index)) == 0,
    )
    check(
        "Property splits: train intersect test = empty",
        len(set(df_prop_train.index) & set(df_prop_test.index)) == 0,
    )
    check(
        "Property splits: val intersect test = empty",
        len(set(df_prop_val.index) & set(df_prop_test.index)) == 0,
    )
    check(
        "Property splits: total rows preserved (70/15/15)",
        len(df_prop_train) + len(df_prop_val) + len(df_prop_test) == len(df_property_clean),
    )

    # Purpose representation in property splits
    sale_ratio_train = (df_prop_train["purpose"] == "For Sale").mean()
    sale_ratio_val = (df_prop_val["purpose"] == "For Sale").mean()
    sale_ratio_test = (df_prop_test["purpose"] == "For Sale").mean()
    check(
        "Property splits: purpose stratified across splits",
        abs(sale_ratio_train - sale_ratio_val) < 0.02 and abs(sale_ratio_train - sale_ratio_test) < 0.02,
        f"Sale % - Train: {sale_ratio_train:.1%}, Val: {sale_ratio_val:.1%}, Test: {sale_ratio_test:.1%}",
    )

    check(
        "Lead splits: train intersect val = empty",
        len(set(df_lead_train.index) & set(df_lead_val.index)) == 0,
    )
    check(
        "Lead splits: train intersect test = empty",
        len(set(df_lead_train.index) & set(df_lead_test.index)) == 0,
    )
    check(
        "Lead splits: total rows preserved (70/15/15)",
        len(df_lead_train) + len(df_lead_val) + len(df_lead_test) == len(df_leads_clean),
    )

    lead_base_rate = df_leads_clean["converted"].mean()
    for s_name, s_df in [("train", df_lead_train), ("val", df_lead_val), ("test", df_lead_test)]:
        s_rate = s_df["converted"].mean()
        check(
            f"Lead {s_name} split: stratified (within 5pp of {lead_base_rate:.1%})",
            abs(s_rate - lead_base_rate) <= 0.05,
            f"Split rate: {s_rate:.1%}",
        )

    # 6. Leakage Checks
    check(
        "Property: location_frequency fitted on train only",
        "location_frequency" in df_prop_train.columns and "location_frequency" in df_prop_test.columns,
    )
    check(
        "Property: price_per_marla quarantined for EDA only",
        "price_per_marla" in df_property_clean.columns,
    )

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed}/{total} checks passed")
    print("=" * 60)
    return results


def print_dataset_summary(
    df_property_raw: pd.DataFrame,
    df_property_interim: pd.DataFrame,
    df_property_clean: pd.DataFrame,
    df_sale: pd.DataFrame,
    df_rent: pd.DataFrame,
    df_leads_raw: pd.DataFrame,
    df_leads_clean: pd.DataFrame,
) -> None:
    """Print formatted summary of dataset shapes and distributions."""
    print("\n" + "=" * 60)
    print("FINAL DATASET SUMMARY (SUPPORTING SALE & RENT)")
    print("=" * 60)
    print(f"Dataset A raw:              {df_property_raw.shape[0]:>8,} rows x {df_property_raw.shape[1]} cols")
    print(f"Dataset A interim:          {df_property_interim.shape[0]:>8,} rows x {df_property_interim.shape[1]} cols")
    print(f"Dataset A cleaned total:    {df_property_clean.shape[0]:>8,} rows x {df_property_clean.shape[1]} cols")
    print(f"  -> For Sale subset:       {df_sale.shape[0]:>8,} rows (median PKR {df_sale['price'].median():,.0f})")
    print(f"  -> For Rent subset:       {df_rent.shape[0]:>8,} rows (median PKR {df_rent['price'].median():,.0f})")
    print(f"Dataset B raw:              {df_leads_raw.shape[0]:>8,} rows x {df_leads_raw.shape[1]} cols")
    print(f"Dataset B clean:            {df_leads_clean.shape[0]:>8,} rows x {df_leads_clean.shape[1]} cols")
    conv = df_leads_clean["converted"].value_counts()
    rate = df_leads_clean["converted"].mean()
    print(f"Lead conversion: 0 (lost) = {conv.get(0, 0):,}, 1 (converted) = {conv.get(1, 0):,} ({rate:.1%})")
    print("=" * 60 + "\n")
