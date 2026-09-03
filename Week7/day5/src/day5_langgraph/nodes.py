"""Node implementations for LangGraph agent."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .state import (
    AgentState,
    Appointment,
    ConversationStage,
    Message,
    PropertyMatch,
    UserIntent,
    UserProfile,
)
from .tools import ToolExecutor

logger = logging.getLogger(__name__)


class AgentNodes:
    """Graph node implementations for conversation flow."""

    def __init__(self, tool_executor: ToolExecutor, llm_client: Any):
        self.tool_executor = tool_executor
        self.llm_client = llm_client

    async def greeting_node(self, state: AgentState) -> dict[str, Any]:
        """Greeting node - welcome user and establish context."""
        logger.info(f"Processing greeting for session {state.session_id}")

        # Generate greeting message
        greeting_prompt = """You are Sara, a warm and professional real estate sales agent. 
Greet the customer in UrduLish (Urdu + English mix). Keep it natural, friendly, and ask how you can help.
Example: "Assalam-o-Alaikum! Sara speaking. Main aap ki kis tarah madad kar sakta hoon?"
"""

        # TODO: Call LLM to generate greeting
        response = "Assalam-o-Alaikum! Sara speaking. Main aap ki kis tarah madad kar sakta hoon?"

        # Add message to conversation
        state.messages.append(Message(role="assistant", content=response))

        # Transition to intent detection
        state.conversation_stage = ConversationStage.INTENT_DETECTION
        state.updated_at = datetime.utcnow()

        return {"conversation_stage": state.conversation_stage.value, "messages": state.messages}

    async def intent_detection_node(self, state: AgentState) -> dict[str, Any]:
        """Intent detection node - classify user intent."""
        logger.info(f"Detecting intent for session {state.session_id}")

        if not state.messages:
            state.current_intent = UserIntent.UNCLEAR
            state.intent_confidence = 0.0
        else:
            last_message = state.messages[-1].content

            # TODO: Call LLM to classify intent
            # For now, use simple heuristics
            if any(word in last_message.lower() for word in ["buy", "purchase", "lena"]):
                state.current_intent = UserIntent.BUYER_INQUIRY
                state.intent_confidence = 0.8
            elif any(word in last_message.lower() for word in ["rent", "lease", "kiraey"]):
                state.current_intent = UserIntent.RENTAL_INQUIRY
                state.intent_confidence = 0.8
            elif any(word in last_message.lower() for word in ["invest", "investment"]):
                state.current_intent = UserIntent.INVESTMENT_INQUIRY
                state.intent_confidence = 0.8
            elif any(word in last_message.lower() for word in ["reschedule", "change time"]):
                state.current_intent = UserIntent.RESCHEDULE_VISIT
                state.intent_confidence = 0.9
            elif any(word in last_message.lower() for word in ["cancel", "cancellation"]):
                state.current_intent = UserIntent.CANCEL_VISIT
                state.intent_confidence = 0.9
            elif any(word in last_message.lower() for word in ["appointment", "book visit", "schedule visit"]):
                state.current_intent = UserIntent.SCHEDULE_VISIT
                state.intent_confidence = 0.9
            elif any(word in last_message.lower() for word in ["commercial", "office", "shop"]):
                state.current_intent = UserIntent.COMMERCIAL_INQUIRY
                state.intent_confidence = 0.8
            else:
                state.current_intent = UserIntent.UNCLEAR
                state.intent_confidence = 0.5

        logger.info(f"Detected intent: {state.current_intent} (confidence: {state.intent_confidence})")

        # Decide next stage
        if state.current_intent in [
            UserIntent.BUYER_INQUIRY,
            UserIntent.RENTAL_INQUIRY,
            UserIntent.INVESTMENT_INQUIRY,
        ]:
            state.conversation_stage = ConversationStage.CLARIFICATION
        else:
            state.conversation_stage = ConversationStage.CLARIFICATION

        state.updated_at = datetime.utcnow()

        return {
            "current_intent": state.current_intent.value if state.current_intent else None,
            "intent_confidence": state.intent_confidence,
            "conversation_stage": state.conversation_stage.value,
        }

    async def clarification_node(self, state: AgentState) -> dict[str, Any]:
        """Clarification node - ask for missing information."""
        logger.info(f"Clarifying requirements for session {state.session_id}")

        # Determine what information we need
        missing_fields = []

        if not state.user_profile.name:
            missing_fields.append("name")
        if not state.user_profile.phone:
            missing_fields.append("phone")
        if not state.user_profile.location:
            missing_fields.append("location")

        if state.current_intent == UserIntent.BUYER_INQUIRY:
            if not state.user_profile.budget_max:
                missing_fields.append("budget")
        elif state.current_intent == UserIntent.RENTAL_INQUIRY:
            if not state.user_profile.bedrooms:
                missing_fields.append("bedrooms")

        # Generate clarification questions
        questions = []
        if "name" in missing_fields:
            questions.append("Aap ka naam kya hai?")
        if "phone" in missing_fields:
            questions.append("Phone number kya hai?")
        if "location" in missing_fields:
            questions.append("Aap kis area mein dhoond rahe ho?")
        if "budget" in missing_fields:
            questions.append("Aap ka budget kya hai?")

        if questions:
            state.clarification_needed = True
            state.clarification_questions = questions

            # Ask first question
            response = questions[0]
            state.messages.append(Message(role="assistant", content=response))
            state.conversation_stage = ConversationStage.CLARIFICATION
        else:
            # All information collected, move to RAG
            state.clarification_needed = False
            state.conversation_stage = ConversationStage.RAG_RETRIEVAL

        state.updated_at = datetime.utcnow()

        return {
            "clarification_needed": state.clarification_needed,
            "clarification_questions": state.clarification_questions,
            "conversation_stage": state.conversation_stage.value,
            "messages": state.messages,
        }

    async def rag_retrieval_node(self, state: AgentState) -> dict[str, Any]:
        """RAG retrieval node - search knowledge base for properties."""
        logger.info(f"Retrieving properties for session {state.session_id}")

        # Build search query from user profile
        search_params = {
            "location": state.user_profile.location or "all",
            "min_price": state.user_profile.budget_min or 0,
            "max_price": state.user_profile.budget_max or 1000000000,
            "bedrooms": state.user_profile.bedrooms,
            "purpose": state.user_profile.purpose or "all",
            "limit": 5,
        }

        results = await self.tool_executor.search_properties(**search_params)

        # Extract properties and store in state
        if isinstance(results, dict) and "properties" in results:
            state.detected_properties = [self._property_match(row) for row in results["properties"]]
            state.rag_confidence = 0.8
        else:
            state.detected_properties = []
            state.rag_confidence = 0.0

        logger.info(f"Retrieved {len(state.detected_properties)} properties")

        # Move to recommendation
        state.conversation_stage = ConversationStage.RECOMMENDATION
        state.updated_at = datetime.utcnow()

        return {
            "detected_properties": state.detected_properties,
            "rag_confidence": state.rag_confidence,
            "conversation_stage": state.conversation_stage.value,
        }

    async def recommendation_node(self, state: AgentState) -> dict[str, Any]:
        """Recommendation node - recommend best matching property."""
        logger.info(f"Generating recommendations for session {state.session_id}")

        if not state.detected_properties:
            response = "Afsoos, ab ke liye koi property available nahi hai. Kya aap doosra search try karna chahenge?"
            state.messages.append(Message(role="assistant", content=response))
            state.conversation_stage = ConversationStage.GOODBYE
        else:
            # Select best property (first one with highest score)
            best_property = state.detected_properties[0]
            state.selected_property = best_property

            # Generate recommendation message
            response = f"Bilkul! Main aap ke liye {best_property.name} recommend kar rahi hoon. "
            response += f"Yeh property {best_property.location} mein hai, aur price PKR {best_property.price:,.0f} hai. "
            response = (
                f"Bilkul! Main aap ke liye {best_property.name} recommend kar rahi hoon. "
                f"Yeh property {best_property.location} mein hai aur price "
                f"PKR {best_property.price:,.0f} hai. Kya aap visit karna chahenge?"
            )

            state.messages.append(Message(role="assistant", content=response))
            state.conversation_stage = ConversationStage.BOOKING

        state.updated_at = datetime.utcnow()

        return {
            "selected_property": state.selected_property.model_dump() if state.selected_property else None,
            "conversation_stage": state.conversation_stage.value,
            "messages": state.messages,
        }

    async def booking_node(self, state: AgentState) -> dict[str, Any]:
        """Booking node - schedule property visit."""
        logger.info(f"Booking appointment for session {state.session_id}")

        if not state.selected_property:
            state.conversation_stage = ConversationStage.GOODBYE
            return {"conversation_stage": state.conversation_stage.value}

        profile = state.user_profile
        if not state.proposed_datetime or not profile.name or not profile.phone:
            response = "Visit book karne ke liye naam, phone, date aur time confirm kar dein."
            state.messages.append(Message(role="assistant", content=response))
            state.booking_status = "needs_confirmation"
            return {"booking_status": state.booking_status, "messages": state.messages}

        result = await self.tool_executor.book_appointment(
            client_name=profile.name,
            client_phone=profile.phone,
            employee_name="Sara AI Agent",
            employee_email=profile.preferences.get("employee_email", "sara@realestatehub.pk"),
            property_id=state.selected_property.property_id,
            property_name=state.selected_property.name,
            starts_at=state.proposed_datetime,
            meeting_notes="Booked by Sara LangGraph agent",
        )
        if result.get("error") or result.get("status") == "failed":
            response = "Booking confirm nahi ho saki. Main representative ko follow-up ke liye note kar rahi hoon."
            state.booking_status = "failed"
        else:
            appointment_data = result.get("appointment", result)
            state.appointment = Appointment.model_validate(appointment_data)
            response = f"Ji, appointment {state.appointment.starts_at} ke liye confirm ho gayi hai."
            state.booking_status = "confirmed"
        state.messages.append(Message(role="assistant", content=response))
        state.conversation_stage = ConversationStage.GOODBYE
        state.updated_at = datetime.utcnow()

        return {
            "booking_status": state.booking_status,
            "appointment": state.appointment,
            "conversation_stage": state.conversation_stage.value,
            "messages": state.messages,
        }

    @staticmethod
    def _property_match(row: dict[str, Any]) -> PropertyMatch:
        """Normalize a verified Day 2 database row into graph state."""
        area = row.get("area") or ""
        city = row.get("city") or ""
        return PropertyMatch(
            property_id=row.get("property_id"),
            name=row.get("property_name") or row.get("name") or "Property",
            location=", ".join(part for part in (area, city) if part),
            price=int(row.get("price") or 0),
            bedrooms=int(row.get("bedrooms") or 0),
            bathrooms=int(row.get("bathrooms") or 0),
            area_sqft=int(row.get("covered_area") or row.get("area_sqft") or 0),
            amenities=list(row.get("amenities") or []),
            score=float(row.get("score") or 1.0),
            reason=row.get("reason") or "Verified match for the supplied filters",
        )

    async def goodbye_node(self, state: AgentState) -> dict[str, Any]:
        """Goodbye node - end conversation with summary."""
        logger.info(f"Ending conversation for session {state.session_id}")

        summary = f"Thanks for calling, {state.user_profile.name or 'sir'}! "
        if state.appointment:
            summary += f"Aap ka appointment {state.appointment.starts_at} par confirm hai. "
        summary += "Bye for now!"

        state.messages.append(Message(role="assistant", content=summary))

        logger.info(f"Conversation ended. Session: {state.session_id}")

        return {"messages": state.messages, "conversation_stage": ConversationStage.GOODBYE.value}
