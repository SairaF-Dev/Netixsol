from pathlib import Path
import sys


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

STRUCTURED_DIR = PROJECT_ROOT / "03_structured_retrieval"
RAG_DIR = PROJECT_ROOT / "02_rag"

for path in (STRUCTURED_DIR, RAG_DIR):
    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from query_router import route_query
from postgres_repository import PostgresPropertyRepository
from rag_pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FALLBACK_ANSWER = (
    "Verified information is currently unavailable."
)


class KnowledgeRouter:
    """
    Production integration layer for the real-estate knowledge system.

    Responsibilities:
        1. Classify the user query.
        2. Route structured questions to PostgreSQL.
        3. Route document/company questions to RAG.
        4. Handle mixed questions using both sources.
        5. Never invent property information.
        6. Return a consistent response structure.

    PostgreSQL:
        Source of truth for exact property facts.

    RAG:
        Source of truth for document-based company/project knowledge.
    """

    def __init__(
        self,
        repository=None,
        rag_pipeline=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else PostgresPropertyRepository()
        )

        self.rag_pipeline = (
            rag_pipeline
            if rag_pipeline is not None
            else RAGPipeline()
        )

    # ------------------------------------------------------------------
    # Structured retrieval
    # ------------------------------------------------------------------

    def _structured_query(self, question):
        """
        Execute a structured PostgreSQL lookup.

        The repository is intentionally kept behind this method so the
        integration layer does not depend on SQL implementation details.
        """

        results = self.repository.search(
            city=None,
            area=None,
            bedrooms=None,
            property_type=None,
            purpose=None,
            budget=None,
            amenities=None,
        )

        return {
            "source": "structured",
            "results": results,
            "answer": None,
        }

    # ------------------------------------------------------------------
    # RAG retrieval
    # ------------------------------------------------------------------

    def _rag_query(self, question):
        """
        Execute a grounded RAG query.
        """

        result = self.rag_pipeline.answer(question)

        return {
            "source": "rag",
            "results": result.get("results", []),
            "answer": result.get(
                "answer",
                FALLBACK_ANSWER,
            ),
        }

    # ------------------------------------------------------------------
    # Mixed retrieval
    # ------------------------------------------------------------------

    def _mixed_query(self, question):
        """
        Execute both structured and RAG retrieval.

        Structured data is retrieved independently from document
        knowledge. The final answer is generated using the RAG pipeline
        only for document-level information.

        This method deliberately does not merge arbitrary PostgreSQL
        records into an LLM prompt, preventing accidental hallucination
        or source confusion.
        """

        structured = self._structured_query(
            question
        )

        rag = self._rag_query(
            question
        )

        return {
            "source": "mixed",
            "structured_results": structured["results"],
            "rag_results": rag["results"],
            "answer": rag["answer"],
        }

    # ------------------------------------------------------------------
    # Main routing
    # ------------------------------------------------------------------

    def answer(self, question):
        """
        Route and answer a real-estate question.

        Returns a consistent dictionary containing:

            question
            route
            answer
            structured_results
            rag_results
        """

        if not isinstance(question, str):
            raise TypeError(
                "question must be a string"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question cannot be empty"
            )

        route = route_query(question)

        # --------------------------------------------------------------
        # STRUCTURED
        # --------------------------------------------------------------

        if route == "structured":

            result = self._structured_query(
                question
            )

            structured_results = result["results"]

            if structured_results:
                answer = (
                    "Structured property information "
                    "retrieved successfully."
                )
            else:
                answer = FALLBACK_ANSWER

            return {
                "question": question,
                "route": "structured",
                "answer": answer,
                "structured_results": structured_results,
                "rag_results": [],
            }

        # --------------------------------------------------------------
        # RAG
        # --------------------------------------------------------------

        if route == "rag":

            result = self._rag_query(
                question
            )

            return {
                "question": question,
                "route": "rag",
                "answer": result["answer"],
                "structured_results": [],
                "rag_results": result["results"],
            }

        # --------------------------------------------------------------
        # MIXED
        # --------------------------------------------------------------

        if route == "mixed":

            result = self._mixed_query(
                question
            )

            return {
                "question": question,
                "route": "mixed",
                "answer": result["answer"],
                "structured_results": (
                    result["structured_results"]
                ),
                "rag_results": (
                    result["rag_results"]
                ),
            }

        # --------------------------------------------------------------
        # Defensive fallback
        # --------------------------------------------------------------

        raise RuntimeError(
            f"Unsupported query route: {route}"
        )


# ---------------------------------------------------------------------------
# Manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    router = KnowledgeRouter()

    test_questions = [
        "What is the price of Skyline Residences?",
        "Skyline available hai?",
        "What is the payment plan?",
        "Can you guarantee investment returns?",
        "Skyline ki price aur payment plan kya hai?",
    ]

    print("=" * 80)
    print("KNOWLEDGE ROUTER")
    print("=" * 80)

    for question in test_questions:

        result = router.answer(
            question
        )

        print("\n" + "-" * 80)
        print(f"QUESTION: {result['question']}")
        print(f"ROUTE:    {result['route']}")
        print(
            f"STRUCTURED RESULTS: "
            f"{len(result['structured_results'])}"
        )
        print(
            f"RAG RESULTS: "
            f"{len(result['rag_results'])}"
        )
        print(
            f"ANSWER: {result['answer']}"
        )