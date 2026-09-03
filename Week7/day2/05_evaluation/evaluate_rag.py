from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAG = ROOT / "02_rag"
INTEG = ROOT / "07_integration"

sys.path[:0] = [
    str(RAG),
    str(INTEG),
]


from rag_pipeline import (
    RAGPipeline,
    FALLBACK_ANSWER,
)
from query_router import route_query


QUESTIONS = Path(__file__).with_name(
    "evaluation_questions.csv"
)


def evaluate_answer(
    answer,
    expected_type,
    must_any,
):
    normalized = (
        answer
        or ""
    ).strip().casefold()

    fallback = (
        FALLBACK_ANSWER
        .strip()
        .casefold()
    )

    # -----------------------------------------
    # Expected refusal
    # -----------------------------------------

    if expected_type == "REFUSAL":
        return (
            normalized == fallback,
            "Expected safe refusal",
        )

    # -----------------------------------------
    # Expected grounded answer
    # -----------------------------------------

    if (
        not normalized
        or normalized == fallback
    ):
        return (
            False,
            "Expected grounded answer but received refusal",
        )

    options = [
        value.strip().casefold()
        for value in (
            must_any
            or ""
        ).split("|")
        if value.strip()
    ]

    if (
        options
        and not any(
            option in normalized
            for option in options
        )
    ):
        return (
            False,
            (
                "Missing expected concept; "
                f"accepted={options}"
            ),
        )

    return (
        True,
        "Grounded answer matched required behavior",
    )


def run():

    provider_failures = 0

    pipe = RAGPipeline(
        documents_dir=str(
            RAG / "documents"
        ),
        chunk_size=512,
        top_k=3,
    )

    with QUESTIONS.open(
        newline="",
        encoding="utf-8",
    ) as file:
        questions = list(
            csv.DictReader(file)
        )

    rows = []

    for q in questions:

        question_id = (
            q.get("question_id")
            or q.get("id")
            or "UNKNOWN"
        )

        question = q["question"]

        route = route_query(
            question
        ).value

        # -------------------------------------
        # Run RAG pipeline safely
        # -------------------------------------

        try:

            result = pipe.answer(
                question
            )

        except Exception as exc:

            provider_failures += 1

            reason = (
                "Provider/API error: "
                f"{exc}"
            )

            rows.append(
                {
                    "question_id": question_id,
                    "question": question,
                    "route": route,
                    "passed": False,
                    "reason": reason,
                    "answer": FALLBACK_ANSWER,
                    "top_sources": "",
                }
            )

            print(
                f"FAIL {question_id} "
                f"route={route} "
                f"reason={reason}"
            )

            continue

        # -------------------------------------
        # Detect graceful provider failure
        # from RAGPipeline
        # -------------------------------------

        if (
            result.get("reason")
            == "llm_provider_error"
        ):

            provider_failures += 1

            reason = (
                result.get("error")
                or "LLM provider error"
            )

            rows.append(
                {
                    "question_id": question_id,
                    "question": question,
                    "route": route,
                    "passed": False,
                    "reason": reason,
                    "answer": result.get(
                        "answer",
                        FALLBACK_ANSWER,
                    ),
                    "top_sources": "",
                }
            )

            print(
                f"FAIL {question_id} "
                f"route={route} "
                f"reason={reason}"
            )

            continue

        answer = result.get(
            "answer",
            FALLBACK_ANSWER,
        )

        expected = (
            q[
                "expected_answer_type"
            ]
            .strip()
            .upper()
        )

        # Structured queries should not be
        # answered by RAG.
        if route == "structured":
            expected = "REFUSAL"

        passed, reason = evaluate_answer(
            answer,
            expected,
            q.get(
                "must_contain_any",
                "",
            ),
        )

        # -------------------------------------
        # Validate expected retrieval source
        # -------------------------------------

        sources = [
            Path(
                item["source"]
            ).name
            for item in result.get(
                "results",
                [],
            )
        ]

        expected_source = (
            q.get(
                "expected_source",
                "",
            )
            .strip()
        )

        if (
            route == "rag"
            and expected_source
            and expected_source != "NONE"
            and expected_source not in sources
        ):
            passed = False

            reason = (
                "Expected source not retrieved: "
                f"{expected_source}"
            )

        # -------------------------------------
        # Store evaluation row
        # -------------------------------------

        rows.append(
            {
                "question_id": question_id,
                "question": question,
                "route": route,
                "passed": passed,
                "reason": reason,
                "answer": answer,
                "top_sources": " | ".join(
                    sources
                ),
            }
        )

        print(
            f"{'PASS' if passed else 'FAIL'} "
            f"{question_id} "
            f"route={route}"
            + (
                ""
                if passed
                else f" reason={reason}"
            )
        )

    # -----------------------------------------
    # Save results
    # -----------------------------------------

    out = Path(__file__).with_name(
        "rag_results.csv"
    )

    fieldnames = [
        "question_id",
        "question",
        "route",
        "passed",
        "reason",
        "answer",
        "top_sources",
    ]

    with out.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )

    # -----------------------------------------
    # Final metrics
    # -----------------------------------------

    total = len(rows)

    passed_count = sum(
        bool(row["passed"])
        for row in rows
    )

    if total:

        pass_rate = (
            passed_count
            / total
        )

    else:
        pass_rate = 0.0

    print()

    print(
        "RAG behavior pass rate: "
        f"{passed_count}/{total} "
        f"({pass_rate:.2%})"
    )

    print(
        "Provider/API failures: "
        f"{provider_failures}"
    )

    print(
        f"Results saved to: {out}"
    )


if __name__ == "__main__":
    run()