from decimal import Decimal


def _normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def score_property(
    property_data,
    budget=None,
    city=None,
    area=None,
    bedrooms=None,
    purpose=None,
    desired_amenities=None,
):
    """
    Calculate recommendation score for a property.

    Property information comes from PostgreSQL.
    No property-specific information is hardcoded.
    """

    score = 0.0

    price = property_data.get("price")

    if price is not None:
        price = Decimal(str(price))

    # ---------------------------------------------------------
    # 1. Budget match - 35 points
    # ---------------------------------------------------------

    if budget is not None and price is not None:

        budget = Decimal(str(budget))

        if price <= budget:
            score += 35

    # ---------------------------------------------------------
    # 2. City match - 20 points
    # ---------------------------------------------------------

    if city and (
        _normalize(property_data.get("city"))
        == _normalize(city)
    ):
        score += 20

    # ---------------------------------------------------------
    # 3. Area match - 15 points
    # ---------------------------------------------------------

    if area and (
        _normalize(area)
        in _normalize(property_data.get("area"))
    ):
        score += 15

    # ---------------------------------------------------------
    # 4. Bedroom match - 15 points
    # ---------------------------------------------------------

    if (
        bedrooms is not None
        and property_data.get("bedrooms") == bedrooms
    ):
        score += 15

    # ---------------------------------------------------------
    # 5. Purpose match - 10 points
    # ---------------------------------------------------------

    if purpose and (
        _normalize(property_data.get("purpose"))
        == _normalize(purpose)
    ):
        score += 10

    # ---------------------------------------------------------
    # 6. Amenity match - 5 points
    # ---------------------------------------------------------

    requested_amenities = {
        _normalize(amenity)
        for amenity in (desired_amenities or [])
        if _normalize(amenity)
    }

    available_amenities = {
        _normalize(amenity)
        for amenity in property_data.get("amenities", [])
        if _normalize(amenity)
    }

    if requested_amenities:

        matched_amenities = (
            requested_amenities
            & available_amenities
        )

        amenity_ratio = (
            len(matched_amenities)
            / len(requested_amenities)
        )

        score += amenity_ratio * 5

    return round(score, 2)