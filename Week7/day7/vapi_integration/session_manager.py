# WARNING [ARCHITECTURE / CODE DUPLICATION ALERT]:
# day7/vapi_integration/session_manager.py reimplements VAPI voice session orchestration and turn logic.
# The source of truth for Sara's agent capabilities is in day3/src/sara_agent.
# Keep day3 logic aligned when modifying session_manager.py!

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
from vapi_integration.customer_identity import normalize_phone
from vapi_integration.customer_service import CustomerContext, CustomerService
from vapi_integration.interaction_repository import InteractionRepository
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
    customer_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_count: int = 0
    appointment_id: Optional[str] = None
    appointment_property_id: Optional[str] = None
    shown_property_ids: list[str] = field(default_factory=list)
    latest_recommended_property_order: list[str] = field(default_factory=list)
    preference_snapshot: dict = field(default_factory=dict)
    search_flexible: set[str] = field(default_factory=set)
    preference_flow: dict = field(default_factory=dict)
    property_snapshots: dict[str, dict] = field(default_factory=dict)
    # Sara's native conversation state
    sara_state: Optional[object] = None
    # Fallback simple message history (used when Day 3 not available)
    messages: list[dict] = field(default_factory=list)


class VapiSessionManager:
    """Manages per-call sessions and routes messages through Sara's agent."""

    def __init__(
        self,
        customer_service: CustomerService | None = None,
        interaction_repository: InteractionRepository | None = None,
    ) -> None:
        self._sessions: dict[str, VapiSession] = {}
        self._lock = asyncio.Lock()

        # Sara's services are created lazily on first call to avoid
        # requiring API keys at server startup
        self._intent_classifier = None
        self._speech_gen = None
        self._off_topic_guardrail = OffTopicGuardrail()
        self._learning_store = LearningRecordStore()
        try:
            self._customer_service = customer_service or CustomerService()
        except Exception as exc:
            logger.info("Customer persistence unavailable: %s", exc)
            self._customer_service = None
        try:
            self._interaction_repository = interaction_repository or InteractionRepository()
        except Exception as exc:
            logger.info("Interaction persistence unavailable: %s", exc)
            self._interaction_repository = None

    def active_count(self) -> int:
        return len(self._sessions)

    async def create_session(
        self,
        call_id: str,
        caller_phone: str = "unknown",
        customer_id: str | None = None,
    ) -> VapiSession:
        async with self._lock:
            customer_context = CustomerContext()
            normalized_phone = normalize_phone(caller_phone)
            if self._customer_service is not None:
                try:
                    if customer_id:
                        customer_context = await asyncio.to_thread(
                            self._customer_service.resolve_for_customer_id,
                            customer_id,
                        )
                    else:
                        customer_context = await asyncio.to_thread(
                            self._customer_service.resolve_for_phone,
                            normalized_phone,
                        )
                except Exception as exc:
                    logger.warning("Customer identity lookup failed: %s", exc)

            customer = customer_context.customer
            preferences = customer_context.preferences
            resolved_phone = (
                customer.phone_normalized if customer and customer.phone_normalized else caller_phone
            )
            if normalized_phone:
                resolved_phone = normalized_phone
            if not resolved_phone or resolved_phone == "unknown":
                resolved_phone = "unknown"

            if _SARA_AVAILABLE:
                user_profile = UserProfile(customer_phone=resolved_phone)
                if customer:
                    user_profile.customer_name = customer.full_name
                if preferences:
                    user_profile.city = preferences.city
                    user_profile.area = preferences.area
                    user_profile.budget = preferences.budget_max
                    user_profile.bedrooms = preferences.bedrooms
                    user_profile.property_type = preferences.property_type
                    if preferences.purpose:
                        user_profile.purpose = preferences.purpose
                    user_profile.amenities_preferred = list(preferences.amenities)
                sara_state = ConversationState(
                    session_id=call_id,
                    user_profile=user_profile,
                )
            else:
                sara_state = None

            session = VapiSession(
                call_id=call_id,
                caller_phone=resolved_phone,
                customer_id=customer.customer_id if customer else customer_id,
                sara_state=sara_state,
            )
            self._sessions[call_id] = session
            logger.info(
                "Session created: %s (customer_id=%s, caller=%s, preferences_loaded=%s)",
                call_id,
                session.customer_id,
                resolved_phone,
                preferences is not None,
            )
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

        from sara_agent.understanding import UserUnderstandingService
        parsed = UserUnderstandingService(deterministic_first=True)._deterministic_understanding(user_message, {})
        if parsed:
            session.search_flexible.update(parsed.relax)
            session.search_flexible.difference_update(parsed.required)

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
            context = {
                "recent_turns": state.messages[-6:],  # last 3 turns
                "user_profile": state.user_profile.__dict__ if hasattr(state.user_profile, "__dict__") else state.user_profile,
                "preference_state": session.preference_flow.get("preference_state"),
                "preference_fields": session.preference_flow.get("preference_fields", []),
            }
            understanding = await asyncio.to_thread(
                understanding_svc.understand,
                user_message,
                context=context,
            )

            intent = understanding.intent if understanding else "unknown"
            state.latest_intent = intent
            logger.info("Executed Sara Day 3 agent stack successfully for call %s (intent=%s)", session.call_id, intent)

            # Update memory and persistence only from structured extraction.
            if understanding:
                from sara_agent.preference_edit import advance_edit, finish_edit, saved_requirement_summary
                flow = session.preference_flow
                if session.turn_count == 1 and understanding.intent == "greeting" and session.customer_id:
                    profile = state.user_profile
                    values = {key: getattr(profile, key, None) for key in ("city", "budget", "property_type", "purpose")}
                    if values.get("city") or values.get("budget"):
                        flow["pending_returning_confirm"] = True
                        response = saved_requirement_summary(values)
                        state.add_message("assistant", response)
                        return response
                question = advance_edit(session.preference_flow, understanding, user_message)
                if question:
                    state.add_message("assistant", question)
                    return question
                if session.preference_flow.get("preference_state") == "editing_preferences" and understanding.intent == "property_search" and not understanding.interaction_action:
                    try:
                        values = await self._persist_preference_edit(session, understanding)
                    except Exception:
                        logger.exception("Preference edit could not be saved")
                        response = "Preference save nahi ho saki. Nayi value dobara bata dein, main phir koshish karti hoon."
                        state.add_message("assistant", response)
                        return response
                    response = finish_edit(session.preference_flow, values)
                    if session.preference_flow["preference_state"] == "ready_for_search":
                        response += await self._generate_response(state, "property_search", session)
                    state.add_message("assistant", response)
                    return response
                if flow.get("pending_returning_confirm"):
                    import re
                    if understanding.intent in {"schedule_visit", "reschedule_visit", "cancel_visit"} or understanding.interaction_action:
                        flow["pending_returning_confirm"] = False
                    elif understanding.preference_action == "continue" or re.search(r"\b(?:haan|yes|wahi|continue|theek hai)\b", user_message, re.I):
                        flow["pending_returning_confirm"] = False
                        flow["preference_state"] = "continuing_saved_preferences"
                        understanding.intent = intent = "property_search"
                    elif not understanding.required:
                        response = "Saved requirement continue karni hai ya koi preference change karni hai?"
                        state.add_message("assistant", response)
                        return response
                    else:
                        flow["pending_returning_confirm"] = False
                if flow.get("preference_state") == "continuing_saved_preferences":
                    understanding.intent = intent = "property_search"
                    flow["preference_state"] = "ready_for_search"
                await self._apply_understanding(session, understanding)
                feedback_response = await self._apply_feedback(session, understanding)
                if feedback_response:
                    state.add_message("assistant", feedback_response)
                    return feedback_response

            # Route to appropriate response
            response = await self._generate_response(state, intent, session)
            state.add_message("assistant", response)
            session.sara_state = state
            return response

        except Exception as exc:
            logger.exception("Error in Sara processing: %s", exc)
            return await self._process_fallback(session, user_message)

    async def _persist_preference_edit(self, session, understanding):
        """Use the same merge/conflict rules as chat; acknowledge only after storage."""
        from sara_agent.memory import ConversationState as SearchState
        from sara_agent.query_planner import QueryPlanner
        from web_api.schemas import PreferencesUpdate
        profile = session.sara_state.user_profile
        fields = ("city", "area", "budget", "bedrooms", "property_type", "purpose")
        before = {f: getattr(profile, f) for f in fields if getattr(profile, f, None) is not None}
        if profile.amenities_preferred:
            before["amenities"] = list(profile.amenities_preferred)
        merged = SearchState(required=dict(before), flexible=set(session.search_flexible))
        QueryPlanner().build_plan(understanding, merged)
        values = {**merged.preferred, **merged.required}
        updates = {("budget_max" if k == "budget" else k): values.get(k)
                   for k in set(before) | set(values) if before.get(k) != values.get(k)}
        if isinstance(updates.get("purpose"), str):
            updates["purpose"] = updates["purpose"].lower()
        validated = PreferencesUpdate(**updates).model_dump(exclude_unset=True)
        if validated and session.customer_id and self._customer_service:
            await asyncio.to_thread(self._customer_service.update_preferences, session.customer_id, validated)
        for key in set(before) | set(values):
            setattr(profile, "amenities_preferred" if key == "amenities" else key,
                    values.get(key, [] if key == "amenities" else None))
        session.search_flexible = merged.flexible
        if updates:
            session.latest_recommended_property_order.clear()
            session.property_snapshots.clear()
        return values

    async def _apply_understanding(self, session: VapiSession, understanding: object) -> None:
        """Apply validated current-turn fields and persist them partially."""
        profile = session.sara_state.user_profile
        structured: dict[str, object] = {}
        for source_name in ("required", "preferred"):
            values = getattr(understanding, source_name, {}) or {}
            if isinstance(values, dict):
                structured.update(values)

        profile_updates = {
            "city": structured.get("city"),
            "area": structured.get("area"),
            "bedrooms": structured.get("bedrooms"),
            "property_type": structured.get("property_type"),
            "purpose": structured.get("purpose"),
        }
        if "budget" in structured:
            profile_updates["budget"] = structured["budget"]
        if "amenities" in structured:
            amenities = self._clean_amenities(structured["amenities"])
            if amenities:
                profile_updates["amenities_preferred"] = amenities

        for field_name, value in profile_updates.items():
            if value is None or value == "":
                continue
            if field_name == "amenities_preferred":
                profile.amenities_preferred = list(dict.fromkeys(value))
            else:
                setattr(profile, field_name, value)

        # customer_name is intentionally read only if supplied by a future
        # structured understanding schema; raw message text is never parsed.
        customer_name = getattr(understanding, "customer_name", None)
        if customer_name:
            profile.customer_name = customer_name

        if not session.customer_id or self._customer_service is None:
            return

        persisted = {}
        field_map = {
            "city": "city",
            "area": "area",
            "bedrooms": "bedrooms",
            "property_type": "property_type",
            "purpose": "purpose",
            "amenities_preferred": "amenities",
        }
        for profile_field, database_field in field_map.items():
            value = profile_updates.get(profile_field)
            if value is not None and value != "":
                persisted[database_field] = value
        if "budget" in structured and structured["budget"] is not None:
            persisted["budget_max"] = structured["budget"]

        if persisted:
            try:
                await asyncio.to_thread(
                    self._customer_service.update_preferences,
                    session.customer_id,
                    persisted,
                )
            except Exception as exc:
                logger.warning(
                    "Customer preference persistence failed for customer_id=%s: %s",
                    session.customer_id,
                    exc,
                )

        if customer_name:
            try:
                await asyncio.to_thread(
                    self._customer_service.update_name,
                    session.customer_id,
                    customer_name,
                )
            except Exception as exc:
                logger.warning(
                    "Customer name persistence failed for customer_id=%s: %s",
                    session.customer_id,
                    exc,
                )

    @staticmethod
    def _clean_amenities(value: object) -> list[str]:
        if not isinstance(value, (list, tuple, set)):
            return []
        return list(dict.fromkeys(
            str(item).strip()
            for item in value
            if str(item).strip()
        ))

    async def _apply_feedback(self, session: VapiSession, understanding: object) -> str | None:
        """Resolve and record structured feedback against this call's results."""
        action = getattr(understanding, "interaction_action", None)
        if not action:
            return None

        property_id = getattr(understanding, "interaction_property_id", None)
        if property_id:
            if property_id not in session.shown_property_ids:
                return "Yeh property current options mein nahi hai. Please dobara select karein."
        else:
            property_id = self._property_for_reference(session, understanding)

        if not property_id:
            return "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?"

        await self._record_interaction(
            session,
            property_id=property_id,
            action=action,
            preference_snapshot=session.preference_snapshot,
            property_snapshot=session.property_snapshots.get(property_id),
        )
        messages = {
            "liked": "Ji, yeh option aap ko pasand aaya — note kar liya.",
            "rejected": "Theek hai, yeh option aap ki preference mein nahi hai — note kar liya.",
            "shortlisted": "Ji, yeh property shortlist kar li hai.",
        }
        return messages[action]

    @staticmethod
    def _property_for_reference(session: VapiSession, understanding: object) -> str | None:
        from shared.sara_service import resolve_property_reference
        return resolve_property_reference(
            understanding, session.latest_recommended_property_order,
            session.shown_property_ids[0] if len(session.shown_property_ids) == 1 else None,
        )

    async def _record_interaction(
        self,
        session: VapiSession,
        *,
        property_id: str,
        action: str,
        reason: str | None = None,
        metadata: dict | None = None,
        preference_snapshot: dict | None = None,
        property_snapshot: dict | None = None,
    ) -> None:
        if not session.customer_id or self._interaction_repository is None:
            return
        try:
            await asyncio.to_thread(
                self._interaction_repository.record_interaction,
                customer_id=session.customer_id,
                conversation_id=session.call_id,
                property_id=property_id,
                action=action,
                reason=reason,
                metadata=metadata,
                preference_snapshot=preference_snapshot,
                property_snapshot=property_snapshot,
            )
        except Exception as exc:
            logger.warning(
                "Interaction persistence failed for customer_id=%s action=%s: %s",
                session.customer_id,
                action,
                exc,
            )

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
