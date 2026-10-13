"""
test_day1_pipeline.py
---------------------
Automated test suite for Day 1 ML pipeline requirements supporting BOTH
'For Sale' and 'For Rent' property valuation and lead scoring.
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load_data import load_property_raw, load_leads_raw
from src.data.generate_leads import generate_leads
from src.data.clean_properties import clean_properties, _parse_area
from src.data.clean_leads import clean_leads
from src.features.property_features import (
    add_synthetic_features,
    add_engineered_features,
    split_property_data,
    extract_purpose_splits,
    apply_location_frequency_encoding,
    build_property_pipeline,
    ML_NUMERIC_COLS,
    ML_LOW_CARD_CATS,
    EXCLUDED_ML_COLS,
)
from src.features.lead_features import (
    add_lead_features,
    split_leads_data,
    apply_location_frequency_lead,
    build_lead_pipeline,
    TARGET as LEAD_TARGET,
)

RANDOM_STATE = 42


@pytest.fixture(scope="module")
def property_raw():
    return load_property_raw()


@pytest.fixture(scope="module")
def property_cleaned(property_raw):
    interim, clean, sale, rent = clean_properties(property_raw)
    return interim, clean, sale, rent


@pytest.fixture(scope="module")
def property_with_features(property_cleaned):
    _, clean, _, _ = property_cleaned
    clean = add_synthetic_features(clean, seed=RANDOM_STATE)
    clean = add_engineered_features(clean)
    return clean


@pytest.fixture(scope="module")
def leads_raw():
    return generate_leads(n=1000, seed=RANDOM_STATE)


@pytest.fixture(scope="module")
def leads_with_features(leads_raw):
    clean = clean_leads(leads_raw)
    return add_lead_features(clean)


# ==============================================================================
# Tests: Task 1 & 2 - Data Integrity & Cleaning (Sale & Rent)
# ==============================================================================

class TestPropertyCleaningSaleAndRent:
    def test_property_raw_dimensions(self, property_raw):
        assert len(property_raw) >= 5000, "Dataset A must contain >= 5,000 rows"
        assert len(property_raw.columns) == 31, "Raw Property.csv must preserve all 31 columns"

    def test_property_raw_unique_ids(self, property_raw):
        assert not property_raw["property_id"].duplicated().any()

    def test_area_parsing_kanal_to_marla(self):
        sample_df = pd.DataFrame({"area": ["1 Kanal", "2 Kanal", "0.5 Kanal", "5 Marla", "10 Marla"]})
        parsed = _parse_area(sample_df)
        assert parsed.loc[0, "area_marla"] == pytest.approx(20.0)
        assert parsed.loc[1, "area_marla"] == pytest.approx(40.0)
        assert parsed.loc[2, "area_marla"] == pytest.approx(10.0)
        assert parsed.loc[3, "area_marla"] == pytest.approx(5.0)
        assert parsed.loc[4, "area_marla"] == pytest.approx(10.0)

    def test_unnamed_columns_removed_from_interim(self, property_cleaned):
        interim, _, _, _ = property_cleaned
        unnamed = [c for c in interim.columns if c.startswith("Unnamed")]
        assert len(unnamed) == 0

    def test_for_sale_cleaning(self, property_cleaned):
        _, _, sale, _ = property_cleaned
        assert (sale["purpose"] == "For Sale").all()
        assert (sale["price"] >= 50000).all(), "Sale price floor >= 50k PKR"
        assert len(sale) == 126666

    def test_for_rent_cleaning(self, property_cleaned):
        _, _, _, rent = property_cleaned
        assert (rent["purpose"] == "For Rent").all()
        assert (rent["price"] >= 1000).all(), "Rent price floor >= 1k PKR"
        assert len(rent) == 64161

    def test_total_cleaned_properties(self, property_cleaned):
        _, clean, sale, rent = property_cleaned
        assert len(clean) == len(sale) + len(rent)
        assert len(clean) == 190827

    def test_residential_bedrooms_imputed(self, property_cleaned):
        _, clean, _, _ = property_cleaned
        residential = clean[clean["property_type"].isin(["House", "Flat", "Upper Portion", "Lower Portion"])]
        assert (residential["bedrooms"] > 0).all()
        assert (residential["baths"] > 0).all()


# ==============================================================================
# Tests: Task 1 & 2 - Lead Generation & Cleaning
# ==============================================================================

class TestLeadGeneration:
    def test_leads_volume(self, leads_raw):
        assert len(leads_raw) >= 1000

    def test_leads_target_binary(self, leads_raw):
        assert set(leads_raw["converted"].unique()).issubset({0, 1})

    def test_leads_conversion_rate(self, leads_raw):
        rate = leads_raw["converted"].mean()
        assert 0.15 <= rate <= 0.35, f"Conversion rate {rate:.1%} must be in realistic range"

    def test_leads_no_negative_budget(self, leads_raw):
        assert (leads_raw["budget_pkr"] > 0).all()

    def test_leads_unique_ids(self, leads_raw):
        assert not leads_raw["lead_id"].duplicated().any()


# ==============================================================================
# Tests: Task 4 - Feature Engineering & Provenance
# ==============================================================================

class TestFeatureEngineering:
    def test_all_synthetic_property_features_present(self, property_with_features):
        expected_synthetic = [
            "property_age_years", "floors", "corner", "park_facing",
            "covered_area_sqft", "parking", "security", "electricity_backup",
            "gas", "water_supply", "park_nearby", "amenity_score",
            "distance_main_road_km", "distance_school_km", "distance_hospital_km"
        ]
        for col in expected_synthetic:
            assert col in property_with_features.columns, f"Missing synthetic feature: {col}"

    def test_amenity_score_bounded(self, property_with_features):
        assert property_with_features["amenity_score"].between(0, 6).all()

    def test_corner_and_park_facing_binary(self, property_with_features):
        assert set(property_with_features["corner"].unique()).issubset({0, 1})
        assert set(property_with_features["park_facing"].unique()).issubset({0, 1})

    def test_lead_engineered_features_present(self, leads_with_features):
        expected = ["engagement_score", "avg_call_duration_min", "lead_age_bucket", "response_speed_category", "follow_up_intensity"]
        for col in expected:
            assert col in leads_with_features.columns, f"Missing engineered lead feature: {col}"


# ==============================================================================
# Tests: Leakage Safeguards
# ==============================================================================

class TestLeakageSafeguards:
    def test_price_per_marla_not_in_ml_features(self):
        assert "price_per_marla" not in ML_NUMERIC_COLS
        assert "price_per_marla" not in ML_LOW_CARD_CATS
        assert "price_per_marla" in EXCLUDED_ML_COLS

    def test_identifiers_not_in_ml_features(self):
        for identifier in ["property_id", "location_id", "page_url", "agency", "agent"]:
            assert identifier not in ML_NUMERIC_COLS
            assert identifier not in ML_LOW_CARD_CATS

    def test_lead_id_and_target_not_in_lead_features(self):
        from src.features.lead_features import NUMERIC_COLS, CAT_COLS
        assert "lead_id" not in NUMERIC_COLS and "lead_id" not in CAT_COLS
        assert "converted" not in NUMERIC_COLS and "converted" not in CAT_COLS


# ==============================================================================
# Tests: Task 5 - Splitting & Preprocessing
# ==============================================================================

class TestSplittingAndPipelines:
    def test_property_split_zero_overlap(self, property_with_features):
        train, val, test = split_property_data(property_with_features, seed=RANDOM_STATE)
        assert len(set(train.index) & set(val.index)) == 0
        assert len(set(train.index) & set(test.index)) == 0
        assert len(set(val.index) & set(test.index)) == 0
        assert len(train) + len(val) + len(test) == len(property_with_features)

    def test_property_split_stratified_purpose(self, property_with_features):
        train, val, test = split_property_data(property_with_features, seed=RANDOM_STATE)
        overall_sale_ratio = (property_with_features["purpose"] == "For Sale").mean()
        assert abs((train["purpose"] == "For Sale").mean() - overall_sale_ratio) < 0.01
        assert abs((val["purpose"] == "For Sale").mean() - overall_sale_ratio) < 0.01
        assert abs((test["purpose"] == "For Sale").mean() - overall_sale_ratio) < 0.01

    def test_lead_split_stratified(self, leads_with_features):
        train, val, test = split_leads_data(leads_with_features, seed=RANDOM_STATE)
        base_rate = leads_with_features[LEAD_TARGET].mean()
        assert abs(train[LEAD_TARGET].mean() - base_rate) <= 0.05
        assert abs(val[LEAD_TARGET].mean() - base_rate) <= 0.05
        assert abs(test[LEAD_TARGET].mean() - base_rate) <= 0.05

    def test_dual_property_pipeline_fit_transform(self, property_with_features):
        train, val, test = split_property_data(property_with_features, seed=RANDOM_STATE)
        train, val, test = apply_location_frequency_encoding(train, val, test)
        (train_sale, val_sale, test_sale), (train_rent, val_rent, test_rent) = extract_purpose_splits(train, val, test)

        sale_pipe = build_property_pipeline(purpose="sale", scaler="robust")
        X_sale_train = sale_pipe.fit_transform(train_sale)
        X_sale_val = sale_pipe.transform(val_sale)
        assert X_sale_train.shape[0] == len(train_sale)
        assert X_sale_val.shape[0] == len(val_sale)

        rent_pipe = build_property_pipeline(purpose="rent", scaler="robust")
        X_rent_train = rent_pipe.fit_transform(train_rent)
        X_rent_val = rent_pipe.transform(val_rent)
        assert X_rent_train.shape[0] == len(train_rent)
        assert X_rent_val.shape[0] == len(val_rent)

    def test_lead_pipeline_fit_transform(self, leads_with_features):
        train, val, test = split_leads_data(leads_with_features, seed=RANDOM_STATE)
        train, val, test = apply_location_frequency_lead(train, val, test)
        pipeline = build_lead_pipeline(scaler="standard")
        X_train_trans = pipeline.fit_transform(train)
        X_val_trans = pipeline.transform(val)
        assert X_train_trans.shape[0] == len(train)
        assert X_val_trans.shape[0] == len(val)


if __name__ == "__main__":
    result = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(result)
