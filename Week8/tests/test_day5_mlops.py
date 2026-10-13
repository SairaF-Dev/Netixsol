"""Regression tests for drift monitoring and validation-gated model rollback."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.mlops.monitoring import build_drift_report, population_stability_index, run_monitoring
from src.mlops.retrain import promote_artifacts, rollback_artifacts, train_candidate


def test_psi_detects_a_simulated_fifteen_percent_price_shift():
    reference = pd.DataFrame({
        "area_marla": np.linspace(2, 20, 100),
        "price": np.linspace(1_000_000, 20_000_000, 100),
        "purpose": ["For Sale"] * 100,
    })
    shifted = reference.copy()
    shifted["price"] *= 1.15

    assert population_stability_index(reference["area_marla"], shifted["area_marla"]) == 0
    report = build_drift_report(reference, shifted, purpose="For Sale")
    assert report["status"] == "alert"
    assert "mape" not in [item["type"] for item in report["alerts"]]


def test_monitor_reports_performance_beyond_the_fifteen_percent_threshold():
    class ConstantLogModel:
        def predict(self, features):
            return np.log1p(np.full(len(features), 50.0))

    class IdentityPreprocessor:
        def transform(self, rows):
            assert "location_frequency" in rows.columns
            return rows[["area_marla"]].to_numpy()

    rows = pd.DataFrame({"area_marla": [10.0, 12.0], "price": [100.0, 120.0]})
    report = build_drift_report(
        rows,
        rows,
        purpose="For Sale",
        model=ConstantLogModel(),
        preprocessor=IdentityPreprocessor(),
    )
    assert report["mape_percent"] > 15
    assert any(alert["type"] == "mape" for alert in report["alerts"])


def test_promote_backs_up_artifacts_and_rollback_restores_pair(tmp_path: Path):
    candidate_model = tmp_path / "candidate-model.joblib"
    candidate_prep = tmp_path / "candidate-preprocessor.joblib"
    active_model = tmp_path / "sale_model_huber.joblib"
    active_prep = tmp_path / "sale_preprocessor_huber.joblib"
    candidate_model.write_bytes(b"new-model")
    candidate_prep.write_bytes(b"new-preprocessor")
    active_model.write_bytes(b"old-model")
    active_prep.write_bytes(b"old-preprocessor")

    backup = promote_artifacts(
        candidate_model,
        candidate_prep,
        active_model,
        active_prep,
        tmp_path / "rollback",
    )
    assert active_model.read_bytes() == b"new-model"
    assert active_prep.read_bytes() == b"new-preprocessor"

    rollback_artifacts(backup, "sale", tmp_path)
    assert active_model.read_bytes() == b"old-model"
    assert active_prep.read_bytes() == b"old-preprocessor"


def test_promotion_requires_both_candidate_artifacts(tmp_path: Path):
    active_model = tmp_path / "sale_model_huber.joblib"
    active_prep = tmp_path / "sale_preprocessor_huber.joblib"
    active_model.write_bytes(b"old-model")
    active_prep.write_bytes(b"old-preprocessor")
    candidate_model = tmp_path / "candidate-model.joblib"
    candidate_model.write_bytes(b"new-model")

    with pytest.raises(FileNotFoundError, match="Model promotion artifact"):
        promote_artifacts(
            candidate_model,
            tmp_path / "missing-preprocessor.joblib",
            active_model,
            active_prep,
            tmp_path / "rollback",
        )
    assert active_model.read_bytes() == b"old-model"
    assert active_prep.read_bytes() == b"old-preprocessor"


def test_retraining_rejects_unknown_purpose_before_reading_data(tmp_path: Path):
    with pytest.raises(ValueError, match="purpose must be sale or rent"):
        train_candidate("lease", tmp_path / "missing-train.csv", tmp_path / "missing-validation.csv")


@pytest.mark.parametrize("shift", [float("inf"), float("nan"), -0.1])
def test_monitoring_rejects_invalid_price_shift(tmp_path: Path, shift: float):
    with pytest.raises(ValueError, match="finite, non-negative"):
        run_monitoring(
            tmp_path / "missing-reference.csv",
            tmp_path / "missing-current.csv",
            tmp_path / "report.json",
            simulate_price_increase=shift,
        )
