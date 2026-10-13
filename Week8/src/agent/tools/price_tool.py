"""
price_tool.py
-------------
LangGraph tool for Property Valuation.
Reuses the existing Task 1 PropertyValuator inference engine (Huber champion models).
Supports both 'For Sale' and 'For Rent'.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.predict_valuation import PropertyValuator
from src.models.prediction_logger import prediction_audit_logger

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

# Shared cached valuator instance
_valuator: Optional[PropertyValuator] = None


def get_valuator() -> PropertyValuator:
    global _valuator
    if _valuator is None:
        _valuator = PropertyValuator(models_dir=MODELS_DIR, model_variant="auto")
        _valuator.load()
    return _valuator


def price_predictor_tool(
    city: str,
    location: str,
    area_marla: float,
    purpose: str = "For Sale",
    property_type: str = "House",
    bedrooms: int = 3,
    baths: int = 3,
    listed_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Predict fair market property price and quantile bounds using trained Huber models.

    Parameters:
    - city: e.g. 'Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad'
    - location: Specific area/society e.g. 'DHA Defence', 'Clifton', 'F-7'
    - area_marla: Area in Marla (must be > 0)
    - purpose: 'For Sale' or 'For Rent'
    - property_type: 'House', 'Flat', 'Upper Portion', etc.
    - bedrooms: Number of bedrooms
    - baths: Number of bathrooms
    - listed_price: Optional asking price to evaluate under/overpricing

    Returns structured valuation dictionary.
    """
    if not city or not location or area_marla <= 0:
        return {
            "success": False,
            "error": "Missing required valuation parameters: valid city, location, and area_marla > 0 required.",
        }

    valid_cities = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]
    matched_city = next((c for c in valid_cities if c.lower() == city.strip().lower()), None)
    if not matched_city:
        return {
            "success": False,
            "error": f"City '{city}' is not in the supported coverage area: {valid_cities}",
        }

    purpose_clean = "For Rent" if "rent" in purpose.lower() else "For Sale"

    listing_payload = {
        "city": matched_city,
        "location": location.strip(),
        "area_marla": float(area_marla),
        "purpose": purpose_clean,
        "property_type": property_type.strip().title(),
        "bedrooms": int(bedrooms),
        "baths": int(baths),
    }
    if listed_price is not None and listed_price > 0:
        listing_payload["price"] = float(listed_price)

    try:
        val = get_valuator()
        res = val.predict(listing_payload, purpose=purpose_clean)
        prediction_audit_logger.log_valuation(
            inputs=listing_payload,
            output=res,
            validation_status="passed",
            purpose=purpose_clean,
            source="assistant",
            model_version=res["model_version"],
        )
        return {
            "success": True,
            "purpose": res["purpose"],
            "predicted_fair_price_pkr": res["predicted_fair_price_pkr"],
            "lower_bound_pkr": res["lower_bound_pkr"],
            "upper_bound_pkr": res["upper_bound_pkr"],
            "confidence_band_pkr": res["confidence_band_pkr"],
            "verdict": res["verdict"],
            "deviation_percentage": res["deviation_percentage"],
            "human_readable_summary": res["human_readable_summary"],
            "model_version": res.get("model_version", "huber_v1.0"),
            "city": matched_city,
            "location": location.strip(),
            "area_marla": float(area_marla),
        }
    except Exception as e:
        logger.error("Valuation tool error: %s", e, exc_info=True)
        is_ood = "OUT_OF_DISTRIBUTION" in str(e)
        prediction_audit_logger.log_valuation(
            inputs=listing_payload,
            output=None,
            validation_status="rejected" if is_ood else "error",
            rejection_reason="OUT_OF_DISTRIBUTION" if is_ood else type(e).__name__,
            purpose=purpose_clean,
            source="assistant",
        )
        return {
            "success": False,
            "prediction_allowed": False if is_ood else True,
            "error_code": "OUT_OF_DISTRIBUTION" if is_ood else "CALCULATION_ERROR",
            "error": f"Valuation calculation failed: {str(e)}",
        }
