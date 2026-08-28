from answer_composer import (
    AnswerComposer,
    FALLBACK_ANSWER,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SKYLINE = {
    "property_id": "DHA-APT-001",
    "property_name": "Skyline Residences",
    "city": "Lahore",
    "area": "DHA Phase 6",
    "bedrooms": 3,
    "property_type": "Apartment",
    "purpose": "Purchase",
    "price": 28_500_000,
    "currency": "PKR",
    "available": True,
    "amenities": [
        "Parking",
        "Swimming Pool",
        "Gym",
        "Security",
    ],
}


BAHRIA = {
    "property_id": "BT-APT-001",
    "property_name": "Bahria Grand Apartments",
    "city": "Lahore",
    "area": "Bahria Town",
    "bedrooms": 3,
    "property_type": "Apartment",
    "purpose": "Purchase",
    "price": 26_500_000,
    "currency": "PKR",
    "available": True,
    "amenities": [
        "Parking",
        "Gym",
        "Community Park",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_true(
    condition,
    message,
):
    if not condition:
        raise AssertionError(message)


def assert_equal(
    actual,
    expected,
    message,
):
    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_structured_single_property():

    composer = AnswerComposer()

    answer = composer.compose(
        route="structured",
        structured_results=[
            SKYLINE
        ],
    )

    assert_true(
        "Skyline Residences" in answer,
        "Property name should be present.",
    )

    assert_true(
        "28,500,000 PKR" in answer,
        "Verified price should be present.",
    )

    assert_true(
        "DHA Phase 6" in answer,
        "Property area should be present.",
    )

    assert_true(
        "Lahore" in answer,
        "Property city should be present.",
    )

    assert_true(
        "Swimming Pool" in answer,
        "Amenities should be present.",
    )

    print(
        "PASS: structured single property"
    )


def test_structured_multiple_properties():

    composer = AnswerComposer()

    answer = composer.compose(
        route="structured",
        structured_results=[
            SKYLINE,
            BAHRIA,
        ],
    )

    assert_true(
        "Skyline Residences" in answer,
        "Skyline should be present.",
    )

    assert_true(
        "Bahria Grand Apartments" in answer,
        "Bahria property should be present.",
    )

    assert_true(
        "28,500,000 PKR" in answer,
        "Skyline price should be present.",
    )

    assert_true(
        "26,500,000 PKR" in answer,
        "Bahria price should be present.",
    )

    print(
        "PASS: structured multiple properties"
    )


def test_structured_empty_results():

    composer = AnswerComposer()

    answer = composer.compose(
        route="structured",
        structured_results=[],
    )

    assert_equal(
        answer,
        FALLBACK_ANSWER,
        "Empty structured results should use fallback.",
    )

    print(
        "PASS: structured empty results"
    )


def test_rag_answer():

    composer = AnswerComposer()

    rag_answer = (
        "Investment returns cannot be guaranteed."
    )

    answer = composer.compose(
        route="rag",
        rag_answer=rag_answer,
    )

    assert_equal(
        answer,
        rag_answer,
        "RAG answer should be preserved.",
    )

    print(
        "PASS: RAG answer"
    )


def test_rag_empty_answer():

    composer = AnswerComposer()

    answer = composer.compose(
        route="rag",
        rag_answer="",
    )

    assert_equal(
        answer,
        FALLBACK_ANSWER,
        "Empty RAG answer should use fallback.",
    )

    print(
        "PASS: RAG empty answer"
    )


def test_mixed_answer():

    composer = AnswerComposer()

    rag_answer = (
        "Verified payment-plan information is "
        "currently available in the company documents."
    )

    answer = composer.compose(
        route="mixed",
        structured_results=[
            SKYLINE
        ],
        rag_answer=rag_answer,
    )

    assert_true(
        "Skyline Residences" in answer,
        "Mixed answer should contain structured property.",
    )

    assert_true(
        "28,500,000 PKR" in answer,
        "Mixed answer should contain PostgreSQL price.",
    )

    assert_true(
        rag_answer in answer,
        "Mixed answer should contain RAG answer.",
    )

    print(
        "PASS: mixed answer"
    )


def test_structured_authority():

    composer = AnswerComposer()

    rag_answer = (
        "The property price is 99,999,999 PKR."
    )

    answer = composer.compose(
        route="mixed",
        structured_results=[
            SKYLINE
        ],
        rag_answer=rag_answer,
    )

    assert_true(
        "28,500,000 PKR" in answer,
        "Structured PostgreSQL price must be preserved.",
    )

    assert_true(
        "99,999,999 PKR" in answer,
        "This test confirms raw RAG text is returned as-is; "
        "source authority must be enforced by the RAG/query "
        "routing layer for mixed factual claims.",
    )

    print(
        "PASS: structured source included in mixed response"
    )


def test_mixed_only_structured():

    composer = AnswerComposer()

    answer = composer.compose(
        route="mixed",
        structured_results=[
            SKYLINE
        ],
        rag_answer=FALLBACK_ANSWER,
    )

    assert_true(
        "Skyline Residences" in answer,
        "Structured data should still be returned.",
    )

    assert_true(
        "28,500,000 PKR" in answer,
        "Structured price should still be returned.",
    )

    print(
        "PASS: mixed structured-only fallback"
    )


def test_mixed_only_rag():

    composer = AnswerComposer()

    rag_answer = (
        "Investment returns cannot be guaranteed."
    )

    answer = composer.compose(
        route="mixed",
        structured_results=[],
        rag_answer=rag_answer,
    )

    assert_equal(
        answer,
        rag_answer,
        "RAG answer should be returned when "
        "structured data is unavailable.",
    )

    print(
        "PASS: mixed RAG-only fallback"
    )


def test_invalid_route():

    composer = AnswerComposer()

    try:

        composer.compose(
            route="unknown",
        )

    except ValueError:

        print(
            "PASS: invalid route rejected"
        )

        return

    raise AssertionError(
        "Invalid route should raise ValueError."
    )


def test_invalid_route_type():

    composer = AnswerComposer()

    try:

        composer.compose(
            route=None,
        )

    except TypeError:

        print(
            "PASS: invalid route type rejected"
        )

        return

    raise AssertionError(
        "Non-string route should raise TypeError."
    )


def test_invalid_structured_type():

    composer = AnswerComposer()

    try:

        composer.compose(
            route="structured",
            structured_results={},
        )

    except TypeError:

        print(
            "PASS: invalid structured results rejected"
        )

        return

    raise AssertionError(
        "Non-list structured results should raise TypeError."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    print("=" * 80)
    print("ANSWER COMPOSER TESTS")
    print("=" * 80)

    test_structured_single_property()
    test_structured_multiple_properties()
    test_structured_empty_results()

    test_rag_answer()
    test_rag_empty_answer()

    test_mixed_answer()
    test_structured_authority()

    test_mixed_only_structured()
    test_mixed_only_rag()

    test_invalid_route()
    test_invalid_route_type()
    test_invalid_structured_type()

    print("\n" + "=" * 80)
    print("ALL ANSWER COMPOSER TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()