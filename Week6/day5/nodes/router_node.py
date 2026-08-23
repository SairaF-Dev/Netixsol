"""
router_node.py
--------------

Context-aware deterministic router for the AFL Day 5 LangGraph capstone.

Responsibilities
----------------
1. Handle empty queries.
2. Handle standalone dates/years.
3. Handle "What about 2027?" style follow-ups.
4. Preserve prediction context only when previous intent/tool was prediction.
5. Preserve retrieval context only when previous intent/tool was retrieval.
6. Handle vague follow-ups.
7. Fall back to the LLM/deterministic router for normal queries.

Important rule
--------------
team_a/team_b ALONE do NOT prove prediction context.

Previous intent/tool is authoritative.
"""

from __future__ import annotations

import re

from state import AgentState
from router import classify_intent


# ============================================================================
# DATE DETECTION
# ============================================================================

def _extract_year(text: str) -> str | None:
    """
    Extract a four-digit year such as 2024 or 2027.
    """

    match = re.search(
        r"\b(20\d{2})\b",
        text or "",
    )

    return match.group(1) if match else None


def _is_date_only_query(text: str) -> bool:
    """
    Detect standalone dates/years.

    Examples:
        2027
        2027?
        2026-08-30
        2026-08-30?
    """

    text = (
        (text or "")
        .strip()
        .rstrip("?")
        .strip()
    )

    return bool(
        re.fullmatch(
            r"20\d{2}(?:-\d{2}-\d{2})?",
            text,
        )
    )


def _is_year_followup_query(text: str) -> bool:
    """
    Detect year follow-up queries.

    Examples:
        What about 2027?
        What about 2024?
        How about 2025?
        And 2023?
        What about the 2022 season?
    """

    text = (
        (text or "")
        .strip()
        .lower()
    )

    patterns = (
    r"^what\s+about\s+20\d{2}\??$",
    r"^how\s+about\s+20\d{2}\??$",
    r"^and\s+20\d{2}\??$",
    r"^what\s+about\s+the\s+20\d{2}\s+season\??$",
    r"^how\s+about\s+the\s+20\d{2}\s+season\??$",
)

    return any(
        re.fullmatch(pattern, text)
        for pattern in patterns
    )


def _extract_followup_year(text: str) -> str | None:
    return _extract_year(text)


# ============================================================================
# PREVIOUS CONTEXT HELPERS
# ============================================================================

def _get_previous_intent(state: AgentState):
    """
    Intent of the PREVIOUS conversation turn.
    """

    return state.get("previous_intent")


def _get_previous_tool(state: AgentState):
    """
    Tool used during the PREVIOUS conversation turn.
    """

    return state.get("previous_tool_name")


def _has_prediction_context(state: AgentState) -> bool:
    """
    True only when the previous turn was actually prediction-related.

    We intentionally do NOT rely only on team_a/team_b.

    Supports:
        - match winner prediction
        - top-player prediction
    """

    previous_intent = _get_previous_intent(state)
    previous_tool = _get_previous_tool(state)

    prediction_tools = {
        "match_winner_prediction",
        "top_player_prediction",
        "prediction",
    }

    return (
        previous_intent == "prediction"
        or previous_tool in prediction_tools
    )


def _has_retrieval_context(state: AgentState) -> bool:
    """
    True when the previous turn was retrieval-related.
    """

    previous_intent = _get_previous_intent(state)
    previous_tool = _get_previous_tool(state)

    retrieval_tools = {
        "retrieval",
        "player_statistics",
        "team_results",
        "head_to_head",
    }

    return (
        previous_intent == "retrieval"
        or previous_tool in retrieval_tools
    )


def _has_afl_context(state: AgentState) -> bool:
    """
    General previous AFL context.

    Used only for vague conversational follow-ups.
    """

    previous_intent = _get_previous_intent(state)
    previous_tool = _get_previous_tool(state)

    afl_tools = {
        "retrieval",
        "player_statistics",
        "team_results",
        "head_to_head",
        "match_winner_prediction",
        "top_player_prediction",
        "prediction",
    }

    return (
        previous_intent in {
            "factual",
            "retrieval",
            "prediction",
        }
        or previous_tool in afl_tools
    )


# ============================================================================
# VAGUE FOLLOW-UP DETECTION
# ============================================================================

def _is_vague_followup(text: str) -> bool:
    """
    Detect conversational follow-ups.

    Examples:
        What about him?
        What about his stats?
        What about the player?
        What about the match?
    """

    lowered = (
        text or ""
    ).strip().lower()

    patterns = (
        r"^what\s+about\s+(him|her|his|their|them)\b",
        r"^what\s+about\s+the\s+player\b",
        r"^what\s+about\s+that\s+player\b",
        r"^what\s+about\s+the\s+match\b",
        r"^what\s+about\s+that\s+match\b",
        r"^what\s+about\s+them\b",
    )

    return any(
        re.search(pattern, lowered)
        for pattern in patterns
    )


# ============================================================================
# ROUTER NODE
# ============================================================================

def router_node(state: AgentState) -> AgentState:
    """
    Context-aware routing node.
    """

    query = (
        state.get("user_query", "") or ""
    ).strip()

    # =========================================================================
    # 1. EMPTY QUERY
    # =========================================================================

    if not query:

        return {
            **state,
            "intent": "off_topic",
            "router_reason": "Empty user query.",
        }

    # =========================================================================
    # 2. STANDALONE DATE / YEAR
    # =========================================================================

    if _is_date_only_query(query):

        year_or_date = (
            _extract_year(query)
            if len(
                query.rstrip("?").strip()
            ) == 4
            else query.rstrip("?").strip()
        )

        # Retrieval context has priority because it is the immediately
        # previous semantic context.

        if _has_retrieval_context(state):

            return {
                **state,
                "intent": "retrieval",
                "router_reason": (
                    "Standalone date/year interpreted as a "
                    "follow-up to the previous AFL retrieval."
                ),
                "date": year_or_date,
            }

        if _has_prediction_context(state):

            return {
                **state,
                "intent": "prediction",
                "router_reason": (
                    "Standalone date/year interpreted as a "
                    "follow-up to the previous AFL prediction."
                ),
                "date": year_or_date,
            }

        return {
            **state,
            "intent": "off_topic",
            "router_reason": (
                "Standalone date/year has no previous AFL context."
            ),
        }

    # =========================================================================
    # 3. YEAR FOLLOW-UP
    # =========================================================================

    if _is_year_followup_query(query):

        year = _extract_followup_year(query)

        if _has_retrieval_context(state):

            return {
                **state,
                "intent": "retrieval",
                "router_reason": (
                    "Year follow-up detected; previous "
                    "retrieval context preserved."
                ),
                "date": year,
            }

        if _has_prediction_context(state):

            return {
                **state,
                "intent": "prediction",
                "router_reason": (
                    "Year follow-up detected; previous "
                    "prediction context preserved."
                ),
                "date": year,
            }

        return {
            **state,
            "intent": "off_topic",
            "router_reason": (
                "Year follow-up has no previous AFL context."
            ),
        }

    # =========================================================================
    # 4. VAGUE FOLLOW-UP
    # =========================================================================

    if _is_vague_followup(query):

        if _has_retrieval_context(state):

            return {
                **state,
                "intent": "retrieval",
                "router_reason": (
                    "Vague follow-up preserved the previous "
                    "AFL retrieval context."
                ),
            }

        if _has_prediction_context(state):

            return {
                **state,
                "intent": "prediction",
                "router_reason": (
                    "Vague follow-up preserved the previous "
                    "AFL prediction context."
                ),
            }

        if _has_afl_context(state):

            return {
                **state,
                "intent": "factual",
                "router_reason": (
                    "Vague follow-up preserved the previous "
                    "AFL conversation context."
                ),
            }

        # No previous context.
        # Let the normal classifier decide rather than silently
        # dropping the query.

    # =========================================================================
    # 5. NORMAL CLASSIFICATION
    # =========================================================================

    result = classify_intent(query)

    return {
        **state,
        "intent": result.intent,
        "router_reason": result.reasoning,
    }