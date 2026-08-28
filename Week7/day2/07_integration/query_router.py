"""
Production query router for Sara's real-estate assistant.

Routing strategy:

1. Structured property facts/search
   -> PostgreSQL / RecommendationEngine

2. Company knowledge / FAQs / payment plans
   -> RAG

3. Mixed questions
   -> Both structured retrieval and RAG

4. Unsupported/general questions
   -> RAG, where the RAG layer can safely return
      the verified-information fallback.

The router does NOT generate answers.
It only determines which verified knowledge source(s)
should be used.
"""

import re
from enum import Enum


class QueryRoute(str, Enum):
    """Available retrieval routes."""

    STRUCTURED = "structured"
    RAG = "rag"
    MIXED = "mixed"


# -------------------------------------------------------------------
# Structured property facts
# -------------------------------------------------------------------

STRUCTURED_PATTERNS = [
    # Price / cost
    r"\bprice\b",
    r"\bprices\b",
    r"\bcost\b",
    r"\bcosts\b",
    r"\brate\b",
    r"\brates\b",
    r"\bhow much\b",
    r"\bkitne\b",
    r"\bkitnay\b",
    r"\bkitni\b",
    r"\bqeemat\b",
    r"\bkeemat\b",
    r"\bdaam\b",

    # Availability
    r"\bavailable\b",
    r"\bavailability\b",
    r"\bvacant\b",
    r"\bready\b",
    r"\bavailable hai\b",
    r"\bkhali\b",

    # Bedrooms / bathrooms
    r"\bbedroom\b",
    r"\bbedrooms\b",
    r"\bbathroom\b",
    r"\bbathrooms\b",
    r"\bkamray\b",
    r"\bkamra\b",

    # Property identity
    r"\bproperty id\b",
    r"\bproperty_id\b",
    r"\bunit id\b",
    r"\bunit number\b",
    r"\bwhich property\b",
    r"\bproperty ka naam\b",
    r"\bproperty name\b",

    # Location
    r"\blocation\b",
    r"\bwhere is\b",
    r"\bwhere located\b",
    r"\barea\b",
    r"\bcity\b",
    r"\blocation kya\b",
    r"\bkahan\b",
    r"\bkahaan\b",

    # Property characteristics
    r"\bproperty\b",
    r"\bproperties\b",
    r"\bapartment\b",
    r"\bapartments\b",
    r"\bflat\b",
    r"\bflats\b",
    r"\bhouse\b",
    r"\bhouses\b",
    r"\bvilla\b",
    r"\bvillas\b",

    # Developer
    r"\bdeveloper\b",
    r"\bdevelopers\b",
    r"\bwho developed\b",
    r"\bdeveloped by\b",
    r"\bdeveloper ka naam\b",
    r"\bkis developer\b",

    # Amenities
    r"\bamenity\b",
    r"\bamenities\b",
    r"\bparking\b",
    r"\bswimming pool\b",
    r"\bswimming\b",
    r"\bpool\b",
    r"\bgym\b",
    r"\belevator\b",
    r"\blift\b",
    r"\bsecurity\b",
    r"\bbackup power\b",

    # Search / recommendation language
    r"\boptions\b",
    r"\boption\b",
    r"\bproperty options\b",
    r"\bshow me\b",
    r"\bfind me\b",
    r"\bfind\b",
    r"\blooking for\b",
    r"\bchahiye\b",
    r"\bchahti hoon\b",
    r"\bchahta hoon\b",
    r"\bchahye\b",
    r"\bwithin budget\b",
    r"\bunder budget\b",
    r"\bunder\b",
    r"\bke andar\b",
    r"\btak\b",
    r"\bup to\b",

    # Purchase / buying
    r"\bbuy\b",
    r"\bbuying\b",
    r"\bpurchase\b",
    r"\bfor sale\b",
    r"\bsale\b",
    r"\bkharid\b",
    r"\bkharna\b",
    r"\bkharidna\b",

    # Rental
    r"\brent\b",
    r"\brental\b",
    r"\brentals\b",
    r"\bfor rent\b",
    r"\bkiraya\b",
    r"\bkiraye\b",
    r"\brent par\b",
]


# -------------------------------------------------------------------
# RAG / company knowledge
# -------------------------------------------------------------------

RAG_PATTERNS = [
    # Payment plans
    r"\bpayment plan\b",
    r"\bpayment plans\b",
    r"\binstallment\b",
    r"\binstallments\b",
    r"\bmonthly payment\b",
    r"\bdown payment\b",
    r"\bbooking amount\b",
    r"\bpayment schedule\b",
    r"\binstallment plan\b",
    r"\bqiston\b",
    r"\bqist\b",
    r"\bqistain\b",
    r"\bpayment kaise\b",

    # Company / FAQ
    r"\bfaq\b",
    r"\bpolicy\b",
    r"\bcompany policy\b",
    r"\bhow does sara\b",
    r"\bhow do you\b",
    r"\bhow does the company\b",
    r"\bcompany information\b",
    r"\bcompany info\b",

    # Investment claims
    r"\binvestment return\b",
    r"\binvestment returns\b",
    r"\breturn on investment\b",
    r"\broi\b",
    r"\bprofit\b",
    r"\bprofits\b",
    r"\bguarantee\b",
    r"\bguaranteed return\b",
    r"\bguaranteed profit\b",
    r"\breturn\b",
    r"\breturns\b",

    # Visits / booking workflow information
    r"\bbook.*visit\b",
    r"\bbooking.*visit\b",
    r"\bproperty visit\b",
    r"\bvisit.*property\b",
    r"\bvisit kaise\b",
    r"\bvisit book\b",
    r"\bsite visit\b",

    # General company/project information
    r"\bproject description\b",
    r"\bproject details\b",
    r"\babout the project\b",
    r"\babout this project\b",
    r"\bproject ke bare mein\b",
    r"\bproject k bare mein\b",
    r"\bdetails\b",
    r"\bcompany\b",
]


# -------------------------------------------------------------------
# Normalization
# -------------------------------------------------------------------

def normalize_question(question: str) -> str:
    """
    Normalize user input for deterministic routing.

    This does NOT translate or rewrite the question.
    It only normalizes whitespace and case.
    """

    if not isinstance(question, str):
        raise TypeError("question must be a string")

    question = question.strip()

    if not question:
        raise ValueError("question cannot be empty")

    question = re.sub(r"\s+", " ", question)

    return question.lower()


# -------------------------------------------------------------------
# Pattern matching
# -------------------------------------------------------------------

def _matches(question: str, patterns: list[str]) -> bool:
    """Return True if any routing pattern matches."""

    return any(
        re.search(pattern, question, flags=re.IGNORECASE)
        for pattern in patterns
    )


# -------------------------------------------------------------------
# Route detection
# -------------------------------------------------------------------

def route_query(question: str) -> QueryRoute:
    """
    Determine which verified knowledge source is required.

    Returns:
        QueryRoute.STRUCTURED
        QueryRoute.RAG
        QueryRoute.MIXED
    """

    question = normalize_question(question)

    structured_match = _matches(
        question,
        STRUCTURED_PATTERNS,
    )

    rag_match = _matches(
        question,
        RAG_PATTERNS,
    )

    # ---------------------------------------------------------------
    # Both sources are required.
    #
    # Example:
    # "Skyline ki price aur payment plan kya hai?"
    # ---------------------------------------------------------------

    if structured_match and rag_match:
        return QueryRoute.MIXED

    # ---------------------------------------------------------------
    # Structured property data.
    # ---------------------------------------------------------------

    if structured_match:
        return QueryRoute.STRUCTURED

    # ---------------------------------------------------------------
    # Company knowledge / FAQ / policy.
    # ---------------------------------------------------------------

    if rag_match:
        return QueryRoute.RAG

    # ---------------------------------------------------------------
    # Safe default.
    #
    # Unknown/general questions go to RAG.
    # RAG is responsible for refusing unsupported facts.
    # ---------------------------------------------------------------

    return QueryRoute.RAG


# -------------------------------------------------------------------
# Convenience helpers
# -------------------------------------------------------------------

def is_structured_query(question: str) -> bool:
    """Return True when structured retrieval is required."""

    return route_query(question) == QueryRoute.STRUCTURED


def is_rag_query(question: str) -> bool:
    """Return True when only RAG retrieval is required."""

    return route_query(question) == QueryRoute.RAG


def is_mixed_query(question: str) -> bool:
    """Return True when both sources are required."""

    return route_query(question) == QueryRoute.MIXED


# -------------------------------------------------------------------
# Manual tests
# -------------------------------------------------------------------

if __name__ == "__main__":

    test_questions = [
        # Structured
        "What is the price of Skyline Residences?",
        "Skyline available hai?",
        "Lahore mein 3 bedroom apartment chahiye.",
        "4 crore ke andar options hain?",
        "Skyline ka developer kon hai?",
        "Is property mein swimming pool hai?",
        "Skyline ki location kya hai?",
        "3 bedroom rental Lahore mein chahiye.",

        # RAG
        "What is the payment plan?",
        "Installment ka kya scene hai?",
        "Can you guarantee investment returns?",
        "How does Sara recommend a property?",
        "Can Sara book a property visit?",

        # Mixed
        "Skyline ki price aur payment plan kya hai?",
        "Is property available hai aur iska payment plan kya hai?",
        "Skyline ka developer kon hai aur investment return guaranteed hai?",
    ]

    print("=" * 80)
    print("QUERY ROUTER TEST")
    print("=" * 80)

    for question in test_questions:

        route = route_query(question)

        print(f"\nQuestion: {question}")
        print(f"Route:    {route.value}")
