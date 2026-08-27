from filters import validate_filters
from scoring import score_property


class RecommendationEngine:
    """
    Production recommendation engine.

    PostgreSQL is the source of truth for property data.
    """

    def __init__(self, repository):
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
        limit=5,
    ):
        """
        Retrieve eligible properties from PostgreSQL
        and rank them using the recommendation score.
        """

        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        # ---------------------------------------------------------
        # 1. Validate basic search filters
        # ---------------------------------------------------------

        filters = validate_filters(
            budget=budget,
            city=city,
            area=area,
            bedrooms=bedrooms,
            property_type=property_type,
            purpose=purpose,
        )

        # ---------------------------------------------------------
        # 2. Normalize requested amenities
        # ---------------------------------------------------------

        desired_amenities = [
            amenity.strip()
            for amenity in (desired_amenities or [])
            if amenity and amenity.strip()
        ]

        # ---------------------------------------------------------
        # 3. Retrieve matching properties from PostgreSQL
        # ---------------------------------------------------------

        properties = self.repository.search(
            budget=filters["budget"],
            city=filters["city"],
            area=filters["area"],
            bedrooms=filters["bedrooms"],
            property_type=filters["property_type"],
            purpose=filters["purpose"],
            amenities=desired_amenities,
        )

        # ---------------------------------------------------------
        # 4. Score each property
        # ---------------------------------------------------------

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
            )

            result = dict(property_data)
            result["recommendation_score"] = score

            ranked.append(result)

        # ---------------------------------------------------------
        # 5. Rank highest score first
        # ---------------------------------------------------------

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


if __name__ == "__main__":

    import sys
    from pathlib import Path

    # Allow importing the PostgreSQL repository
    sys.path.insert(
        0,
        str(
            Path(__file__).resolve().parents[1]
            / "03_structured_retrieval"
        ),
    )

    from postgres_repository import PostgresPropertyRepository

    repository = PostgresPropertyRepository()

    engine = RecommendationEngine(repository)

    # ---------------------------------------------------------
    # Production-style test
    # ---------------------------------------------------------

    results = engine.recommend(
        budget=40_000_000,
        city="Lahore",
        bedrooms=3,
        purpose="Purchase",
        desired_amenities=[
            "Swimming Pool",
            "Gym",
        ],
    )

    print("\nRECOMMENDATIONS")
    print("=" * 80)

    if not results:
        print("No matching properties found.")

    else:
        for result in results:
            print(
                f"{result['property_name']} | "
                f"{result['area']} | "
                f"{result['bedrooms']} bedrooms | "
                f"{result['price']} {result['currency']} | "
                f"Amenities: {', '.join(result.get('amenities', []))} | "
                f"Score={result['recommendation_score']}"
            )