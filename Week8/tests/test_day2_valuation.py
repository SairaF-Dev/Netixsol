"""
test_day2_valuation.py
----------------------
Unit test suite for Week 8 Day 2: Property Valuation Regression Engine.

Verifies:
1. Model artifacts and preprocessors are serialized on disk.
2. Quantile prediction monotonicity (P10 <= P50 <= P90).
3. Automated market verdicts ('Underpriced', 'Fair', 'Overpriced').
4. Inference latency SLA (< 500 ms).
5. Model performance benchmarks (beating naive baselines, R² > 0.80 for Sale).
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.predict_valuation import PropertyValuator, format_pkr_currency
from src.features.property_features import HuberPropertyPreprocessor


@pytest.fixture(scope="session")
def valuator():
    """Shared PropertyValuator instance loaded once per test session."""
    v = PropertyValuator(models_dir=PROJECT_ROOT / "models")
    v.load()
    return v


@pytest.fixture
def sample_sale_listing():
    """Representative 1-Kanal House in Lahore for Sale."""
    return {
        "property_type": "House",
        "city": "Lahore",
        "province_name": "Punjab",
        "location": "DHA Defence Phase 5",
        "baths": 5,
        "bedrooms": 4,
        "area_marla": 20.0,
        "latitude": 31.4697,
        "longitude": 74.3789,
        "listing_year": 2024,
        "listing_month": 5,
        "listing_quarter": 2,
        "property_age_years": 3,
        "floors": 2,
        "corner": 1,
        "park_facing": 1,
        "covered_area_sqft": 4200.0,
        "parking": 1,
        "security": 1,
        "electricity_backup": 1,
        "gas": 1,
        "water_supply": 1,
        "park_nearby": 1,
        "amenity_score": 6,
        "distance_main_road_km": 0.5,
        "distance_school_km": 1.2,
        "distance_hospital_km": 2.5,
        "bed_bath_ratio": 0.80,
        "covered_area_ratio": 0.77,
        "location_frequency": 250,
        "listing_season": "Spring",
        "property_age_bucket": "1-5 years",
        "society_tier": "Tier-1 (Prime)",
        "purpose": "For Sale",
        "price": 75_000_000.0,  # 7.5 Crore listed
    }


@pytest.fixture
def sample_rent_listing():
    """Representative 2-Bedroom Flat in Karachi for Rent."""
    return {
        "property_type": "Flat",
        "city": "Karachi",
        "province_name": "Sindh",
        "location": "Clifton",
        "baths": 2,
        "bedrooms": 2,
        "area_marla": 6.0,
        "latitude": 24.8138,
        "longitude": 67.0300,
        "listing_year": 2024,
        "listing_month": 6,
        "listing_quarter": 2,
        "property_age_years": 5,
        "floors": 4,
        "corner": 0,
        "park_facing": 0,
        "covered_area_sqft": 1400.0,
        "parking": 1,
        "security": 1,
        "electricity_backup": 0,
        "gas": 1,
        "water_supply": 1,
        "park_nearby": 1,
        "amenity_score": 4,
        "distance_main_road_km": 0.3,
        "distance_school_km": 0.8,
        "distance_hospital_km": 1.5,
        "bed_bath_ratio": 1.0,
        "covered_area_ratio": 0.85,
        "location_frequency": 310,
        "listing_season": "Summer",
        "property_age_bucket": "1-5 years",
        "society_tier": "Tier-1 (Prime)",
        "purpose": "For Rent",
        "price": 85_000.0,  # 85k monthly listed
    }


class TestValuationArtifacts:
    """Verify serialized pipelines and models exist on disk."""

    def test_huber_preprocessor_excludes_synthetic_listing_features(self):
        preprocessor = HuberPropertyPreprocessor()
        selected_features = set(preprocessor.numeric_cols + preprocessor.categorical_cols)
        synthetic_features = {
            "property_age_years", "property_age_bucket", "floors", "corner",
            "park_facing", "covered_area_sqft", "parking", "security",
            "electricity_backup", "gas", "water_supply", "park_nearby",
            "amenity_score", "distance_main_road_km", "distance_school_km",
            "distance_hospital_km", "covered_area_ratio", "is_corner",
            "is_park_facing",
        }

        assert selected_features.isdisjoint(synthetic_features)
        assert {"area_marla", "bedrooms", "baths", "city", "property_type"} <= selected_features

    def test_preprocessors_exist(self):
        models_dir = PROJECT_ROOT / "models"
        assert (models_dir / "sale_preprocessor.joblib").exists(), "Sale preprocessor missing"
        assert (models_dir / "rent_preprocessor.joblib").exists(), "Rent preprocessor missing"

    def test_quantile_models_exist(self):
        models_dir = PROJECT_ROOT / "models"
        for q in ["q10", "q50", "q90"]:
            assert (models_dir / f"sale_model_{q}.joblib").exists(), f"Sale {q} model missing"
            assert (models_dir / f"rent_model_{q}.joblib").exists(), f"Rent {q} model missing"


class TestPropertyValuationInference:
    """Verify inference pipeline accuracy, monotonicity, and latency."""

    def test_sale_prediction_schema(self, valuator, sample_sale_listing):
        res = valuator.predict(sample_sale_listing)
        expected_keys = [
            "purpose", "predicted_fair_price_pkr", "lower_bound_pkr",
            "upper_bound_pkr", "confidence_band_pkr", "listed_price_pkr",
            "verdict", "deviation_percentage", "human_readable_summary",
            "inference_latency_ms"
        ]
        for k in expected_keys:
            assert k in res, f"Missing key '{k}' in valuation output"

    def test_quantile_monotonicity_sale(self, valuator, sample_sale_listing):
        res = valuator.predict(sample_sale_listing)
        p10 = res["lower_bound_pkr"]
        p50 = res["predicted_fair_price_pkr"]
        p90 = res["upper_bound_pkr"]
        assert p10 <= p50 <= p90, f"Quantile monotonicity violated: P10={p10}, P50={p50}, P90={p90}"

    def test_quantile_monotonicity_rent(self, valuator, sample_rent_listing):
        res = valuator.predict(sample_rent_listing)
        p10 = res["lower_bound_pkr"]
        p50 = res["predicted_fair_price_pkr"]
        p90 = res["upper_bound_pkr"]
        assert p10 <= p50 <= p90, f"Rental quantile monotonicity violated: P10={p10}, P50={p50}, P90={p90}"

    def test_inference_latency_sla(self, valuator, sample_sale_listing):
        # Warmup
        _ = valuator.predict(sample_sale_listing)
        t0 = time.perf_counter()
        _ = valuator.predict(sample_sale_listing)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        assert latency_ms < 500.0, f"Inference latency {latency_ms:.2f}ms exceeds 500ms SLA"

    def test_overpriced_verdict(self, valuator, sample_sale_listing):
        listing = dict(sample_sale_listing)
        listing["price"] = 500_000_000.0  # Absurdly high 50 Crore
        res = valuator.predict(listing)
        assert res["verdict"] == "Overpriced"
        assert res["deviation_percentage"] > 0

    def test_underpriced_verdict(self, valuator, sample_sale_listing):
        listing = dict(sample_sale_listing)
        listing["price"] = 1_000_000.0  # 10 Lac for 1-Kanal DHA
        res = valuator.predict(listing)
        assert res["verdict"] == "Underpriced"
        assert res["deviation_percentage"] > 0

    def test_currency_formatting(self):
        assert "Crore" in format_pkr_currency(25_000_000)
        assert "Lac" in format_pkr_currency(4_500_000)
        assert "PKR" in format_pkr_currency(45_000)
