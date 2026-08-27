from pathlib import Path
import sys
import csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = PROJECT_ROOT / "02_rag"

sys.path.insert(0, str(RAG_DIR))

from rag_pipeline import RAGPipeline


QUESTIONS_FILE = Path(__file__).resolve().parent / "evaluation_questions.csv"


def evaluate_answer(question, answer, expected_answer_type):
    """
    Evaluate whether the generated answer behaves correctly.

    expected_answer_type:
        VERIFIED  -> should provide verified information
        REFUSAL   -> should refuse because information is unavailable
    """

    answer_normalized = answer.strip().lower()

    refusal_phrase = (
        "verified information is currently unavailable."
    )

    if expected_answer_type == "REFUSAL":
        passed = refusal_phrase in answer_normalized

        return passed, (
            "Correct refusal"
            if passed
            else "Expected refusal but model provided information"
        )

    if expected_answer_type == "VERIFIED":
        passed = (
            answer_normalized
            and refusal_phrase not in answer_normalized
        )

        return passed, (
            "Generated grounded answer"
            if passed
            else "Expected verified answer but model refused"
        )

    return False, "Unknown answer type"


def run():

    pipeline = RAGPipeline(
    documents_dir=str(RAG_DIR / "documents"),
    chunk_size=512,
    top_k=3,
)

    with QUESTIONS_FILE.open(
        newline="",
        encoding="utf-8",
    ) as f:

        questions = list(csv.DictReader(f))

    rows = []

    print("\nRAG EVALUATION")
    print("=" * 70)

    for index, q in enumerate(questions, start=1):

        question_id = q["question_id"]
        question = q["question"]

        # Expected answer type must be defined in CSV.
        expected_type = q.get(
            "expected_answer_type",
            "VERIFIED",
        ).strip().upper()

        print(f"\nTest {index}")
        print("-" * 70)
        print(f"Question: {question}")

        try:

            result = pipeline.answer(question)

            answer = result["answer"]

            retrieved_results = result["results"]

            sources = [
                Path(item["source"]).name
                for item in retrieved_results
            ]

            passed, reason = evaluate_answer(
                question,
                answer,
                expected_type,
            )

        except Exception as exc:

            answer = ""
            sources = []
            passed = False
            reason = f"ERROR: {exc}"

        print("\nRetrieved Sources:")

        if sources:
            for source in sources:
                print(f"- {source}")
        else:
            print("- None")

        print("\nGenerated Answer:")
        print(answer if answer else "No answer generated.")

        print(f"\nResult: {'PASS' if passed else 'FAIL'}")
        print(f"Reason: {reason}")

        rows.append(
            {
                "question_id": question_id,
                "question": question,
                "expected_answer_type": expected_type,
                "passed": passed,
                "reason": reason,
                "answer": answer,
                "top_sources": " | ".join(sources),
            }
        )

    output_file = (
        Path(__file__).resolve().parent
        / "rag_results.csv"
    )

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    passed = sum(
        1
        for row in rows
        if row["passed"]
    )

    accuracy = (
        passed / total
        if total
        else 0
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests: {total}")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {total - passed}")
    print(f"RAG evaluation pass rate: {accuracy:.2%}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    run()
