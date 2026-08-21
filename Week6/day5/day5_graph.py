from __future__ import annotations

import time
import pprint

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from state import AgentState

from nodes.guardrail_node import guardrail_node
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


# ============================================================================
# ENVIRONMENT
# ============================================================================

load_dotenv()


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_start(state: AgentState):
    """
    Decide whether this is:

    1. A normal new query -> guardrail
    2. A follow-up answer to a previous clarification -> pending_clarification
    """

    if state.get("clarification_needed"):
        return "pending_clarification"

    return "guardrail"


def route_after_guardrail(state: AgentState):
    """
    After deterministic guardrail:

    - off_topic -> off_topic node
    - otherwise -> router
    """

    if state.get("intent") == "off_topic":
        return "off_topic"

    return "router"


def route_intent(state: AgentState):
    """
    Route according to classifier intent.
    """

    return state.get("intent", "off_topic")


def route_after_validation(state: AgentState):
    """
    Decide what happens after validation.
    """

    status = state.get("validation_status")

    if status == "valid":
        return "format"

    if status == "needs_clarification":
        return "clarification"

    return "fallback"


# ============================================================================
# GRAPH
# ============================================================================

def build_graph():

    graph = StateGraph(AgentState)

    # ------------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------------

    graph.add_node(
        "guardrail",
        guardrail_node
    )

    graph.add_node(
        "router",
        router_node
    )

    graph.add_node(
        "pending_clarification",
        pending_clarification_node
    )

    graph.add_node(
        "retrieval",
        retrieval_node
    )

    graph.add_node(
        "prediction",
        prediction_node
    )

    graph.add_node(
        "factual",
        factual_node
    )

    graph.add_node(
        "off_topic",
        off_topic_node
    )

    graph.add_node(
        "validation",
        validation_node
    )

    graph.add_node(
        "format",
        formatter_node
    )

    graph.add_node(
        "clarification",
        clarification_node
    )

    graph.add_node(
        "fallback",
        fallback_node
    )

    # ------------------------------------------------------------------------
    # START
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        START,
        route_start,
        {
            "guardrail": "guardrail",
            "pending_clarification": "pending_clarification",
        }
    )

    # ------------------------------------------------------------------------
    # GUARDRAIL
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "router": "router",
            "off_topic": "off_topic",
        }
    )

    # ------------------------------------------------------------------------
    # PENDING CLARIFICATION
    #
    # Example:
    #
    # Turn 1:
    # "Who will win Collingwood vs Geelong?"
    #
    # -> asks for date
    #
    # Turn 2:
    # "2025-08-30"
    #
    # -> pending_clarification
    # -> prediction
    # ------------------------------------------------------------------------

    graph.add_edge(
        "pending_clarification",
        "prediction"
    )

    # ------------------------------------------------------------------------
    # INTENT ROUTING
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "retrieval": "retrieval",
            "prediction": "prediction",
            "factual": "factual",
            "off_topic": "off_topic",
        }
    )

    # ------------------------------------------------------------------------
    # RETRIEVAL
    # ------------------------------------------------------------------------

    graph.add_edge(
        "retrieval",
        "validation"
    )

    # ------------------------------------------------------------------------
    # PREDICTION
    # ------------------------------------------------------------------------

    graph.add_edge(
        "prediction",
        "validation"
    )

    # ------------------------------------------------------------------------
    # FACTUAL
    # ------------------------------------------------------------------------

    graph.add_edge(
        "factual",
        "format"
    )

    # ------------------------------------------------------------------------
    # OFF TOPIC
    # ------------------------------------------------------------------------

    graph.add_edge(
        "off_topic",
        "format"
    )

    # ------------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "format": "format",
            "clarification": "clarification",
            "fallback": "fallback",
        }
    )

    # ------------------------------------------------------------------------
    # TERMINAL NODES
    # ------------------------------------------------------------------------

    graph.add_edge(
        "format",
        END
    )

    graph.add_edge(
        "clarification",
        END
    )

    graph.add_edge(
        "fallback",
        END
    )

    # ------------------------------------------------------------------------
    # CHECKPOINTER
    # ------------------------------------------------------------------------

    return graph.compile(
        checkpointer=MemorySaver()
    )


# ============================================================================
# BUILD APP
# ============================================================================

app = build_graph()


# ============================================================================
# RUN QUERY
# ============================================================================

def run_query(
    query: str,
    conversation_id: str = "afl-day5-cli",
    history=None,
):
    """
    Execute one conversation turn.

    Supports multi-turn clarification.

    Example:

        User: Who will win Collingwood vs Geelong?
        Assistant: Please provide the date...

        User: 2025-08-30
        Assistant: Model prediction: Geelong Cats...
    """

    started = time.perf_counter()

    # ================================================================
    # GET PREVIOUS CHECKPOINT STATE
    # ================================================================

    checkpoint = app.get_state(
        {
            "configurable": {
                "thread_id": conversation_id
            }
        }
    )

    previous_state = checkpoint.values or {}

    # ================================================================
    # CHECK PENDING CLARIFICATION
    # ================================================================

    previous_clarification_needed = previous_state.get(
        "clarification_needed"
    )

    previous_pending_tool_name = previous_state.get(
        "pending_tool_name"
    )

    # ================================================================
    # PRESERVE PREDICTION CONTEXT
    # ================================================================

    previous_team_a = previous_state.get(
        "team_a"
    )

    previous_team_b = previous_state.get(
        "team_b"
    )

    previous_tool_input = previous_state.get(
        "tool_input"
    )

    previous_date = previous_state.get(
        "date"
    )

    # ================================================================
    # BUILD NEW STATE
    # ================================================================

    state = {
        # ------------------------------------------------------------
        # Current user input
        # ------------------------------------------------------------

        "user_query": query,

        # ------------------------------------------------------------
        # Conversation history
        # ------------------------------------------------------------

        "conversation_history": history or [],

        # ------------------------------------------------------------
        # IMPORTANT:
        # Start fresh routing for every turn.
        # ------------------------------------------------------------

        "intent": None,
        "router_reason": None,

        # ------------------------------------------------------------
        # Tool context
        # ------------------------------------------------------------

        "tool_name": previous_state.get(
            "tool_name"
        ),

        "tool_input": previous_tool_input,

        "tool_result": None,

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        "validation_status": None,
        "validation_error": None,

        # ------------------------------------------------------------
        # Clarification context
        # ------------------------------------------------------------

        "clarification_needed": (
            previous_clarification_needed
        ),

        "pending_tool_name": (
            previous_pending_tool_name
        ),

        # ------------------------------------------------------------
        # Prediction context
        # ------------------------------------------------------------

        "team_a": previous_team_a,
        "team_b": previous_team_b,
        "date": previous_date,

        # ------------------------------------------------------------
        # Execution state
        # ------------------------------------------------------------

        "final_response": None,
        "error": None,
        "tools_called": [],
    }

    # ================================================================
    # INVOKE GRAPH
    # ================================================================

    result = app.invoke(
        state,
        config={
            "configurable": {
                "thread_id": conversation_id
            }
        }
    )

    # ================================================================
    # LATENCY
    # ================================================================

    result["latency_ms"] = round(
        (
            time.perf_counter()
            - started
        ) * 1000,
        2
    )

    return result


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":

    print(
        "AFL Day 5 LangGraph application"
    )

    print(
        "Type 'quit' to exit."
    )

    history = []

    while True:

        q = input("\nYou: ").strip()

        if q.lower() in {
            "quit",
            "exit"
        }:
            break

        # ------------------------------------------------------------
        # Run query
        # ------------------------------------------------------------

        result = run_query(
            q,
            conversation_id="afl-day5-cli",
            history=history,
        )

        # ------------------------------------------------------------
        # Assistant response
        # ------------------------------------------------------------

        print(
            "\nAssistant:",
            result.get(
                "final_response",
                ""
            )
        )

        # ------------------------------------------------------------
        # Update conversation history
        # ------------------------------------------------------------

        history += [
            {
                "role": "user",
                "content": q,
            },
            {
                "role": "assistant",
                "content": result.get(
                    "final_response",
                    ""
                ),
            },
        ]

        # ------------------------------------------------------------
        # Debug information
        # ------------------------------------------------------------

        pprint.pp(
            {
                "intent": result.get(
                    "intent"
                ),

                "router_reason": result.get(
                    "router_reason"
                ),

                "tools_called": result.get(
                    "tools_called"
                ),

                "validation_status": result.get(
                    "validation_status"
                ),

                "latency_ms": result.get(
                    "latency_ms"
                ),

                "error": result.get(
                    "error"
                ),
            }
        )