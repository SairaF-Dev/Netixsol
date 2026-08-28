from decimal import Decimal

from postgres_repository import PostgresPropertyRepository


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    repo = PostgresPropertyRepository()

    # ============================================================
    # 1. EXACT PROPERTY LOOKUP
    # ============================================================

    print("\n1. EXACT LOOKUP")
    print("=" * 70)

    result = repo.get_property("LHR-DHA-APT-002")

    assert_true(
        result is not None,
        "Expected LHR-DHA-APT-002 to exist",
    )

    assert_true(
        result["property_id"] == "LHR-DHA-APT-002",
        "Wrong property_id returned",
    )

    assert_true(
        result["property_name"] == "Horizon Heights Apartment",
        "Wrong property name",
    )

    assert_true(
        result["city"] == "Lahore",
        "Wrong city",
    )

    assert_true(
        result["bedrooms"] == 3,
        "Wrong bedroom count",
    )

    assert_true(
        result["bathrooms"] == 3,
        "Wrong bathroom count",
    )

    assert_true(
        result["price"] == Decimal("36000000"),
        "Wrong property price",
    )

    assert_true(
        result["currency"] == "PKR",
        "Wrong currency",
    )

    assert_true(
        result["available"] is True,
        "Property should be available",
    )

    assert_true(
        result["verification_status"] == "Verified",
        "Property price should be verified",
    )

    print("PASS: exact property lookup")


    # ============================================================
    # 2. NON-EXISTENT PROPERTY
    # ============================================================

    print("\n2. NON-EXISTENT PROPERTY")
    print("=" * 70)

    result = repo.get_property("MOONLIGHT-001")

    assert_true(
        result is None,
        "Unknown property should return None",
    )

    print("PASS: unknown property correctly returned None")


    # ============================================================
    # 3. STRUCTURED PROPERTY SEARCH
    # ============================================================

    print("\n3. STRUCTURED SEARCH")
    print("=" * 70)

    results = repo.search(
        budget=40_000_000,
        city="Lahore",
        bedrooms=3,
        purpose="Purchase",
    )

    print(f"Rows returned: {len(results)}")

    assert_true(
        len(results) > 0,
        "Expected structured search to return properties",
    )

    for item in results:
        print(
            f"{item['property_id']} | "
            f"{item['property_name']} | "
            f"{item['price']} {item['currency']} | "
            f"{item['city']} | "
            f"{item['bedrooms']} bedrooms"
        )

        # Verify every returned record satisfies filters.
        assert_true(
            item["city"].lower() == "lahore",
            "Search returned property outside Lahore",
        )

        assert_true(
            item["bedrooms"] == 3,
            "Search returned property with wrong bedroom count",
        )

        assert_true(
            item["purpose"].lower() == "purchase",
            "Search returned non-purchase property",
        )

        assert_true(
            item["price"] <= Decimal("40000000"),
            "Search returned property above budget",
        )

        assert_true(
            item["available"] is True,
            "Search returned unavailable property",
        )

    # Verify ascending price ordering.
    prices = [item["price"] for item in results]

    assert_true(
        prices == sorted(prices),
        "Results are not ordered by price ascending",
    )

    print("PASS: structured search returned valid PostgreSQL records")


    # ============================================================
    # 4. AMENITY FILTER
    # ============================================================

    print("\n4. AMENITY FILTER")
    print("=" * 70)

    results = repo.search(
        city="Lahore",
        purpose="Purchase",
        amenities=["Swimming Pool", "Gym"],
    )

    print(f"Rows returned: {len(results)}")

    assert_true(
        len(results) > 0,
        "Expected properties with Swimming Pool + Gym",
    )

    for item in results:
        print(
            f"{item['property_id']} | "
            f"{item['property_name']} | "
            f"amenities={item['amenities']}"
        )

        amenities = {
            amenity.lower()
            for amenity in item["amenities"]
        }

        assert_true(
            "swimming pool" in amenities,
            f"{item['property_id']} missing Swimming Pool",
        )

        assert_true(
            "gym" in amenities,
            f"{item['property_id']} missing Gym",
        )

    print("PASS: amenity filtering works correctly")


    # ============================================================
    # 5. EMPTY SEARCH
    # ============================================================

    print("\n5. EMPTY SEARCH")
    print("=" * 70)

    results = repo.search(
        city="Lahore",
        bedrooms=99,
    )

    assert_true(
        results == [],
        "Expected empty list for impossible search",
    )

    print("PASS: impossible search correctly returned empty list")


    # ============================================================
    # FINAL RESULT
    # ============================================================

    print("\n" + "=" * 70)
    print("ALL POSTGRESQL REPOSITORY TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("\n" + "=" * 70)
        print("TEST FAILED")
        print("=" * 70)
        print(f"Reason: {error}")
        raise
    except Exception as error:
        print("\n" + "=" * 70)
        print("UNEXPECTED ERROR")
        print("=" * 70)
        print(f"{type(error).__name__}: {error}")
        raise