from __future__ import annotations

import re

from state import AgentState


# ============================================================================
# FACTUAL ANSWERS
# ============================================================================

FACTUAL_ANSWERS = {
    "behind": (
        "A behind is worth **1 point** in AFL. "
        "It is scored when the ball passes through the goal area "
        "without completely passing between the two goal posts."
    ),

    "mark": (
        "A mark is a clean catch of the ball from a kick that has "
        "travelled at least **15 metres**. The player who takes the mark "
        "can stop play and take a kick without being tackled."
    ),

    "players_on_field": (
        "Each AFL team has **18 players on the field** during normal play, "
        "so there are **36 players** on the field in total."
    ),

    "free_kick": (
        "A free kick is awarded when a player infringes an AFL rule, "
        "such as holding, pushing, or committing an illegal tackle. "
        "The player awarded the free kick can then restart play."
    ),

    "goal": (
        "A goal is worth **6 points** in AFL. "
        "It is scored when the ball is completely kicked through "
        "the two large goal posts without being touched by another player."
    ),

    "premiership": (
        "The AFL premiership is the championship awarded to the team "
        "that wins the AFL Grand Final at the end of the season."
    ),

    "handball": (
        "A handball is a legal way of disposing of the ball by punching "
        "it with a clenched fist from the other hand. Unlike a throw, "
        "the ball must be punched rather than thrown."
    ),

    "scoring": (
        "In AFL, a **goal is worth 6 points** and a **behind is worth 1 point**. "
        "A team's score is written as goals.behinds.total points. "
        "For example, 10 goals and 8 behinds gives a total of 68 points."
    ),

    "quarters": (
        "An AFL match is normally divided into **four quarters**. "
        "The teams change ends after each quarter."
    ),

    "field": (
        "AFL is played on a large oval-shaped field. "
        "Each team has 18 players on the field during normal play."
    ),

    "bounce": (
        "The bounce is used by the umpire to restart play at the beginning "
        "of each quarter and after certain stoppages."
    ),

    "tackle": (
        "A tackle is an attempt to legally stop an opponent who has "
        "possession of the ball. AFL tackles must follow the game's "
        "contact rules."
    ),

    "disposal": (
        "A disposal is an intentional legal attempt to dispose of the ball. "
        "The two main types of disposal are a **kick** and a **handball**."
    ),
}


# ============================================================================
# QUERY HELPERS
# ============================================================================

def _contains_phrase(text: str, phrase: str) -> bool:
    """
    Case-insensitive whole-phrase matching.
    """

    return bool(
        re.search(
            rf"\b{re.escape(phrase)}\b",
            text,
        )
    )


# ============================================================================
# FACTUAL CLASSIFIER
# ============================================================================

def get_factual_answer(query: str) -> str:
    """
    Return a deterministic answer for supported general AFL questions.

    This node intentionally does not use an LLM so that factual answers
    remain predictable and evaluation-friendly.
    """

    q = (query or "").strip().casefold()

    if not q:
        return (
            "Please ask a question about AFL rules, scoring, "
            "players, teams, matches, or history."
        )

    # ------------------------------------------------------------------------
    # Scoring / behind
    # ------------------------------------------------------------------------

    if (
        _contains_phrase(q, "behind")
        and (
            "what is" in q
            or "how many points" in q
            or "worth" in q
            or "score" in q
        )
    ):
        return FACTUAL_ANSWERS["behind"]

    # ------------------------------------------------------------------------
    # Mark
    # ------------------------------------------------------------------------

    if (
        _contains_phrase(q, "mark")
        and (
            "what is" in q
            or "how does" in q
            or "how many metres" in q
            or "15 metres" in q
        )
    ):
        return FACTUAL_ANSWERS["mark"]

    # ------------------------------------------------------------------------
    # Players / teams on field
    # ------------------------------------------------------------------------

    if (
        (
            "how many players" in q
            or "how many teams" in q
        )
        and (
            "field" in q
            or "on the field" in q
        )
    ):
        return FACTUAL_ANSWERS["players_on_field"]

    # ------------------------------------------------------------------------
    # Free kick
    # ------------------------------------------------------------------------

    if (
        _contains_phrase(q, "free kick")
        or _contains_phrase(q, "free-kick")
    ):
        return FACTUAL_ANSWERS["free_kick"]

    # ------------------------------------------------------------------------
    # Goal
    # ------------------------------------------------------------------------

    if (
        _contains_phrase(q, "goal")
        and (
            "what is" in q
            or "worth" in q
            or "how many points" in q
            or "score" in q
        )
    ):
        return FACTUAL_ANSWERS["goal"]

    # ------------------------------------------------------------------------
    # Premiership
    # ------------------------------------------------------------------------

    if "premiership" in q:
        return FACTUAL_ANSWERS["premiership"]

    # ------------------------------------------------------------------------
    # Handball
    # ------------------------------------------------------------------------

    if "handball" in q:
        return FACTUAL_ANSWERS["handball"]

    # ------------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------------

    if (
        "afl scoring" in q
        or "how does scoring work" in q
        or "how is scoring" in q
        or "scoring in afl" in q
    ):
        return FACTUAL_ANSWERS["scoring"]

    # ------------------------------------------------------------------------
    # Quarters
    # ------------------------------------------------------------------------

    if (
        "how many quarters" in q
        or "quarters in afl" in q
        or "afl quarters" in q
    ):
        return FACTUAL_ANSWERS["quarters"]

    # ------------------------------------------------------------------------
    # Field
    # ------------------------------------------------------------------------

    if (
        "afl field" in q
        or "football field" in q
        or "field in afl" in q
    ):
        return FACTUAL_ANSWERS["field"]

    # ------------------------------------------------------------------------
    # Bounce
    # ------------------------------------------------------------------------

    if (
        "what is a bounce" in q
        or "what is the bounce" in q
        or "bounce in afl" in q
    ):
        return FACTUAL_ANSWERS["bounce"]

    # ------------------------------------------------------------------------
    # Tackle
    # ------------------------------------------------------------------------

    if (
        "what is a tackle" in q
        or "what is tackling" in q
        or "tackle in afl" in q
    ):
        return FACTUAL_ANSWERS["tackle"]

    # ------------------------------------------------------------------------
    # Disposal
    # ------------------------------------------------------------------------

    if (
        "what is a disposal" in q
        or "what are disposals" in q
        or "disposal in afl" in q
    ):
        return FACTUAL_ANSWERS["disposal"]

    # ------------------------------------------------------------------------
    # Generic fallback
    # ------------------------------------------------------------------------

    return (
        "I can answer general AFL questions about rules, scoring, "
        "players, teams, matches, competition structure, and history."
    )


# ============================================================================
# FACTUAL NODE
# ============================================================================

def factual_node(state: AgentState) -> AgentState:
    """
    LangGraph node for general AFL factual questions.
    """

    query = (
        state.get("user_query", "")
        or ""
    ).strip()

    answer = get_factual_answer(query)

    return {
        **state,

        "intent": "factual",

        "tool_name": "direct_factual_answer",

        "tools_called": (
            state.get("tools_called", [])
            + ["direct_factual_answer"]
        ),

        "tool_result": answer,

        "validation_status": "valid",

        "validation_error": None,

        "clarification_needed": None,

        "pending_tool_name": None,

        "final_response": answer,

        "error": None,
    }