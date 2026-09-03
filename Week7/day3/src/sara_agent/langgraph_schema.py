"""LangGraph state schema for Sara conversation orchestration.

This module defines the state structure that flows through the LangGraph
conversation state machine, enabling tool orchestration, memory management,
and multi-turn conversation handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


@dataclass
class UserProfile:
    """Track customer preferences across conversation.
    
    Fields persist across turns and enable context-aware recommendations.
    """
    
    # Property search constraints
    budget: Optional[int] = None
    city: Optional[str] = None
    area: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    
    # Customer context
    purpose: str = "buy"  # buy, rent, invest
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Preferences
    amenities_required: list[str] = field(default_factory=list)
    amenities_preferred: list[str] = field(default_factory=list)
    excluded_areas: list[str] = field(default_factory=list)
    flexible_fields: list[str] = field(default_factory=list)
    
    # Tracking
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationState:
    """LangGraph state for Sara conversation.
    
    This state flows through all nodes in the conversation graph and
    accumulates results from tool calls, intent detection, and retrieval.
    """
    
    # Conversation history
    messages: list[dict] = field(default_factory=list)
    
    # User profile (persistent across turns)
    user_profile: UserProfile = field(default_factory=UserProfile)
    
    # Current turn input
    latest_user_input: str = ""
    input_timestamp: datetime = field(default_factory=datetime.now)
    
    # Intent and understanding
    latest_intent: Optional[str] = None  # "greeting", "search", "booking", "faq", "objection", "goodbye"
    intent_confidence: float = 0.0
    parsed_constraints: dict = field(default_factory=dict)  # Extracted budget, city, etc.
    
    # Tool results
    search_results: list[dict] = field(default_factory=list)
    rag_results: Optional[str] = None
    rag_confidence: float = 0.0
    selected_property_id: Optional[int] = None
    selected_property_details: dict = field(default_factory=dict)
    
    # Availability and booking state
    availability_info: Optional[dict] = None
    available_slots: list[datetime] = field(default_factory=list)
    
    # Appointment state
    booking_requested: bool = False
    appointment_time: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    appointment_id: Optional[str] = None
    
    # Objection handling
    objection_type: Optional[str] = None
    objection_response: Optional[str] = None
    
    # Agent response (output)
    agent_response: str = ""
    response_type: str = "chat"  # chat, filler, thinking, success, clarification
    
    # Context tracking
    turn_count: int = 0
    session_id: str = ""
    
    # Latency tracking
    turn_start_time: datetime = field(default_factory=datetime.now)
    stt_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    tts_time_ms: float = 0.0
    
    def add_message(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add message to conversation history."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "turn": self.turn_count,
        }
        if metadata:
            msg.update(metadata)
        self.messages.append(msg)
    
    def get_conversation_summary(self) -> str:
        """Get formatted conversation history for LLM context."""
        summary_lines = []
        for msg in self.messages[-10:]:  # Last 10 messages for context
            role = msg["role"].upper()
            content = msg["content"]
            summary_lines.append(f"{role}: {content}")
        return "\n".join(summary_lines)
    
    def to_dict(self) -> dict:
        """Serialize for storage/logging."""
        return {
            "turn_count": self.turn_count,
            "session_id": self.session_id,
            "latest_intent": self.latest_intent,
            "user_profile": {
                "budget": self.user_profile.budget,
                "city": self.user_profile.city,
                "area": self.user_profile.area,
                "bedrooms": self.user_profile.bedrooms,
                "purpose": self.user_profile.purpose,
            },
            "search_results_count": len(self.search_results),
            "selected_property_id": self.selected_property_id,
            "appointment_requested": self.booking_requested,
            "appointment_time": self.appointment_time.isoformat() if self.appointment_time else None,
            "agent_response": self.agent_response[:200],  # First 200 chars
            "turn_start_time": self.turn_start_time.isoformat(),
        }


@dataclass
class ToolResult:
    """Result from a tool execution."""
    
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }
