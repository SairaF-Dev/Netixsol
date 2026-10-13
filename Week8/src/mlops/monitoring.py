"""Population drift and labeled-performance monitoring for sale/rent models."""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.models.predict_valuation import PropertyValuator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "day5" / "drift_report.json"
PSI_WARNING = 0.10
PSI_CRITICAL = 0.25
MAPE_ALERT_PERCENT = 15.0
logger = logging.getLogger(__name__)


def population_stability_index(reference: pd.Series, current: pd.Series) -> float:
    """Calculate PSI with reference quantile bins or category buckets."""
    reference = reference.dropna()
    current = current.dropna()
    if reference.empty or current.empty:
        raise ValueError("Reference and current feature columns must both contain values.")

    if pd.api.types.is_numeric_dtype(reference) and pd.api.types.is_numeric_dtype(current):
        quantiles = np.unique(np.quantile(reference.astype(float), np.linspace(0, 1, 11)))
        if len(quantiles) < 2:
            quantiles = np.array([reference.min() - 0.5, reference.max() + 0.5])
        edges = np.concatenate(([-np.inf], quantiles[1:-1], [np.inf]))
        ref_counts = np.histogram(reference.astype(float), bins=edges)[0]
        cur_counts = np.histogram(current.astype(float), bins=edges)[0]
    else:
        ref_values = reference.astype(str)
        cur_values = current.astype(str)
        categories = sorted(set(ref_values) | set(cur_values))
        ref_counts = ref_values.value_counts().reindex(categories, fill_value=0).to_numpy()
        cur_counts = cur_values.value_counts().reindex(categories, fill_value=0).to_numpy()

    ref_pct = np.maximum(ref_counts / ref_counts.sum(), 1e-6)
    cur_pct = np.maximum(cur_counts / cur_counts.sum(), 1e-6)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def evaluate_mape(model: Any, preprocessor: Any, rows: pd.DataFrame) -> float:
    if "price" not in rows.columns:
        raise ValueError("Labeled current data must contain a 'price' column for MAPE monitoring.")
    features = preprocessor.transform(PropertyValuator._prepare_df(rows))
    predictions = np.expm1(model.predict(features))
    actual = rows["price"].to_numpy(dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predictions) & (actual > 0)
    if not valid.any():
        raise ValueError("Current labeled data contains no valid positive prices.")
    return float(np.mean(np.abs(actual[valid] - predictions[valid]) / actual[valid]) * 100)


def _load_current_rows(path: Path, purpose: str, max_rows: int, price_increase: float) -> pd.DataFrame:
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1.")
    rows = pd.read_csv(path, low_memory=False)
    if "purpose" in rows.columns:
        rows = rows[rows["purpose"].astype(str).str.casefold() == purpose.casefold()]
    if rows.empty:
        raise ValueError(f"No {purpose} rows found in {path}.")
    if price_increase:
        rows = rows.copy()
        rows["price"] = rows["price"] * (1 + price_increase)
    if len(rows) > max_rows:
        rows = rows.sample(n=max_rows, random_state=42)
    return rows


def build_drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    purpose: str,
    model: Any | None = None,
    preprocessor: Any | None = None,
) -> dict[str, Any]:
    """Report per-feature PSI and optional labeled MAPE for one property purpose."""
    ignored = {"purpose", "property_id"}
    common = sorted((set(reference.columns) & set(current.columns)) - ignored)
    if not common:
        raise ValueError("Reference and current datasets have no comparable feature columns.")
    feature_results = {}
    for column in common:
        if reference[column].isna().all() or current[column].isna().all():
            continue
        psi = population_stability_index(reference[column], current[column])
        status = "critical" if psi >= PSI_CRITICAL else "warning" if psi >= PSI_WARNING else "stable"
        feature_results[column] = {"psi": round(psi, 6), "status": status}

    if not feature_results:
        raise ValueError("No non-empty comparable features were available for drift analysis.")
    max_psi = max(item["psi"] for item in feature_results.values())
    max_feature = max(feature_results, key=lambda key: feature_results[key]["psi"])
    performance = None
    if model is not None and preprocessor is not None:
        performance = round(evaluate_mape(model, preprocessor, current), 4)

    alerts = []
    if max_psi >= PSI_WARNING:
        alerts.append({
            "type": "feature_drift",
            "severity": "critical" if max_psi >= PSI_CRITICAL else "warning",
            "feature": max_feature,
            "psi": round(max_psi, 6),
        })
    if performance is not None and performance > MAPE_ALERT_PERCENT:
        alerts.append({
            "type": "mape",
            "severity": "critical",
            "mape_percent": performance,
            "threshold_percent": MAPE_ALERT_PERCENT,
        })

    return {
        "purpose": purpose,
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "psi_thresholds": {"warning": PSI_WARNING, "critical": PSI_CRITICAL},
        "max_psi": round(max_psi, 6),
        "max_psi_feature": max_feature,
        "features": feature_results,
        "mape_percent": performance,
        "mape_alert_threshold_percent": MAPE_ALERT_PERCENT,
        "alerts": alerts,
        "status": "alert" if alerts else "healthy",
    }


def run_monitoring(
    reference_path: Path,
    current_path: Path,
    output_path: Path,
    *,
    max_rows: int = 2000,
    simulate_price_increase: float = 0.0,
) -> dict[str, Any]:
    if not math.isfinite(simulate_price_increase) or simulate_price_increase < 0:
        raise ValueError("Price increase simulation must be a finite, non-negative value.")
    reference_all = pd.read_csv(reference_path, low_memory=False)
    reports = []
    for purpose, prefix in (("For Sale", "sale"), ("For Rent", "rent")):
        if "purpose" in reference_all.columns:
            reference = reference_all[
                reference_all["purpose"].astype(str).str.casefold() == purpose.casefold()
            ]
        else:
            reference = reference_all
        current = _load_current_rows(
            current_path,
            purpose,
            max_rows,
            simulate_price_increase,
        )
        if reference.empty:
            raise ValueError(f"No {purpose} reference rows found in {reference_path}.")
        model_path = MODELS_DIR / f"{prefix}_model_huber.joblib"
        prep_path = MODELS_DIR / f"{prefix}_preprocessor_huber.joblib"
        if not model_path.is_file() or not prep_path.is_file():
            raise FileNotFoundError(f"Active {purpose} model/preprocessor artifacts are missing.")
        report = build_drift_report(
            reference,
            current,
            purpose=purpose,
            model=joblib.load(model_path),
            preprocessor=joblib.load(prep_path),
        )
        reports.append(report)

    result = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "reference_path": str(reference_path),
        "current_path": str(current_path),
        "price_increase_simulation": simulate_price_increase,
        "overall_status": "alert" if any(item["alerts"] for item in reports) else "healthy",
        "models": reports,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DATA_DIR / "prop_train.csv")
    parser.add_argument("--current", type=Path, default=DATA_DIR / "properties_clean.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-rows", type=int, default=2000)
    parser.add_argument(
        "--simulate-price-increase",
        type=float,
        default=0.0,
        help="Apply a fractional price increase to the current sample (e.g. 0.15 for +15%%).",
    )
    parser.add_argument("--fail-on-alert", action="store_true")
    args = parser.parse_args()
    report = run_monitoring(
        args.reference,
        args.current,
        args.output,
        max_rows=args.max_rows,
        simulate_price_increase=args.simulate_price_increase,
    )
    print(json.dumps(report, indent=2))
    return 2 if args.fail_on_alert and report["overall_status"] == "alert" else 0


if __name__ == "__main__":
    raise SystemExit(main())
