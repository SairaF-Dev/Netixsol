from knowledge_router import KnowledgeRouter


# ---------------------------------------------------------------------------
# Fake structured repository
# ---------------------------------------------------------------------------

class FakeRepository:
    """
    Deterministic fake repository for integration testing.

    No PostgreSQL connection is required.
    """

    def __init__(self):
        self.search_called = False
        self.last_search_args = {}

    def search(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose=None,
        amenities=None,
    ):
        self.search_called = True
        self.last_search_args = {
            "budget": budget,
            "city": city,
            "area": area,
            "bedrooms": bedrooms,
            "property_type": property_type,
            "purpose": purpose,
            "amenities": amenities,
        }

        return [
            {
                "property_id": "LHR-DHA-APT-001",
                "property_name": "Horizon Heights Apartment",
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
        ]


# ---------------------------------------------------------------------------
# Fake RAG pipeline
# ---------------------------------------------------------------------------

class FakeRAGPipeline:
    """
    Deterministic fake RAG pipeline.

    No OpenRouter or embedding model is required.
    """

    def __init__(self):
        self.answer_called = False

    def answer(self, question):
        self.answer_called = True

        if "payment plan" in question.lower():

            return {
                "question": question,
                "results": [
                    {
                        "source": "real_estate_faq.md",
                        "chunk_id": 0,
                        "distance": 0.20,
                        "text": (
                            "Verified information about "
                            "payment plans is available."
                        ),
                    }
                ],
                "answer": (
                    "Verified information about "
                    "payment plans is available."
                ),
            }

        if "guarantee" in question.lower():

            return {
                "question": question,
                "results": [
                    {
                        "source": "real_estate_faq.md",
                        "chunk_id": 1,
                        "distance": 0.21,
                        "text": (
                            "Investment returns cannot "
                            "be guaranteed."
                        ),
                    }
                ],
                "answer": (
                    "Investment returns cannot "
                    "be guaranteed."
                ),
            }

        return {
            "question": question,
            "results": [],
            "answer": (
                "Verified information is currently unavailable."
            ),
        }


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def build_router():
    repository = FakeRepository()
    rag_pipeline = FakeRAGPipeline()

    router = KnowledgeRouter(
        repository=repository,
        rag_pipeline=rag_pipeline,
    )

    return router, repository, rag_pipeline


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_structured_route():

    router, repository, rag = build_router()

    result = router.answer(
        "What is the price of Horizon Heights Apartment?"
    )

    assert_equal(
        result["route"],
        "structured",
        "Price question should use structured retrieval.",
    )

    assert_true(
        len(result["structured_results"]) == 1,
        "Structured result should be returned.",
    )

    assert_equal(
        result["structured_results"][0]["property_name"],
        "Horizon Heights Apartment",
        "Expected Skyline property.",
    )

    assert_true(
        repository.search_called,
        "Repository.search() should be called.",
    )

    assert_true(
        not rag.answer_called,
        "RAG should not be called for structured-only queries.",
    )

    print(
        "PASS: structured route"
    )


def test_structured_filter_passing():

    router, repository, rag = build_router()

    result = router.answer(
        "Lahore mein 3 bedroom apartment 4 crore ke andar chahiye."
    )

    assert_equal(
        result["route"],
        "structured",
        "Search query should use structured retrieval.",
    )

    assert_true(
        repository.search_called,
        "Repository.search() should be called.",
    )

    assert_equal(
        repository.last_search_args.get("city"),
        "Lahore",
        "City filter should be passed to repository.",
    )

    assert_equal(
        repository.last_search_args.get("bedrooms"),
        3,
        "Bedrooms filter should be passed to repository.",
    )

    assert_equal(
        repository.last_search_args.get("budget"),
        40_000_000,
        "Budget filter should be passed to repository.",
    )

    print(
        "PASS: structured filter passing"
    )


def test_rag_route():

    router, repository, rag = build_router()

    result = router.answer(
        "What is the payment plan?"
    )

    assert_equal(
        result["route"],
        "rag",
        "Payment-plan question should use RAG.",
    )

    assert_true(
        len(result["rag_results"]) == 1,
        "RAG result should be returned.",
    )

    assert_true(
        rag.answer_called,
        "RAG pipeline should be called.",
    )

    assert_true(
        not repository.search_called,
        "PostgreSQL should not be called for RAG-only queries.",
    )

    assert_equal(
        result["answer"],
        (
            "Verified information about "
            "payment plans is available."
        ),
        "Unexpected RAG answer.",
    )

    print(
        "PASS: rag route"
    )


def test_mixed_route():

    router, repository, rag = build_router()

    result = router.answer(
        "Skyline ki price aur payment plan kya hai?"
    )

    assert_equal(
        result["route"],
        "mixed",
        "Mixed question should use both sources.",
    )

    assert_true(
        len(result["structured_results"]) == 1,
        "Mixed query should contain structured results.",
    )

    assert_true(
        len(result["rag_results"]) == 1,
        "Mixed query should contain RAG results.",
    )

    assert_true(
        repository.search_called,
        "Mixed query must call PostgreSQL.",
    )

    assert_true(
        rag.answer_called,
        "Mixed query must call RAG.",
    )

    print(
        "PASS: mixed route"
    )


def test_mixed_guarantee_question():

    router, repository, rag = build_router()

    result = router.answer(
        "Skyline ka developer kon hai aur "
        "investment return guaranteed hai?"
    )

    assert_equal(
        result["route"],
        "mixed",
        "Mixed developer/investment question "
        "should use both sources.",
    )

    assert_true(
        len(result["structured_results"]) == 1,
        "Structured developer data should be available.",
    )

    assert_true(
        len(result["rag_results"]) == 1,
        "Investment-policy RAG data should be available.",
    )

    assert_equal(
        result["answer"],
        (
            "Investment returns cannot "
            "be guaranteed."
        ),
        "Investment guarantee answer is incorrect.",
    )

    print(
        "PASS: mixed guarantee question"
    )


def test_empty_question():

    router, _, _ = build_router()

    try:
        router.answer("")

    except ValueError:
        print(
            "PASS: empty question rejected"
        )
        return

    raise AssertionError(
        "Empty question should raise ValueError."
    )


def test_non_string_question():

    router, _, _ = build_router()

    try:
        router.answer(None)

    except TypeError:
        print(
            "PASS: non-string question rejected"
        )
        return

    raise AssertionError(
        "Non-string question should raise TypeError."
    )


def test_whitespace_question():

    router, _, _ = build_router()

    try:
        router.answer("   ")

    except ValueError:
        print(
            "PASS: whitespace question rejected"
        )
        return

    raise AssertionError(
        "Whitespace-only question should raise ValueError."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    print("=" * 80)
    print("KNOWLEDGE ROUTER TESTS")
    print("=" * 80)

    test_structured_route()
    test_structured_filter_passing()
    test_rag_route()
    test_mixed_route()
    test_mixed_guarantee_question()
    test_empty_question()
    test_non_string_question()
    test_whitespace_question()

    print("\n" + "=" * 80)
    print(
        "ALL KNOWLEDGE ROUTER TESTS PASSED"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()