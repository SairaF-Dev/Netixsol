from filters import validate_filters
from scoring import score_property


class RecommendationEngine:
    """
    Production recommendation engine.

    PostgreSQL is the source of truth for property data.
    """

    def __init__(self, repository):
        if repository is None:
            raise ValueError("repository is required")

        self.repository = repository

    def recommend(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose=None,
        desired_amenities=None,
        investment_goal=None,
        limit=5,
    ):
        """
        Retrieve eligible properties from PostgreSQL
        and rank them using recommendation scoring.
        """

        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValueError("limit must be a positive integer")

        if limit <= 0:
            raise ValueError(
                "limit must be greater than 0"
            )

        filters = validate_filters(
            budget=budget,
            city=city,
            area=area,
            bedrooms=bedrooms,
            property_type=property_type,
            purpose=purpose,
            investment_goal=investment_goal,
        )

        desired_amenities = [
            str(amenity).strip()
            for amenity in (desired_amenities or [])
            if amenity is not None
            and str(amenity).strip()
        ]

        properties = self.repository.search(
            budget=filters["budget"],
            city=filters["city"],
            area=filters["area"],
            bedrooms=filters["bedrooms"],
            property_type=filters["property_type"],
            purpose=filters["purpose"],
            amenities=desired_amenities,
        )

        ranked = []

        for property_data in properties:
            score = score_property(
                property_data,
                budget=filters["budget"],
                city=filters["city"],
                area=filters["area"],
                bedrooms=filters["bedrooms"],
                purpose=filters["purpose"],
                desired_amenities=desired_amenities,
                investment_goal=filters["investment_goal"],
            )

            result = dict(property_data)
            result["recommendation_score"] = score
            result["investment_goal"] = filters["investment_goal"]

            ranked.append(result)

        ranked.sort(
            key=lambda item: (
                item["recommendation_score"],
                -float(item["price"])
                if item.get("price") is not None
                else 0,
            ),
            reverse=True,
        )

        return ranked[:limit]