from __future__ import annotations

from types import SimpleNamespace

import joblib
import numpy as np
import pytest

from ml import FEATURE_NAMES
from ml.model_service import ModelValidationError, PropertyPreferenceModelService


class FakeModel:
    def __init__(self, probabilities=(0.2, 0.8)):
        self.probabilities = probabilities
        self.inputs = []

    def predict_proba(self, features):
        self.inputs.append(features)
        return np.asarray([[1 - p, p] for p in self.probabilities[: len(features)]])


class BrokenModel:
    def predict_proba(self, features):
        raise RuntimeError("broken")


class MalformedModel:
    def __init__(self, output):
        self.output = output

    def predict_proba(self, features):
        return np.asarray(self.output)


def artifact(model=None, **overrides):
    result = {
        "model": model or FakeModel(),
        "model_version": "property_ranker_v1",
        "synthetic": True,
        "data_source": "synthetic_development",
        "feature_names": list(FEATURE_NAMES),
    }
    result.update(overrides)
    return result


def candidates():
    return [
        {"property_id": "p1", "name": "One", "price": 10, "city": "Lahore", "area": "DHA", "bedrooms": 3, "property_type": "Apartment", "purpose": "Purchase", "amenities": ["parking"], "available": True},
        {"property_id": "p2", "name": "Two", "price": 20, "city": "Lahore", "area": "Gulberg", "bedrooms": 2, "property_type": "House", "purpose": "Purchase", "amenities": [], "available": True},
    ]


PROFILE = SimpleNamespace(city="Lahore", area="DHA", budget=15, bedrooms=3, property_type="Apartment", purpose="Purchase", amenities_preferred=["parking"])


def test_off_mode_does_not_load_or_change_order(tmp_path):
    service = PropertyPreferenceModelService(tmp_path / "missing.joblib", mode="off")
    original = candidates()
    assert service.rank_properties(original, PROFILE) is original
    assert service.health()["available"] is False


def test_valid_artifact_load_and_probability(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(), path)
    service = PropertyPreferenceModelService(path, mode="shadow")
    probability = service.score_property(PROFILE, candidates()[0])
    assert 0 <= probability <= 1
    assert service.health()["available"] is True


@pytest.mark.parametrize("bad_artifact", [
    {},
    artifact(model_version="wrong"),
    artifact(synthetic=False),
    artifact(data_source="production"),
    artifact(feature_names=list(reversed(FEATURE_NAMES))),
    artifact(model=object()),
])
def test_invalid_artifact_fails_validation(tmp_path, bad_artifact):
    path = tmp_path / "bad.joblib"
    joblib.dump(bad_artifact, path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    with pytest.raises(ModelValidationError):
        service.load_model()


def test_missing_and_corrupt_artifacts_fail_safely(tmp_path):
    missing = PropertyPreferenceModelService(tmp_path / "missing.joblib", mode="active_dev")
    assert [item["property_id"] for item in missing.rank_properties(candidates(), PROFILE)] == ["p1", "p2"]
    corrupt_path = tmp_path / "corrupt.joblib"
    corrupt_path.write_text("not a joblib", encoding="ascii")
    corrupt = PropertyPreferenceModelService(corrupt_path, mode="active_dev")
    assert [item["property_id"] for item in corrupt.rank_properties(candidates(), PROFILE)] == ["p1", "p2"]


def test_shadow_preserves_deterministic_order_and_adds_internal_comparison(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(FakeModel((0.2, 0.8))), path)
    service = PropertyPreferenceModelService(path, mode="shadow")
    original = candidates()
    ranked = service.rank_properties(original, PROFILE)
    assert ranked is original
    assert [item["property_id"] for item in ranked] == ["p1", "p2"]
    assert service.last_comparison == [
        {"property_id": "p1", "deterministic_rank": 1, "ml_rank": 2, "ml_probability": 0.2},
        {"property_id": "p2", "deterministic_rank": 2, "ml_rank": 1, "ml_probability": 0.8},
    ]
    assert all(set(item) == {"property_id", "deterministic_rank", "ml_rank", "ml_probability"} for item in service.last_comparison)


def test_active_dev_reorders_but_preserves_facts(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(FakeModel((0.2, 0.8))), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    original = candidates()
    original_facts = [dict(item) for item in original]
    ranked = service.rank_properties(original, PROFILE)
    assert [item["property_id"] for item in ranked] == ["p2", "p1"]
    for item in ranked:
        before = next(row for row in original_facts if row["property_id"] == item["property_id"])
        for field in ("property_id", "name", "price", "city", "area", "bedrooms", "property_type", "purpose", "amenities", "available"):
            assert item[field] == before[field]
    assert all(not any(str(key).startswith("_ml") for key in item) for item in ranked)


def test_prediction_failure_returns_original_candidates(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(BrokenModel()), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    original = candidates()
    assert service.rank_properties(original, PROFILE) is original


def test_model_input_reuses_feature_order_and_excludes_identifiers(tmp_path):
    model = FakeModel((0.5,))
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(model), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    service.score_property(PROFILE, {**candidates()[0], "customer_id": "secret", "property_id": "p1"})
    loaded_model = service.load_model()["model"]
    assert loaded_model.inputs[0].shape == (1, len(FEATURE_NAMES))
    assert service.load_model()["feature_names"] == list(FEATURE_NAMES)


@pytest.mark.parametrize("configured", ["", "ACTIVE", "production", "true"])
def test_invalid_mode_safely_defaults_to_off(configured):
    assert PropertyPreferenceModelService(mode=configured).mode == "off"


def test_missing_mode_environment_defaults_to_off(monkeypatch):
    monkeypatch.delenv("SARA_ML_RANKING_MODE", raising=False)
    assert PropertyPreferenceModelService().mode == "off"


@pytest.mark.parametrize("output", [
    [[0.5, 0.5]],
    [0.5, 0.5],
    [[0.2], [0.8]],
    [[0.8, 0.2], [0.2, float("nan")]],
    [[0.8, 0.2], [0.2, float("inf")]],
    [[0.8, 0.2], [-0.1, 1.1]],
])
def test_malformed_predictions_fall_back_to_deterministic(tmp_path, output):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(MalformedModel(output)), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    original = candidates()
    assert service.rank_properties(original, PROFILE) is original
    assert service.last_comparison == []


def test_feature_engineering_exception_falls_back(tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    monkeypatch.setattr("ml.model_service.engineer_features", lambda row: (_ for _ in ()).throw(ValueError("bad features")))
    original = candidates()
    assert service.rank_properties(original, PROFILE) is original


def test_non_finite_feature_falls_back(tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    monkeypatch.setattr("ml.model_service.engineer_features", lambda row: {name: (float("nan") if name == FEATURE_NAMES[0] else 0.0) for name in FEATURE_NAMES})
    original = candidates()
    assert service.rank_properties(original, PROFILE) is original


def test_batch_prediction_alignment_and_probability_contract(tmp_path):
    model = FakeModel((0.1, 0.9))
    path = tmp_path / "model.joblib"
    joblib.dump(artifact(model), path)
    service = PropertyPreferenceModelService(path, mode="active_dev")
    ranked = service.rank_properties(candidates(), PROFILE)
    assert [item["property_id"] for item in ranked] == ["p2", "p1"]
    loaded_model = service.load_model()["model"]
    assert loaded_model.inputs[0].shape == (2, len(FEATURE_NAMES))
    assert len(service.last_comparison) == 2
    assert all(0.0 <= row["ml_probability"] <= 1.0 for row in service.last_comparison)
