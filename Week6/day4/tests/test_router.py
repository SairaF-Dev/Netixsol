"""Router evaluation: 18 varied queries.

Requires OPENROUTER_API_KEY.
Run:
    pytest tests/test_router.py -v
"""

import pandas as pd
import pytest

from router import classify_intent


ROUTING_CASES = [
    ("Who will win the Pies vs Cats?", "prediction"),
    ("Will Collingwood beat Geelong?", "prediction"),
    ("Who will be Collingwood's top player next match?", "prediction"),
    ("Predict the top player for Richmond.", "prediction"),
    ("How many disposals did Collingwood have last round?", "retrieval"),
    ("What were Richmond's last five results?", "retrieval"),
    ("What was Geelong's recent form?", "retrieval"),
    ("Give me the head-to-head record between Richmond and Carlton.", "retrieval"),
    ("What is a mark in AFL?", "factual"),
    ("How does AFL scoring work?", "factual"),
    ("How does the AFL finals system work?", "factual"),
    ("What is a behind?", "factual"),
    ("What's the weather today?", "off_topic"),
    ("Write a Python script for me.", "off_topic"),
    ("Who won the last soccer World Cup?", "off_topic"),
    ("Can you help me with my database homework?", "off_topic"),
    ("What is 25 times 4?", "off_topic"),
    ("Tell me a joke.", "off_topic"),
]


@pytest.mark.integration
def test_router_accuracy():
    rows = []

    for query, expected in ROUTING_CASES:
        result = classify_intent(query)
        rows.append({
            "query": query,
            "expected": expected,
            "predicted": result.intent,
            "correct": result.intent == expected,
            "reasoning": result.reasoning,
        })

    df = pd.DataFrame(rows)
    df.to_csv("routing_accuracy_results.csv", index=False)

    accuracy = df["correct"].mean()
    print("\nRouting accuracy:")
    print(df[["query", "expected", "predicted", "correct"]].to_string(index=False))
    print(f"\nAccuracy: {accuracy:.2%}")

    assert accuracy >= 0.80, (
        f"Router accuracy {accuracy:.2%} is below the 80% Day 4 test threshold."
    )
