"""Executable LangGraph workflow for Sara's real-estate agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .callbacks import trace_transition
from .nodes import AgentNodes
from .state import AgentState, Appointment, ConversationStage, Message, UserIntent
from .validators import StateValidationError, validate_booking, validate_search


def _traced(name: str, handler):
    async def run(state: AgentState) -> dict[str, Any]:
        try:
            result = await handler(state)
            trace_transition(state, name)
            result["conversation_log"] = state.conversation_log
            return result
        except Exception as exc:
            state.errors.append(f"{name}: {exc}")
            trace_transition(state, name, "error")
            return {
                "errors": state.errors,
                "conversation_log": state.conversation_log,
                "conversation_stage": ConversationStage.GOODBYE,
                "messages": state.messages
                + [Message(role="assistant", content="System issue aa raha hai; representative follow-up karega.")],
            }

    return run


def build_graph(nodes: AgentNodes):
    """Build and compile the production conversation graph."""
    builder = StateGraph(AgentState)

    async def search(state: AgentState) -> dict[str, Any]:
        validate_search(state)
        return await nodes.rag_retrieval_node(state)

    async def reschedule(state: AgentState) -> dict[str, Any]:
        if not state.appointment or not state.proposed_datetime:
            raise StateValidationError("appointment and new date/time are required")
        result = await nodes.tool_executor.reschedule_appointment(
            appointment_id=str(state.appointment.appointment_id),
            starts_at=state.proposed_datetime,
        )
        if result.get("error"):
            raise RuntimeError(result["error"])
        appointment_data = result.get("appointment", result)
        appointment = Appointment.model_validate(appointment_data)
        return {
            "appointment": appointment,
            "booking_status": "rescheduled",
            "conversation_stage": ConversationStage.GOODBYE,
            "messages": state.messages
            + [Message(role="assistant", content=f"Appointment {appointment.starts_at} ke liye reschedule ho gayi hai.")],
        }

    async def cancel(state: AgentState) -> dict[str, Any]:
        if not state.appointment:
            raise StateValidationError("appointment is required for cancellation")
        result = await nodes.tool_executor.cancel_appointment(
            appointment_id=str(state.appointment.appointment_id)
        )
        if result.get("error"):
            raise RuntimeError(result["error"])
        appointment_data = result.get("appointment", result)
        appointment = Appointment.model_validate(appointment_data)
        return {
            "appointment": appointment,
            "booking_status": "cancelled",
            "conversation_stage": ConversationStage.GOODBYE,
            "messages": state.messages
            + [Message(role="assistant", content="Appointment successfully cancel ho gayi hai.")],
        }

    async def booking(state: AgentState) -> dict[str, Any]:
        validate_booking(state)
        return await nodes.booking_node(state)

    for name, handler in {
        "greeting": nodes.greeting_node,
        "intent_detection": nodes.intent_detection_node,
        "clarification": nodes.clarification_node,
        "rag_retrieval": search,
        "recommendation": nodes.recommendation_node,
        "booking": booking,
        "reschedule": reschedule,
        "cancellation": cancel,
        "goodbye": nodes.goodbye_node,
    }.items():
        builder.add_node(name, _traced(name, handler))

    builder.add_conditional_edges(
        START, lambda state: "intent_detection" if state.messages else "greeting"
    )
    builder.add_edge("greeting", END)
    builder.add_conditional_edges(
        "intent_detection",
        lambda state: {
            UserIntent.SCHEDULE_VISIT: "booking",
            UserIntent.RESCHEDULE_VISIT: "reschedule",
            UserIntent.CANCEL_VISIT: "cancellation",
            UserIntent.OFF_TOPIC: "goodbye",
        }.get(state.current_intent, "clarification"),
    )
    builder.add_conditional_edges(
        "clarification",
        lambda state: END if state.clarification_needed else "rag_retrieval",
    )
    builder.add_edge("rag_retrieval", "recommendation")
    builder.add_edge("recommendation", END)
    builder.add_edge("booking", END)
    builder.add_edge("reschedule", END)
    builder.add_edge("cancellation", END)
    builder.add_edge("goodbye", END)
    return builder.compile()
