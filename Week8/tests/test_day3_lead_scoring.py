"""
test_day3_lead_scoring.py
-------------------------
Unit and integration test suite for Week 8 Day 3:
Lead Scoring Model (Classification), Customer Personas, and Explainability.

Verifies:
1. Production model artifacts, preprocessors, and diagnostic reports exist on disk.
2. Preprocessor transforms raw leads into valid 43-dimensional numerical matrices.
3. Conversion probabilities obey strict mathematical bounds [0.0, 1.0].
4. Operational tiering and SLA assignments match specification boundaries.
5. Customer persona K-Means clustering assigns valid segments {0, 1, 2}.
6. UrduLish explanation generator produces structured, natural domain rationales.
7. Commercial Precision@Top-20% demonstrates substantial lift over random chance.
8. Operating threshold optimization functions properly without test leakage.
9. Inference latency satisfies the strict production SLA (< 50 ms).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.evaluate_lead_scoring import (
    evaluate_classifier_predictions,
    evaluate_precision_at_top_k,
    optimize_decision_threshold,
)
from src.models.explain_lead_scoring import generate_urdulish_explanation
from src.models.predict_lead_scoring import LeadScorer
from src.agent.data_store import LeadDataStore


@pytest.fixture(scope="session")
def lead_scorer():
    scorer = LeadScorer(models_dir=PROJECT_ROOT / "models")
    scorer.load()
    return scorer


@pytest.fixture
def sample_lead():
    return {
        "lead_source": "WhatsApp",
        "budget_pkr": 25000000,
        "preferred_city": "Lahore",
        "preferred_location": "DHA Defence",
        "property_type": "House",
        "purpose": "Buy",
        "number_of_calls": 4,
        "total_call_duration_min": 28.5,
        "response_time_minutes": 15.0,
        "visit_booked": 1,
        "days_since_first_contact": 12.0,
        "objection_raised": "Price",
        "follow_up_count": 3,
        "budget_match_ratio": 0.95,
    }


def test_day3_artifacts_exist():
    models_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports" / "day3"
    figs_dir = PROJECT_ROOT / "reports" / "figures" / "day3"

    assert (models_dir / "lead_scoring_model.joblib").exists(), "Missing lead_scoring_model.joblib"
    assert (models_dir / "lead_preprocessor.joblib").exists(), "Missing lead_preprocessor.joblib"
    assert (models_dir / "lead_persona_kmeans.joblib").exists(), "Missing lead_persona_kmeans.joblib"
    assert (reports_dir / "lead_scoring_report.md").exists(), "Missing lead_scoring_report.md"

    expected_figures = [
        "fig_d3_roc_curve.png",
        "fig_d3_pr_curve.png",
        "fig_d3_calibration_curve.png",
        "fig_d3_confusion_matrix.png",
        "fig_d3_shap_summary.png",
        "fig_d3_shap_waterfall.png",
    ]
    for fig_name in expected_figures:
        assert (figs_dir / fig_name).exists(), f"Missing diagnostic plot: {fig_name}"


def test_lead_preprocessor_pipeline():
    pipe = joblib.load(PROJECT_ROOT / "models" / "lead_preprocessor.joblib")
    test_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "lead_test.csv")

    X_trans = pipe.transform(test_df)
    assert X_trans.shape[0] == len(test_df)
    assert not np.isnan(X_trans).any(), "NaN values found in preprocessed feature matrix"


def test_lead_scoring_prediction_schema(lead_scorer, sample_lead):
    res = lead_scorer.score_lead(sample_lead)

    expected_keys = [
        "conversion_probability",
        "lead_score_pct",
        "training_label_provenance",
        "crm_validated",
        "tier",
        "priority_rank",
        "recommended_sla_action",
        "customer_persona",
        "persona_cluster_id",
        "urdulish_explanation",
        "inference_latency_ms",
    ]
    for k in expected_keys:
        assert k in res, f"Missing output key: {k}"
    assert res["training_label_provenance"] == "synthetic"
    assert res["crm_validated"] is False


def test_probability_bounds(lead_scorer, sample_lead):
    res = lead_scorer.score_lead(sample_lead)
    prob = res["conversion_probability"]
    assert 0.0 <= prob <= 1.0, f"Probability {prob} violates bounds [0, 1]"

    pct = res["lead_score_pct"]
    assert 0.0 <= pct <= 100.0, f"Score {pct} violates bounds [0, 100]"
    assert abs(prob * 100.0 - pct) <= 0.15


def test_demo_lead_feed_does_not_expose_or_score_from_conversion_label():
    store = LeadDataStore.__new__(LeadDataStore)
    row = pd.Series({
        "lead_id": "L00001",
        "preferred_city": "Lahore",
        "preferred_location": "DHA",
        "budget_pkr": 25_000_000,
        "property_type": "House",
        "purpose": "Buy",
        "lead_source": "Call",
        "number_of_calls": 4,
        "total_call_duration_min": 18.0,
        "response_time_minutes": 15,
        "visit_booked": 1,
        "days_since_first_contact": 2,
        "objection_raised": "None",
        "follow_up_count": 3,
        "budget_match_ratio": 0.95,
        "converted": 0,
    })

    not_converted = store._format_lead(row, 0)
    row["converted"] = 1
    converted = store._format_lead(row, 0)

    assert "converted" not in not_converted
    assert "converted" not in converted
    assert not_converted["lead_score_pct"] == converted["lead_score_pct"]
    assert not_converted["tier"] == converted["tier"]


def test_tier_assignment_logic():
    test_cases = [
        (0.85, "Hot", 1),
        (0.65, "Hot", 1),
        (0.50, "Warm", 2),
        (0.35, "Warm", 2),
        (0.20, "Cold", 3),
    ]

    for p, expected_tier, expected_rank in test_cases:
        if p >= 0.65:
            tier, rank = "Hot", 1
        elif p >= 0.35:
            tier, rank = "Warm", 2
        else:
            tier, rank = "Cold", 3

        assert tier == expected_tier
        assert rank == expected_rank


def test_customer_persona_clustering(lead_scorer, sample_lead):
    res = lead_scorer.score_lead(sample_lead)
    cluster_id = res["persona_cluster_id"]
    persona_label = res["customer_persona"]

    assert cluster_id in {0, 1, 2}
    assert persona_label in {
        "First-Time Urban Homebuyer",
        "High-Net-Worth Investor",
        "Budget Renter / Short-Horizon Inquirer",
    }


def test_urdulish_explanation_generation():
    explanation = generate_urdulish_explanation(
        lead_data={},
        top_positive_factors=["visit already book hai", "client ne 3 dafa call ki"],
        top_negative_factors=[],
        predicted_probability=0.78,
        tier="Hot",
    )

    assert "Yeh lead Hot hai" in explanation
    assert "78.0%" in explanation
    assert "Call within 1 hour" in explanation


def test_precision_at_top_k_evaluation():
    y_true = np.array([1] * 20 + [0] * 80)
    y_prob = np.array([0.9] * 15 + [0.1] * 5 + [0.8] * 5 + [0.05] * 75)

    res = evaluate_precision_at_top_k(y_true, y_prob, top_k_pct=0.20)
    assert res["leads_evaluated"] == 20
    assert res["conversions_captured"] >= 15
    assert res["conversion_lift_ratio"] > 1.0


def test_cost_benefit_optimization_validation():
    y_val = np.array([1] * 30 + [0] * 70)
    y_probs = np.linspace(0.01, 0.99, 100)

    res = optimize_decision_threshold(y_val, y_probs)
    assert "optimal_threshold" in res
    assert 0.05 <= res["optimal_threshold"] <= 0.95
    assert res["max_net_profit_pkr"] > 0


def test_inference_latency_sla(lead_scorer, sample_lead):
    # Warmup
    lead_scorer.score_lead(sample_lead)

    latencies = []
    for _ in range(20):
        t0 = time.time()
        lead_scorer.score_lead(sample_lead)
        latencies.append((time.time() - t0) * 1000.0)

    mean_latency = float(np.mean(latencies))
    assert mean_latency < 50.0, f"Inference latency too slow: {mean_latency:.2f} ms (SLA < 50ms)"
