"""
train_lead_scoring.py
---------------------
Training and hyperparameter optimization engine for sales lead conversion scoring.

Components:
1. Baseline Classification Models (Logistic Regression, Random Forest, XGBoost, LightGBM)
2. Imbalance Handling Benchmarks (Unweighted, Balanced Class Weights, SMOTE)
3. Optuna Bayesian Optimization for Gradient Boosting Classifier
4. K-Means Customer Persona Clustering & Cluster Profiling
5. MLflow Experiment Tracking and Model Registry integration
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

optuna.logging.set_verbosity(optuna.logging.WARNING)
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"

logger = logging.getLogger(__name__)
RANDOM_STATE = 42


def train_classification_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    strategy: str = "unweighted",
    seed: int = RANDOM_STATE,
) -> Dict[str, Any]:
    X_fit, y_fit = X_train, y_train

    if strategy == "smote":
        smote = SMOTE(random_state=seed)
        X_fit, y_fit = smote.fit_resample(X_train, y_train)

    pos_count = np.sum(y_train == 1)
    neg_count = np.sum(y_train == 0)
    scale_pos = neg_count / max(pos_count, 1)

    cw = "balanced" if strategy == "class_weight" else None
    spw = scale_pos if strategy == "class_weight" else 1.0

    models = {
        f"Logistic Regression ({strategy})": LogisticRegression(
            class_weight=cw,
            max_iter=1000,
            random_state=seed,
        ),
        f"Random Forest ({strategy})": RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            class_weight=cw,
            n_jobs=-1,
            random_state=seed,
        ),
        f"XGBoost ({strategy})": xgb.XGBClassifier(
            n_estimators=150,
            learning_rate=0.08,
            max_depth=5,
            scale_pos_weight=spw,
            eval_metric="logloss",
            random_state=seed,
            n_jobs=-1,
        ),
        f"LightGBM ({strategy})": lgb.LGBMClassifier(
            n_estimators=150,
            learning_rate=0.07,
            num_leaves=31,
            class_weight=cw,
            random_state=seed,
            verbose=-1,
            n_jobs=-1,
        ),
    }

    fitted = {}
    for name, model in models.items():
        t0 = time.time()
        model.fit(X_fit, y_fit)
        elapsed = time.time() - t0
        logger.info("Trained %s in %.2fs", name, elapsed)
        fitted[name] = model

    return fitted


def train_all_imbalance_benchmarks(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int = RANDOM_STATE,
) -> Dict[str, Any]:
    all_models = {}
    for strat in ("unweighted", "class_weight", "smote"):
        strat_models = train_classification_models(
            X_train, y_train, strategy=strat, seed=seed
        )
        all_models.update(strat_models)
    return all_models


def optimize_lead_classifier(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    n_trials: int = 15,
    seed: int = RANDOM_STATE,
) -> Tuple[lgb.LGBMClassifier, Dict[str, Any]]:
    pos_count = np.sum(y_train == 1)
    neg_count = np.sum(y_train == 0)
    scale_pos = neg_count / max(pos_count, 1)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 80, 300, step=20),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "subsample": trial.suggest_float("subsample", 0.65, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, scale_pos * 1.2),
            "random_state": seed,
            "verbose": -1,
            "n_jobs": -1,
        }
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_val)[:, 1]
        score = average_precision_score(y_val, probs)
        return float(score)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=seed),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_params.update({"random_state": seed, "verbose": -1, "n_jobs": -1})
    best_model = lgb.LGBMClassifier(**best_params)
    best_model.fit(X_train, y_train)

    logger.info("Optuna Best Lead Classifier Validation PR-AUC: %.4f", study.best_value)
    return best_model, best_params


def train_persona_clustering(
    X_train: np.ndarray,
    n_clusters: int = 3,
    seed: int = RANDOM_STATE,
) -> KMeans:
    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    kmeans.fit(X_train)
    logger.info("Fitted K-Means persona clustering model with %d clusters.", n_clusters)
    return kmeans


def compute_persona_profiles(
    df_raw: pd.DataFrame,
    cluster_labels: np.ndarray,
) -> pd.DataFrame:
    df_prof = df_raw.copy()
    df_prof["cluster"] = cluster_labels

    records = []
    for c_id, grp in df_prof.groupby("cluster"):
        median_budget = grp["budget_pkr"].median()
        mean_calls = grp["number_of_calls"].mean()
        mean_dur = grp["total_call_duration_min"].mean()
        visit_rate = grp["visit_booked"].mean() * 100.0

        if "converted" in grp.columns:
            conv_rate = grp["converted"].mean() * 100.0
        else:
            conv_rate = np.nan

        top_prop = grp["property_type"].mode().iloc[0] if "property_type" in grp.columns else "N/A"
        top_purp = grp["purpose"].mode().iloc[0] if "purpose" in grp.columns else "N/A"

        records.append({
            "Cluster_ID": int(c_id),
            "Size": len(grp),
            "Size_Pct": round(len(grp) / len(df_prof) * 100.0, 1),
            "Median_Budget_PKR": float(median_budget),
            "Mean_Calls": round(mean_calls, 1),
            "Mean_Call_Duration_Min": round(mean_dur, 1),
            "Visit_Booked_Pct": round(visit_rate, 1),
            "Empirical_Conversion_Pct": round(conv_rate, 1),
            "Dominant_Property_Type": top_prop,
            "Dominant_Purpose": top_purp,
        })

    return pd.DataFrame(records)


def log_lead_experiment_to_mlflow(
    model: Any,
    model_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, float],
    register_model: bool = False,
    registered_model_name: Optional[str] = None,
) -> str:
    mlflow.set_experiment("Lead_Scoring_Classification")

    with mlflow.start_run(run_name=f"{model_name}_{int(time.time())}") as run:
        clean_params = {k: str(v) for k, v in params.items()}
        mlflow.log_params(clean_params)

        for k, v in metrics.items():
            if isinstance(v, (int, float, np.number)):
                mlflow.log_metric(k, float(v))

        if "LGBM" in model_name or "LightGBM" in model_name:
            mlflow.lightgbm.log_model(model, artifact_path="model")
        elif "XGB" in model_name or "XGBoost" in model_name:
            mlflow.xgboost.log_model(model, artifact_path="model")
        else:
            mlflow.sklearn.log_model(model, artifact_path="model")

        if register_model and registered_model_name:
            try:
                model_uri = f"runs:/{run.info.run_id}/model"
                mlflow.register_model(model_uri, registered_model_name)
                logger.info("Registered model in MLflow Registry as: %s", registered_model_name)
            except Exception as e:
                logger.warning("MLflow registration note: %s", e)

        run_id = run.info.run_id
        logger.info("Logged %s to MLflow run ID: %s", model_name, run_id)
        return run_id
