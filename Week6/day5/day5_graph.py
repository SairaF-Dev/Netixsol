"""
day5_graph.py
-------------
AFL Day 5 LangGraph Capstone

Fixed version.

Important fixes
---------------
1. Previous tool_input is NOT blindly copied into the new turn.
2. Previous AFL prediction context is preserved through:
       team_a
       team_b
       date
3. Previous clarification state is preserved safely.
4. Current query gets a fresh tool_input.
5. Router can use previous conversation context.
6. Retrieval queries cannot accidentally inherit prediction inputs.
7. Prediction follow-ups can reuse previous teams.
8. Date/year follow-ups can be routed by router_node.
9. Safe graph-level error handling.
"""

from __future__ import annotations

import logging
import os
import time

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
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("afl_day5")


# ============================================================================
# START ROUTING
# ============================================================================

def route_start(state: AgentState):
    """
    Decide whether the current query is:

    1. A new query
    2. An answer to a previous clarification request
    """

    clarification = state.get("clarification_needed")

    if clarification:
        return "pending_clarification"

    return "guardrail"


# ============================================================================
# GUARDRAIL ROUTING
# ============================================================================

def route_after_guardrail(state: AgentState):
    """
    After guardrail:

    off_topic -> off_topic
    otherwise -> router
    """

    if state.get("intent") == "off_topic":
        return "off_topic"

    return "router"


# ============================================================================
# INTENT ROUTING
# ============================================================================

def route_intent(state: AgentState):
    """
    Route according to the classified intent.
    """

    intent = state.get("intent")

    valid_routes = {
        "retrieval",
        "prediction",
        "factual",
        "off_topic",
    }

    if intent in valid_routes:
        return intent

    logger.warning(
        "Unknown intent received: %r. Routing to off_topic.",
        intent,
    )

    return "off_topic"


# ============================================================================
# VALIDATION ROUTING
# ============================================================================

def route_after_validation(state: AgentState):
    """
    Decide what happens after validation.
    """

    status = state.get("validation_status")

    if status == "valid":
        return "format"

    if status == "needs_clarification":
        return "clarification"

    if status == "invalid":
        return "fallback"

    return "fallback"


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_graph():

    graph = StateGraph(AgentState)

    # ------------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------------

    graph.add_node(
        "guardrail",
        guardrail_node,
    )

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
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        START,
        route_start,
        {
            "guardrail": "guardrail",
            "pending_clarification": "pending_clarification",
        },
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
        },
    )

    # ------------------------------------------------------------------------
    # PENDING CLARIFICATION
    # ------------------------------------------------------------------------

    graph.add_edge(
        "pending_clarification",
        "prediction",
    )

    # ------------------------------------------------------------------------
    # ROUTER
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
    # RETRIEVAL
    # ------------------------------------------------------------------------

    graph.add_edge(
        "retrieval",
        "validation",
    )

    # ------------------------------------------------------------------------
    # PREDICTION
    # ------------------------------------------------------------------------

    graph.add_edge(
        "prediction",
        "validation",
    )

    # ------------------------------------------------------------------------
    # FACTUAL
    # ------------------------------------------------------------------------

    graph.add_edge(
        "factual",
        "format",
    )

    # ------------------------------------------------------------------------
    # OFF TOPIC
    # ------------------------------------------------------------------------

    graph.add_edge(
        "off_topic",
        "format",
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
        },
    )

    # ------------------------------------------------------------------------
    # TERMINAL NODES
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
    # ------------------------------------------------------------------------

    return graph.compile(
        checkpointer=MemorySaver(),
    )


# ============================================================================
# BUILD APP
# ============================================================================

app = build_graph()


# ============================================================================
# SAFE ERROR RESULT
# ============================================================================

def build_error_result(
    query: str,
    error: Exception,
    started: float,
):
    """
    Return a safe result if the graph itself crashes.
    """

    logger.exception(
        "Graph execution failed for query=%r",
        query,
    )

    return {
        "user_query": query,
        "intent": "off_topic",
        "router_reason": "Graph execution failed safely.",

        "tool_name": None,
        "tool_input": None,
        "tool_result": None,

        "tools_called": [],

        "validation_status": "invalid",
        "validation_error": None,

        "clarification_needed": None,
        "pending_tool_name": None,

        "team_a": None,
        "team_b": None,
        "date": None,

        "final_response": (
            "Sorry, I couldn't process that request right now. "
            "Please try your AFL question again."
        ),

        "error": str(error),

        "latency_ms": round(
            (time.perf_counter() - started) * 1000,
            2,
        ),
    }


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

    Important:
        - Never reuse stale tool_input.
        - Preserve useful AFL conversation context.
        - Preserve previous intent only as context.
        - Let the router determine the current intent.
        - A year/date follow-up can refer to the previous prediction
          OR previous retrieval depending on previous intent.
    """

    started = time.perf_counter()

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    query = (query or "").strip()

    if not query:
        return {
            "user_query": "",
            "intent": "off_topic",
            "router_reason": "Empty user query.",

            "tool_name": None,
            "tool_input": None,
            "tool_result": None,

            "tools_called": [],

            "validation_status": "invalid",
            "validation_error": "Empty query.",

            "final_response": (
                "Please enter an AFL-related question."
            ),

            "error": None,

            "latency_ms": round(
                (time.perf_counter() - started) * 1000,
                2,
            ),
        }

    # =========================================================================
    # CHECKPOINT CONFIG
    # =========================================================================

    config = {
        "configurable": {
            "thread_id": conversation_id,
        }
    }

    try:

        # =====================================================================
        # GET PREVIOUS CHECKPOINT
        # =====================================================================

        checkpoint = app.get_state(config)

        previous_state = checkpoint.values or {}

        # =====================================================================
        # PREVIOUS CONTEXT
        # =====================================================================

        previous_intent = previous_state.get("intent")
        previous_tool_name = previous_state.get("tool_name")

        previous_clarification_needed = previous_state.get(
            "clarification_needed"
        )

        previous_pending_tool_name = previous_state.get(
            "pending_tool_name"
        )

        previous_team_a = previous_state.get("team_a")
        previous_team_b = previous_state.get("team_b")
        previous_date = previous_state.get("date")
        previous_player_name = previous_state.get("player_name")
        previous_player_id = previous_state.get("player_id")

        # Previous query is useful for resolving:
        #
        #   What were Nick Daicos's statistics?
        #   What about 2024?
        #
        previous_query = previous_state.get("user_query")

        # =====================================================================
        # CRITICAL:
        #
        # NEVER carry previous tool_input into a fresh turn.
        # =====================================================================

        current_tool_input = None

        # =====================================================================
        # BUILD FRESH STATE
        # =====================================================================

        state: AgentState = {

            # Current user input
            "user_query": query,

            # Conversation
            "conversation_history": history or [],

            # Current routing must start fresh
            "intent": None,
            "router_reason": None,

            # Current tool execution must start fresh
            "tool_name": None,
            "tool_input": None,
            "tool_result": None,
            "tools_called": [],

            # Validation
            "validation_status": None,
            "validation_error": None,

            # Clarification state
            "clarification_needed": previous_clarification_needed,
            "pending_tool_name": previous_pending_tool_name,

            # AFL context
            "team_a": previous_team_a,
            "team_b": previous_team_b,
            "date": previous_date,
            "player_name": previous_player_name,
            "player_id": previous_player_id,

            # Final response
            "final_response": None,

            # Error / monitoring
            "error": None,

            # Metadata
            "prediction_metadata": {},

            "latency_ms": 0.0,

            "request_id": None,
            "node_name": None,
            "success": None,

            # -----------------------------------------------------------------
            # Extra context fields
            #
            # These are useful for follow-up resolution.
            # -----------------------------------------------------------------

            "previous_intent": previous_intent,
            "previous_tool_name": previous_tool_name,
            "previous_query": previous_query,
        }

        # =========================================================================
        # DEBUG
        # =========================================================================

        print("--------------------")
        print("\n--- BEFORE GRAPH ---")

        print("conversation_id:", conversation_id)
        print("current_query:", query)

        print("previous_query:", previous_query)
        print("previous_intent:", previous_intent)
        print("previous_tool_name:", previous_tool_name)

        print(
            "previous_clarification_needed:",
            previous_clarification_needed,
        )

        print(
            "previous_pending_tool_name:",
            previous_pending_tool_name,
        )

        print("previous_team_a:", previous_team_a)
        print("previous_team_b:", previous_team_b)
        print("previous_date:", previous_date)

        print("current_tool_input:", current_tool_input)

        print("--------------------\n")

        # =========================================================================
        # INVOKE GRAPH
        # =========================================================================

        result = app.invoke(
            state,
            config=config,
        )

        # =========================================================================
        # EMPTY RESULT PROTECTION
        # =========================================================================

        if not result:
            raise RuntimeError(
                "Graph returned an empty state."
            )

        # =========================================================================
        # FINAL RESPONSE PROTECTION
        # =========================================================================

        if not result.get("final_response"):

            logger.warning(
                "Graph completed without final_response."
            )

            result["final_response"] = (
                "Sorry, I could not generate a response. "
                "Please try again."
            )

        # =========================================================================
        # LATENCY
        # =========================================================================

        result["latency_ms"] = round(
            (
                time.perf_counter()
                - started
            ) * 1000,
            2,
        )

        return result

    except Exception as exc:

        return build_error_result(
            query=query,
            error=exc,
            started=started,
        )

# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":

    print()
    print("AFL Day 5 LangGraph application")
    print("Type 'quit' to exit.")
    print()

    history: list[dict[str, str]] = []

    while True:

        # ---------------------------------------------------------------------
        # INPUT
        # ---------------------------------------------------------------------

        try:

            q = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):

            print(
                "\n\nExiting AFL assistant."
            )

            break

        # ---------------------------------------------------------------------
        # EXIT
        # ---------------------------------------------------------------------

        if q.lower() in {
            "quit",
            "exit",
        }:

            print(
                "\nGoodbye!"
            )

            break

        # ---------------------------------------------------------------------
        # EMPTY
        # ---------------------------------------------------------------------

        if not q:

            print(
                "\nAssistant: "
                "Please enter an AFL-related question."
            )

            continue

        # ---------------------------------------------------------------------
        # RUN
        # ---------------------------------------------------------------------

        result = run_query(
            q,
            conversation_id="afl-day5-cli",
            history=history,
        )

        # ---------------------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------------------

        print(
            "\nAssistant:",
            result.get(
                "final_response",
                "",
            ),
        )

        # ---------------------------------------------------------------------
        # HISTORY
        # ---------------------------------------------------------------------

        history.extend(
            [
                {
                    "role": "user",
                    "content": q,
                },
                {
                    "role": "assistant",
                    "content": result.get(
                        "final_response",
                        "",
                    ),
                },
            ]
        )

        # ---------------------------------------------------------------------
        # DEBUG
        # ---------------------------------------------------------------------

        print(
            "\n--- AFTER GRAPH ---"
        )

        print(
            "intent:",
            result.get("intent"),
        )

        print(
            "router_reason:",
            result.get("router_reason"),
        )

        print(
            "tool_name:",
            result.get("tool_name"),
        )

        print(
            "tool_input:",
            result.get("tool_input"),
        )

        print(
            "tool_result:",
            result.get("tool_result"),
        )

        print(
            "validation_status:",
            result.get("validation_status"),
        )

        print(
            "clarification_needed:",
            result.get("clarification_needed"),
        )

        print(
            "pending_tool_name:",
            result.get("pending_tool_name"),
        )

        print(
            "team_a:",
            result.get("team_a"),
        )

        print(
            "team_b:",
            result.get("team_b"),
        )

        print(
            "date:",
            result.get("date"),
        )

        print(
            "latency_ms:",
            result.get("latency_ms"),
        )

        print("-------------------\n")
