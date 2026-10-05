"""
train_valuation.py
------------------
Training engine for property valuation regression models supporting BOTH
'For Sale' and 'For Rent' listings.

Implements:
1. Baseline Models (Mean/Median Dummy, Linear Regression, Ridge, Lasso)
2. Advanced Ensemble Models (Random Forest, XGBoost, LightGBM, CatBoost)
3. Optuna Hyperparameter Optimization for Gradient Boosting
4. Quantile Regression for Price Ranges (P10, P50, P90 confidence intervals)
5. MLflow Experiment Tracking and Model Registry integration
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor
import optuna
import mlflow
import mlflow.sklearn
import mlflow.lightgbm
import mlflow.xgboost

# Suppress Optuna and MLflow verbose loggers
optuna.logging.set_verbosity(optuna.logging.WARNING)
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"

logger = logging.getLogger(__name__)
RANDOM_STATE = 42


# ==============================================================================
# 1. Baseline Models
# ==============================================================================

def train_baseline_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int = RANDOM_STATE,
) -> Dict[str, Any]:
    """
    Train statistical and linear baseline models on log-transformed price.
    """
    y_log = np.log1p(y_train)
    models = {
        "Median Baseline": DummyRegressor(strategy="median"),
        "Mean Baseline": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=100.0, random_state=seed),
        "Lasso Regression": Lasso(alpha=0.01, max_iter=2000, random_state=seed),
    }

    fitted = {}
    for name, model in models.items():
        t0 = time.time()
        model.fit(X_train, y_log)
        elapsed = time.time() - t0
        logger.info("Trained %s in %.2fs", name, elapsed)
        fitted[name] = model

    return fitted


# ==============================================================================
# 2. Advanced Ensemble Models
# ==============================================================================

def train_advanced_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int = RANDOM_STATE,
) -> Dict[str, Any]:
    """
    Train production-grade gradient boosting and tree ensemble models.
    All models predict log1p(price) for variance stabilization.
    """
    y_log = np.log1p(y_train)
    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=16,
            min_samples_split=6,
            n_jobs=-1,
            random_state=seed,
        ),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=250,
            learning_rate=0.06,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            n_jobs=-1,
            random_state=seed,
        ),
        "LightGBM": lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=63,
            subsample=0.85,
            colsample_bytree=0.85,
            n_jobs=-1,
            random_state=seed,
            verbose=-1,
        ),
        "CatBoost": CatBoostRegressor(
            iterations=300,
            learning_rate=0.06,
            depth=7,
            random_seed=seed,
            verbose=0,
        ),
    }

    fitted = {}
    for name, model in models.items():
        t0 = time.time()
        model.fit(X_train, y_log)
        elapsed = time.time() - t0
        logger.info("Trained %s in %.2fs", name, elapsed)
        fitted[name] = model

    return fitted


# ==============================================================================
# 3. Optuna Hyperparameter Optimization
# ==============================================================================

def optimize_lightgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    n_trials: int = 20,
    seed: int = RANDOM_STATE,
) -> Tuple[lgb.LGBMRegressor, Dict[str, Any]]:
    """
    Tune LightGBM hyperparameters with Optuna to minimize validation MAPE.
    """
    y_train_log = np.log1p(y_train)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 150, 400, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.12, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 127),
            "max_depth": trial.suggest_int("max_depth", 6, 12),
            "subsample": trial.suggest_float("subsample", 0.65, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 15, 60),
            "n_jobs": -1,
            "random_state": seed,
            "verbose": -1,
        }
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train_log)
        preds = np.expm1(model.predict(X_val))
        mape = mean_absolute_percentage_error(y_val, preds)
        return float(mape)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_params.update({"n_jobs": -1, "random_state": seed, "verbose": -1})
    best_model = lgb.LGBMRegressor(**best_params)
    best_model.fit(X_train, y_train_log)

    logger.info("Optuna Best LightGBM Validation MAPE: %.2f%%", study.best_value * 100)
    return best_model, best_params


# ==============================================================================
# 4. Quantile Regression for Price Ranges (Task 5)
# ==============================================================================

def train_quantile_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    quantiles: List[float] = [0.10, 0.50, 0.90],
    seed: int = RANDOM_STATE,
) -> Dict[float, lgb.LGBMRegressor]:
    """
    Train quantile regression models (P10, P50, P90) to generate
    asymmetric prediction intervals representing fair market valuation bounds.
    """
    y_train_log = np.log1p(y_train)
    quantile_models = {}

    for q in quantiles:
        t0 = time.time()
        model = lgb.LGBMRegressor(
            objective="quantile",
            alpha=q,
            n_estimators=250,
            learning_rate=0.06,
            num_leaves=45,
            n_jobs=-1,
            random_state=seed,
            verbose=-1,
        )
        model.fit(X_train, y_train_log)
        elapsed = time.time() - t0
        logger.info("Trained Quantile Model (alpha=%.2f) in %.2fs", q, elapsed)
        quantile_models[q] = model

    return quantile_models


# ==============================================================================
# 5. MLflow Tracking & Experiment Logging (Task 4)
# ==============================================================================

def log_experiment_to_mlflow(
    model: Any,
    model_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, float],
    purpose: str = "sale",
    register_model: bool = False,
    registered_model_name: Optional[str] = None,
) -> str:
    """
    Log experiment run parameters, test metrics, and model artifacts to MLflow.
    """
    experiment_name = f"Property_Valuation_{purpose.capitalize()}"
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"{model_name}_{int(time.time())}") as run:
        # Log parameters
        clean_params = {k: str(v) for k, v in params.items()}
        mlflow.log_params(clean_params)

        # Log metrics
        for metric_name, val in metrics.items():
            if isinstance(val, (int, float, np.number)):
                mlflow.log_metric(metric_name, float(val))

        # Log model artifact
        if "LGBM" in model_name or "LightGBM" in model_name:
            mlflow.lightgbm.log_model(model, artifact_path="model")
        elif "XGB" in model_name or "XGBoost" in model_name:
            mlflow.xgboost.log_model(model, artifact_path="model")
        else:
            mlflow.sklearn.log_model(model, artifact_path="model")

        # Model registration
        if register_model and registered_model_name:
            model_uri = f"runs:/{run.info.run_id}/model"
            try:
                mlflow.register_model(model_uri, registered_model_name)
                logger.info("Registered model in MLflow Registry as: %s", registered_model_name)
            except Exception as e:
                logger.warning("Model registration note: %s", e)

        run_id = run.info.run_id
        logger.info("Logged %s to MLflow run ID: %s", model_name, run_id)
        return run_id
