"""
run_day2_training.py
--------------------
Master execution orchestrator for Week 8 Day 2:
Property Valuation Model (Regression) supporting BOTH For Sale and For Rent.

Executes:
1. Data loading for Sale & Rent splits
2. Scikit-learn Pipeline fitting & serialization
3. Baseline Models training (Median, Mean, Linear, Ridge, Lasso)
4. Advanced Ensembles training (Random Forest, XGBoost, LightGBM, CatBoost)
5. Optuna Bayesian Hyperparameter Optimization
6. Quantile Regression for Price Ranges (P10, P50, P90)
7. MLflow Experiment Logging & Model Registry
8. Test set evaluation, diagnostic plots, and markdown report generation
"""

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

from src.features.property_features import build_property_pipeline
from src.models.train_valuation import (
    train_baseline_models,
    train_advanced_models,
    optimize_lightgbm,
    train_quantile_models,
    log_experiment_to_mlflow,
)
from src.models.evaluate_valuation import (
    evaluate_model_suite,
    analyze_error_by_city,
    analyze_error_by_price_tier,
    generate_evaluation_plots,
    generate_model_comparison_report,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("day2_training")

MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "day2"
FIGS_DIR = PROJECT_ROOT / "reports" / "figures" / "day2"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def main():
    print("=" * 70)
    print("WEEK 8 DAY 2: PROPERTY VALUATION REGRESSION PLATFORM")
    print("=" * 70)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # 1. Load Data Splits
    # --------------------------------------------------------------------------
    print("\n[1/7] Loading Pre-Split Datasets...")
    sale_train = pd.read_csv(DATA_DIR / "prop_sale_train.csv", low_memory=False)
    sale_val = pd.read_csv(DATA_DIR / "prop_sale_val.csv", low_memory=False)
    sale_test = pd.read_csv(DATA_DIR / "prop_sale_test.csv", low_memory=False)

    rent_train = pd.read_csv(DATA_DIR / "prop_rent_train.csv", low_memory=False)
    rent_val = pd.read_csv(DATA_DIR / "prop_rent_val.csv", low_memory=False)
    rent_test = pd.read_csv(DATA_DIR / "prop_rent_test.csv", low_memory=False)

    print(f"  -> For Sale Splits: Train={len(sale_train):,}, Val={len(sale_val):,}, Test={len(sale_test):,}")
    print(f"  -> For Rent Splits: Train={len(rent_train):,}, Val={len(rent_val):,}, Test={len(rent_test):,}")

    # --------------------------------------------------------------------------
    # 2. Fit Preprocessing Pipelines
    # --------------------------------------------------------------------------
    print("\n[2/7] Fitting Preprocessing Pipelines...")
    sale_pipe = build_property_pipeline(purpose="sale", scaler="robust")
    X_sale_tr = sale_pipe.fit_transform(sale_train)
    X_sale_vl = sale_pipe.transform(sale_val)
    X_sale_ts = sale_pipe.transform(sale_test)

    rent_pipe = build_property_pipeline(purpose="rent", scaler="robust")
    X_rent_tr = rent_pipe.fit_transform(rent_train)
    X_rent_vl = rent_pipe.transform(rent_val)
    X_rent_ts = rent_pipe.transform(rent_test)

    joblib.dump(sale_pipe, MODELS_DIR / "sale_preprocessor.joblib")
    joblib.dump(rent_pipe, MODELS_DIR / "rent_preprocessor.joblib")
    print(f"  -> Saved preprocessors to {MODELS_DIR}")

    y_sale_tr, y_sale_vl, y_sale_ts = sale_train["price"].values, sale_val["price"].values, sale_test["price"].values
    y_rent_tr, y_rent_vl, y_rent_ts = rent_train["price"].values, rent_val["price"].values, rent_test["price"].values

    # --------------------------------------------------------------------------
    # 3. Train Baselines & Advanced Models (For Sale)
    # --------------------------------------------------------------------------
    print("\n[3/7] Training 'For Sale' Valuation Suite...")
    print("  -> Training Baseline Models (Median, Mean, Linear, Ridge, Lasso)...")
    sale_baselines = train_baseline_models(X_sale_tr, y_sale_tr)

    print("  -> Training Advanced Ensemble Models (Random Forest, XGBoost, LightGBM, CatBoost)...")
    sale_advanced = train_advanced_models(X_sale_tr, y_sale_tr)

    all_sale_models = {**sale_baselines, **sale_advanced}
    sale_eval_df = evaluate_model_suite(all_sale_models, X_sale_ts, y_sale_ts)
    print("\n--- FOR SALE TEST SET PERFORMANCE ---")
    print(sale_eval_df.to_string(index=False))

    # --------------------------------------------------------------------------
    # 4. Optuna Hyperparameter Optimization (For Sale)
    # --------------------------------------------------------------------------
    print("\n[4/7] Running Optuna Hyperparameter Optimization on LightGBM (15 Trials)...")
    best_sale_lgbm, best_params = optimize_lightgbm(
        X_sale_tr, y_sale_tr, X_sale_vl, y_sale_vl, n_trials=15
    )
    all_sale_models["Tuned LightGBM (Optuna)"] = best_sale_lgbm

    # Re-evaluate with tuned model
    sale_eval_df = evaluate_model_suite(all_sale_models, X_sale_ts, y_sale_ts)

    # --------------------------------------------------------------------------
    # 5. Train Quantile Models for Valuation Intervals (P10, P50, P90)
    # --------------------------------------------------------------------------
    print("\n[5/7] Training Quantile Regression Models (P10, P50, P90)...")
    sale_quantile_models = train_quantile_models(X_sale_tr, y_sale_tr, quantiles=[0.10, 0.50, 0.90])
    for q, m in sale_quantile_models.items():
        joblib.dump(m, MODELS_DIR / f"sale_model_q{int(q*100):02d}.joblib")

    rent_quantile_models = train_quantile_models(X_rent_tr, y_rent_tr, quantiles=[0.10, 0.50, 0.90])
    for q, m in rent_quantile_models.items():
        joblib.dump(m, MODELS_DIR / f"rent_model_q{int(q*100):02d}.joblib")

    print(f"  -> Serialized quantile models to {MODELS_DIR}")

    # --------------------------------------------------------------------------
    # 6. Train Rental Models Suite
    # --------------------------------------------------------------------------
    print("\n[6/7] Training 'For Rent' Valuation Suite...")
    rent_baselines = train_baseline_models(X_rent_tr, y_rent_tr)
    rent_advanced = train_advanced_models(X_rent_tr, y_rent_tr)
    all_rent_models = {**rent_baselines, **rent_advanced}
    rent_eval_df = evaluate_model_suite(all_rent_models, X_rent_ts, y_rent_ts)
    print("\n--- FOR RENT TEST SET PERFORMANCE ---")
    print(rent_eval_df.to_string(index=False))

    # --------------------------------------------------------------------------
    # 7. MLflow Experiment Logging, Diagnostics & Final Report
    # --------------------------------------------------------------------------
    print("\n[7/7] Logging Experiments to MLflow & Compiling Reports...")
    top_sale_model = all_sale_models["Tuned LightGBM (Optuna)"]
    top_rent_model = all_rent_models["LightGBM"]

    # MLflow log top models
    sale_test_metrics = evaluate_predictions(y_sale_ts, np.expm1(top_sale_model.predict(X_sale_ts)))
    rent_test_metrics = evaluate_predictions(y_rent_ts, np.expm1(top_rent_model.predict(X_rent_ts)))

    log_experiment_to_mlflow(
        model=top_sale_model,
        model_name="Tuned_LightGBM_Sale",
        params=best_params,
        metrics=sale_test_metrics,
        purpose="sale",
        register_model=True,
        registered_model_name="PropertyValuation_Sale_Production",
    )

    log_experiment_to_mlflow(
        model=top_rent_model,
        model_name="LightGBM_Rent",
        params={"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 63},
        metrics=rent_test_metrics,
        purpose="rent",
        register_model=True,
        registered_model_name="PropertyValuation_Rent_Production",
    )

    # Segmented analysis
    sale_preds = np.expm1(top_sale_model.predict(X_sale_ts))
    rent_preds = np.expm1(top_rent_model.predict(X_rent_ts))

    sale_city_df = analyze_error_by_city(sale_test, sale_preds)
    sale_tier_df = analyze_error_by_price_tier(sale_test, sale_preds, purpose="sale")
    rent_city_df = analyze_error_by_city(rent_test, rent_preds)
    rent_tier_df = analyze_error_by_price_tier(rent_test, rent_preds, purpose="rent")

    # Diagnostic plots
    generate_evaluation_plots(y_sale_ts, sale_preds, sale_test, purpose="sale", output_dir=FIGS_DIR)
    generate_evaluation_plots(y_rent_ts, rent_preds, rent_test, purpose="rent", output_dir=FIGS_DIR)

    # Markdown report
    generate_model_comparison_report(
        sale_suite_df=sale_eval_df,
        rent_suite_df=rent_eval_df,
        sale_city_df=sale_city_df,
        sale_tier_df=sale_tier_df,
        rent_city_df=rent_city_df,
        rent_tier_df=rent_tier_df,
        optuna_params=best_params,
        report_path=REPORTS_DIR / "model_comparison_report.md",
    )

    print("\n" + "=" * 70)
    print("SUCCESS: Week 8 Day 2 Property Valuation Training Pipeline Complete!")
    print(f"  -> Model comparison report: {REPORTS_DIR / 'model_comparison_report.md'}")
    print(f"  -> Diagnostic plots:        {FIGS_DIR}")
    print(f"  -> Production models:       {MODELS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
