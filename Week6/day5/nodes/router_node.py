from __future__ import annotations

import re

from state import AgentState

from router import classify_intent


# ============================================================================
# PREDICTION KEYWORDS
# ============================================================================

MATCH_PREDICTION_TERMS = (
    "who will win",
    "winner",
    "will win",
    "match prediction",
    "predict",
    "prediction",
    "beat",
    "defeat",
)


TOP_PLAYER_TERMS = (
    "top player",
    "best player",
    "top performer",
    "top scorer",
)


# ============================================================================
# DATE DETECTION
# ============================================================================

DATE_ONLY_RE = re.compile(
    r"^\s*20\d{2}-\d{2}-\d{2}\s*$"
)


def _is_date_only(text: str) -> bool:
    return bool(
        DATE_ONLY_RE.fullmatch(text.strip())
    )


# ============================================================================
# DETERMINISTIC PREDICTION DETECTION
# ============================================================================

def _is_prediction_query(text: str) -> bool:

    q = text.lower().strip()

    # ------------------------------------------------------------
    # Top-player prediction
    # ------------------------------------------------------------

    if any(
        term in q
        for term in TOP_PLAYER_TERMS
    ):
        return True

    # ------------------------------------------------------------
    # Match-winner prediction
    # ------------------------------------------------------------

    if any(
        term in q
        for term in MATCH_PREDICTION_TERMS
    ):
        return True

    return False


# ============================================================================
# ROUTER NODE
# ============================================================================

def router_node(
    state: AgentState,
) -> AgentState:

    query = state.get(
        "user_query",
        "",
    ).strip()

    # =========================================================================
    # PENDING CLARIFICATION
    # =========================================================================
    #
    # Do NOT classify the clarification answer as a fresh query.
    #
    # Example:
    #
    # Turn 1:
    #   Who is the top player for Collingwood?
    #
    # Turn 2:
    #   2025-08-30
    #
    # The date belongs to the previous prediction request.
    #
    # =========================================================================

    if (
        state.get("clarification_needed")
        and state.get("pending_tool_name")
    ):

        return {
            **state,

            "intent":
                "prediction",

            "router_reason":
                "Continuing a pending prediction clarification.",
        }

    # =========================================================================
    # DETERMINISTIC TOP-PLAYER / PREDICTION OVERRIDE
    # =========================================================================
    #
    # This prevents the LLM router from incorrectly classifying:
    #
    #   "Who is the top player for Collingwood?"
    #
    # as retrieval.
    #
    # =========================================================================

    if _is_prediction_query(query):

        if any(
            term in query.lower()
            for term in TOP_PLAYER_TERMS
        ):

            reason = (
                "The user asks for a top-player prediction "
                "for an AFL team."
            )

        else:

            reason = (
                "The user asks for a future AFL match "
                "outcome prediction."
            )

        return {
            **state,

            "intent":
                "prediction",

            "router_reason":
                reason,
        }

    # =========================================================================
    # DATE-ONLY WITHOUT PENDING CLARIFICATION
    # =========================================================================

    if _is_date_only(query):

        return {
            **state,

            "intent":
                "off_topic",

            "router_reason":
                "The input is only a date and there is "
                "no pending AFL prediction clarification.",
        }

    # =========================================================================
    # NORMAL LLM / EXISTING ROUTER
    # =========================================================================

    result = classify_intent(
        query
    )

    return {
        **state,

        "intent":
            result.intent,

        "router_reason":
            result.reasoning,
    }