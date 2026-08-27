def normalize_text(value):
    """Normalize user-provided text for consistent filtering."""
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def validate_filters(
    budget=None,
    city=None,
    area=None,
    bedrooms=None,
    property_type=None,
    purpose=None,
):
    """Validate and normalize recommendation filters."""

    if budget is not None:
        if not isinstance(budget, (int, float)) or budget < 0:
            raise ValueError("budget must be a non-negative number")

    if bedrooms is not None:
        if not isinstance(bedrooms, int) or bedrooms < 0:
            raise ValueError("bedrooms must be a non-negative integer")

    return {
        "budget": budget,
        "city": normalize_text(city),
        "area": normalize_text(area),
        "bedrooms": bedrooms,
        "property_type": normalize_text(property_type),
        "purpose": normalize_text(purpose),
    }