from recommendation_engine import RecommendationEngine


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    def search(self, **kwargs):
        return list(self.rows)


def test_rental_income_goal_prefers_rental_property():
    rows = [
        {
            "property_id": "P1",
            "property_name": "Rental Flat",
            "city": "Lahore",
            "area": "DHA",
            "bedrooms": 2,
            "property_type": "Apartment",
            "purpose": "Rental",
            "price": 100000,
            "amenities": [],
        },
        {
            "property_id": "P2",
            "property_name": "Sale Flat",
            "city": "Lahore",
            "area": "DHA",
            "bedrooms": 2,
            "property_type": "Apartment",
            "purpose": "Purchase",
            "price": 100000,
            "amenities": [],
        },
    ]

    results = RecommendationEngine(FakeRepository(rows)).recommend(
        investment_goal="rental income",
        limit=2,
    )

    assert results[0]["property_id"] == "P1"
    assert results[0]["recommendation_score"] == 10.0
    assert results[1]["recommendation_score"] == 0.0


def test_unknown_goal_does_not_invent_financial_score():
    rows = [{
        "property_id": "P1",
        "property_name": "Verified Property",
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 2,
        "property_type": "Apartment",
        "purpose": "Purchase",
        "price": 100000,
        "amenities": [],
    }]

    result = RecommendationEngine(FakeRepository(rows)).recommend(
        investment_goal="guaranteed 30 percent ROI",
        limit=1,
    )[0]

    assert result["recommendation_score"] == 0.0
