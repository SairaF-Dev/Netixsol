from decimal import Decimal


def _normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def _investment_goal_score(property_data, investment_goal):
    """
    Score an investment preference using only verified property facts.

    This function deliberately does NOT estimate ROI, rental yield,
    appreciation, or future profit because those facts are not present
    in the verified Day 2 dataset.
    """

    goal = _normalize(investment_goal)

    if not goal:
        return 0.0

    purpose = _normalize(property_data.get("purpose"))
    property_type = _normalize(property_data.get("property_type"))

    rental_terms = (
        "rental income",
        "rent income",
        "monthly income",
        "cash flow",
        "cashflow",
    )

    purchase_terms = (
        "capital appreciation",
        "long term",
        "long-term",
        "investment",
        "resale",
    )

    commercial_terms = (
        "commercial",
        "business",
        "office",
        "shop",
    )

    plot_terms = (
        "plot",
        "land",
    )

    if any(term in goal for term in rental_terms):
        return 10.0 if purpose == "rental" else 0.0

    if any(term in goal for term in commercial_terms):
        return 10.0 if "commercial" in property_type else 0.0

    if any(term in goal for term in plot_terms):
        return 10.0 if "plot" in property_type else 0.0

    if any(term in goal for term in purchase_terms):
        return 10.0 if purpose == "purchase" else 0.0

    # Unknown goals are accepted but do not receive an evidence-free bonus.
    return 0.0


def score_property(
    property_data,
    budget=None,
    city=None,
    area=None,
    bedrooms=None,
    purpose=None,
    desired_amenities=None,
    investment_goal=None,
):
    """
    Calculate a recommendation score using verified PostgreSQL facts.

    Investment goals influence ranking only where they can be mapped to
    existing structured facts. No financial return is predicted.
    """

    score = 0.0

    price = property_data.get("price")

    if price is not None:
        price = Decimal(str(price))

    # 1. Budget match - 35 points
    if budget is not None and price is not None:
        budget = Decimal(str(budget))
        if price <= budget:
            score += 35

    # 2. City match - 20 points
    if city and _normalize(property_data.get("city")) == _normalize(city):
        score += 20

    # 3. Area match - 15 points
    if area and _normalize(area) in _normalize(property_data.get("area")):
        score += 15

    # 4. Bedroom match - 15 points
    if bedrooms is not None and property_data.get("bedrooms") == bedrooms:
        score += 15

    # 5. Purpose match - 10 points
    if purpose and _normalize(property_data.get("purpose")) == _normalize(purpose):
        score += 10

    # 6. Amenity match - up to 5 points
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
        matched_amenities = requested_amenities & available_amenities
        score += (len(matched_amenities) / len(requested_amenities)) * 5

    # 7. Investment-goal match - 10 grounded bonus points
    score += _investment_goal_score(
        property_data,
        investment_goal,
    )

    return round(score, 2)
