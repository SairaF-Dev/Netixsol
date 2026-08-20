"""Week 6 Day 4 - AFL LangGraph integration.

Run:
    python day4_graph.py

Environment:
    OPENROUTER_API_KEY=...
    OPENAI_BASE_URL=https://openrouter.ai/api/v1
    ROUTER_MODEL=openai/gpt-oss-120b
"""

from __future__ import annotations

import pprint

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from state import AgentState

from nodes.router_node import router_node
from nodes.retrieval_node import retrieval_node
from nodes.prediction_node import prediction_node
from nodes.factual_node import factual_node
from nodes.off_topic_node import off_topic_node
from nodes.validation_node import validation_node
from nodes.formatter_node import formatter_node
from nodes.clarification_node import clarification_node
from nodes.fallback_node import fallback_node
from nodes.pending_clarification_node import pending_clarification_node


load_dotenv()


# ============================================================================
# START ROUTING
# ============================================================================

def route_start(state: AgentState) -> str:
    """
    Decide whether the current user message is:

    1. A normal new request -> router
    2. An answer to a previous clarification -> pending_clarification

    Example:

        User:
            Who will win Pies vs Cats?

        Assistant:
            Please provide the match date.

        User:
            2026-08-22

    The second message must NOT go through the normal intent router.
    """

    if state.get("clarification_needed"):
        return "pending_clarification"

    return "router"


# ============================================================================
# NORMAL INTENT ROUTING
# ============================================================================

def route_intent(state: AgentState) -> str:
    return state["intent"]


# ============================================================================
# VALIDATION ROUTING
# ============================================================================

def route_after_validation(state: AgentState) -> str:

    status = state.get("validation_status")

    if status == "valid":
        return "format"

    if status == "needs_clarification":
        return "clarification"

    return "fallback"


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_graph():

    graph = StateGraph(AgentState)

    # ------------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------------

    graph.add_node(
        "router",
        router_node,
    )

    graph.add_node(
        "pending_clarification",
        pending_clarification_node,
    )

    graph.add_node(
        "retrieval",
        retrieval_node,
    )

    graph.add_node(
        "prediction",
        prediction_node,
    )

    graph.add_node(
        "factual",
        factual_node,
    )

    graph.add_node(
        "off_topic",
        off_topic_node,
    )

    graph.add_node(
        "validation",
        validation_node,
    )

    graph.add_node(
        "format",
        formatter_node,
    )

    graph.add_node(
        "clarification",
        clarification_node,
    )

    graph.add_node(
        "fallback",
        fallback_node,
    )

    # ------------------------------------------------------------------------
    # START
    #
    # IMPORTANT:
    # Do NOT directly connect START -> router.
    #
    # We first check whether the previous turn left a pending clarification.
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        START,
        route_start,
        {
            "router": "router",
            "pending_clarification": "pending_clarification",
        },
    )

    # ------------------------------------------------------------------------
    # Pending clarification
    #
    # Example:
    #
    # Previous:
    #   Who will win Pies vs Cats?
    #
    # Current:
    #   2026-08-22
    #
    # pending_clarification restores the previous prediction context.
    # ------------------------------------------------------------------------

    graph.add_edge(
        "pending_clarification",
        "prediction",
    )

    # ------------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "retrieval": "retrieval",
            "prediction": "prediction",
            "factual": "factual",
            "off_topic": "off_topic",
        },
    )

    # ------------------------------------------------------------------------
    # Retrieval / Prediction -> Validation
    # ------------------------------------------------------------------------

    graph.add_edge(
        "retrieval",
        "validation",
    )

    graph.add_edge(
        "prediction",
        "validation",
    )

    # ------------------------------------------------------------------------
    # Factual / Off-topic -> Formatter
    # ------------------------------------------------------------------------

    graph.add_edge(
        "factual",
        "format",
    )

    graph.add_edge(
        "off_topic",
        "format",
    )

    # ------------------------------------------------------------------------
    # Validation routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "format": "format",
            "clarification": "clarification",
            "fallback": "fallback",
        },
    )

    # ------------------------------------------------------------------------
    # Terminal nodes
    # ------------------------------------------------------------------------

    graph.add_edge(
        "format",
        END,
    )

    graph.add_edge(
        "clarification",
        END,
    )

    graph.add_edge(
        "fallback",
        END,
    )

    # ------------------------------------------------------------------------
    # CHECKPOINTER
    #
    # MemorySaver keeps AgentState between turns using the same thread_id.
    # ------------------------------------------------------------------------

    checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
    )


app = build_graph()


# ============================================================================
# QUERY RUNNER
# ============================================================================

THREAD_ID = "afl-day4-cli"


def run_query(
    query: str,
    history: list[dict[str, str]] | None = None,
):

    config = {
        "configurable": {
            "thread_id": THREAD_ID,
        }
    }

    state: AgentState = {
        "user_query": query,
        "conversation_history": history or [],
    }

    return app.invoke(
        state,
        config=config,
    )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":

    print("AFL Day 4 LangGraph application")
    print("Type 'quit' to exit.\n")

    history: list[dict[str, str]] = []

    while True:

        query = input("You: ").strip()

        if query.lower() in {"quit", "exit"}:
            break

        result = run_query(
            query,
            history,
        )

        print(
            "\nAssistant:",
            result.get(
                "final_response",
                "",
            ),
        )

        # --------------------------------------------------------------------
        # Application-level conversation history
        # --------------------------------------------------------------------

        history.append(
            {
                "role": "user",
                "content": query,
            }
        )

        history.append(
            {
                "role": "assistant",
                "content": result.get(
                    "final_response",
                    "",
                ),
            }
        )

        # --------------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------------

        print("\n[trace]")

        pprint.pp(
            {
                "intent": result.get("intent"),
                "router_reason": result.get("router_reason"),
                "tool_name": result.get("tool_name"),
                "validation_status": result.get(
                    "validation_status"
                ),
            }
        )

        print()