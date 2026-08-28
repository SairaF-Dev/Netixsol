from structured_query_parser import (
    StructuredQueryParser,
)


def create_parser():
    return StructuredQueryParser()


# ---------------------------------------------------------------------------
# Budget tests
# ---------------------------------------------------------------------------

def test_crore_budget():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein apartment 4 crore ke andar chahiye."
    )

    assert result["budget"] == 40_000_000

    print("PASS: crore budget")


def test_decimal_crore_budget():

    parser = create_parser()

    result = parser.parse(
        "2.5 crore ka apartment chahiye."
    )

    assert result["budget"] == 25_000_000

    print("PASS: decimal crore budget")


def test_lakh_budget():

    parser = create_parser()

    result = parser.parse(
        "50 lakh ke andar property chahiye."
    )

    assert result["budget"] == 5_000_000

    print("PASS: lakh budget")


def test_pkr_budget():

    parser = create_parser()

    result = parser.parse(
        "Budget 150000 PKR hai."
    )

    assert result["budget"] == 150_000

    print("PASS: PKR budget")


# ---------------------------------------------------------------------------
# Location tests
# ---------------------------------------------------------------------------

def test_city():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein property chahiye."
    )

    assert result["city"] == "Lahore"

    print("PASS: city parsing")


def test_city_alias():

    parser = create_parser()

    result = parser.parse(
        "LHR mein apartment chahiye."
    )

    assert result["city"] == "Lahore"

    print("PASS: city alias")


def test_area():

    parser = create_parser()

    result = parser.parse(
        "DHA Phase 6 Lahore mein apartment chahiye."
    )

    assert result["area"] == "DHA Phase 6"

    assert result["city"] == "Lahore"

    print("PASS: area parsing")


def test_bahria_area():

    parser = create_parser()

    result = parser.parse(
        "Bahria Town mein apartment chahiye."
    )

    assert result["area"] == "Bahria Town"

    print("PASS: Bahria area parsing")


# ---------------------------------------------------------------------------
# Bedroom tests
# ---------------------------------------------------------------------------

def test_bedrooms():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein 3 bedroom apartment chahiye."
    )

    assert result["bedrooms"] == 3

    print("PASS: bedroom parsing")


def test_bedroom_plural():

    parser = create_parser()

    result = parser.parse(
        "I need a 4 bedrooms house."
    )

    assert result["bedrooms"] == 4

    print("PASS: bedroom plural parsing")


# ---------------------------------------------------------------------------
# Property type
# ---------------------------------------------------------------------------

def test_apartment_type():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein apartment chahiye."
    )

    assert result["property_type"] == "Apartment"

    print("PASS: apartment type")


def test_flat_alias():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein flat chahiye."
    )

    assert result["property_type"] == "Apartment"

    print("PASS: flat alias")


def test_house_type():

    parser = create_parser()

    result = parser.parse(
        "DHA mein house chahiye."
    )

    assert result["property_type"] == "House"

    print("PASS: house type")


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------

def test_purchase_purpose():

    parser = create_parser()

    result = parser.parse(
        "I want to buy an apartment in Lahore."
    )

    assert result["purpose"] == "Purchase"

    print("PASS: purchase purpose")


def test_rental_purpose():

    parser = create_parser()

    result = parser.parse(
        "3 bedroom rental Lahore mein chahiye."
    )

    assert result["purpose"] == "Rental"

    print("PASS: rental purpose")


# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------

def test_single_amenity():

    parser = create_parser()

    result = parser.parse(
        "Apartment with swimming pool."
    )

    assert result["amenities"] == [
        "Swimming Pool"
    ]

    print("PASS: single amenity")


def test_multiple_amenities():

    parser = create_parser()

    result = parser.parse(
        "Lahore apartment with gym, parking and security."
    )

    assert set(result["amenities"]) == {
        "Gym",
        "Parking",
        "Security",
    }

    print("PASS: multiple amenities")


# ---------------------------------------------------------------------------
# Complete query
# ---------------------------------------------------------------------------

def test_complete_buyer_query():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein DHA Phase 6 "
        "3 bedroom apartment "
        "4 crore ke andar "
        "buy karna hai."
    )

    assert result == {
        "budget": 40_000_000,
        "city": "Lahore",
        "area": "DHA Phase 6",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "Purchase",
        "amenities": [],
    }

    print("PASS: complete buyer query")


def test_complete_rental_query():

    parser = create_parser()

    result = parser.parse(
        "Lahore mein 3 bedroom apartment "
        "150,000 PKR rental chahiye."
    )

    assert result["budget"] == 150_000

    assert result["city"] == "Lahore"

    assert result["bedrooms"] == 3

    assert result["property_type"] == "Apartment"

    assert result["purpose"] == "Rental"

    print("PASS: complete rental query")


# ---------------------------------------------------------------------------
# Unknown values
# ---------------------------------------------------------------------------

def test_unknown_filters_return_none():

    parser = create_parser()

    result = parser.parse(
        "Mujhe property chahiye."
    )

    assert result["budget"] is None

    assert result["city"] is None

    assert result["area"] is None

    assert result["bedrooms"] is None

    assert result["property_type"] is None

    assert result["purpose"] is None

    assert result["amenities"] == []

    print("PASS: unknown filters handled safely")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_empty_question():

    parser = create_parser()

    try:
        parser.parse("")

    except ValueError:
        print(
            "PASS: empty question rejected"
        )
        return

    raise AssertionError(
        "Empty question should raise ValueError."
    )


def test_whitespace_question():

    parser = create_parser()

    try:
        parser.parse("   ")

    except ValueError:
        print(
            "PASS: whitespace question rejected"
        )
        return

    raise AssertionError(
        "Whitespace question should raise ValueError."
    )


def test_non_string_question():

    parser = create_parser()

    try:
        parser.parse(123)

    except TypeError:
        print(
            "PASS: non-string question rejected"
        )
        return

    raise AssertionError(
        "Non-string question should raise TypeError."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    print("=" * 80)
    print("STRUCTURED QUERY PARSER TESTS")
    print("=" * 80)

    test_crore_budget()
    test_decimal_crore_budget()
    test_lakh_budget()
    test_pkr_budget()

    test_city()
    test_city_alias()
    test_area()
    test_bahria_area()

    test_bedrooms()
    test_bedroom_plural()

    test_apartment_type()
    test_flat_alias()
    test_house_type()

    test_purchase_purpose()
    test_rental_purpose()

    test_single_amenity()
    test_multiple_amenities()

    test_complete_buyer_query()
    test_complete_rental_query()

    test_unknown_filters_return_none()

    test_empty_question()
    test_whitespace_question()
    test_non_string_question()

    print("\n" + "=" * 80)
    print(
        "ALL STRUCTURED QUERY PARSER TESTS PASSED"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()