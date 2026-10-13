"""
run_day1_pipeline.py
--------------------
Master execution pipeline for Week 8 Day 1 supporting BOTH
For Sale and For Rent property valuation and lead scoring.

Usage:
  python run_day1_pipeline.py
"""

import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load_data import load_property_raw
from src.data.generate_leads import generate_leads, save_leads
from src.data.clean_properties import clean_properties
from src.data.clean_leads import clean_leads
from src.features.property_features import (
    add_synthetic_features,
    add_engineered_features,
    split_property_data,
    extract_purpose_splits,
    apply_location_frequency_encoding,
    apply_location_target_encoding,
    build_property_pipeline,
)
from src.features.lead_features import (
    add_lead_features,
    split_leads_data,
    apply_location_frequency_lead,
    build_lead_pipeline,
)
from src.utils.validation import run_all_checks, print_dataset_summary

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RANDOM_STATE = 42
DATA = PROJECT_ROOT / "data"


def main():
    print("=" * 60)
    print("WEEK 8 DAY 1: MASTER PIPELINE (FOR SALE & FOR RENT)")
    print("=" * 60)

    # 1. Lead Generation (Dataset B)
    print("\n[1/8] Generating / Verifying Dataset B (Inbound Leads)...")
    leads_raw_path = DATA / "raw" / "leads_raw.csv"
    if leads_raw_path.exists() and leads_raw_path.stat().st_size > 1000:
        df_leads_raw = pd.read_csv(leads_raw_path)
    else:
        df_leads_raw = generate_leads(n=5000, seed=RANDOM_STATE)
        save_leads(df_leads_raw, leads_raw_path)
    print(f"  -> Leads raw shape: {df_leads_raw.shape}, Conversion rate: {df_leads_raw['converted'].mean():.1%}")

    # 2. Raw Property Loading (Dataset A)
    print("\n[2/8] Loading Dataset A (Property.csv)...")
    df_property_raw = load_property_raw()
    print(f"  -> Property raw shape: {df_property_raw.shape}")

    # 3. Clean Properties (Sale & Rent)
    print("\n[3/8] Cleaning property listings for Sale and Rent...")
    df_prop_interim, df_prop_clean_base, df_sale_base, df_rent_base = clean_properties(df_property_raw)
    print(f"  -> Interim: {len(df_prop_interim):,} rows")
    print(f"  -> For Sale subset: {len(df_sale_base):,} rows (price >= 50,000 PKR)")
    print(f"  -> For Rent subset: {len(df_rent_base):,} rows (price >= 1,000 PKR)")
    print(f"  -> Total Cleaned: {len(df_prop_clean_base):,} rows")

    # 4. Feature Augmentation & Engineering (Dataset A)
    print("\n[4/8] Adding synthetic augmentation & derived features...")
    df_prop_clean = add_synthetic_features(df_prop_clean_base, seed=RANDOM_STATE)
    df_prop_clean = add_engineered_features(df_prop_clean)

    df_sale = df_prop_clean[df_prop_clean["purpose"] == "For Sale"].copy().reset_index(drop=True)
    df_rent = df_prop_clean[df_prop_clean["purpose"] == "For Rent"].copy().reset_index(drop=True)

    # Persist property datasets
    df_prop_interim.to_csv(DATA / "interim" / "properties_interim.csv", index=False)
    df_prop_clean.to_csv(DATA / "processed" / "properties_clean.csv", index=False)
    df_sale.to_csv(DATA / "processed" / "properties_sale_clean.csv", index=False)
    df_rent.to_csv(DATA / "processed" / "properties_rent_clean.csv", index=False)
    print(f"  -> Saved properties_interim.csv, properties_clean.csv, properties_sale_clean.csv, properties_rent_clean.csv")

    # 5. Clean Leads & Feature Engineering (Dataset B)
    print("\n[5/8] Cleaning leads & engineering behavioral features...")
    df_leads_clean = clean_leads(df_leads_raw)
    df_leads_enriched = add_lead_features(df_leads_clean)
    df_leads_enriched.to_csv(DATA / "interim" / "leads_interim.csv", index=False)
    df_leads_enriched.to_csv(DATA / "processed" / "leads_clean.csv", index=False)
    print(f"  -> Saved leads_interim.csv and leads_clean.csv")

    # 6. Splitting Datasets (70/15/15)
    print("\n[6/8] Splitting datasets (70% Train / 15% Val / 15% Test)...")
    p_train, p_val, p_test = split_property_data(df_prop_clean, seed=RANDOM_STATE)
    p_train, p_val, p_test = apply_location_frequency_encoding(p_train, p_val, p_test)
    p_train, p_val, p_test = apply_location_target_encoding(p_train, p_val, p_test)

    (p_sale_train, p_sale_val, p_sale_test), (p_rent_train, p_rent_val, p_rent_test) = extract_purpose_splits(
        p_train, p_val, p_test
    )

    l_train, l_val, l_test = split_leads_data(df_leads_enriched, seed=RANDOM_STATE)
    l_train, l_val, l_test = apply_location_frequency_lead(l_train, l_val, l_test)

    # Persist split datasets
    p_train.to_csv(DATA / "processed" / "prop_train.csv", index=False)
    p_val.to_csv(DATA / "processed" / "prop_val.csv", index=False)
    p_test.to_csv(DATA / "processed" / "prop_test.csv", index=False)

    p_sale_train.to_csv(DATA / "processed" / "prop_sale_train.csv", index=False)
    p_sale_val.to_csv(DATA / "processed" / "prop_sale_val.csv", index=False)
    p_sale_test.to_csv(DATA / "processed" / "prop_sale_test.csv", index=False)

    p_rent_train.to_csv(DATA / "processed" / "prop_rent_train.csv", index=False)
    p_rent_val.to_csv(DATA / "processed" / "prop_rent_val.csv", index=False)
    p_rent_test.to_csv(DATA / "processed" / "prop_rent_test.csv", index=False)

    l_train.to_csv(DATA / "processed" / "lead_train.csv", index=False)
    l_val.to_csv(DATA / "processed" / "lead_val.csv", index=False)
    l_test.to_csv(DATA / "processed" / "lead_test.csv", index=False)

    print(f"  -> Property Unified Splits: Train={len(p_train):,}, Val={len(p_val):,}, Test={len(p_test):,}")
    print(f"     * For Sale Splits:       Train={len(p_sale_train):,}, Val={len(p_sale_val):,}, Test={len(p_sale_test):,}")
    print(f"     * For Rent Splits:       Train={len(p_rent_train):,}, Val={len(p_rent_val):,}, Test={len(p_rent_test):,}")
    print(f"  -> Lead Splits:             Train={len(l_train):,}, Val={len(l_val):,}, Test={len(l_test):,}")

    # 7. Fit Reusable Preprocessing Pipelines
    print("\n[7/8] Fitting Scikit-learn ColumnTransformer Pipelines on Train folds...")
    sale_pipeline = build_property_pipeline(purpose="sale", scaler="robust")
    X_sale_train = sale_pipeline.fit_transform(p_sale_train)
    X_sale_val = sale_pipeline.transform(p_sale_val)
    print(f"  [OK] Sale Preprocessor fitted on train: output shape {X_sale_train.shape}")

    rent_pipeline = build_property_pipeline(purpose="rent", scaler="robust")
    X_rent_train = rent_pipeline.fit_transform(p_rent_train)
    X_rent_val = rent_pipeline.transform(p_rent_val)
    print(f"  [OK] Rent Preprocessor fitted on train: output shape {X_rent_train.shape}")

    lead_pipeline = build_lead_pipeline(scaler="standard")
    X_lead_train = lead_pipeline.fit_transform(l_train)
    X_lead_val = lead_pipeline.transform(l_val)
    print(f"  [OK] Lead Preprocessor fitted on train: output shape {X_lead_train.shape}")

    # 8. Validation Assertions & Summary
    print("\n[8/8] Executing automated pipeline validation checks...")
    results = run_all_checks(
        df_property_raw=df_property_raw,
        df_property_interim=df_prop_interim,
        df_property_clean=df_prop_clean,
        df_sale=df_sale,
        df_rent=df_rent,
        df_leads_raw=df_leads_raw,
        df_leads_clean=df_leads_enriched,
        df_prop_train=p_train,
        df_prop_val=p_val,
        df_prop_test=p_test,
        df_lead_train=l_train,
        df_lead_val=l_val,
        df_lead_test=l_test,
    )

    print_dataset_summary(
        df_property_raw=df_property_raw,
        df_property_interim=df_prop_interim,
        df_property_clean=df_prop_clean,
        df_sale=df_sale,
        df_rent=df_rent,
        df_leads_raw=df_leads_raw,
        df_leads_clean=df_leads_enriched,
    )

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    if passed == total:
        print(f"SUCCESS: All {passed}/{total} pipeline checks PASSED.")
    else:
        print(f"WARNING: {total - passed}/{total} checks FAILED.")
    return results


if __name__ == "__main__":
    main()
