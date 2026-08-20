"""Structured-output intent router for the Day 4 LangGraph."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI


load_dotenv(Path(__file__).with_name(".env"))


class IntentResult(BaseModel):
    intent: Literal[
        "factual",
        "retrieval",
        "prediction",
        "off_topic",
    ] = Field(
        description="Exactly one routing category."
    )

    reasoning: str = Field(
        description="Short explanation for the classification."
    )


ROUTER_PROMPT = """
You are the routing classifier for an AFL-only assistant.

Classify the user query into exactly ONE category.

prediction:
- asks who will win a future/upcoming AFL match
- asks whether one team will beat another
- asks who is likely to be a top player in an upcoming match
- asks for a future player/team outcome
- asks to predict a stat, even if unsupported by the models

retrieval:
- asks for historical or dataset-backed statistics
- asks about recent form
- asks about past results
- asks about past player performance
- asks for recorded team/player statistics
- asks for historical head-to-head records

factual:
- asks general AFL rules
- asks AFL terminology
- asks AFL history
- asks about competition structure
- asks general AFL facts

off_topic:
- unrelated to AFL
- coding
- weather
- recipes
- other sports
- general math
- personal advice
- unrelated questions

Rules:
1. Future outcome = prediction.
2. Historical/recent recorded data = retrieval.
3. General AFL knowledge = factual.
4. Non-AFL = off_topic.
5. Do not answer the question.
6. Return exactly one category.
7. reasoning must be short.

Examples:

"Who will win the Pies vs Cats?"
prediction

"Will Collingwood beat Geelong?"
prediction

"Who will be Collingwood's top player next match?"
prediction

"How many disposals did Collingwood have last round?"
retrieval

"What were Richmond's last five results?"
retrieval

"What is the head-to-head record between Pies and Cats?"
retrieval

"What is a mark in AFL?"
factual

"How does AFL scoring work?"
factual

"What's the weather today?"
off_topic

"Write a Python program."
off_topic

"Who will win Lakers vs Cats?"
off_topic
"""


def build_router_llm():
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY or OPENAI_API_KEY is not set."
        )

    return ChatOpenAI(
        model=os.getenv(
            "ROUTER_MODEL",
            "openai/gpt-oss-120b",
        ),
        base_url=os.getenv(
            "OPENAI_BASE_URL",
            "https://openrouter.ai/api/v1",
        ),
        api_key=api_key,
        temperature=0,
        max_tokens=300,
    )


def _fallback_classification(query: str) -> IntentResult:
    """
    Deterministic fallback if the LLM returns malformed
    structured output.
    """

    text = query.lower().strip()

    # ------------------------------------------------------------
    # OFF-TOPIC
    # ------------------------------------------------------------

    off_topic_terms = (
        "weather",
        "recipe",
        "python",
        "javascript",
        "coding",
        "programming",
        "lakers",
        "nba",
        "football",
        "soccer",
        "cricket",
        "personal advice",
    )

    if any(term in text for term in off_topic_terms):
        return IntentResult(
            intent="off_topic",
            reasoning=(
                "The query is unrelated to AFL."
            ),
        )

    # ------------------------------------------------------------
    # PREDICTION
    # ------------------------------------------------------------

    prediction_terms = (
        "who will win",
        "will .* beat",
        "predict",
        "prediction",
        "likely to win",
        "top player",
        "best player",
        "future",
        "upcoming",
    )

    import re

    if any(
        re.search(term, text)
        for term in prediction_terms
    ):
        return IntentResult(
            intent="prediction",
            reasoning=(
                "The query asks for a future AFL outcome."
            ),
        )

    # ------------------------------------------------------------
    # RETRIEVAL
    # ------------------------------------------------------------

    retrieval_terms = (
        "last",
        "recent",
        "historical",
        "history",
        "record",
        "head-to-head",
        "h2h",
        "statistics",
        "stats",
        "disposals",
        "goals",
        "marks",
        "tackles",
        "results",
        "performance",
    )

    if any(term in text for term in retrieval_terms):
        return IntentResult(
            intent="retrieval",
            reasoning=(
                "The query asks for historical or "
                "dataset-backed AFL information."
            ),
        )

    # ------------------------------------------------------------
    # FACTUAL
    # ------------------------------------------------------------

    return IntentResult(
        intent="factual",
        reasoning=(
            "The query appears to ask about general AFL knowledge."
        ),
    )


def classify_intent(query: str) -> IntentResult:

    llm = build_router_llm()

    structured = llm.with_structured_output(
        IntentResult,
        method="json_schema",
    )

    try:

        response = structured.invoke(
            [
                (
                    "system",
                    ROUTER_PROMPT,
                ),
                (
                    "human",
                    query,
                ),
            ]
        )

        # --------------------------------------------------------
        # IMPORTANT:
        # Never blindly trust the provider response.
        # --------------------------------------------------------

        if isinstance(response, IntentResult):
            return response

        if isinstance(response, dict):
            return IntentResult.model_validate(response)

        raise ValueError(
            f"Unexpected router response type: "
            f"{type(response).__name__}"
        )

    except (
        ValidationError,
        ValueError,
        TypeError,
    ) as exc:

        print(
            f"[router warning] Structured output failed: {exc}"
        )

        print(
            "[router warning] Using deterministic fallback."
        )

        return _fallback_classification(query)