"""
train_huber.py
--------------
Reproducible training and serialization pipeline for the Huber Property Valuation
champion models (Exp F1).

Produces:
  - models/sale_preprocessor_huber.joblib
  - models/rent_preprocessor_huber.joblib
  - models/sale_model_huber.joblib
  - models/rent_model_huber.joblib

Preserves existing L2 models (sale_model_tuned.joblib / rent_model_tuned.joblib) untouched.
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error

from src.features.property_features import HuberPropertyPreprocessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_huber")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

SALE_HUBER_PARAMS = {
    "objective": "huber",
    "alpha": 0.9,
    "n_estimators": 350,
    "learning_rate": 0.118,
    "num_leaves": 110,
    "max_depth": 11,
    "subsample": 0.72,
    "colsample_bytree": 0.72,
    "reg_alpha": 0.006,
    "reg_lambda": 0.67,
    "min_child_samples": 36,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}

RENT_HUBER_PARAMS = {
    "objective": "huber",
    "alpha": 0.9,
    "n_estimators": 400,
    "learning_rate": 0.045,
    "num_leaves": 110,
    "max_depth": 10,
    "subsample": 0.74,
    "colsample_bytree": 0.71,
    "reg_alpha": 0.008,
    "reg_lambda": 0.63,
    "min_child_samples": 23,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}


def eval_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_pred = np.clip(y_pred, 1.0, None)
    ape = np.abs(y_true - y_pred) / y_true * 100.0
    return {
        "MAPE": float(np.mean(ape)),
        "MdAPE": float(np.median(ape)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def train_and_serialize_huber():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    logger.info("Loading train and validation splits...")
    sale_train = pd.read_csv(DATA_DIR / "prop_sale_train.csv", low_memory=False)
    sale_val = pd.read_csv(DATA_DIR / "prop_sale_val.csv", low_memory=False)
    rent_train = pd.read_csv(DATA_DIR / "prop_rent_train.csv", low_memory=False)
    rent_val = pd.read_csv(DATA_DIR / "prop_rent_val.csv", low_memory=False)

    # 2. Fit Sale Huber Pipeline
    logger.info("Fitting Sale Huber Preprocessor and Model...")
    sale_prep = HuberPropertyPreprocessor(random_state=42)
    X_sale_tr = sale_prep.fit_transform(sale_train)
    y_sale_tr_log = np.log1p(sale_train["price"].values)

    sale_model = lgb.LGBMRegressor(**SALE_HUBER_PARAMS)
    sale_model.fit(X_sale_tr, y_sale_tr_log)

    # Validate Sale Huber
    X_sale_vl = sale_prep.transform(sale_val)
    sale_preds_val = np.expm1(sale_model.predict(X_sale_vl))
    sale_val_metrics = eval_metrics(sale_val["price"].values, sale_preds_val)
    logger.info(
        "Sale Huber Validation: MAPE=%.2f%% | MdAPE=%.2f%% | MAE=PKR %s | RMSE=PKR %s | R2=%.4f",
        sale_val_metrics["MAPE"], sale_val_metrics["MdAPE"],
        f"{sale_val_metrics['MAE']:,.0f}", f"{sale_val_metrics['RMSE']:,.0f}",
        sale_val_metrics["R2"]
    )

    # 3. Fit Rent Huber Pipeline
    logger.info("Fitting Rent Huber Preprocessor and Model...")
    rent_prep = HuberPropertyPreprocessor(random_state=42)
    X_rent_tr = rent_prep.fit_transform(rent_train)
    y_rent_tr_log = np.log1p(rent_train["price"].values)

    rent_model = lgb.LGBMRegressor(**RENT_HUBER_PARAMS)
    rent_model.fit(X_rent_tr, y_rent_tr_log)

    # Validate Rent Huber
    X_rent_vl = rent_prep.transform(rent_val)
    rent_preds_val = np.expm1(rent_model.predict(X_rent_vl))
    rent_val_metrics = eval_metrics(rent_val["price"].values, rent_preds_val)
    logger.info(
        "Rent Huber Validation: MAPE=%.2f%% | MdAPE=%.2f%% | MAE=PKR %s | RMSE=PKR %s | R2=%.4f",
        rent_val_metrics["MAPE"], rent_val_metrics["MdAPE"],
        f"{rent_val_metrics['MAE']:,.0f}", f"{rent_val_metrics['RMSE']:,.0f}",
        rent_val_metrics["R2"]
    )

    # 4. Serialize Artifacts
    logger.info("Serializing Huber production artifacts to %s...", MODELS_DIR)
    joblib.dump(sale_prep, MODELS_DIR / "sale_preprocessor_huber.joblib")
    joblib.dump(rent_prep, MODELS_DIR / "rent_preprocessor_huber.joblib")
    joblib.dump(sale_model, MODELS_DIR / "sale_model_huber.joblib")
    joblib.dump(rent_model, MODELS_DIR / "rent_model_huber.joblib")

    logger.info("SUCCESS: All 4 Huber artifacts successfully saved!")
    return sale_val_metrics, rent_val_metrics


if __name__ == "__main__":
    train_and_serialize_huber()
