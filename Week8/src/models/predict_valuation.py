"""
predict_valuation.py
--------------------
Production inference engine for AI Property Valuation.

Features:
1. Loads preprocessor pipelines and trained quantile regression models.
2. Evaluates incoming property parameters and routes to Sale or Rent model.
3. Computes point estimate (Huber / tuned), lower bound (P10), and upper bound (P90).
4. Generates market verdict: 'Underpriced', 'Fair', or 'Overpriced'.
5. Returns human-readable summary, model version, and executes under 50ms latency.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, Any, Union, Optional

import joblib
import numpy as np
import pandas as pd

from src.models.valuation_guardrails import (
    VALUATION_DISCLAIMER,
    validate_property_distribution,
)

logger = logging.getLogger(__name__)


def format_pkr_currency(amount: float) -> str:
    """Format PKR amount into human-readable Pakistani units (Lac, Crore, or Thousand)."""
    if amount >= 10_000_000:
        return f"{amount / 10_000_000:.2f} Crore PKR"
    elif amount >= 100_000:
        return f"{amount / 100_000:.2f} Lac PKR"
    else:
        return f"{amount:,.0f} PKR"


class PropertyValuator:
    """Production valuation service supporting Sale and Rent models."""

    def __init__(self, models_dir: Path = Path("models"), model_variant: str = "auto"):
        self.models_dir = Path(models_dir)
        self.model_variant = model_variant
        self.sale_pipe = None
        self.rent_pipe = None
        self.sale_models: Dict[float, Any] = {}
        self.rent_models: Dict[float, Any] = {}
        self.sale_model_tuned: Optional[Any] = None
        self.rent_model_tuned: Optional[Any] = None
        self.sale_model_huber: Optional[Any] = None
        self.rent_model_huber: Optional[Any] = None
        self.sale_pipe_huber: Optional[Any] = None
        self.rent_pipe_huber: Optional[Any] = None
        self._is_loaded = False

    def load(self) -> "PropertyValuator":
        """Load pipelines, quantile models, and regression models (Huber & tuned) from disk."""
        t0 = time.time()
        # Pipelines for Quantile Models & L2 models
        self.sale_pipe = joblib.load(self.models_dir / "sale_preprocessor.joblib")
        self.rent_pipe = joblib.load(self.models_dir / "rent_preprocessor.joblib")

        # Sale Quantile Models
        for q in [0.10, 0.50, 0.90]:
            path = self.models_dir / f"sale_model_q{int(q*100):02d}.joblib"
            if path.exists():
                self.sale_models[q] = joblib.load(path)

        # Rent Quantile Models
        for q in [0.10, 0.50, 0.90]:
            path = self.models_dir / f"rent_model_q{int(q*100):02d}.joblib"
            if path.exists():
                self.rent_models[q] = joblib.load(path)

        # Tuned Regression Models for Point Estimates
        sale_tuned_path = self.models_dir / "sale_model_tuned.joblib"
        if sale_tuned_path.exists():
            self.sale_model_tuned = joblib.load(sale_tuned_path)
            logger.info("Loaded tuned Sale model from %s", sale_tuned_path)

        rent_tuned_path = self.models_dir / "rent_model_tuned.joblib"
        if rent_tuned_path.exists():
            self.rent_model_tuned = joblib.load(rent_tuned_path)
            logger.info("Loaded tuned Rent model from %s", rent_tuned_path)

        # Huber Champion Models (Exp F1)
        sale_huber_path = self.models_dir / "sale_model_huber.joblib"
        sale_prep_huber_path = self.models_dir / "sale_preprocessor_huber.joblib"
        if sale_huber_path.exists() and sale_prep_huber_path.exists():
            self.sale_model_huber = joblib.load(sale_huber_path)
            self.sale_pipe_huber = joblib.load(sale_prep_huber_path)
            logger.info("Loaded Huber Sale model and preprocessor from %s", sale_huber_path)

        rent_huber_path = self.models_dir / "rent_model_huber.joblib"
        rent_prep_huber_path = self.models_dir / "rent_preprocessor_huber.joblib"
        if rent_huber_path.exists() and rent_prep_huber_path.exists():
            self.rent_model_huber = joblib.load(rent_huber_path)
            self.rent_pipe_huber = joblib.load(rent_prep_huber_path)
            logger.info("Loaded Huber Rent model and preprocessor from %s", rent_huber_path)

        self._is_loaded = True
        logger.info("PropertyValuator loaded all models in %.3fs", time.time() - t0)
        return self

    @staticmethod
    def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
        """Enrich input DataFrame with default values for required model features if omitted."""
        df = df.copy()
        city_province = {
            "Islamabad": "Islamabad",
            "Lahore": "Punjab",
            "Karachi": "Sindh",
            "Rawalpindi": "Punjab",
            "Faisalabad": "Punjab",
        }
        city_coords = {
            "Islamabad": (33.6844, 73.0479),
            "Lahore": (31.5204, 74.3587),
            "Karachi": (24.8607, 67.0011),
            "Rawalpindi": (33.5651, 73.0169),
            "Faisalabad": (31.4504, 73.1350),
        }
        if "city" not in df.columns:
            df["city"] = "Lahore"
        if "property_type" not in df.columns:
            df["property_type"] = "House"
        if "location" not in df.columns:
            df["location"] = "Unknown"
        if "area_marla" not in df.columns:
            df["area_marla"] = 10.0
        if "bedrooms" not in df.columns:
            df["bedrooms"] = 3
        if "baths" not in df.columns:
            df["baths"] = 3

        if "province_name" not in df.columns:
            df["province_name"] = df["city"].map(city_province).fillna("Punjab")

        if "latitude" not in df.columns or "longitude" not in df.columns:
            coords = df["city"].map(city_coords)
            if "latitude" not in df.columns:
                df["latitude"] = coords.apply(lambda c: c[0] if isinstance(c, tuple) else 31.5204)
            if "longitude" not in df.columns:
                df["longitude"] = coords.apply(lambda c: c[1] if isinstance(c, tuple) else 74.3587)

        if "listing_year" not in df.columns:
            df["listing_year"] = 2024
        if "listing_month" not in df.columns:
            df["listing_month"] = 6
        if "listing_quarter" not in df.columns:
            df["listing_quarter"] = 2
        if "listing_season" not in df.columns:
            season_map = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Autumn"}
            df["listing_season"] = df["listing_quarter"].map(season_map).fillna("Spring")

        if "property_age_years" not in df.columns:
            df["property_age_years"] = 5
        if "property_age_bucket" not in df.columns:
            df["property_age_bucket"] = "0-5yr"

        if "floors" not in df.columns:
            df["floors"] = np.where(df["property_type"] == "House", 2, 1)

        if "corner" not in df.columns:
            df["corner"] = 0
        if "park_facing" not in df.columns:
            df["park_facing"] = 0

        if "covered_area_sqft" not in df.columns:
            df["covered_area_sqft"] = (df["area_marla"] * 272.0 * 0.70).round(0).clip(lower=100)

        amenity_cols = ["parking", "security", "electricity_backup", "gas", "water_supply", "park_nearby"]
        for col in amenity_cols:
            if col not in df.columns:
                df[col] = 1 if col in ["parking", "gas", "water_supply"] else 0

        if "amenity_score" not in df.columns:
            df["amenity_score"] = df[amenity_cols].sum(axis=1)

        if "distance_main_road_km" not in df.columns:
            df["distance_main_road_km"] = 1.0
        if "distance_school_km" not in df.columns:
            df["distance_school_km"] = 1.5
        if "distance_hospital_km" not in df.columns:
            df["distance_hospital_km"] = 2.5

        if "bed_bath_ratio" not in df.columns:
            safe_baths = df["baths"].replace(0, np.nan).fillna(1)
            df["bed_bath_ratio"] = (df["bedrooms"] / safe_baths).round(2)

        if "covered_area_ratio" not in df.columns:
            plot_sqft = df["area_marla"] * 272.0
            df["covered_area_ratio"] = (df["covered_area_sqft"] / plot_sqft).clip(0, 2.0).round(3)

        if "location_frequency" not in df.columns:
            df["location_frequency"] = 0.01

        if "society_tier" not in df.columns:
            loc_lower = df["location"].astype(str).str.lower()
            premium_kw = ["dha", "bahria", "f-6", "f-7", "f-8", "e-7", "clifton", "cantt", "gulberg", "askari", "model town"]
            budget_kw = ["scheme 33", "korangi", "surjani", "north karachi", "shadman", "chungi", "rehman", "badami"]
            df["society_tier"] = np.where(
                loc_lower.str.contains("|".join(premium_kw)), "Premium",
                np.where(loc_lower.str.contains("|".join(budget_kw)), "Budget", "Mid")
            )

        if "is_furnished" not in df.columns:
            df["is_furnished"] = 0
        if "is_brand_new" not in df.columns:
            df["is_brand_new"] = 0
        if "is_main_road" not in df.columns:
            df["is_main_road"] = 0
        if "is_corner" not in df.columns:
            df["is_corner"] = df["corner"].fillna(0).astype(int)
        if "is_park_facing" not in df.columns:
            df["is_park_facing"] = df["park_facing"].fillna(0).astype(int)

        return df

    def predict(
        self,
        listing: Union[Dict[str, Any], pd.DataFrame],
        purpose: Optional[str] = None,
        validate_ood: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate listing and generate fair market valuation with bounds and verdict.
        """
        if not self._is_loaded:
            self.load()

        t0 = time.time()

        if isinstance(listing, dict):
            df = pd.DataFrame([listing])
        else:
            df = listing.copy()

        if validate_ood:
            check_dict = df.iloc[0].to_dict()
            if purpose:
                check_dict["purpose"] = purpose
            ood_result = validate_property_distribution(check_dict)
            if not ood_result["prediction_allowed"]:
                raise ValueError(f"OUT_OF_DISTRIBUTION: {ood_result['message']}")

        df = self._prepare_df(df)

        # Determine purpose
        p_val = purpose or df["purpose"].iloc[0] if "purpose" in df.columns else "For Sale"
        is_sale = "sale" in p_val.lower()

        pipeline = self.sale_pipe if is_sale else self.rent_pipe
        models = self.sale_models if is_sale else self.rent_models

        # Transform features for quantile prediction
        X_trans = pipeline.transform(df)

        # Predict quantiles
        p10 = float(np.expm1(models[0.10].predict(X_trans)[0]))
        p50 = float(np.expm1(models[0.50].predict(X_trans)[0]))
        p90 = float(np.expm1(models[0.90].predict(X_trans)[0]))

        # Fair price point estimate: prioritize Huber model when available and selected
        use_huber = (
            (self.model_variant in ["auto", "huber"])
            and (self.sale_model_huber is not None if is_sale else self.rent_model_huber is not None)
        )

        if use_huber:
            huber_pipe = self.sale_pipe_huber if is_sale else self.rent_pipe_huber
            huber_model = self.sale_model_huber if is_sale else self.rent_model_huber
            X_huber = huber_pipe.transform(df)
            fair_price = float(np.expm1(huber_model.predict(X_huber)[0]))
            model_ver = "huber_v1.0"
        elif is_sale and self.sale_model_tuned is not None:
            fair_price = float(np.expm1(self.sale_model_tuned.predict(X_trans)[0]))
            model_ver = "tuned_l2_v1.0"
        elif not is_sale and self.rent_model_tuned is not None:
            fair_price = float(np.expm1(self.rent_model_tuned.predict(X_trans)[0]))
            model_ver = "tuned_l2_v1.0"
        else:
            fair_price = p50
            model_ver = "quantile_q50_v1.0"

        # Enforce quantile monotonicity
        lower_bound = min(p10, p50, fair_price)
        upper_bound = max(p90, p50, fair_price)

        # Check listed price if provided
        listed_price = df["price"].iloc[0] if "price" in df.columns and pd.notna(df["price"].iloc[0]) else None

        if listed_price is not None and listed_price > 0:
            if listed_price > upper_bound:
                verdict = "Overpriced"
                dev_pct = ((listed_price - fair_price) / fair_price) * 100.0
            elif listed_price < lower_bound:
                verdict = "Underpriced"
                dev_pct = ((fair_price - listed_price) / fair_price) * 100.0
            else:
                verdict = "Fair"
                dev_pct = ((listed_price - fair_price) / fair_price) * 100.0
        else:
            verdict = "N/A"
            dev_pct = 0.0

        latency_ms = (time.time() - t0) * 1000.0

        # Construct concise human-readable summary
        summary = (
            f"Predicted Fair Price: {format_pkr_currency(fair_price)} "
            f"(Range: {format_pkr_currency(lower_bound)} - {format_pkr_currency(upper_bound)})"
        )
        if listed_price is not None:
            summary += f". Listed at {format_pkr_currency(listed_price)} -> {verdict} ({dev_pct:+.1f}%)"

        return {
            "purpose": "For Sale" if is_sale else "For Rent",
            "predicted_fair_price_pkr": round(fair_price, 2),
            "lower_bound_pkr": round(lower_bound, 2),
            "upper_bound_pkr": round(upper_bound, 2),
            "confidence_band_pkr": (round(lower_bound, 2), round(upper_bound, 2)),
            "listed_price_pkr": float(listed_price) if listed_price is not None else None,
            "verdict": verdict,
            "deviation_percentage": round(dev_pct, 2),
            "human_readable_summary": summary,
            "inference_latency_ms": round(latency_ms, 2),
            "model_version": model_ver,
            "disclaimer": VALUATION_DISCLAIMER,
        }
