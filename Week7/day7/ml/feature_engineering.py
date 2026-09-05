"""Deterministic feature engineering from structured customer/property rows."""

from __future__ import annotations

import math
from typing import Any

from ml import FEATURE_NAMES


def _text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _amenities(value: Any) -> set[str]:
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {_text(item) for item in value if _text(item)}


def engineer_features(row: dict[str, Any]) -> dict[str, float]:
    """Build finite numeric features; missing values use neutral values."""
    budget = _number(row.get("budget_max"))
    price = _number(row.get("price"))
    preferred_bedrooms = _number(row.get("preferred_bedrooms"))
    property_bedrooms = _number(row.get("bedrooms"))
    requested = _amenities(row.get("preferred_amenities"))
    available = _amenities(row.get("property_amenities"))
    matching = requested & available

    price_difference = price - budget if price is not None and budget is not None else 0.0
    price_difference_ratio = price_difference / budget if price is not None and budget not in (None, 0) else 0.0
    bedroom_difference = abs(preferred_bedrooms - property_bedrooms) if preferred_bedrooms is not None and property_bedrooms is not None else 0.0
    amenity_ratio = len(matching) / len(requested) if requested else 0.0

    features = {
        "city_match": float(bool(_text(row.get("preferred_city"))) and _text(row.get("preferred_city")) == _text(row.get("city"))),
        "area_match": float(bool(_text(row.get("preferred_area"))) and _text(row.get("preferred_area")) == _text(row.get("area"))),
        "budget_match": float(price is not None and budget is not None and price <= budget),
        "price_difference": price_difference,
        "price_difference_ratio": price_difference_ratio,
        "bedrooms_match": float(preferred_bedrooms is not None and property_bedrooms is not None and preferred_bedrooms == property_bedrooms),
        "bedroom_difference": bedroom_difference,
        "property_type_match": float(bool(_text(row.get("preferred_property_type"))) and _text(row.get("preferred_property_type")) == _text(row.get("property_type"))),
        "purpose_match": float(bool(_text(row.get("preferred_purpose"))) and _text(row.get("preferred_purpose")) == _text(row.get("purpose"))),
        "amenity_match_ratio": amenity_ratio,
        "is_under_budget": float(price is not None and budget is not None and price <= budget),
        "number_of_matching_amenities": float(len(matching)),
    }
    return {name: float(features[name]) for name in FEATURE_NAMES}