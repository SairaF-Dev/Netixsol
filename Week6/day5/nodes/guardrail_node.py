from __future__ import annotations

import re

from state import AgentState


DATE_ONLY_RE = re.compile(
    r"^\s*20\d{2}-\d{2}-\d{2}\s*$"
)


# ============================================================================
# PROMPT-INJECTION PATTERNS
# ============================================================================

PROMPT_INJECTION_PATTERNS = (
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bignore\s+(all\s+)?prior\s+instructions\b",
    r"\bforget\s+(all\s+)?previous\s+instructions\b",
    r"\bdisregard\s+(all\s+)?previous\s+instructions\b",
    r"\boverride\s+(the\s+)?system\s+prompt\b",
    r"\breveal\s+(the\s+)?system\s+prompt\b",
    r"\bshow\s+(me\s+)?your\s+system\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\bsystem\s+instructions\b",
    r"\bact\s+as\s+an?\s+(unrestricted|general)\s+assistant\b",
    r"\byou\s+are\s+no\s+longer\s+restricted\b",
    r"\bdisable\s+(your\s+)?guardrails\b",
    r"\bbypass\s+(your\s+)?guardrails\b",
    r"\bdo\s+not\s+follow\s+(your\s+)?instructions\b",
)


def _is_date_only(text: str) -> bool:
    return bool(
        DATE_ONLY_RE.fullmatch(text.strip())
    )


def _is_prompt_injection(text: str) -> bool:
    q = text.casefold()

    return any(
        re.search(pattern, q)
        for pattern in PROMPT_INJECTION_PATTERNS
    )


def guardrail_node(
    state: AgentState,
) -> AgentState:

    query = state.get(
        "user_query",
        "",
    ).strip()

    # =========================================================================
    # 1. PROMPT INJECTION PROTECTION
    # =========================================================================

    if _is_prompt_injection(query):

        return {
            **state,

            "intent": "off_topic",

            "router_reason": (
                "Prompt-injection attempt detected. "
                "The AFL-only system instructions remain enforced."
            ),

            "tool_name": "scope_guardrail",

            "tools_called": (
                state.get("tools_called", [])
                + ["scope_guardrail"]
            ),

            "tool_result": {
                "blocked": True,
                "reason": "prompt_injection",
            },

            "validation_status": "valid",

            "clarification_needed": None,
            "pending_tool_name": None,

            "final_response": (
                "I can only help with AFL-related questions. "
                "I can't follow requests to override or bypass my instructions."
            ),
        }

    # =========================================================================
    # 2. DATE-ONLY FOLLOW-UP
    # =========================================================================

    if _is_date_only(query):

        pending_tool = state.get(
            "pending_tool_name"
        )

        clarification_needed = state.get(
            "clarification_needed"
        )

        team_a = state.get("team_a")
        team_b = state.get("team_b")

        if (
            pending_tool
            == "match_winner_prediction"
            and clarification_needed == "date"
            and team_a
            and team_b
        ):

            return {
                **state,

                "intent": "prediction",

                "router_reason": (
                    "The user supplied the date requested "
                    "for a pending AFL match prediction."
                ),

                "clarification_needed": "date",

                "pending_tool_name":
                    "match_winner_prediction",
            }

        if (
            pending_tool
            == "top_player_prediction"
            and clarification_needed == "date"
            and team_a
        ):

            return {
                **state,

                "intent": "prediction",

                "router_reason": (
                    "The user supplied the date requested "
                    "for a pending AFL top-player prediction."
                ),

                "clarification_needed": "date",

                "pending_tool_name":
                    "top_player_prediction",
            }

    # =========================================================================
    # 3. NORMAL QUERY
    # =========================================================================

    return state