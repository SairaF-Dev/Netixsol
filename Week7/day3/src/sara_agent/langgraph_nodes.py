"""LangGraph nodes for Sara conversation workflow.

Each node represents a step in the conversation pipeline:
1. greeting - Welcome and explain capabilities
2. intent_detection - Classify user intent
3. memory_update - Update context from user input
4. property_search - Search PostgreSQL for matching properties
5. rag_retrieval - Search ChromaDB for FAQ/brochure info
6. recommendation - Select and explain top result
7. objection_handling - Handle customer concerns
8. booking - Create calendar event and send email
9. rescheduling - Update existing appointment
10. cancellation - Cancel appointment
11. escalation - Transfer to human representative
12. goodbye - End conversation gracefully
"""

import logging
from datetime import datetime
from sara_agent.langgraph_schema import ConversationState
from sara_agent.understanding import IntentClassifier
from sara_agent.memory import ConversationMemory
from sara_agent.query_planner import QueryPlanner
from sara_agent.objections import ObjectionHandler
from sara_agent.natural_speech import NaturalSpeechGenerator


logger = logging.getLogger(__name__)


# ============================================================
# CORE NODES
# ============================================================

async def node_greeting(state: ConversationState) -> ConversationState:
    """Greet user and explain capabilities.
    
    Entry point for new conversations. Sets a warm, professional tone.
    """
    if state.turn_count == 0:
        state.agent_response = (
            "Assalam-o-Alaikum! RealEstate Hub se Sara baat kar rahi hoon. "
            "Main aap ki kis tarah help kar sakti hoon?"
        )
        state.response_type = "greeting"
    
    state.add_message("assistant", state.agent_response)
    state.turn_count += 1
    return state


async def node_intent_detection(state: ConversationState) -> ConversationState:
    """Classify user intent and extract key information.
    
    Determines what the user is asking for:
    - greeting: User greeting/opening
    - property_search: Looking for properties
    - faq: Question about process/company
    - booking: Wants to schedule visit
    - rescheduling: Wants to change appointment
    - cancellation: Wants to cancel appointment
    - objection: Raising a concern
    - goodbye: Ending conversation
    """
    classifier = IntentClassifier()
    intent_result = classifier.classify(state.latest_user_input)
    
    state.latest_intent = intent_result.get("intent", "unknown")
    state.intent_confidence = intent_result.get("confidence", 0.0)
    
    logger.debug(f"Intent: {state.latest_intent} (confidence: {state.intent_confidence})")
    
    return state


async def node_memory_update(state: ConversationState) -> ConversationState:
    """Update user profile with information from latest input.
    
    Extracts constraints like budget, city, area, bedrooms, etc.
    Updates persistent memory that carries across turns.
    """
    memory = ConversationMemory()
    
    # Extract and update constraints
    state.parsed_constraints = memory.extract_constraints_from_text(
        state.latest_user_input,
        state.user_profile
    )
    
    # Apply extracted constraints to user profile
    if "budget" in state.parsed_constraints:
        state.user_profile.budget = state.parsed_constraints["budget"]
    if "city" in state.parsed_constraints:
        state.user_profile.city = state.parsed_constraints["city"]
    if "area" in state.parsed_constraints:
        state.user_profile.area = state.parsed_constraints["area"]
    if "bedrooms" in state.parsed_constraints:
        state.user_profile.bedrooms = state.parsed_constraints["bedrooms"]
    
    state.user_profile.updated_at = datetime.now()
    
    logger.debug(f"Updated user profile: {state.user_profile}")
    
    return state


async def node_property_search(state: ConversationState) -> ConversationState:
    """Search PostgreSQL for matching properties.
    
    Uses user profile constraints to find available properties.
    Results are ranked by fit to user preferences.
    """
    if not state.user_profile.city or not state.user_profile.budget:
        # Missing critical info for search
        state.agent_response = "Budget aur city ke baare mein bataiye, toh main properties dekh saktai hoon."
        state.response_type = "clarification"
        state.add_message("assistant", state.agent_response)
        return state
    
    # Use QueryPlanner to build and execute query
    planner = QueryPlanner()
    
    # TODO: Wire to actual PostgreSQL search
    # For now, return placeholder
    state.search_results = [
        {
            "id": 1,
            "name": "DHA Phase 6 Apartment",
            "city": state.user_profile.city,
            "area": state.user_profile.area or "DHA",
            "price": 5000000,
            "bedrooms": 3,
            "bathrooms": 2,
        }
    ]
    
    logger.debug(f"Found {len(state.search_results)} properties")
    
    return state


async def node_recommendation(state: ConversationState) -> ConversationState:
    """Select and present top property to customer.
    
    Chooses best matching property from search results.
    Generates natural language recommendation.
    """
    if not state.search_results:
        state.agent_response = "Aapke criteria ke mutabiq koi property nahi mila. Budget ya city badal kar dekh sakte hain?"
        state.response_type = "clarification"
        state.add_message("assistant", state.agent_response)
        return state
    
    # Take top result
    top_property = state.search_results[0]
    state.selected_property_id = top_property["id"]
    state.selected_property_details = top_property
    
    # Generate natural response
    name = top_property.get("name", "Property")
    price_cr = top_property.get("price", 0) / 10000000
    beds = top_property.get("bedrooms", "?")
    
    state.agent_response = (
        f"Aapke budget mein ye property match hai: {name}. "
        f"Price {price_cr:.1f} crore hai, aur is mein {beds} bedrooms hain. "
        f"Kya aap visit karna pasand karenge?"
    )
    state.response_type = "recommendation"
    state.add_message("assistant", state.agent_response)
    
    return state


async def node_objection_handling(state: ConversationState) -> ConversationState:
    """Handle customer concerns and objections.
    
    Addresses common concerns:
    - Price too high → Show alternatives
    - Location concerns → Explain proximity to key areas
    - Construction concerns → Verify status
    - Investment concerns → Show appreciation history
    """
    handler = ObjectionHandler()
    response = handler.handle_objection(
        state.latest_user_input,
        state.selected_property_details
    )
    
    state.objection_type = response.get("objection_type", "general")
    state.objection_response = response.get("response", "")
    state.agent_response = response.get("response", "")
    state.response_type = "objection_response"
    
    state.add_message("assistant", state.agent_response)
    
    return state


async def node_booking(state: ConversationState) -> ConversationState:
    """Create appointment and send confirmation.
    
    Books property visit with customer.
    Creates Google Calendar event.
    Sends email to assigned real estate agent.
    """
    if not state.selected_property_id:
        state.agent_response = "Pehle property select kariye."
        state.response_type = "clarification"
        return state
    
    # TODO: Wire to Google Calendar API
    # TODO: Wire to Email service
    # TODO: Wire to CRM logging
    
    state.booking_requested = True
    state.appointment_time = datetime.now()  # Placeholder
    state.agent_response = "Aapka appointment book ho gaya! Aapko confirmation message milegaa."
    state.response_type = "success"
    
    state.add_message("assistant", state.agent_response)
    
    return state


async def node_rescheduling(state: ConversationState) -> ConversationState:
    """Handle appointment rescheduling.
    
    Cancels old appointment and creates new one.
    Notifies customer and agent.
    """
    state.agent_response = "Naya time set kar sakte hain. Kaun sa din acha rahega?"
    state.response_type = "clarification"
    
    state.add_message("assistant", state.agent_response)
    
    return state


async def node_cancellation(state: ConversationState) -> ConversationState:
    """Handle appointment cancellation.
    
    Cancels appointment in calendar.
    Sends cancellation email to agent.
    Offers alternative times.
    """
    state.agent_response = "Aapka appointment cancel ho gaya. Kya dusri taareekh fix karni hai?"
    state.response_type = "success"
    
    state.add_message("assistant", state.agent_response)
    
    return state


async def node_escalation(state: ConversationState) -> ConversationState:
    """Escalate to human representative.
    
    Used for:
    - Complex queries requiring human judgment
    - Angry or frustrated customers
    - Requests outside Sara's scope
    """
    state.agent_response = "Ek human representative se connect karte hain. Ek moment..."
    state.response_type = "escalation"
    
    state.add_message("assistant", state.agent_response)
    
    # TODO: Wire to Zendesk/Twilio queue
    
    return state


async def node_goodbye(state: ConversationState) -> ConversationState:
    """End conversation gracefully."""
    state.agent_response = "Allah Hafiz! RealEstate Hub ko contact karne ke liye dhanyavaad!"
    state.response_type = "goodbye"
    
    state.add_message("assistant", state.agent_response)
    
    return state


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def route_by_intent(state: ConversationState) -> str:
    """Route to next node based on classified intent."""
    intent = state.latest_intent
    
    if intent == "greeting":
        return "greeting"
    elif intent == "property_search":
        return "property_search"
    elif intent == "booking":
        return "booking"
    elif intent == "rescheduling":
        return "rescheduling"
    elif intent == "cancellation":
        return "cancellation"
    elif intent == "objection":
        return "objection_handling"
    elif intent == "faq":
        return "rag_retrieval"
    elif intent == "goodbye":
        return "goodbye"
    else:
        # Default: assume property search
        return "property_search"


def should_continue_conversation(state: ConversationState) -> str:
    """Determine if conversation should continue or end."""
    if state.latest_intent == "goodbye":
        return "end"
    elif not state.agent_response:
        return "clarify"
    else:
        return "continue"
