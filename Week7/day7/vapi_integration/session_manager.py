"""Session Manager — keeps per-call conversation state and routes
user messages through Sara's Day 3 LangGraph conversation engine.

Each VAPI call gets its own isolated ConversationState so memory
doesn't bleed between callers (the same bug the audit flagged in Day 3).

The session lifecycle:
    create_session(call_id)  ← on call-start
    process_turn(call_id, user_message) ← on each transcript event
    get_session(call_id)     ← for tool handlers
    close_session(call_id)   ← on end-of-call-report
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from vapi_integration.guardrails import OffTopicGuardrail
from vapi_integration.learning import LearningRecordStore
from vapi_integration.metrics import metrics

logger = logging.getLogger("vapi.sessions")

# ── import Sara's Day 3 conversation engine ───────────────────────────────────
_DAY3_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "day3", "src")
if _DAY3_SRC not in sys.path:
    sys.path.insert(0, os.path.abspath(_DAY3_SRC))

try:
    from sara_agent.langgraph_schema import ConversationState, UserProfile
    from sara_agent.understanding import UserUnderstandingService
    from sara_agent.natural_speech import NaturalSpeechPolicy
    from sara_agent.memory import ConversationMemory
    _SARA_AVAILABLE = True
    logger.info("Sara Day 3 core engine loaded successfully")
except ImportError as e:
    logger.warning("Sara Day 3 engine not available (%s) — using fallback mode", e)
    _SARA_AVAILABLE = False


@dataclass
class VapiSession:
    """Per-call session state."""
    call_id: str
    caller_phone: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_count: int = 0
    appointment_id: Optional[str] = None
    # Sara's native conversation state
    sara_state: Optional[object] = None
    # Fallback simple message history (used when Day 3 not available)
    messages: list[dict] = field(default_factory=list)


class VapiSessionManager:
    """Manages per-call sessions and routes messages through Sara's agent."""

    def __init__(self) -> None:
        self._sessions: dict[str, VapiSession] = {}
        self._lock = asyncio.Lock()

        # Sara's services are created lazily on first call to avoid
        # requiring API keys at server startup
        self._intent_classifier = None
        self._speech_gen = None
        self._off_topic_guardrail = OffTopicGuardrail()
        self._learning_store = LearningRecordStore()

    def active_count(self) -> int:
        return len(self._sessions)

    async def create_session(self, call_id: str, caller_phone: str = "unknown") -> VapiSession:
        async with self._lock:
            if _SARA_AVAILABLE:
                sara_state = ConversationState(
                    session_id=call_id,
                    user_profile=UserProfile(customer_phone=caller_phone),
                )
            else:
                sara_state = None

            session = VapiSession(
                call_id=call_id,
                caller_phone=caller_phone,
                sara_state=sara_state,
            )
            self._sessions[call_id] = session
            logger.info("Session created: %s (caller: %s)", call_id, caller_phone)
            return session

    async def get_session(self, call_id: str) -> Optional[VapiSession]:
        return self._sessions.get(call_id)

    async def process_turn(self, call_id: str, user_message: str) -> str:
        """
        Process one user turn through Sara's LangGraph nodes.

        Returns the text Sara should speak back to the caller.
        VAPI will pass this to the configured TTS provider (Fish Audio).
        """
        session = self._sessions.get(call_id)
        if session is None:
            # Caller connected before call-start was processed — create lazily
            session = await self.create_session(call_id)

        decision = self._off_topic_guardrail.evaluate(
            user_message,
            has_conversation_context=session.turn_count > 0,
        )
        if not decision.allowed:
            session.turn_count += 1
            logger.info(
                "Guardrail blocked turn %d for call %s: reason=%s",
                session.turn_count,
                call_id,
                decision.reason,
            )
            metrics.increment(f"guardrail_blocked_{decision.reason}")
            return decision.response or "Main sirf real estate se related madad kar sakti hoon."

        session.turn_count += 1
        logger.info(
            "Processing turn %d for call %s: %r",
            session.turn_count, call_id, user_message[:60]
        )

        started = time.perf_counter()
        try:
            if _SARA_AVAILABLE and session.sara_state is not None:
                response = await self._process_with_sara(session, user_message)
            else:
                response = await self._process_fallback(session, user_message)
            metrics.increment("conversation_turn_success")
            return response
        except Exception:
            metrics.increment("conversation_turn_failure")
            raise
        finally:
            metrics.observe_ms("conversation_turn", (time.perf_counter() - started) * 1000)

    async def _process_with_sara(self, session: VapiSession, user_message: str) -> str:
        """Route through Sara's Day 3 understanding + fallback routing."""
        state: ConversationState = session.sara_state
        state.latest_user_input = user_message
        state.turn_start_time = datetime.now()
        state.add_message("user", user_message)

        try:
            # VAPI sends firstMessage as greeting, so don't send another greeting here
            # Process the user's actual first message normally

            # Use Day3 understanding service for intent classification
            understanding_svc = UserUnderstandingService()
            understanding = await understanding_svc.understand(
                user_message,
                conversation_history=state.messages[-6:],  # last 3 turns
                user_profile=state.user_profile.__dict__,
            )

            intent = understanding.intent if understanding else "unknown"
            state.latest_intent = intent

            # Update user profile from extracted constraints
            if understanding and understanding.constraints:
                profile = state.user_profile
                c = understanding.constraints
                if c.get("budget"):
                    profile.budget = c["budget"]
                if c.get("city"):
                    profile.city = c["city"]
                if c.get("area"):
                    profile.area = c["area"]
                if c.get("bedrooms"):
                    profile.bedrooms = c["bedrooms"]
                if c.get("customer_name"):
                    profile.customer_name = c["customer_name"]
                if c.get("purpose"):
                    profile.purpose = c["purpose"]

            # Route to appropriate response
            response = await self._generate_response(state, intent, session)
            state.add_message("assistant", response)
            session.sara_state = state
            return response

        except Exception as exc:
            logger.exception("Error in Sara processing: %s", exc)
            return await self._process_fallback(session, user_message)

    async def _generate_response(
        self, state: ConversationState, intent: str, session: VapiSession
    ) -> str:
        """Generate response based on detected intent using Sara's natural speech."""
        profile = state.user_profile
        speech = NaturalSpeechPolicy()

        if intent in ("greeting",):
            return "Ji, batain — aap ko kya chahiye? Property leni hai, kiraye pe leni hai, ya invest karna chahte hain?"

        elif intent in ("property_search", "recommendation"):
            missing = []
            if not profile.city:
                missing.append("city ya area")
            if not profile.budget:
                missing.append("budget")
            if missing:
                return f"Zaroor! Pehle mujhe bataiye — aap ka {' aur '.join(missing)} kya hai?"
            return (
                f"Theek hai! {profile.city} mein "
                f"{'up to PKR {:,}'.format(profile.budget) if profile.budget else ''} budget mein "
                f"property dhundh rahi hoon. "
                f"Ek second ruko, main aap ke liye best options nikaal rahi hoon."
            )

        elif intent in ("schedule_visit", "appointment"):
            if not profile.customer_name:
                return "Visit book karne ke liye — aap ka naam aur phone number bata dein please?"
            return (
                f"Bilkul {profile.customer_name} ji! "
                f"Kab available hain visit ke liye? Date aur time batain."
            )

        elif intent in ("reschedule_visit",):
            return "Appointment reschedule karne ke liye appointment ID batain please, ya main check karti hoon."

        elif intent in ("cancel_visit",):
            return "Appointment cancel karne ke liye — appointment ID confirm karein please?"

        elif intent in ("faq",):
            return "Ji, yeh sawal mujhe note kar liya. Main aap ko iska jawab de rahi hoon..."

        elif intent in ("objection",):
            return (
                "Main samajh sakti hoon aap ki concern. "
                "Kya aap thoda aur detail mein batayen taake main better help kar sakoon?"
            )

        elif intent in ("greeting", "unknown"):
            return (
                "Ji, main samajh rahi hoon. Kya aap property dhundh rahe hain, "
                "kiraye pe leni hai, ya invest karna chahte hain?"
            )

        else:
            return (
                "Ji bilkul. Kya aap thoda aur detail mein bata sakte hain "
                "taake main aap ki properly help kar sakoon?"
            )

    async def _process_fallback(self, session: VapiSession, user_message: str) -> str:
        """Simple fallback when Day 3 LangGraph is not available."""
        session.messages.append({"role": "user", "content": user_message})

        # Very basic intent keywords (UrduLish)
        msg_lower = user_message.lower()

        # VAPI already sent firstMessage as greeting, so don't send another greeting on turn 1
        # Process the user's actual first message normally

        if any(w in msg_lower for w in ["property", "ghar", "flat", "plot", "buy", "lena"]):
            response = (
                "Bilkul! Aap kis city mein property dhundh rahe hain, "
                "aur aap ka approximate budget kya hai?"
            )
        elif any(w in msg_lower for w in ["rent", "kiraya", "lease"]):
            response = (
                "Kiraye pe lene ke liye — aap kis area mein chahiye, "
                "aur kitne bedrooms chahiye?"
            )
        elif any(w in msg_lower for w in ["appointment", "visit", "milna", "dekhna"]):
            response = (
                "Zaroor! Aap kab available hain property visit ke liye? "
                "Date aur time batain."
            )
        elif any(w in msg_lower for w in ["shukriya", "thanks", "bye", "allah hafiz"]):
            response = (
                "Bahut shukriya aap ki call ka! Agar koi sawal ho toh "
                "dobara call karein. Allah Hafiz!"
            )
        else:
            response = (
                "Ji, main samajh rahi hoon. Kya aap thoda aur detail mein bata sakte hain "
                "taake main aap ki properly help kar sakoon?"
            )

        session.messages.append({"role": "assistant", "content": response})
        return response

    async def close_session(
        self,
        call_id: str,
        summary: str = "",
        transcript: str = "",
        recording_url: str = "",
    ) -> None:
        """Clean up session and log to CRM."""
        session = self._sessions.pop(call_id, None)
        if session is None:
            return

        logger.info(
            "Session closed: %s | turns=%d | duration=%s",
            call_id,
            session.turn_count,
            datetime.now(timezone.utc) - session.created_at,
        )

        try:
            messages = (
                list(getattr(session.sara_state, "messages", []))
                if session.sara_state is not None
                else session.messages
            )
            self._learning_store.record(
                call_id=session.call_id,
                caller_phone=session.caller_phone,
                created_at=session.created_at,
                turn_count=session.turn_count,
                messages=messages,
                summary=summary,
                transcript=transcript,
            )
        except Exception as e:
            logger.warning("Learning record failed for %s: %s", call_id, e)

        # ── Log to Day 4 CRM via n8n webhook (fire and forget) ───────────────
        try:
            await self._log_to_crm(session, summary, transcript, recording_url)
        except Exception as e:
            logger.warning("CRM logging failed for %s: %s", call_id, e)

    async def _log_to_crm(
        self,
        session: VapiSession,
        summary: str,
        transcript: str,
        recording_url: str,
    ) -> None:
        """Push call data to CRM via Day 4's n8n webhook."""
        import httpx

        n8n_url = os.getenv("N8N_WEBHOOK_URL")
        if not n8n_url:
            logger.debug("N8N_WEBHOOK_URL not set — skipping CRM log")
            return

        payload = {
            "event": "call_completed",
            "call_id": session.call_id,
            "caller_phone": session.caller_phone,
            "turns": session.turn_count,
            "appointment_id": session.appointment_id,
            "summary": summary,
            "recording_url": recording_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(n8n_url, json=payload)
            resp.raise_for_status()
            logger.info("CRM log sent for call %s", session.call_id)
