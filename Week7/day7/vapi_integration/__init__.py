"""VAPI Integration — Day 7 telephony layer for Sara AI Voice Agent.

This package wires VAPI's inbound call infrastructure to Sara's
existing LangGraph conversation engine (Day 3/5) and appointment
workflow service (Day 4).

Architecture:
    Phone Call → VAPI (STT + TTS + Telephony)
                    ↕  HTTP Webhook
            FastAPI webhook_server.py (this package)
                    ↕
        Day 3 sara_agent LangGraph nodes
                    ↕
        Day 4 appointment workflow API (port 8004)
"""
__version__ = "1.0.0"

