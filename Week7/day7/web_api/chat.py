"""Authenticated transport adapter for shared Sara capabilities and website tools."""
import asyncio
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from shared.sara_service import SaraService, resolve_property_reference
from sara_agent.formatting import format_details
from web_api.schemas import PreferencesUpdate, MeInteractionCreate, MeAppointmentBook, AppointmentReschedule


class ChatAdapter:
    def __init__(self, services, store, sara=None):
        self.services = services
        self.store = store
        self.sara = sara or SaraService()

    async def turn(self, identity, payload, feedback, book, reschedule, cancel):
        async with self.store.turn(payload.conversation_id, identity) as (conversation_id, saved):
            customer = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            if not customer.customer:
                raise PermissionError()
            state = self.sara.hydrate(customer.preferences, saved)
            context = {
                "required": state.required, "preferred": {}, "excluded": state.excluded,
                "pending_action": saved.get("pending_action"),
                "recent_turns": saved.get("recent_turns", [])[-6:],
                "last_results": [{"property_id": value} for value in saved.get("property_order", [])],
                "selected_property": {"property_id": saved["selected"]} if saved.get("selected") else None,
                "current_date": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
                "timezone": "Asia/Karachi",
            }
            understanding = await asyncio.to_thread(self.sara.understand, payload.message, context)
            before = dict(state.required)
            # Day 3 owns merge, city/area invalidation, relaxation and ambiguity rules.
            self.sara.planner.build_plan(understanding, state)
            combined = {**state.preferred, **state.required}
            updates = {}
            for key in set(before) | set(combined):
                value = combined.get(key)
                if value != before.get(key):
                    field = "budget_max" if key == "budget" else key
                    if field in PreferencesUpdate.model_fields:
                        updates[field] = value.lower() if field == "purpose" and isinstance(value, str) else value
            if updates:
                validated = PreferencesUpdate(**updates).model_dump(exclude_unset=True)
                minimum = validated.get("budget_min", getattr(customer.preferences, "budget_min", None))
                maximum = validated.get("budget_max", getattr(customer.preferences, "budget_max", None))
                if minimum is not None and maximum is not None and minimum > maximum:
                    return self._response(conversation_id, "Minimum budget maximum se zyada hai. Minimum budget kya rakhna hai?", True)
                await asyncio.to_thread(self.services.customers.update_preferences, identity.customer_id, validated)
            saved["flexible"] = sorted(state.flexible)
            saved["excluded"] = state.excluded
            result = await self._route(identity, conversation_id, saved, state, understanding,
                                       feedback, book, reschedule, cancel)
            # No user or assistant text is persisted. Only bounded semantic continuity.
            saved["recent_turns"] = (saved.get("recent_turns", []) + [{
                "intent": understanding.intent,
                "interaction_action": understanding.interaction_action,
                "selected_index": understanding.selected_index,
            }])[-6:]
            return result

    def _response(self, conversation_id, message, clarification=False, **fields):
        return {"conversation_id": conversation_id,
                "message": self.sara.speech.decorate(message),
                "requires_clarification": clarification, **fields}

    async def _route(self, identity, cid, saved, state, u, feedback, book, reschedule, cancel):
        respond = lambda message, clarification=False, **fields: self._response(cid, message, clarification, **fields)
        order = saved.get("property_order", [])
        selected = resolve_property_reference(u, order, saved.get("selected"))
        has_reference = u.selected_index is not None or u.reference_type or u.interaction_property_id
        if selected:
            saved["selected"] = selected
        if u.interaction_action:
            if not selected or u.needs_clarification:
                return respond("Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?", True)
            await feedback(MeInteractionCreate(property_id=selected, action=u.interaction_action,
                                               recommendation_session_id=saved["recommendation_session_id"]))
            messages = {"liked": "Ji, yeh option aap ko pasand aaya, note kar liya.",
                        "rejected": "Theek hai, yeh option reject kar diya.",
                        "shortlisted": "Ji, yeh property shortlist kar li hai."}
            return respond(messages[u.interaction_action])

        if u.intent in {"schedule_visit", "reschedule_visit", "cancel_visit"}:
            pending = saved.get("pending_action") or {}
            if pending.get("intent") != u.intent:
                pending = {"intent": u.intent}
            saved["pending_action"] = pending
            if u.intent == "schedule_visit":
                selected = selected or (saved.get("selected") if not has_reference else None)
                if not selected or selected not in order:
                    return respond("Kis property ka visit book karna hai? Option number bata dein.", True)
                starts = u.starts_at or (pending.get("starts_at") if pending.get("property_id") == selected else None)
                saved["pending_action"] = {"intent": u.intent, "property_id": selected, "starts_at": starts}
                if not starts:
                    return respond("Visit ke liye kis date aur time par available hain?", True)
                if u.needs_clarification:
                    return respond("Visit ki date aur time dobara confirm kar dein.", True)
                # Re-check membership/expiry before any external side effect.
                await self._recommendation(identity, saved, selected)
                try:
                    request = MeAppointmentBook(property_id=selected, starts_at=starts)
                except ValueError:
                    return respond("Visit ki date aur time timezone ke saath confirm kar dein.", True)
                response = await book(request)
            else:
                appointment_id = u.appointment_id or pending.get("appointment_id")
                if not appointment_id:
                    return respond("Appointments page se apni appointment ID confirm kar dein.", True)
                try:
                    appointment_id = UUID(appointment_id)
                except ValueError:
                    return respond("Appointment ID dobara confirm kar dein.", True)
                pending["appointment_id"] = str(appointment_id)
                if u.needs_clarification:
                    return respond("Appointment request dobara confirm kar dein.", True)
                # Ownership checked by existing authenticated endpoint before Day 4.
                if u.intent == "cancel_visit":
                    response = await cancel(appointment_id)
                else:
                    if not u.starts_at:
                        return respond("Nayi date aur time bata dein.", True)
                    try:
                        request = AppointmentReschedule(starts_at=u.starts_at)
                    except ValueError:
                        return respond("Nayi date aur time timezone ke saath confirm kar dein.", True)
                    response = await reschedule(appointment_id, request)
            appointment = response.get("appointment")
            if not isinstance(appointment, dict) or not appointment.get("appointment_id"):
                return respond("Appointment service ne confirmation nahi di. Appointments page par status check kar lein.")
            saved["pending_action"] = None
            return respond("Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
                           appointment={key: appointment[key] for key in ("appointment_id", "status") if key in appointment})

        if u.intent in {"property_details", "property_selection", "availability"}:
            if not selected:
                return respond("Kis option ki details chahiye? Option number bata dein.", True)
            await self._recommendation(identity, saved, selected)
            row = await asyncio.to_thread(self.services.properties.get_property, selected)
            if not row or not row.get("available"):
                return respond("Yeh property ab available nahi hai. Naye options dekhna chahenge?")
            return respond(format_details(row))

        if u.intent in {"property_search", "recommendation"}:
            # Current web search contract cannot express exclusion/comparison filters.
            # Ask instead of silently discarding a constraint and presenting false matches.
            if state.excluded or u.comparison.field:
                return respond("Is comparison ke liye apni exact city, area ya maximum budget bata dein.", True)
            decision = await asyncio.to_thread(self.sara.policy.next_requirement,
                                               intent=u.intent, state=state, knowledge=self.services.properties)
            if decision:
                saved["pending_action"] = decision.pending_action
                return respond(decision.message, True)
            if u.needs_clarification:
                return respond("Apni requirement thori clear kar dein please.", True)
            rid, rows = await self.services.recommendations(identity.customer_id, self.sara.presentation.batch_size,
                                                           None, identity.user_id)
            saved.update(recommendation_session_id=str(rid), property_order=[r["property_id"] for r in rows],
                         selected=None, pending_action=None)
            if not rows:
                return respond("Is criteria par verified options nahi mile. Kis preference mein flexibility hai?")
            return respond(self.sara.presentation.format_batch(rows, has_more=False, first_batch=True),
                           recommendation_session_id=str(rid), properties=rows)
        if u.intent == "greeting":
            return respond("Ji, batayein, property ke bare mein kya madad chahiye?")
        if (u.required or u.preferred or u.relax) and not u.needs_clarification:
            return respond("Ji, aapki preferences update ho gayi hain.")
        return respond("Property search, options ki details ya visit booking mein kya madad chahiye?", True)

    async def _recommendation(self, identity, saved, property_id):
        context = await asyncio.to_thread(self.services.sessions.get, UUID(saved["recommendation_session_id"]))
        if not context or context.customer_id != identity.customer_id or property_id not in context.property_snapshots:
            raise PermissionError()
        return context
