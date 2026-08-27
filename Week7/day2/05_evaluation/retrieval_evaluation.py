import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = PROJECT_ROOT / "02_rag"

sys.path.insert(0, str(RAG_DIR))

from retriever import Retriever


TEST_CASES = [
    {
        "question": "What amenities are listed for Skyline Residences?",
        "expected_source": "skyline_residences.md",
        "expected_type": "source",
    },
    {
        "question": "What is the price of DHA Pearl Apartments?",
        "expected_source": "dha_pearl_apartments.md",
        "expected_type": "source",
    },
    {
        "question": "What is the price of Bahria Grand Apartments?",
        "expected_source": "bahria_grand_apartments.md",
        "expected_type": "source",
    },
    {
        "question": "Can Sara guarantee investment returns?",
        "expected_source": "real_estate_faq.md",
        "expected_type": "source",
    },
    {
        "question": "Skyline mein swimming pool hai?",
        "expected_source": "skyline_residences.md",
        "expected_type": "source",
    },
    {
        "question": "What payment plan is available for DHA-APT-001?",
        "expected_source": None,
        "expected_type": "no_relevant_source",
    },
    {
        "question": "What is the price of a property that does not exist?",
        "expected_source": None,
        "expected_type": "no_relevant_source",
    },
]


def evaluate():
    retriever = Retriever(
        documents_dir=str(RAG_DIR / "documents")
    )

    total = len(TEST_CASES)
    passed = 0
    known_source_tests = 0
    source_hits = 0
    unknown_tests = 0
    unknown_passes = 0

    print("\nRETRIEVAL EVALUATION")
    print("=" * 70)

    for index, case in enumerate(TEST_CASES, start=1):

        question = case["question"]
        expected_source = case["expected_source"]
        expected_type = case["expected_type"]

        results = retriever.retrieve(
            question,
            top_k=4,
        )

        print(f"\nTest {index}")
        print("-" * 70)
        print(f"Question: {question}")

        if results:
            print("\nRetrieved:")

            for rank, result in enumerate(results, start=1):
                print(
                    f"{rank}. "
                    f"Distance={result['distance']:.4f} | "
                    f"Source={Path(result['source']).name} | "
                    f"Chunk={result['chunk_id']}"
                )
        else:
            print("\nNo results returned.")

        # ---------------------------------------------------------
        # Known-source test
        # ---------------------------------------------------------

        if expected_type == "source":

            known_source_tests += 1

            hit = any(
                expected_source in result["source"]
                for result in results
            )

            if hit:
                source_hits += 1
                passed += 1
                print("\nResult: PASS")
            else:
                print("\nResult: FAIL")

        # ---------------------------------------------------------
        # Unknown-information test
        # ---------------------------------------------------------

        elif expected_type == "no_relevant_source":

            unknown_tests += 1

            # The retriever should not return a strongly relevant
            # document for information that is not present.
            #
            # We use the same threshold as Retriever.
            relevant_results = [
                result
                for result in results
                if result["distance"] <= 0.60
            ]

            if not relevant_results:
                unknown_passes += 1
                passed += 1
                print("\nResult: PASS")
                print("Reason: No sufficiently relevant source retrieved.")
            else:
                print("\nResult: FAIL")
                print(
                    "Reason: Relevant-looking context was retrieved "
                    "for an unknown query."
                )

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"Total tests: {total}")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {total - passed}")

    if known_source_tests:
        hit_rate = source_hits / known_source_tests
        print(f"Known-source tests: {known_source_tests}")
        print(f"Source hit rate: {hit_rate:.2%}")

    if unknown_tests:
        unknown_rate = unknown_passes / unknown_tests
        print(f"Unknown-information tests: {unknown_tests}")
        print(f"Unknown-query pass rate: {unknown_rate:.2%}")

    overall_accuracy = passed / total
    print(f"Overall evaluation pass rate: {overall_accuracy:.2%}")


if __name__ == "__main__":
    evaluate()
