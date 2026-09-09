"""Tool Handler — executes Sara's tools when VAPI sends 'tool-calls' events.

VAPI tool-call flow:
    1. LangGraph agent decides it needs to call a tool
    2. VAPI sends POST /vapi/webhook with type="tool-calls"
    3. This handler executes the tool by calling Day 4 API or PostgreSQL
    4. Returns result → VAPI includes it in the next LLM context
    5. Agent generates a natural-language confirmation for the caller

All tool calls are logged with latency for monitoring.

Architecture:
    - Appointment tools: Day 4 REST API
    - Property search: PostgreSQL (via PostgresPropertyRepository)
    - Never reads Day 2 CSV files at runtime
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
from decimal import Decimal
from typing import Any, Optional

from vapi_integration.metrics import metrics
from vapi_integration.retrieval_policy import RETRIEVAL_UNAVAILABLE
from vapi_integration.customer_learning import (
    CustomerPreferenceRepository,
    ExplainablePreferenceRanker,
    customer_key_for_phone,
)
from vapi_integration.interaction_repository import InteractionRepository
from ml.model_service import PropertyPreferenceModelService

import httpx

logger = logging.getLogger("vapi.tools")

# ── Import PostgresPropertyRepository from Day 2 ───────────────────────────────
_DAY2_STRUCTURED = os.path.join(
    os.path.dirname(__file__), "..", "..", "day2", "03_structured_retrieval"
)
if _DAY2_STRUCTURED not in sys.path:
    sys.path.insert(0, _DAY2_STRUCTURED)

try:
    from postgres_repository import PostgresPropertyRepository
except ImportError as e:
    logger.warning("PostgresPropertyRepository not available: %s", e)
    PostgresPropertyRepository = None  # type: ignore


class VapiToolHandler:
    """Executes Sara's tools by calling Day 4 appointment API and PostgreSQL."""

    def __init__(self, day4_api_url: str = "http://localhost:8004", interaction_repository=None) -> None:
        self.day4_url = day4_api_url.rstrip("/")
        self.day4_api_key = os.getenv("DAY4_API_KEY", "").strip()
        self.n8n_appointment_url = os.getenv("N8N_APPOINTMENT_WEBHOOK_URL", "").rstrip("/")
        # Calendar + SMTP may legitimately take longer than a simple DB call.
        # Keep this below Vapi's server timeout while allowing the core Day 4
        # workflow enough time to return its confirmed result.
        self.timeout = 300.0

        # Initialize PostgreSQL repository for property searches
        # This is the single source of truth for property facts
        self.repository = None
        try:
            if PostgresPropertyRepository:
                self.repository = PostgresPropertyRepository()
                logger.info("PostgresPropertyRepository initialized")
            else:
                logger.warning("PostgresPropertyRepository not available")
        except Exception as e:
            logger.error("Failed to initialize PostgresPropertyRepository: %s", e)
            # Continue without repository; search_properties will handle gracefully

        self.preference_repository = None
        try:
            self.preference_repository = CustomerPreferenceRepository()
        except Exception as e:
            logger.info("Customer preference profiles unavailable: %s", e)
        self.preference_ranker = ExplainablePreferenceRanker()
        self.ml_ranker = PropertyPreferenceModelService()
        try:
            self.interaction_repository = interaction_repository or InteractionRepository()
        except Exception as e:
            logger.info("Interaction persistence unavailable: %s", e)
            self.interaction_repository = None

    async def _appointment_request(
        self,
        action: str,
        *,
        payload: dict,
        appointment_id: str = "",
    ) -> httpx.Response:
        if not self.day4_api_key:
            raise RuntimeError("DAY4_API_KEY is not configured")
        headers = {"Authorization": f"Bearer {self.day4_api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Day 4 is the authoritative transactional workflow. It persists
            # the appointment, creates the calendar event, sends email, and
            # publishes to n8n. Calling n8n directly bypasses those guarantees
            # and makes booking fail whenever n8n is temporarily offline.
            if action == "book":
                return await client.post(f"{self.day4_url}/appointments", json=payload, headers=headers)
            if action == "reschedule":
                return await client.patch(
                    f"{self.day4_url}/appointments/{appointment_id}/reschedule",
                    json=payload, headers=headers,
                )
            return await client.delete(f"{self.day4_url}/appointments/{appointment_id}", headers=headers)

    async def execute(
        self,
        tool_name: str,
        arguments: dict,
        call_id: str,
        session: Any = None,
    ) -> str:
        """
        Execute a named tool and return a human-readable result string.
        VAPI passes this string back to the LLM as the tool result,
        so Sara can speak it naturally to the caller.
        """
        start = time.perf_counter()
        logger.info("Executing tool '%s' for call %s: %s", tool_name, call_id, arguments)

        try:
            if tool_name == "book_appointment":
                result = await self._book_appointment(arguments, session)
            elif tool_name == "reschedule_appointment":
                result = await self._reschedule_appointment(arguments)
            elif tool_name == "cancel_appointment":
                result = await self._cancel_appointment(arguments, session)
            elif tool_name == "search_properties":
                result = await self._search_properties(arguments, session=session)
            elif tool_name == "list_available_locations":
                result = await self._list_available_locations()
            else:
                result = f"Tool '{tool_name}' is not supported yet."

        except Exception as exc:
            logger.exception("Tool '%s' failed: %s", tool_name, exc)
            result = (
                "System mein thodi takleef aa gayi. "
                "please thori der baad dobara try karein."
            )
            metrics.increment(f"tool_failure_{tool_name}")

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        metrics.increment(f"tool_call_{tool_name}")
        metrics.observe_ms(f"tool_{tool_name}", elapsed_ms)
        logger.info("Tool '%s' completed in %.1f ms", tool_name, elapsed_ms)
        return result

    def _get_assigned_agent(self, property_id: str) -> tuple[str, str]:
        """
        Lookup assigned real estate agent name and email.
        Tries PostgresPropertyRepository.get_agents_for_property() (Day 2) first, with CSV fallback.
        Returns (agent_name, agent_email).
        """
        default_email = os.getenv("EMPLOYEE_EMAIL", os.getenv("SMTP_USERNAME", "sairafatima193@gmail.com"))
        default_name = "Sara AI Agent"

        if not property_id:
            return default_name, default_email

        # 1. Try PostgresPropertyRepository (Day 2) if initialized
        if self.repository is not None:
            try:
                agents = self.repository.get_agents_for_property(str(property_id))
                if agents and len(agents) > 0:
                    first_agent = agents[0]
                    agent_name = first_agent.get("name") or first_agent.get("agent_name") or default_name
                    logger.info("Postgres agent lookup success for %s: %s", property_id, agent_name)
                    return agent_name, default_email
            except Exception as e:
                logger.warning("Postgres agent lookup failed for %s: %s", property_id, e)

        # 2. Fallback to raw CSV lookup if Postgres repo unavailable
        import csv
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "day2", "01_knowledge_base")
        )
        ap_file = os.path.join(base_dir, "agent_properties.csv")
        agent_file = os.path.join(base_dir, "agents.csv")

        if not os.path.exists(ap_file) or not os.path.exists(agent_file):
            return default_name, default_email

        agent_id = None
        with open(ap_file, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if str(row.get("property_id", "")).strip().lower() == str(property_id).strip().lower():
                    agent_id = row.get("agent_id", "").strip()
                    break

        if not agent_id:
            return default_name, default_email

        with open(agent_file, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if str(row.get("agent_id", "")).strip().lower() == agent_id.lower():
                    return row.get("name", default_name), default_email

        return default_name, default_email

    # ── book_appointment ──────────────────────────────────────────────────────
    async def _book_appointment(self, args: dict, session: Any) -> str:
        pid = args.get("property_id", "")
        emp_name, emp_email = self._get_assigned_agent(pid)

        payload = {
            "client_name": args.get("client_name", ""),
            "client_phone": args.get("client_phone", ""),
            "client_email": args.get("client_email"),
            "employee_name": emp_name,
            "employee_email": emp_email,
            "property_id": pid,
            "property_name": args.get("property_name", "Property"),
            "starts_at": args.get("starts_at", ""),
            "duration_minutes": 60,
            "meeting_notes": args.get("meeting_notes", f"Assigned Agent: {emp_name}. Booked via phone call through Sara AI"),
        }

        resp = await self._appointment_request("book", payload=payload)

        if resp.status_code in (200, 201) and resp.content:
            data = resp.json()
            apt = data.get("appointment", {})
            if not apt:
                logger.error("Booking workflow returned no appointment: %s", resp.text)
                return (
                    "Appointment workflow ne booking confirm nahi ki. "
                    "Please koi aur time try karein ya representative se rabta karein."
                )
            apt_id = apt.get("appointment_id", "N/A")
            notification_sent = bool(data.get("notification_sent"))
            warnings = data.get("warnings") or []

            # Save appointment ID to session for future reschedule/cancel
            if session:
                session.appointment_id = apt_id
                session.appointment_property_id = pid
                await self._record_interaction(
                    session,
                    property_id=pid,
                    action="appointment_booked",
                    preference_snapshot=getattr(session, "preference_snapshot", None),
                    property_snapshot=getattr(session, "property_snapshots", {}).get(pid),
                )

            notification_text = (
                "Email notification bhi bhej di gayi hai."
                if notification_sent
                else "Booking confirm hai, lekin email notification send nahi ho saki."
            )
            if warnings:
                logger.warning("Booking completed with warnings: %s", warnings)

            return (
                f"Appointment successfully book ho gayi! "
                f"Appointment ID: {apt_id}. "
                f"{args.get('client_name', 'Aap')} ji, "
                f"{args.get('property_name', 'property')} ki visit "
                f"{args.get('starts_at', '')} par confirm hai. "
                f"{notification_text}"
            )
        elif resp.status_code == 409:
            return (
                "Yeh slot already book hai. "
                "Kya aap koi aur time prefer karenge?"
            )
        else:
            logger.error("Booking failed: %d %s", resp.status_code, resp.text)
            return (
                "Appointment book karne mein masla aa gaya. "
                "Kya aap thodi der baad dobara try karenge?"
            )

    # ── reschedule_appointment ────────────────────────────────────────────────
    async def _reschedule_appointment(self, args: dict) -> str:
        apt_id = args.get("appointment_id", "")
        new_time = args.get("starts_at", "")

        if not apt_id:
            return (
                "Appointment reschedule karne ke liye mujhe appointment ID chahiye. "
                "Kya aap apni previous appointment ID bata sakte hain?"
            )

        resp = await self._appointment_request(
            "reschedule", payload={"starts_at": new_time}, appointment_id=apt_id
        )

        if resp.status_code == 200:
            return (
                f"Appointment successfully reschedule ho gayi! "
                f"Naya time: {new_time}. "
                f"Updated calendar invite aur email notification bhej di gayi hai."
            )
        elif resp.status_code == 404:
            return "Yeh appointment ID nahi mili. Kya aap sahi ID confirm kar sakte hain?"
        elif resp.status_code == 409:
            return "Yeh naya slot already book hai. Koi aur time batain."
        else:
            return "Reschedule mein masla aa gaya. Dobara try karein please."

    # ── cancel_appointment ────────────────────────────────────────────────────
    async def _cancel_appointment(self, args: dict, session: Any = None) -> str:
        apt_id = args.get("appointment_id", "")

        if not apt_id:
            return (
                "Cancel karne ke liye appointment ID chahiye. "
                "Kya aap apni appointment ID bata sakte hain?"
            )

        resp = await self._appointment_request("cancel", payload={}, appointment_id=apt_id)

        if resp.status_code == 200:
            if session and getattr(session, "appointment_property_id", None):
                await self._record_interaction(
                    session,
                    property_id=session.appointment_property_id,
                    action="appointment_cancelled",
                    preference_snapshot=getattr(session, "preference_snapshot", None),
                    property_snapshot=getattr(session, "property_snapshots", {}).get(session.appointment_property_id),
                )
            return (
                "Appointment cancel ho gayi. "
                "Cancellation confirmation email bhi bhej di gayi hai. "
                "Agar dobara visit karni ho toh please call karein."
            )
        elif resp.status_code == 404:
            return "Yeh appointment ID nahi mili system mein."
        else:
            return "Cancel karne mein masla aa gaya. Dobara try karein."

    async def _search_properties(self, args: dict, session: Any = None) -> str:
        """
        Search properties using PostgreSQL (single source of truth).

        Orchestration only; the heavy lifting lives in the helpers:
            - _normalize_search_args: raw VAPI args -> repository filters
            - _apply_policy_tier1: flexible-requirement conversation policy
            - _rank_results: preference + ML ranking
            - _persist_session_state: snapshot shown results onto the session

        Returns:
            Human-readable property matches formatted for Sara to speak.
        """
        if not self.repository:
            logger.error("PostgreSQL repository not initialized")
            return RETRIEVAL_UNAVAILABLE

        normalized = self._normalize_search_args(args)
        validation = self._validate_search_args(normalized, session)
        if validation is not None:
            return validation

        try:
            max_price, city, area = await self._apply_policy_tier1(args, normalized, session)
            if getattr(self, "_tier1_decision", None):
                return self._tier1_decision
            results = await self._run_repository_search(max_price, city, area, normalized)

            if session is not None and callable(getattr(self.repository, "budget_area_options", None)):
                narrowing = self._policy.next_narrowing_requirement(
                    state=self._policy_state, matching_count=len(results)
                )
                if narrowing:
                    return narrowing.message

            results = await self._rank_results(results, session)

            if not results:
                logger.info("No properties found for filters: %s", args)
                return (
                    f"Bohot sorri! Aapke criteria ke andar koi property "
                    f"abhi available nahi hai (location: {normalized['location']}, "
                    f"bedrooms: {normalized['bedrooms']}, max budget: {max_price}). "
                    f"Kya aap apne requirements thora adjust kar sakte hain? "
                    f"Maslan budget badha sakta hoon ya kisi aur location mein dekhun?"
                )

            presented_results = results[:3]
            if session:
                await self._persist_session_state(session, presented_results)
            formatted_results = self._format_property_results(presented_results)

            return (
                f"Found {len(results)} verified properties matching aapki requirements. "
                f"Here are the best ones:\n\n{formatted_results}\n\n"
                f"Instruct the AI: Tell the customer about these options in natural UrduLish. "
                f"Mention key features and amenities naturally. "
                f"Then ask 'Kya aap in mein se kisi ko visit karna chahenge?'"
            )

        except Exception as e:
            logger.exception("Property search failed: %s", e)
            return RETRIEVAL_UNAVAILABLE

    def _normalize_search_args(self, args: dict) -> dict:
        """Extract and normalize filter arguments from the raw VAPI tool args."""
        location = str(args.get("location", "")).strip()
        purpose = str(args.get("purpose", "")).lower().strip()
        # Normalize purpose: map VAPI enum values to repository values.
        purpose_map = {
            "buy": "purchase",
            "purchase": "purchase",
            "rent": "rental",
            "rental": "rental",
            "invest": "investment",
            "investment": "investment",
            "commercial": "commercial",
            "": None,
        }
        return {
            "location": location,
            "max_price": args.get("max_price"),
            "bedrooms": args.get("bedrooms"),
            "property_type": str(args.get("property_type", "")).strip() or None,
            "repo_purpose": purpose_map.get(purpose, purpose or None),
        }

    def _validate_search_args(self, normalized: dict, session: Any) -> str | None:
        """Return a clarifying reply when required arguments are missing."""
        if session is not None and not normalized["repo_purpose"]:
            return "Aap purchase karna chahte hain ya rent par lena hai?"
        if not normalized["location"]:
            return (
                "Property search ke liye mujhe location batayen. "
                "Maslan: DHA Lahore, Bahria Town Karachi, etc."
            )
        return None

    async def _apply_policy_tier1(
        self, args: dict, normalized: dict, session: Any
    ) -> tuple[Any, str, str | None]:
        """Apply the tier-1 requirement conversation policy and return (max_price, city, area).

        Transcript observations carry explicit flexibility into the tools; a
        flexible budget/area relaxes that filter before the repository search.
        Sets self._policy_state / self._policy for the later narrowing step.
        """
        from vapi_integration.customer_identity import property_location
        city, area = property_location(normalized["location"])
        max_price = normalized["max_price"]

        self._policy_state = None
        self._policy = None
        if session is None or not callable(getattr(self.repository, "budget_area_options", None)):
            return max_price, city, area

        from sara_agent.memory import ConversationState as RequirementState
        from sara_agent.conversation_policy import ConversationPolicy
        state = RequirementState(required={key: value for key, value in {
            "city": city, "area": area, "purpose": normalized["repo_purpose"],
            "budget": max_price, "property_type": normalized["property_type"],
            "bedrooms": normalized["bedrooms"],
        }.items() if value is not None})
        flexibility = getattr(session, "search_flexible", [])
        if isinstance(flexibility, (list, set, tuple)):
            state.flexible.update(flexibility)
        for field in ("budget", "area"):
            if args.get(field + "_flexible") is True:
                state.flexible.add(field)
                state.required.pop(field, None)
        self._policy = ConversationPolicy()
        self._policy_state = state

        decision = await asyncio.to_thread(
            self._policy.next_tier1_requirement, state=state, knowledge=self.repository
        )
        if decision:
            # Signal the caller to short-circuit with the policy message.
            self._tier1_decision = decision.message
        else:
            self._tier1_decision = None
        if "budget" in state.flexible:
            max_price = None
        if "area" in state.flexible:
            area = None
        return max_price, city, area

    async def _run_repository_search(
        self, max_price: Any, city: str, area: str | None, normalized: dict
    ) -> list[dict]:
        """Call the repository in a thread-safe manner (sync psycopg under the hood)."""
        decision_message = getattr(self, "_tier1_decision", None)
        if decision_message:
            return []
        return await asyncio.to_thread(
            self.repository.search,
            budget=max_price,
            city=city,
            area=area,
            bedrooms=normalized["bedrooms"],
            property_type=normalized["property_type"],
            purpose=normalized["repo_purpose"],
            amenities=None,
            limit=10,  # Get more than top 3 for flexibility
        )

    async def _rank_results(self, results: list[dict], session: Any) -> list[dict]:
        """Rank raw repository results by stored preference profile, then by the ML ranker."""
        profile = None
        if self.preference_repository is not None and session is not None:
            try:
                customer_key = customer_key_for_phone(session.caller_phone)
                if customer_key:
                    profile = await asyncio.to_thread(
                        self.preference_repository.get,
                        customer_key,
                    )
            except Exception as profile_error:
                logger.warning("Preference profile lookup failed: %s", profile_error)
        if profile is not None:
            results = self.preference_ranker.rank(results, profile)

        runtime_profile = None
        if session is not None:
            runtime_profile = getattr(
                getattr(session, "sara_state", None), "user_profile", None
            )
        return self.ml_ranker.rank_properties(results, runtime_profile)

    async def _persist_session_state(self, session: Any, presented_results: list[dict]) -> None:
        """Snapshot the presented properties onto the session and log 'shown' interactions."""
        presented_ids = [
            str(item["property_id"])
            for item in presented_results
            if item.get("property_id")
        ]
        session.shown_property_ids = presented_ids
        session.latest_recommended_property_order = list(presented_ids)
        session.preference_snapshot = self._preference_snapshot(session)
        if not isinstance(getattr(session, "property_snapshots", None), dict):
            session.property_snapshots = {}
        for property_id in presented_ids:
            property = next(item for item in presented_results if str(item.get("property_id")) == property_id)
            session.property_snapshots[property_id] = self._property_snapshot(property)
            await self._record_interaction(
                session,
                property_id=property_id,
                action="shown",
                preference_snapshot=session.preference_snapshot,
                property_snapshot=session.property_snapshots[property_id],
            )

    async def _record_interaction(
        self,
        session: Any,
        *,
        property_id: str,
        action: str,
        reason: str | None = None,
        metadata: dict | None = None,
        preference_snapshot: dict | None = None,
        property_snapshot: dict | None = None,
    ) -> None:
        if not session or not getattr(session, "customer_id", None) or not self.interaction_repository:
            return
        try:
            await asyncio.to_thread(
                self.interaction_repository.record_interaction,
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

    @staticmethod
    def _preference_snapshot(session: Any) -> dict:
        profile = getattr(getattr(session, "sara_state", None), "user_profile", None)
        if profile is None:
            return {}
        amenities = getattr(profile, "amenities_preferred", [])
        if not isinstance(amenities, (list, tuple, set)):
            amenities = []
        return {
            "city": getattr(profile, "city", None),
            "area": getattr(profile, "area", None),
            "budget_min": None,
            "budget_max": getattr(profile, "budget", None),
            "bedrooms": getattr(profile, "bedrooms", None),
            "property_type": getattr(profile, "property_type", None),
            "purpose": getattr(profile, "purpose", None),
            "amenities": list(amenities),
        }

    @staticmethod
    def _property_snapshot(property_data: dict) -> dict:
        price = property_data.get("price")
        if isinstance(price, Decimal):
            price = float(price)
        return {
            "property_id": str(property_data.get("property_id")),
            "city": property_data.get("city"),
            "area": property_data.get("area"),
            "price": price,
            "bedrooms": property_data.get("bedrooms"),
            "property_type": property_data.get("property_type"),
            "purpose": property_data.get("purpose"),
            "amenities": list(property_data.get("amenities") or []),
        }

    async def _list_available_locations(self) -> str:
        """List cities from currently available, verified PostgreSQL inventory."""
        if not self.repository:
            logger.error("PostgreSQL repository not initialized")
            return RETRIEVAL_UNAVAILABLE

        try:
            cities = await asyncio.to_thread(self.repository.list_available_cities)
        except Exception as exc:
            logger.exception("Available-city lookup failed: %s", exc)
            return RETRIEVAL_UNAVAILABLE

        if not cities:
            return "Database mein is waqt koi verified available city nahi mili."

        city_list = ", ".join(cities)
        return (
            f"Verified available cities ({len(cities)}): {city_list}. "
            "Sirf isi list ke shehron ka naam customer ko batayen; koi aur city add na karein."
        )

    def _format_property_results(self, properties: list[dict]) -> str:
        """
        Format PostgreSQL property results into a readable string for Sara.

        Each property result from PostgreSQL includes:
            - property_id, property_name, area, city
            - bedrooms, bathrooms, covered_area
            - price, currency, property_type, purpose
            - developer_name, status, available
            - amenities (array from SQL GROUP_CONCAT)
        """

        if not properties:
            return "No properties to display."

        lines = []
        for i, prop in enumerate(properties, 1):
            prop_id = prop.get("property_id", "N/A")
            prop_name = prop.get("property_name", "Unnamed")
            area = prop.get("area", "Unknown")
            city = prop.get("city", "Unknown")
            bedrooms = prop.get("bedrooms", "?")
            bathrooms = prop.get("bathrooms", "?")
            property_type = prop.get("property_type", "Property")
            price = prop.get("price")
            currency = prop.get("currency", "PKR")
            developer = prop.get("developer_name", "")
            status = prop.get("status", "Available")
            amenities = prop.get("amenities", [])

            # Format price: convert to Crore if in PKR
            price_str = ""
            if price:
                try:
                    price_num = float(price) if isinstance(price, (int, str, Decimal)) else price
                    if currency == "PKR":
                        price_crore = price_num / 10_000_000
                        price_str = f"{price_crore:.2f} Crore PKR"
                    else:
                        price_str = f"{price_num:,.0f} {currency}"
                except (ValueError, TypeError):
                    price_str = "Price on request"

            # Build property description
            description = (
                f"{i}. {prop_name} (ID: {prop_id})\n"
                f"   Location: {area}, {city}\n"
                f"   Type: {bedrooms}BED {bathrooms}BATH {property_type}\n"
            )

            if price_str:
                description += f"   Price: {price_str}\n"

            if developer:
                description += f"   Developer: {developer}\n"

            if amenities and isinstance(amenities, list):
                # Show top 3 amenities
                top_amenities = amenities[:3]
                if top_amenities:
                    description += f"   Amenities: {', '.join(top_amenities)}\n"

            description += f"   Status: {status}\n"

            lines.append(description)

        return "".join(lines)
