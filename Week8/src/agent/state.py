"""
state.py
--------
LangGraph state definitions for the Real Estate AI Assistant.
Maintains conversational context, extracted entity slots, verified tool outputs,
and guardrail state across the graph execution.
"""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Optional, TypedDict, Annotated


class AgentState(TypedDict, total=False):
    """LangGraph conversation state flowing through orchestrator nodes."""

    # History & user input
    messages: Annotated[List[Dict[str, Any]], operator.add]
    query: str
    language: str  # 'english', 'urdulish', 'urdu'
    conversation_id: Optional[str]

    # Intent & extracted slots
    intent: str  # 'valuation', 'lead_scoring', 'comparables', 'market_stats', 'hybrid', 'general'
    extracted_entities: Dict[str, Any]
    missing_fields: List[str]

    # Tool execution & verified facts
    tool_calls: List[str]
    tool_results: Dict[str, Any]
    verified_numbers: List[float]

    # Final generated answer & safety status
    final_response: str
    guard_triggered: bool
    status: str
