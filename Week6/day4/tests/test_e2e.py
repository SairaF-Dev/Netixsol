"""End-to-end smoke tests for the graph.

These tests require the Day 2 artifacts, Day 3 data, and API key.
Run:
    pytest tests/test_e2e.py -v
"""

import pytest

from day4_graph import run_query


CASES = [
    (
        "What were Richmond's last five results?",
        "retrieval",
    ),
    (
        "What is a mark in AFL?",
        "factual",
    ),
    (
        "What's the weather today?",
        "off_topic",
    ),
    (
        "Who will win the Pies vs Cats?",
        "prediction",
    ),
    (
        "Who will be the top player for Richmond?",
        "prediction",
    ),
    (
        "Who will win Tigers?",
        "prediction",
    ),
    (
        "Predict how many tackles a player will make.",
        "prediction",
    ),
    (
        "How does AFL scoring work?",
        "factual",
    ),
    (
        "Write Python code to scrape a website.",
        "off_topic",
    ),
    (
        "Give me the head-to-head record between Richmond and Carlton.",
        "retrieval",
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize("query,expected_intent", CASES)
def test_end_to_end(query, expected_intent):
    result = run_query(query)

    assert result["intent"] == expected_intent
    assert result.get("final_response")

    if expected_intent == "prediction" and result.get("validation_status") == "valid":
        assert (
            "probability" in result["final_response"].lower()
            or "predicted" in result["final_response"].lower()
        )


@pytest.mark.integration
def test_ambiguous_prediction_requires_clarification():
    result = run_query("Who will win Tigers?")
    assert result["intent"] == "prediction"
    assert result["validation_status"] == "needs_clarification"
    assert result["final_response"]
