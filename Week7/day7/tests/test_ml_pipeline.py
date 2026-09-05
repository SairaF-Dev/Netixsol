from __future__ import annotations

import json

import numpy as np
import pytest

from ml import FEATURE_NAMES
from ml.build_dataset import build_dataset, resolve_outcomes
from ml.feature_engineering import engineer_features
from ml.model_types import InsufficientTrainingData
from ml.train_model import grouped_split, train_candidate


def row(customer_id: str, property_id: str, action: str, **overrides):
    value = {
        "customer_id": customer_id,
        "property_id": property_id,
        "action": action,
        "city": "Lahore",
        "area": "DHA",
        "preferred_city": "Lahore",
        "preferred_area": "DHA",
        "price": 25_000_000,
        "budget_max": 30_000_000,
        "bedrooms": 3,
        "preferred_bedrooms": 3,
        "property_type": "Apartment",
        "preferred_property_type": "Apartment",
        "purpose": "buy",
        "preferred_purpose": "buy",
        "preferred_amenities": ["parking", "gym"],
        "property_amenities": ["parking"],
    }
    value.update(overrides)
    return value


def balanced_rows():
    rows = []
    for index in range(4):
        rows.extend([
            row(f"customer-{index}", f"positive-{index}", "shown"),
            row(f"customer-{index}", f"positive-{index}", "liked"),
            row(f"customer-{index}", f"negative-{index}", "rejected"),
        ])
    return rows


def test_label_policy_ignores_non_outcomes_and_resolves_duplicates():
    resolved = resolve_outcomes([
        row("c", "p", "shown"),
        row("c", "p", "viewed"),
        row("c", "p", "liked"),
        row("c", "p", "shortlisted"),
        row("c", "p", "appointment_booked"),
    ])
    assert len(resolved) == 1
    assert resolved[0]["target"] == 1
    assert resolve_outcomes([row("c", "p", "liked"), row("c", "p", "rejected")])[0]["target"] == 0


def test_feature_definitions_are_finite_and_expected():
    features = engineer_features(row("c", "p", "liked"))
    assert tuple(features) == FEATURE_NAMES
    assert features["city_match"] == 1.0
    assert features["area_match"] == 1.0
    assert features["budget_match"] == 1.0
    assert features["price_difference"] == -5_000_000
    assert features["price_difference_ratio"] == pytest.approx(-1 / 6)
    assert features["bedrooms_match"] == 1.0
    assert features["property_type_match"] == 1.0
    assert features["purpose_match"] == 1.0
    assert features["amenity_match_ratio"] == 0.5
    assert np.isfinite(list(features.values())).all()


def test_missing_or_zero_budget_uses_safe_neutral_values():
    features = engineer_features(row("c", "p", "liked", budget_max=0, price=None, preferred_bedrooms=None))
    assert features["price_difference"] == 0.0
    assert features["price_difference_ratio"] == 0.0
    assert features["bedroom_difference"] == 0.0
    assert features["amenity_match_ratio"] == 0.5


def test_dataset_excludes_identifiers_from_model_features():
    dataset = build_dataset(balanced_rows())
    assert "customer_id" not in dataset.feature_names
    assert "property_id" not in dataset.feature_names
    assert dataset.features.shape == (8, len(FEATURE_NAMES))


def test_grouped_split_has_disjoint_customers():
    dataset = build_dataset(balanced_rows())
    train, test = grouped_split(dataset)
    assert set(dataset.groups[train]).isdisjoint(set(dataset.groups[test]))


def test_single_class_and_single_customer_fail_gracefully():
    with pytest.raises(InsufficientTrainingData):
        build_dataset([row("c", "p", "shown"), row("c", "p", "liked")])
    dataset = build_dataset([row("c", "p1", "liked"), row("c", "p2", "rejected")])
    with pytest.raises(InsufficientTrainingData, match="two customers"):
        grouped_split(dataset)


def test_logistic_regression_fit_and_artifact_round_trip(tmp_path):
    dataset = build_dataset(balanced_rows())
    artifact_path = tmp_path / "property_ranker_v1.joblib"
    artifact = train_candidate(dataset, artifact_path)
    assert artifact_path.exists()
    assert artifact["feature_names"] == list(FEATURE_NAMES)
    assert set(artifact["coefficients"]) == set(FEATURE_NAMES)
    assert set(artifact["metrics"]) >= {"accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix"}

    import joblib
    loaded = joblib.load(artifact_path)
    assert loaded["model_version"] == "property_ranker_v1"
    assert loaded["model"].predict_proba(dataset.features[:1]).shape == (1, 2)