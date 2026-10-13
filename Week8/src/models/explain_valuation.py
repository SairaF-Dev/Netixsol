"""Local TreeSHAP explanations for the active property valuation model."""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.models.predict_valuation import PropertyValuator

logger = logging.getLogger(__name__)
_EXPLAINER_CACHE: dict[int, shap.TreeExplainer] = {}

FEATURE_LABELS = {
    "area_marla": "Property size (marla)",
    "bedrooms": "Bedrooms",
    "baths": "Bathrooms",
    "location": "Locality",
    "loc_te": "Locality price history",
    "city": "City",
    "property_type": "Property type",
    "property_age_years": "Property age",
    "floors": "Number of floors",
    "corner": "Corner plot",
    "park_facing": "Park-facing",
    "covered_area_sqft": "Covered area",
    "amenity_score": "Amenities",
    "distance_main_road_km": "Distance to main road",
    "distance_school_km": "Distance to school",
    "distance_hospital_km": "Distance to hospital",
    "society_tier": "Locality tier",
}


def _active_model(valuator: PropertyValuator, purpose: str) -> tuple[Any, Any, str]:
    is_sale = "sale" in purpose.casefold()
    huber_model = valuator.sale_model_huber if is_sale else valuator.rent_model_huber
    huber_pipe = valuator.sale_pipe_huber if is_sale else valuator.rent_pipe_huber
    if valuator.model_variant in {"auto", "huber"} and huber_model is not None and huber_pipe is not None:
        return huber_model, huber_pipe, "huber_v1.0"

    tuned_model = valuator.sale_model_tuned if is_sale else valuator.rent_model_tuned
    if tuned_model is not None:
        pipe = valuator.sale_pipe if is_sale else valuator.rent_pipe
        return tuned_model, pipe, "tuned_l2_v1.0"

    quantile_models = valuator.sale_models if is_sale else valuator.rent_models
    median_model = quantile_models.get(0.50)
    if median_model is None:
        raise RuntimeError(f"No active {'sale' if is_sale else 'rent'} valuation model is loaded.")
    pipe = valuator.sale_pipe if is_sale else valuator.rent_pipe
    return median_model, pipe, "quantile_q50_v1.0"


def _feature_names(preprocessor: Any, feature_count: int) -> list[str]:
    transformer = getattr(preprocessor, "column_transformer", preprocessor)
    get_names = getattr(transformer, "get_feature_names_out", None)
    if callable(get_names):
        names = [str(name) for name in get_names()]
        if len(names) == feature_count:
            return names
    return [f"feature_{index}" for index in range(feature_count)]


def _display_name(name: str) -> str:
    clean = name.removeprefix("num__").removeprefix("cat__")
    for feature, label in FEATURE_LABELS.items():
        if clean == feature or clean.startswith(f"{feature}_"):
            suffix = clean[len(feature):].strip("_").replace("_", " ")
            return f"{label}: {suffix}" if suffix else label
    return clean.replace("_", " ").strip().capitalize()


def explain_valuation(
    valuator: PropertyValuator,
    listing: dict[str, Any],
    *,
    purpose: str | None = None,
    max_features: int = 10,
) -> dict[str, Any]:
    """Return local attributions on the model's log-price output scale."""
    if not valuator._is_loaded:
        valuator.load()

    started = time.perf_counter()
    prediction = valuator.predict(listing, purpose=purpose)
    resolved_purpose = purpose or prediction["purpose"]
    model, preprocessor, model_version = _active_model(valuator, resolved_purpose)
    frame = pd.DataFrame([listing]) if isinstance(listing, dict) else listing.copy()
    if purpose:
        frame["purpose"] = purpose
    frame = valuator._prepare_df(frame)
    transformed = preprocessor.transform(frame)

    cache_key = id(model)
    explainer = _EXPLAINER_CACHE.get(cache_key)
    if explainer is None:
        explainer = shap.TreeExplainer(model)
        _EXPLAINER_CACHE[cache_key] = explainer

    raw_values = explainer.shap_values(transformed)
    values = np.asarray(raw_values)
    if values.ndim == 3:
        values = values[0, :, -1]
    elif values.ndim == 2:
        values = values[0]
    else:
        values = values.reshape(-1)

    names = _feature_names(preprocessor, len(values))
    if len(names) != len(values) or not np.isfinite(values).all():
        raise RuntimeError("Valuation explainer returned invalid feature attributions.")

    contributions = [
        {
            "feature": _display_name(name),
            "shap_value": round(float(value), 6),
            "direction": "increases" if value > 0 else "decreases",
        }
        for name, value in zip(names, values)
        if value != 0
    ]
    contributions.sort(key=lambda item: abs(item["shap_value"]), reverse=True)
    contributions = contributions[:max_features]

    positive = [item["feature"] for item in contributions if item["shap_value"] > 0][:3]
    negative = [item["feature"] for item in contributions if item["shap_value"] < 0][:3]
    drivers = []
    if positive:
        drivers.append(f"estimate ko barhane wale asraat: {', '.join(positive)}")
    if negative:
        drivers.append(f"estimate ko kam karne wale asraat: {', '.join(negative)}")
    if not drivers:
        drivers.append("koi aik feature numaya asar nahi dikha raha")
    summary = (
        f"Model ke mutabiq {prediction['purpose']} estimate "
        f"{prediction['predicted_fair_price_pkr']:,.0f} PKR hai; "
        f"{'; '.join(drivers)}. SHAP contributions log-price scale par hain, PKR mein alag-alag price changes nahi."
    )

    return {
        "status": "shap_available",
        "message": "Local TreeSHAP contributions for the active valuation model; attribution values are on log-price scale.",
        "explanation_available": True,
        "predicted_fair_price_pkr": prediction["predicted_fair_price_pkr"],
        "lower_bound_pkr": prediction["lower_bound_pkr"],
        "upper_bound_pkr": prediction["upper_bound_pkr"],
        "top_features": contributions,
        "urdulish_summary": summary,
        "inference_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "model_version": model_version,
        "target_scale": "log_price",
    }


def generate_valuation_shap_report(
    valuator: PropertyValuator,
    rows: pd.DataFrame,
    *,
    purpose: str,
    output_dir: Path,
    max_rows: int = 1000,
    sample_index: int = 0,
) -> dict[str, Any]:
    """Save a global SHAP summary and a local waterfall for a valuation model."""
    normalized_purpose = purpose.strip().casefold()
    if normalized_purpose not in {"sale", "rent"}:
        raise ValueError("purpose must be sale or rent.")
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1.")
    model_purpose = "For Sale" if normalized_purpose == "sale" else "For Rent"
    if "purpose" in rows.columns:
        rows = rows[rows["purpose"].astype(str).str.casefold() == model_purpose.casefold()]
    if rows.empty:
        raise ValueError(f"No {model_purpose} rows are available for SHAP reporting.")
    if len(rows) > max_rows:
        rows = rows.sample(n=max_rows, random_state=42)
    if not 0 <= sample_index < len(rows):
        raise ValueError(f"sample_index must be between 0 and {len(rows) - 1}.")

    if not valuator._is_loaded:
        valuator.load()
    model, preprocessor, model_version = _active_model(valuator, model_purpose)
    prepared = valuator._prepare_df(rows)
    transformed = preprocessor.transform(prepared)
    explainer = shap.TreeExplainer(model)
    explanation = explainer(transformed)
    values = np.asarray(explanation.values)
    if values.ndim == 3:
        values = values[:, :, -1]
    if values.ndim != 2 or values.shape[0] != len(rows):
        raise RuntimeError("Valuation TreeSHAP returned an invalid attribution matrix.")

    names = _feature_names(preprocessor, values.shape[1])
    if len(names) != values.shape[1] or not np.isfinite(values).all():
        raise RuntimeError("Valuation TreeSHAP returned invalid feature attributions.")
    importance = np.mean(np.abs(values), axis=0)
    ranked_indices = np.argsort(importance)[::-1][:12]
    top_features = [
        {
            "feature": _display_name(names[index]),
            "mean_absolute_shap": round(float(importance[index]), 6),
        }
        for index in ranked_indices
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    global_plot = output_dir / f"valuation_{normalized_purpose}_shap_summary.png"
    local_plot = output_dir / f"valuation_{normalized_purpose}_shap_waterfall.png"
    report_path = output_dir / f"valuation_{normalized_purpose}_shap_summary.json"

    shap.summary_plot(
        values,
        transformed,
        feature_names=names,
        show=False,
        max_display=12,
    )
    plt.title(f"Valuation SHAP Importance ({model_purpose}; log-price scale)")
    plt.tight_layout()
    plt.savefig(global_plot, dpi=200, bbox_inches="tight")
    plt.close()

    base_values = np.asarray(explanation.base_values)
    base_value = float(base_values.reshape(-1)[-1])
    local_explanation = shap.Explanation(
        values=values[sample_index],
        base_values=base_value,
        data=np.asarray(transformed)[sample_index],
        feature_names=names,
    )
    shap.plots.waterfall(local_explanation, max_display=10, show=False)
    plt.title(f"Valuation SHAP Explanation ({model_purpose}; log-price scale)")
    plt.tight_layout()
    plt.savefig(local_plot, dpi=200, bbox_inches="tight")
    plt.close()

    report = {
        "purpose": model_purpose,
        "model_version": model_version,
        "target_scale": "log_price",
        "rows_explained": int(len(rows)),
        "top_features": top_features,
        "global_plot": str(global_plot),
        "local_plot": str(local_plot),
        "local_sample_index": sample_index,
        "report_path": str(report_path),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate global and local valuation TreeSHAP reports.")
    parser.add_argument("--purpose", choices=("sale", "rent"), required=True)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-rows", type=int, default=1000)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    purpose_data = args.data or project_root / "data" / "processed" / f"prop_{args.purpose}_val.csv"
    output_dir = args.output_dir or project_root / "reports" / "figures" / "day3"
    rows = pd.read_csv(purpose_data, low_memory=False)
    valuator = PropertyValuator(models_dir=project_root / "models", model_variant="auto")
    report = generate_valuation_shap_report(
        valuator,
        rows,
        purpose=args.purpose,
        output_dir=output_dir,
        max_rows=args.max_rows,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
