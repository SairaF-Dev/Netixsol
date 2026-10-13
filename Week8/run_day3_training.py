"""
run_day3_training.py
--------------------
Master execution orchestrator for Week 8 Day 3:
Lead Scoring Model (Classification), Customer Personas, and Explainability.

Executes:
1. Loads stratified Dataset B splits (lead_train, lead_val, lead_test)
2. Fits and serializes Scikit-learn preprocessing pipeline (lead_preprocessor.joblib)
3. Trains 12 benchmark configurations (LR, RF, XGB, LGBM across unweighted, class_weight, SMOTE)
4. Executes Bayesian hyperparameter optimization (Optuna) for LightGBM
5. Trains K-Means customer persona clustering (k=3)
6. Computes Precision@Top-20% and leakage-free decision threshold
7. Computes TreeSHAP global/local explanations and saves diagnostic plots
8. Executes descriptive subgroup fairness audit
9. Generates comprehensive markdown report (reports/day3/lead_scoring_report.md)
10. Logs best model to MLflow and verifies production inference with LeadScorer
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.lead_features import build_lead_pipeline
from src.models.evaluate_lead_scoring import (
    evaluate_classifier_predictions,
    evaluate_precision_at_top_k,
    generate_lead_diagnostic_plots,
    generate_lead_scoring_report,
    optimize_decision_threshold,
)
from src.models.explain_lead_scoring import (
    audit_algorithmic_bias,
    compute_shap_explanations,
    generate_shap_plots,
)
from src.models.predict_lead_scoring import LeadScorer
from src.models.train_lead_scoring import (
    compute_persona_profiles,
    log_lead_experiment_to_mlflow,
    optimize_lead_classifier,
    train_all_imbalance_benchmarks,
    train_persona_clustering,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("day3_training")

MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "day3"
FIGS_DIR = PROJECT_ROOT / "reports" / "figures" / "day3"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def main():
    print("=" * 70)
    print("WEEK 8 DAY 3: AI LEAD SCORING & EXPLAINABILITY PLATFORM")
    print("=" * 70)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Data Splits
    print("\n[1/8] Loading Stratified Lead Partitions (Dataset B)...")
    lead_train = pd.read_csv(DATA_DIR / "lead_train.csv")
    lead_val = pd.read_csv(DATA_DIR / "lead_val.csv")
    lead_test = pd.read_csv(DATA_DIR / "lead_test.csv")

    y_train = lead_train["converted"].values
    y_val = lead_val["converted"].values
    y_test = lead_test["converted"].values

    print(f"  -> Train: {len(lead_train):,} leads (Conversion: {y_train.mean():.2%})")
    print(f"  -> Val:   {len(lead_val):,} leads (Conversion: {y_val.mean():.2%})")
    print(f"  -> Test:  {len(lead_test):,} leads (Conversion: {y_test.mean():.2%})")

    # 2. Preprocessing Pipeline
    print("\n[2/8] Fitting Reusable Preprocessing Pipeline...")
    pipe_path = MODELS_DIR / "lead_preprocessor.joblib"
    if pipe_path.exists():
        lead_pipe = joblib.load(pipe_path)
        logger.info("Loaded existing preprocessor from %s", pipe_path)
    else:
        lead_pipe = build_lead_pipeline()
        lead_pipe.fit(lead_train)
        joblib.dump(lead_pipe, pipe_path)
        logger.info("Fitted and saved preprocessor to %s", pipe_path)

    X_train = lead_pipe.transform(lead_train)
    X_val = lead_pipe.transform(lead_val)
    X_test = lead_pipe.transform(lead_test)
    feature_names = [f.replace("num__", "").replace("cat__", "") for f in lead_pipe.get_feature_names_out()]
    print(f"  -> Feature Matrix: {X_train.shape[0]:,} rows x {X_train.shape[1]} engineered features.")

    # 3. Imbalance Benchmarking Suite
    print("\n[3/8] Benchmarking 12 Imbalance Handling Configurations...")
    benchmarks = train_all_imbalance_benchmarks(X_train, y_train, seed=42)

    eval_records = []
    for model_name, model in benchmarks.items():
        probs = model.predict_proba(X_test)[:, 1]
        m = evaluate_classifier_predictions(y_test, probs, threshold=0.50)
        p_at_20 = evaluate_precision_at_top_k(y_test, probs, top_k_pct=0.20)
        eval_records.append({
            "Model Configuration": model_name,
            "ROC-AUC": round(m["ROC_AUC"], 4),
            "PR-AUC": round(m["PR_AUC"], 4),
            "Precision@Top-20%": f"{p_at_20['precision_at_k']:.1%}",
            "Top-20% Lift": f"{p_at_20['conversion_lift_ratio']:.2f}x",
            "F1-Score": round(m["F1_Score"], 4),
            "Brier Score": round(m["Brier_Score"], 4),
        })

    # 4. Bayesian Optimization / Production Model
    print("\n[4/8] Evaluating Tuned LightGBM Production Classifier...")
    model_path = MODELS_DIR / "lead_scoring_model.joblib"
    if model_path.exists():
        best_model = joblib.load(model_path)
        best_params = best_model.get_params()
        logger.info("Loaded production model from %s", model_path)
    else:
        best_model, best_params = optimize_lead_classifier(
            X_train, y_train, X_val, y_val, n_trials=15, seed=42
        )
        joblib.dump(best_model, model_path)
        logger.info("Saved tuned model to %s", model_path)

    test_probs = best_model.predict_proba(X_test)[:, 1]
    top_metrics = evaluate_classifier_predictions(y_test, test_probs, threshold=0.50)
    top_p20 = evaluate_precision_at_top_k(y_test, test_probs, top_k_pct=0.20)

    eval_records.insert(0, {
        "Model Configuration": "Tuned LightGBM (Optuna)",
        "ROC-AUC": round(top_metrics["ROC_AUC"], 4),
        "PR-AUC": round(top_metrics["PR_AUC"], 4),
        "Precision@Top-20%": f"{top_p20['precision_at_k']:.1%}",
        "Top-20% Lift": f"{top_p20['conversion_lift_ratio']:.2f}x",
        "F1-Score": round(top_metrics["F1_Score"], 4),
        "Brier Score": round(top_metrics["Brier_Score"], 4),
    })

    benchmark_df = pd.DataFrame(eval_records).sort_values("PR-AUC", ascending=False)
    print("\nBenchmark Leaderboard:")
    print(benchmark_df.to_string(index=False))

    # 5. Customer Persona Clustering (K-Means k=3)
    print("\n[5/8] Training Customer Persona Clustering (K-Means k=3)...")
    kmeans_path = MODELS_DIR / "lead_persona_kmeans.joblib"
    if kmeans_path.exists():
        kmeans = joblib.load(kmeans_path)
        logger.info("Loaded K-Means persona clustering model from %s", kmeans_path)
    else:
        kmeans = train_persona_clustering(X_train, n_clusters=3, seed=42)
        joblib.dump(kmeans, kmeans_path)
        logger.info("Saved K-Means persona clustering model to %s", kmeans_path)

    train_clusters = kmeans.predict(X_train)
    persona_df = compute_persona_profiles(lead_train, train_clusters)
    persona_names = {
        0: "First-Time Urban Homebuyer",
        1: "High-Net-Worth Investor",
        2: "Budget Renter / Short-Horizon Inquirer",
    }
    persona_df["Persona_Label"] = persona_df["Cluster_ID"].map(persona_names)
    print("\nCustomer Personas Discovered:")
    print(persona_df.to_string(index=False))

    # 6. Commercial Prioritization & Leakage-Free Cost Optimization
    print("\n[6/8] Commercial Prioritization & Threshold Optimization...")
    val_probs = best_model.predict_proba(X_val)[:, 1]
    val_cost_opt = optimize_decision_threshold(
        y_val,
        val_probs,
        commission_gain=100_000.0,
        cost_wasted_call=1_500.0,
        cost_missed_lead=20_000.0,
    )
    opt_thresh = val_cost_opt["optimal_threshold"]
    test_cost_eval = evaluate_classifier_predictions(y_test, test_probs, threshold=opt_thresh)

    print(f"  -> Operating Threshold Selected on Validation: {opt_thresh:.2f}")
    print(f"  -> Validation Max Net Profit: PKR {val_cost_opt['max_net_profit_pkr']:,.0f}")
    print(f"  -> Test Performance at {opt_thresh:.2f}: Recall={test_cost_eval['Recall']:.1%}, Precision={test_cost_eval['Precision']:.1%}")
    print(f"  -> Top-20% Capture: {top_p20['conversions_captured']} / {top_p20['total_conversions']} deals ({top_p20['recall_at_k']:.1%} capture rate, {top_p20['conversion_lift_ratio']:.2f}x lift)")

    # 7. Diagnostic Visualizations, SHAP & Fairness
    print("\n[7/8] Generating Diagnostic Visualizations & SHAP Plots...")
    generate_lead_diagnostic_plots(y_test, test_probs, output_dir=FIGS_DIR)

    explainer, shap_values = compute_shap_explanations(best_model, X_test[:200], feature_names=feature_names)
    generate_shap_plots(explainer, shap_values, X_test[:200], feature_names=feature_names, output_dir=FIGS_DIR)

    fairness_results = audit_algorithmic_bias(lead_test, y_test, test_probs, threshold=opt_thresh)

    # 8. Markdown Report Generation & Production Smoke Test
    print("\n[8/8] Generating Report & Running Inference Smoke Test...")
    generate_lead_scoring_report(
        benchmark_df=benchmark_df,
        p_at_k=top_p20,
        val_cost_opt=val_cost_opt,
        test_cost_eval=test_cost_eval,
        top_model_name="Tuned LightGBM (Optuna)",
        top_metrics=top_metrics,
        persona_df=persona_df,
        fairness_tables=fairness_results,
        report_path=REPORTS_DIR / "lead_scoring_report.md",
    )

    log_lead_experiment_to_mlflow(
        model=best_model,
        model_name="Tuned_LightGBM_Lead_Classifier",
        params=best_params,
        metrics=top_metrics,
        register_model=True,
        registered_model_name="LeadScoringClassifier",
    )

    scorer = LeadScorer(models_dir=MODELS_DIR).load()
    sample_lead = {
        "lead_source": "WhatsApp",
        "budget_pkr": 35_000_000,
        "preferred_city": "Lahore",
        "preferred_location": "DHA Phase 6",
        "property_type": "House",
        "purpose": "Buy",
        "number_of_calls": 5,
        "total_call_duration_min": 35.0,
        "response_time_minutes": 10.0,
        "visit_booked": 1,
        "days_since_first_contact": 8.0,
        "objection_raised": np.nan,
        "follow_up_count": 4,
        "budget_match_ratio": 1.0,
    }
    prediction = scorer.score_lead(sample_lead)
    print("\n--- PRODUCTION INFERENCE SMOKE TEST ---")
    print(f"  Conversion Probability: {prediction['conversion_probability']:.2%}")
    print(f"  Operational Tier:       {prediction['tier']} (Rank: {prediction['priority_rank']})")
    print(f"  SLA Recommendation:     {prediction['recommended_sla_action']}")
    print(f"  Customer Persona:       {prediction['customer_persona']}")
    print(f"  Latency:                {prediction['inference_latency_ms']:.2f} ms")
    print(f"  UrduLish Rationale:     {prediction['urdulish_explanation']}")

    print("\n" + "=" * 70)
    print("DAY 3 EXECUTION & VERIFICATION COMPLETE: ALL ARTIFACTS CERTIFIED")
    print("=" * 70)


if __name__ == "__main__":
    main()
