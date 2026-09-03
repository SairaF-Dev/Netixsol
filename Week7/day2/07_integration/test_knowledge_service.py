import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STRUCTURED_DIR = (
    ROOT / "03_structured_retrieval"
)

sys.path.insert(
    0,
    str(STRUCTURED_DIR),
)

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent),
)


from knowledge_service import KnowledgeService


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeParser:

    def __init__(self, result):
        self.result = result
        self.questions = []

    def parse(self, question):
        self.questions.append(question)
        return self.result


class FakeRepository:

    def __init__(self):
        self.search_calls = []
        self.name_calls = []
        self.property_calls = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)

        return [
            {
                "property_id": "LHR-LHR-DHA-APT-003",
                "property_name": "Horizon Heights Apartment",
                "area": "DHA Phase 6",
                "city": "Lahore",
                "property_type": "Apartment",
                "bedrooms": 3,
                "bathrooms": 3,
                "price": 36_000_000,
                "currency": "PKR",
                "purpose": "Purchase",
                "available": True,
                "amenities": [
                    "Parking",
                    "Security",
                ],
            }
        ]

    def get_property_by_name(self, property_name):
        self.name_calls.append(property_name)

        return {
            "property_id": "LHR-LHR-DHA-APT-003",
            "property_name": property_name,
            "city": "Lahore",
            "price": 36_000_000,
            "currency": "PKR",
        }


class FakeRAG:

    def __init__(self, answer=None):
        self.answer_value = answer
        self.calls = []

    def answer(self, question):
        self.calls.append(question)
        return self.answer_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_raises(expected_exception, fn):
    try:
        fn()
    except expected_exception:
        return

    raise AssertionError(
        f"Expected {expected_exception.__name__}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_structured_service():
    repository = FakeRepository()

    parser = FakeParser(
        {
            "budget": 40_000_000,
            "city": "Lahore",
            "area": None,
            "bedrooms": 3,
            "property_type": "Apartment",
            "purpose": "Purchase",
            "amenities": [],
        }
    )

    rag = FakeRAG(
        "RAG should not be called."
    )

    service = KnowledgeService(
        repository,
        rag,
        parser,
    )

    result = service.answer(
        "Lahore mein 3 bedroom apartment 4 crore ke andar.",
        "structured",
    )

    assert len(
        result["structured_results"]
    ) == 1

    assert result["rag_answer"] is None

    assert "postgresql" in result["sources"]

    assert len(
        repository.search_calls
    ) == 1

    assert len(
        rag.calls
    ) == 0

    print(
        "PASS: structured service"
    )


def test_rag_service():
    repository = FakeRepository()

    parser = FakeParser({})

    rag = FakeRAG(
        "Verified payment-plan information."
    )

    service = KnowledgeService(
        repository,
        rag,
        parser,
    )

    result = service.answer(
        "What is the payment plan?",
        "rag",
    )

    assert result["structured_results"] == []

    assert (
        result["rag_answer"]
        == "Verified payment-plan information."
    )

    assert len(
        repository.search_calls
    ) == 0

    assert len(
        rag.calls
    ) == 1

    print(
        "PASS: RAG service"
    )


def test_mixed_service():
    repository = FakeRepository()

    parser = FakeParser(
        {
            "budget": None,
            "city": "Lahore",
            "area": None,
            "bedrooms": None,
            "property_type": "Apartment",
            "purpose": None,
            "amenities": [],
        }
    )

    rag = FakeRAG(
        "Verified payment-plan information."
    )

    service = KnowledgeService(
        repository,
        rag,
        parser,
    )

    result = service.answer(
        "Lahore apartment payment plan?",
        "mixed",
    )

    assert len(
        result["structured_results"]
    ) == 1

    assert (
        result["rag_answer"]
        == "Verified payment-plan information."
    )

    assert "postgresql" in result["sources"]
    assert "rag" in result["sources"]

    assert len(
        repository.search_calls
    ) == 1

    assert len(
        rag.calls
    ) == 1

    print(
        "PASS: mixed service"
    )


def test_rental_routing():
    repository = FakeRepository()

    parser = FakeParser(
        {
            "budget": 150_000,
            "city": "Lahore",
            "area": None,
            "bedrooms": 3,
            "property_type": "Apartment",
            "purpose": "Rental",
            "amenities": [],
        }
    )

    rag = FakeRAG()

    service = KnowledgeService(
        repository,
        rag,
        parser,
    )

    result = service.answer(
        "3 bedroom rental Lahore",
        "structured",
    )

    assert (
        result["filters"]["purpose"]
        == "Rental"
    )

    print(
        "PASS: rental routing"
    )


def test_question_normalization():
    repository = FakeRepository()

    parser = FakeParser({})

    rag = FakeRAG()

    service = KnowledgeService(
        repository,
        rag,
        parser,
    )

    result = service.answer(
        "   Lahore    apartment   ",
        "rag",
    )

    assert (
        result["question"]
        == "Lahore apartment"
    )

    print(
        "PASS: question normalization"
    )


def test_empty_question_rejected():
    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        FakeParser({}),
    )

    assert_raises(
        ValueError,
        lambda: service.answer(
            "",
            "rag",
        ),
    )

    print(
        "PASS: empty question rejected"
    )


def test_whitespace_question_rejected():
    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        FakeParser({}),
    )

    assert_raises(
        ValueError,
        lambda: service.answer(
            "     ",
            "rag",
        ),
    )

    print(
        "PASS: whitespace question rejected"
    )


def test_non_string_question_rejected():
    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        FakeParser({}),
    )

    assert_raises(
        TypeError,
        lambda: service.answer(
            123,
            "rag",
        ),
    )

    print(
        "PASS: non-string question rejected"
    )


def test_invalid_route_rejected():
    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        FakeParser({}),
    )

    assert_raises(
        ValueError,
        lambda: service.answer(
            "hello",
            "invalid",
        ),
    )

    print(
        "PASS: invalid route rejected"
    )


def test_non_string_route_rejected():
    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        FakeParser({}),
    )

    assert_raises(
        TypeError,
        lambda: service.answer(
            "hello",
            123,
        ),
    )

    print(
        "PASS: non-string route rejected"
    )


def test_invalid_repository_result_rejected():
    class BadRepository:
        def search(self, **kwargs):
            return "not a list"

    parser = FakeParser(
        {
            "city": "Lahore",
        }
    )

    service = KnowledgeService(
        BadRepository(),
        FakeRAG(),
        parser,
    )

    assert_raises(
        TypeError,
        lambda: service.answer(
            "Lahore apartments",
            "structured",
        ),
    )

    print(
        "PASS: invalid repository result rejected"
    )


def test_invalid_rag_result_rejected():
    class BadRAG:
        def answer(self, question):
            return {"bad": "result"}

    service = KnowledgeService(
        FakeRepository(),
        BadRAG(),
        FakeParser({}),
    )

    assert_raises(
        TypeError,
        lambda: service.answer(
            "payment plan",
            "rag",
        ),
    )

    print(
        "PASS: invalid RAG result rejected"
    )


def test_structured_source_preserved():
    parser = FakeParser(
        {
            "city": "Lahore",
        }
    )

    service = KnowledgeService(
        FakeRepository(),
        FakeRAG(),
        parser,
    )

    result = service.answer(
        "Lahore apartments",
        "structured",
    )

    assert (
        result["sources"]
        == ["postgresql"]
    )

    print(
        "PASS: structured source preserved"
    )


def test_parser_filters_reach_repository():
    repository = FakeRepository()

    parser = FakeParser(
        {
            "budget": 40_000_000,
            "city": "Lahore",
            "area": "DHA Phase 6",
            "bedrooms": 3,
            "property_type": "Apartment",
            "purpose": "Purchase",
            "amenities": [
                "Parking",
                "Security",
            ],
        }
    )

    service = KnowledgeService(
        repository,
        FakeRAG(),
        parser,
    )

    service.answer(
        "DHA Phase 6 Lahore apartment",
        "structured",
    )

    assert len(
        repository.search_calls
    ) == 1

    filters = repository.search_calls[0]

    assert filters["budget"] == 40_000_000
    assert filters["city"] == "Lahore"
    assert filters["area"] == "DHA Phase 6"
    assert filters["bedrooms"] == 3
    assert filters["property_type"] == "Apartment"
    assert filters["purpose"] == "Purchase"
    assert filters["amenities"] == [
        "Parking",
        "Security",
    ]

    print(
        "PASS: parser filters reach repository"
    )


def test_rag_not_called_for_structured_route():
    rag = FakeRAG(
        "This must not be called."
    )

    parser = FakeParser(
        {
            "city": "Lahore",
        }
    )

    service = KnowledgeService(
        FakeRepository(),
        rag,
        parser,
    )

    service.answer(
        "Lahore apartments",
        "structured",
    )

    assert rag.calls == []

    print(
        "PASS: RAG not called for structured route"
    )


def test_postgres_not_called_for_rag_route():
    repository = FakeRepository()

    service = KnowledgeService(
        repository,
        FakeRAG(
            "Verified answer."
        ),
        FakeParser(
            {
                "city": "Lahore",
            }
        ),
    )

    service.answer(
        "What is the payment plan?",
        "rag",
    )

    assert repository.search_calls == []

    print(
        "PASS: PostgreSQL not called for RAG route"
    )


# ---------------------------------------------------------------------------
# CRITICAL REGRESSION TEST
# ---------------------------------------------------------------------------

def test_structured_route_does_not_run_broad_search():
    """
    Critical production safety test.

    If the parser extracts no filters, the knowledge service
    MUST NOT execute repository.search().

    This prevents a question such as:

        "Skyline ki price kya hai?"

    from accidentally returning every available property.
    """

    repository = FakeRepository()

    parser = FakeParser(
        {
            "budget": None,
            "city": None,
            "area": None,
            "bedrooms": None,
            "property_type": None,
            "purpose": None,
            "amenities": [],
        }
    )

    service = KnowledgeService(
        repository,
        FakeRAG(),
        parser,
    )

    result = service.answer(
        "Skyline ki price kya hai?",
        "structured",
    )

    assert repository.search_calls == []

    assert (
        result["structured_results"]
        == []
    )

    assert (
        "couldn't find"
        in result["final_answer"].lower()
    )

    print(
        "PASS: broad structured search blocked"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("=" * 80)
    print("KNOWLEDGE SERVICE PRODUCTION INTEGRATION TESTS")
    print("=" * 80)

    test_structured_service()
    test_rag_service()
    test_mixed_service()
    test_rental_routing()
    test_question_normalization()
    test_empty_question_rejected()
    test_whitespace_question_rejected()
    test_non_string_question_rejected()
    test_invalid_route_rejected()
    test_non_string_route_rejected()
    test_invalid_repository_result_rejected()
    test_invalid_rag_result_rejected()
    test_structured_source_preserved()
    test_parser_filters_reach_repository()
    test_rag_not_called_for_structured_route()
    test_postgres_not_called_for_rag_route()
    test_structured_route_does_not_run_broad_search()

    print()
    print("=" * 80)
    print("ALL KNOWLEDGE SERVICE INTEGRATION TESTS PASSED")
    print("=" * 80)