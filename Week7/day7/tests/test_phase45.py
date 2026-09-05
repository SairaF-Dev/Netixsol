from __future__ import annotations

import json

from ml.build_dataset import build_dataset, resolve_outcomes
from ml.feature_engineering import engineer_features
from ml.readiness import readiness, summarize_rows


def base_row(customer="c1", property_id="p1", action="liked"):
    return {
        "customer_id": customer, "property_id": property_id, "action": action,
        "preferred_city": "Lahore", "preferred_area": "DHA", "budget_max": 30_000_000,
        "preferred_bedrooms": 3, "preferred_property_type": "Apartment",
        "preferred_purpose": "buy", "preferred_amenities": ["parking"],
        "city": "Lahore", "area": "DHA", "price": 25_000_000, "bedrooms": 3,
        "property_type": "Apartment", "purpose": "buy", "property_amenities": ["parking"],
    }


def test_historical_snapshots_override_latest_profile_values():
    row = base_row()
    row["preferred_city"] = "Karachi"
    row["budget_max"] = 40_000_000
    row["preference_snapshot"] = {
        "city": "Lahore", "area": "DHA", "budget_min": None, "budget_max": 30_000_000,
        "bedrooms": 3, "property_type": "Apartment", "purpose": "buy", "amenities": ["parking"],
    }
    row["property_snapshot"] = {
        "property_id": "p1", "city": "Lahore", "area": "DHA", "price": 20_000_000,
        "bedrooms": 3, "property_type": "Apartment", "purpose": "buy", "amenities": ["parking"],
    }
    resolved = resolve_outcomes([row])
    assert resolved[0]["snapshot_source"] == "historical"
    assert resolved[0]["budget_max"] == 30_000_000
    assert resolved[0]["price"] == 20_000_000


def test_legacy_rows_use_latest_profile_fallback():
    resolved = resolve_outcomes([base_row()])
    assert resolved[0]["snapshot_source"] == "latest_profile_fallback"


def test_snapshot_fields_contain_no_pii():
    row = base_row()
    row["preference_snapshot"] = {"city": "Lahore", "budget_max": 30_000_000}
    row["property_snapshot"] = {"property_id": "p1", "city": "Lahore", "price": 1}
    serialized = json.dumps(row["preference_snapshot"] + row["property_snapshot"] if isinstance(row["preference_snapshot"], list) else {**row["preference_snapshot"], **row["property_snapshot"]})
    assert all(value not in serialized for value in ("email", "phone", "full_name", "customer_id"))


def test_readiness_thresholds_and_summary_are_separate():
    rows = [base_row(f"c{i}", f"p{i}", "liked") for i in range(10)]
    rows += [base_row(f"c{i}", f"n{i}", "rejected") for i in range(10)]
    dataset = build_dataset(rows)
    assert readiness(dataset, min_rows=10, min_customers=10)["training_ready"] is True
    assert readiness(dataset, min_rows=50, min_customers=10)["training_ready"] is False
    summary = summarize_rows(rows, synthetic=True)
    assert summary["synthetic"] is True
    assert summary["positives"] == 10
    assert summary["negatives"] == 10


def test_snapshot_source_is_not_a_model_feature():
    row = base_row()
    row["snapshot_source"] = "historical"
    assert "snapshot_source" not in engineer_features(row)