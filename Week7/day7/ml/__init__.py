"""Offline customer-property recommendation model training."""

FEATURE_NAMES = (
    "city_match", "area_match", "budget_match", "price_difference",
    "price_difference_ratio", "bedrooms_match", "bedroom_difference",
    "property_type_match", "purpose_match", "amenity_match_ratio",
    "is_under_budget", "number_of_matching_amenities",
)