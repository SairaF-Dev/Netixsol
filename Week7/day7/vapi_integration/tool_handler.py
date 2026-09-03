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

    def __init__(self, day4_api_url: str = "http://localhost:8004") -> None:
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
                result = await self._cancel_appointment(arguments)
            elif tool_name == "search_properties":
                result = await self._search_properties(arguments)
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
    async def _cancel_appointment(self, args: dict) -> str:
        apt_id = args.get("appointment_id", "")

        if not apt_id:
            return (
                "Cancel karne ke liye appointment ID chahiye. "
                "Kya aap apni appointment ID bata sakte hain?"
            )

        resp = await self._appointment_request("cancel", payload={}, appointment_id=apt_id)

        if resp.status_code == 200:
            return (
                "Appointment cancel ho gayi. "
                "Cancellation confirmation email bhi bhej di gayi hai. "
                "Agar dobara visit karni ho toh please call karein."
            )
        elif resp.status_code == 404:
            return "Yeh appointment ID nahi mili system mein."
        else:
            return "Cancel karne mein masla aa gaya. Dobara try karein."

    async def _search_properties(self, args: dict) -> str:
        """
        Search properties using PostgreSQL (single source of truth).

        Previously this method read Day 2 CSV files directly.
        Now it uses PostgresPropertyRepository to query verified data
        from PostgreSQL, ensuring data consistency and accuracy.

        Supported filters:
            - location (city/area name)
            - max_price (budget in PKR)
            - min_price (minimum budget in PKR)
            - bedrooms (integer)
            - purpose (buy, rent, invest, commercial)

        Returns:
            Human-readable property matches formatted for Sara to speak.
        """

        # Validate repository is available
        if not self.repository:
            logger.error("PostgreSQL repository not initialized")
            return (
                "Abhi property database se connection nahi ban pa raha. "
                "please thori der baad dobara try karein."
            )

        # Extract and normalize filter arguments
        location = str(args.get("location", "")).strip()
        max_price = args.get("max_price")
        bedrooms = args.get("bedrooms")
        property_type = str(args.get("property_type", "")).strip() or None
        purpose = str(args.get("purpose", "")).lower().strip()

        # Validate location is provided
        if not location:
            return (
                "Property search ke liye mujhe location batayen. "
                "Maslan: DHA Lahore, Bahria Town Karachi, etc."
            )

        # Normalize purpose: map VAPI enum values to repository values
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
        repo_purpose = purpose_map.get(purpose, purpose or None)

        # Split a natural location into the repository's city and area fields.
        # "DHA" is an area; "DHA Phase 6 Lahore" contains both filters.
        city = None
        area = location
        for known_city in ("Lahore", "Karachi", "Islamabad", "Rawalpindi"):
            if re.search(rf"\b{re.escape(known_city)}\b", location, re.IGNORECASE):
                city = known_city
                area = re.sub(
                    rf"\b{re.escape(known_city)}\b",
                    "",
                    location,
                    flags=re.IGNORECASE,
                ).strip(" ,-") or None
                break

        try:
            # Call repository in a thread-safe manner
            # (repository uses sync psycopg, but we're in an async context)
            results = await asyncio.to_thread(
                self.repository.search,
                budget=max_price,
                city=city,
                area=area,
                bedrooms=bedrooms,
                property_type=property_type,
                purpose=repo_purpose,
                amenities=None,
                limit=10,  # Get more than top 3 for flexibility
            )

            if not results:
                logger.info("No properties found for filters: %s", args)
                return (
                    f"Bohot sorri! Aapke criteria ke andar koi property "
                    f"abhi available nahi hai (location: {location}, "
                    f"bedrooms: {bedrooms}, max budget: {max_price}). "
                    f"Kya aap apne requirements thora adjust kar sakte hain? "
                    f"Maslan budget badha sakta hoon ya kisi aur location mein dekhun?"
                )

            # Format top 3 results for Sara to speak
            formatted_results = self._format_property_results(results[:3])

            response = (
                f"Found {len(results)} verified properties matching aapki requirements. "
                f"Here are the best ones:\n\n{formatted_results}\n\n"
                f"Instruct the AI: Tell the customer about these options in natural UrduLish. "
                f"Mention key features and amenities naturally. "
                f"Then ask 'Kya aap in mein se kisi ko visit karna chahenge?'"
            )

            return response

        except Exception as e:
            logger.exception("Property search failed: %s", e)
            return (
                "Property search mein ek masla aa gaya. "
                "Kripya thori der baad dobara try karein ya "
                "representative se rabta karein."
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
