"""
Structured-output intent router for the AFL Day 5 LangGraph capstone.

Responsibilities:
1. Detect obvious prompt-injection attempts.
2. Detect obvious non-AFL queries.
3. Classify valid AFL queries as:
   - factual
   - retrieval
   - prediction
4. Fall back safely if the LLM router fails.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).with_name(".env"))


# ---------------------------------------------------------------------------
# Structured router output
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# LLM router prompt
# ---------------------------------------------------------------------------

ROUTER_PROMPT = """
You are the routing classifier for an AFL-only assistant.

Your job is ONLY to classify the user's query.

Return exactly ONE category:

prediction:
- future or upcoming AFL outcome
- asks who will win an AFL match
- asks whether one AFL team will beat another
- asks for a predicted AFL player/team outcome
- asks to predict a future AFL statistic

retrieval:
- historical AFL statistics
- recent AFL form
- past AFL results
- previous player performance
- recorded team/player statistics
- historical AFL head-to-head records

factual:
- general AFL rules
- AFL terminology
- general AFL history
- competition structure
- general AFL knowledge

off_topic:
- anything unrelated to Australian Football League (AFL)
- coding/programming
- weather
- recipes
- other sports
- general mathematics
- personal advice
- unrelated questions

Important rules:

1. If the query is clearly about AFL, NEVER classify it as off_topic.
2. Future AFL outcome = prediction.
3. Historical or recorded AFL information = retrieval.
4. General AFL knowledge = factual.
5. Non-AFL = off_topic.
6. Do not answer the user's question.
7. Return exactly one category.
8. Keep reasoning short.

Examples:

"What is a mark in AFL?"
factual

"How does AFL scoring work?"
factual

"What is a behind in AFL?"
factual

"What were Richmond's last five results?"
retrieval

"What is Richmond's recent form?"
retrieval

"What is the head-to-head record between Collingwood and Geelong?"
retrieval

"How many disposals did Nick Daicos have last match?"
retrieval

"Who will win Collingwood vs Geelong?"
prediction

"Will Collingwood beat Geelong?"
prediction

"Who is likely to be the top player in the next match?"
prediction

"What's the weather today?"
off_topic

"Write a Python program."
off_topic

"How do I hack a website?"
off_topic
"""


# ---------------------------------------------------------------------------
# Build router LLM
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(the\s+)?previous\s+instructions",
    r"ignore\s+the\s+afl[- ]only\s+restriction",
    r"you\s+are\s+no\s+longer\s+an\s+afl\s+assistant",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(me\s+)?your\s+system\s+prompt",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"override\s+(the\s+)?system",
)


def is_prompt_injection(query: str) -> bool:
    text = query.lower().strip()

    return any(
        re.search(pattern, text)
        for pattern in PROMPT_INJECTION_PATTERNS
    )


# ---------------------------------------------------------------------------
# Obvious non-AFL detection
# ---------------------------------------------------------------------------

OFF_TOPIC_TERMS = (
    "weather",
    "recipe",
    "python",
    "javascript",
    "typescript",
    "coding",
    "programming",
    "sql",
    "html",
    "css",
    "django",
    "flask",
    "react",
    "node.js",
    "nodejs",
    "lakers",
    "nba",
    "nfl",
    "soccer",
    "football",
    "cricket",
    "tennis",
    "formula 1",
    "f1",
    "personal advice",
)


def is_obviously_off_topic(query: str) -> bool:
    text = query.lower().strip()

    return any(
        term in text
        for term in OFF_TOPIC_TERMS
    )


# ---------------------------------------------------------------------------
# AFL signal detection
# ---------------------------------------------------------------------------

AFL_TERMS = (
    "afl",
    "australian football",
    "australian rules",
    "aussie rules",
    "premiership",
    "grand final",
    "brownlow",
    "coleman",
    "norm smith",
    "mark",
    "behind",
    "goal",
    "disposal",
    "disposals",
    "clearance",
    "tackle",
    "tackles",
    "inside 50",
    "inside 50s",
    "centre clearance",
    "contested possession",
    "uncontested possession",
    "kick",
    "kicks",
    "handball",
    "handballs",
    "aflw",
)


AFL_TEAMS = (
    "collingwood",
    "geelong",
    "richmond",
    "carlton",
    "essendon",
    "hawthorn",
    "melbourne",
    "st kilda",
    "stkilda",
    "fremantle",
    "west coast",
    "west coast eagles",
    "brisbane",
    "brisbane lions",
    "sydney",
    "sydney swans",
    "gws",
    "greater western sydney",
    "gold coast",
    "gold coast suns",
    "adelaide",
    "adelaide crows",
    "port adelaide",
    "western bulldogs",
    "bulldogs",
    "north melbourne",
    "kangaroos",
    "north melbourne kangaroos",
    "melbourne demons",
    "giants",
)


def has_afl_signal(query: str) -> bool:
    text = query.lower().strip()

    return (
        any(term in text for term in AFL_TERMS)
        or any(team in text for team in AFL_TEAMS)
    )


# ---------------------------------------------------------------------------
# Deterministic fallback classifier
# ---------------------------------------------------------------------------

def _fallback_classification(query: str) -> IntentResult:
    """
    Deterministic classification used when the LLM router fails.

    The order is important:
        1. prompt injection
        2. obvious off-topic
        3. prediction
        4. retrieval
        5. factual
    """

    text = query.lower().strip()

    # ------------------------------------------------------------
    # Prompt injection
    # ------------------------------------------------------------

    if is_prompt_injection(text):
        return IntentResult(
            intent="off_topic",
            reasoning=(
                "Prompt-injection attempt detected by "
                "deterministic guardrail."
            ),
        )

    # ------------------------------------------------------------
    # Obvious off-topic
    # ------------------------------------------------------------

    if is_obviously_off_topic(text):
        return IntentResult(
            intent="off_topic",
            reasoning=(
                "The query is unrelated to AFL."
            ),
        )

    # ------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------

    prediction_patterns = (
        r"\bwho\s+will\s+win\b",
        r"\bwill\s+.+\s+beat\s+.+",
        r"\bpredict\b",
        r"\bprediction\b",
        r"\blikely\s+to\s+win\b",
        r"\btop\s+player\b",
        r"\bbest\s+player\b",
        r"\bupcoming\b",
        r"\bnext\s+match\b",
        r"\bfuture\b",
    )

    if any(
        re.search(pattern, text)
        for pattern in prediction_patterns
    ):
        return IntentResult(
            intent="prediction",
            reasoning=(
                "The query asks for a future AFL outcome."
            ),
        )


def deterministic_intent(query: str) -> str:
    q = query.lower().strip()

    # ---------------------------------------------------------
    # OFF TOPIC
    # ---------------------------------------------------------
    # Keep your existing AFL scope logic here.
    # Do NOT classify a date as off-topic if it is handled
    # by pending clarification before router classification.
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # PREDICTION
    # ---------------------------------------------------------
    prediction_words = (
        "who will win",
        "will win",
        "winner",
        "predict",
        "prediction",
        "match prediction",
        "top player",
        "best player",
        "top performer",
        "top scorer",
    )

    if any(word in q for word in prediction_words):
        return "prediction"

    # ---------------------------------------------------------
    # RETRIEVAL
    # ---------------------------------------------------------
    retrieval_words = (
        "how many",
        "average",
        "statistic",
        "stats",
        "statistics",
        "record",
        "history",
        "disposals",
        "goals",
        "fantasy points",
    )

    if any(word in q for word in retrieval_words):
        return "retrieval"

    # ---------------------------------------------------------
    # FACTUAL
    # ---------------------------------------------------------
    factual_words = (
        "what is",
        "what are",
        "rule",
        "rules",
        "when did",
        "who won",
        "history",
    )

    if any(word in q for word in factual_words):
        return "factual"

    return "off_topic"
    # ------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------

    retrieval_terms = (
        "last",
        "recent",
        "historical",
        "history",
        "record",
        "head-to-head",
        "head to head",
        "h2h",
        "statistics",
        "stats",
        "disposals",
        "goals",
        "marks",
        "tackles",
        "results",
        "performance",
        "form",
    )

    if any(
        term in text
        for term in retrieval_terms
    ):
        return IntentResult(
            intent="retrieval",
            reasoning=(
                "The query asks for historical or "
                "dataset-backed AFL information."
            ),
        )

    # ------------------------------------------------------------
    # Factual
    # ------------------------------------------------------------

    if has_afl_signal(text):
        return IntentResult(
            intent="factual",
            reasoning=(
                "The query asks about general AFL knowledge."
            ),
        )

    # ------------------------------------------------------------
    # Unknown non-AFL query
    # ------------------------------------------------------------

    return IntentResult(
        intent="off_topic",
        reasoning=(
            "The query does not contain sufficient AFL context."
        ),
    )


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def classify_intent(query: str) -> IntentResult:
    """
    Classify an AFL query.

    Deterministic guardrails run BEFORE the LLM so that:
    - prompt injection cannot reach the LLM router
    - obvious off-topic requests are rejected immediately
    - valid AFL questions are protected from bad LLM classifications
    """

    query = (query or "").strip()

    # ------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------

    if not query:
        return IntentResult(
            intent="off_topic",
            reasoning="Empty user query.",
        )

    # ------------------------------------------------------------
    # Deterministic prompt-injection guardrail
    # ------------------------------------------------------------

    if is_prompt_injection(query):
        return IntentResult(
            intent="off_topic",
            reasoning=(
                "Prompt-injection attempt detected by "
                "deterministic guardrail."
            ),
        )

    # ------------------------------------------------------------
    # Deterministic obvious off-topic guardrail
    # ------------------------------------------------------------

    if is_obviously_off_topic(query):
        return IntentResult(
            intent="off_topic",
            reasoning=(
                "The query is clearly unrelated to AFL."
            ),
        )

    # ------------------------------------------------------------
    # Ask LLM to classify
    # ------------------------------------------------------------

    try:
        llm = build_router_llm()

        structured = llm.with_structured_output(
            IntentResult,
            method="json_schema",
        )

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
        # Validate provider response
        # --------------------------------------------------------

        if isinstance(response, IntentResult):
            result = response

        elif isinstance(response, dict):
            result = IntentResult.model_validate(response)

        else:
            raise ValueError(
                "Unexpected router response type: "
                f"{type(response).__name__}"
            )

        # --------------------------------------------------------
        # Safety correction:
        #
        # If the query clearly contains AFL context but the LLM
        # says off_topic, use the deterministic fallback.
        # --------------------------------------------------------

        if (
            result.intent == "off_topic"
            and has_afl_signal(query)
        ):
            print(
                "[router warning] LLM classified an AFL query "
                "as off_topic."
            )

            print(
                "[router warning] Using deterministic AFL fallback."
            )

            return _fallback_classification(query)

        return result

    except (
        ValidationError,
        ValueError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:

        print(
            f"[router warning] Structured output failed: {exc}"
        )

        print(
            "[router warning] Using deterministic fallback."
        )

        return _fallback_classification(query)