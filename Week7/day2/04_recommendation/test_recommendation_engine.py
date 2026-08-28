import sys
from pathlib import Path


# Allow imports from 03_structured_retrieval
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "03_structured_retrieval"
    ),
)

# Allow imports from 04_recommendation
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent
    ),
)

from postgres_repository import PostgresPropertyRepository
from recommendation_engine import RecommendationEngine


def print_results(title, results):
    print(f"\n{title}")
    print("=" * 80)

    print(f"Rows returned: {len(results)}")

    for item in results:
        amenities = item.get("amenities", [])

        print(
            f"{item['property_id']} | "
            f"{item['property_name']} | "
            f"{item['area']} | "
            f"{item['price']} {item['currency']} | "
            f"{item['bedrooms']} bedrooms | "
            f"Score={item['recommendation_score']} | "
            f"Amenities={amenities}"
        )


def main():

    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    repository = PostgresPropertyRepository()

    engine = RecommendationEngine(repository)

    print("=" * 80)
    print("RECOMMENDATION ENGINE TESTS")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. BUYER RECOMMENDATION
    # ---------------------------------------------------------

    results = engine.recommend(
        budget=40_000_000,
        city="Lahore",
        bedrooms=3,
        purpose="Purchase",
        limit=5,
    )

    print_results(
        "1. BUYER RECOMMENDATION",
        results,
    )

    if results:
        print("PASS: buyer recommendations returned")
    else:
        print("FAIL: expected buyer recommendations")

    # ---------------------------------------------------------
    # 2. AMENITY RECOMMENDATION
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
        limit=5,
    )

    print_results(
        "2. AMENITY RECOMMENDATION",
        results,
    )

    if results:
        print("PASS: amenity recommendations returned")
    else:
        print("FAIL: expected amenity recommendations")

    # ---------------------------------------------------------
    # 3. RENTAL RECOMMENDATION
    # ---------------------------------------------------------

    results = engine.recommend(
        budget=150_000,
        city="Lahore",
        bedrooms=3,
        purpose="Rental",
        limit=5,
    )

    print_results(
        "3. RENTAL RECOMMENDATION",
        results,
    )

    if results:
        print("PASS: rental recommendations returned")
    else:
        print("FAIL: expected rental recommendations")

    # ---------------------------------------------------------
    # 4. EMPTY RESULT
    # ---------------------------------------------------------

    results = engine.recommend(
        budget=1,
        city="Lahore",
        bedrooms=10,
        purpose="Purchase",
        limit=5,
    )

    print("\n4. EMPTY RESULT")
    print("=" * 80)

    if results == []:
        print(
            "PASS: impossible search correctly "
            "returned empty list"
        )
    else:
        print(
            "FAIL: expected empty recommendation list"
        )

    # ---------------------------------------------------------
    # 5. LIMIT
    # ---------------------------------------------------------

    results = engine.recommend(
        city="Lahore",
        purpose="Purchase",
        limit=2,
    )

    print("\n5. LIMIT TEST")
    print("=" * 80)

    print(f"Rows returned: {len(results)}")

    if len(results) <= 2:
        print("PASS: recommendation limit works")
    else:
        print("FAIL: recommendation limit ignored")

    # ---------------------------------------------------------
    # 6. INVALID BUDGET
    # ---------------------------------------------------------

    print("\n6. INVALID BUDGET")
    print("=" * 80)

    try:
        engine.recommend(
            budget=-100,
            city="Lahore",
        )

        print(
            "FAIL: negative budget should "
            "raise ValueError"
        )

    except ValueError:
        print(
            "PASS: invalid budget correctly rejected"
        )

    # ---------------------------------------------------------
    # 7. INVALID BEDROOMS
    # ---------------------------------------------------------

    print("\n7. INVALID BEDROOMS")
    print("=" * 80)

    try:
        engine.recommend(
            bedrooms=-1,
            city="Lahore",
        )

        print(
            "FAIL: negative bedrooms should "
            "raise ValueError"
        )

    except ValueError:
        print(
            "PASS: invalid bedrooms correctly rejected"
        )

    # ---------------------------------------------------------
    # 8. INVALID LIMIT
    # ---------------------------------------------------------

    print("\n8. INVALID LIMIT")
    print("=" * 80)

    try:
        engine.recommend(
            city="Lahore",
            limit=0,
        )

        print(
            "FAIL: zero limit should "
            "raise ValueError"
        )

    except ValueError:
        print(
            "PASS: invalid limit correctly rejected"
        )

    # ---------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------

    print("\n" + "=" * 80)
    print("ALL RECOMMENDATION ENGINE TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()