from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx

from ml.model_service import PropertyPreferenceModelService
from vapi_integration.customer_learning import ExplainablePreferenceRanker, PreferenceProfile
from vapi_integration.customer_service import CustomerService
from vapi_integration.interaction_repository import InteractionRepository


PROPERTY_FIELDS = (
    "property_id", "property_name", "city", "area", "price", "currency",
    "bedrooms", "bathrooms", "property_type", "purpose", "amenities",
    "available", "status",
)


def public_property(row: dict[str, Any]) -> dict[str, Any]:
    result = {field: row.get(field) for field in PROPERTY_FIELDS}
    result["property_name"] = result["property_name"] or row.get("name")
    result["price"] = float(result["price"])
    result["amenities"] = list(result["amenities"] or [])
    result["available"] = bool(result["available"])
    result["currency"] = result["currency"] or "PKR"
    return result


def preference_snapshot(preferences: Any) -> dict[str, Any]:
    return {
        "city": preferences.city, "area": preferences.area,
        "budget_min": preferences.budget_min, "budget_max": preferences.budget_max,
        "bedrooms": preferences.bedrooms, "property_type": preferences.property_type,
        "purpose": preferences.purpose, "amenities": list(preferences.amenities or []),
    }


def property_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    public = public_property(row)
    return {key: public[key] for key in (
        "property_id", "city", "area", "price", "bedrooms",
        "property_type", "purpose", "amenities", "available",
    )}


@dataclass
class RecommendationContext:
    customer_id: str
    property_snapshots: dict[str, dict[str, Any]]
    preference_snapshot: dict[str, Any]
    shown_recorded: bool = False


class RecommendationSessionExpired(PermissionError):
    pass


class RecommendationSessionStore:
    """In-memory compatibility store used only by dependency-injected tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, RecommendationContext] = {}

    def get(self, session_id: UUID) -> RecommendationContext | None:
        return self._sessions.get(str(session_id))

    def put(self, session_id: UUID, context: RecommendationContext) -> None:
        self._sessions[str(session_id)] = context


class PostgresRecommendationSessionStore:
    """Shared recommendation ownership and returned-property snapshots."""

    def __init__(self, database_url: str | None = None, ttl_hours: int | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")
        self.ttl_hours = ttl_hours or int(os.getenv("SARA_RECOMMENDATION_SESSION_HOURS", "24"))

    def get(self, session_id: UUID) -> RecommendationContext | None:
        import psycopg
        query = """SELECT s.customer_id,s.expires_at,s.status,p.property_id,
                   p.preference_snapshot,p.property_snapshot
                   FROM recommendation_sessions s LEFT JOIN recommendation_session_properties p
                   ON p.recommendation_session_id=s.recommendation_session_id
                   WHERE s.recommendation_session_id=%s ORDER BY p.display_position"""
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (session_id,)); rows = cursor.fetchall()
            if not rows:
                return None
            if rows[0][2] != "active" or rows[0][1] <= datetime.now(timezone.utc):
                connection.execute("UPDATE recommendation_sessions SET status='expired' WHERE recommendation_session_id=%s AND status='active'", (session_id,))
                raise RecommendationSessionExpired("Recommendation session has expired")
        snapshots = {str(row[3]): row[5] for row in rows if row[3] is not None}
        preference = next((row[4] for row in rows if row[4] is not None), {})
        return RecommendationContext(str(rows[0][0]), snapshots, preference, True)

    def put(self, session_id: UUID, context: RecommendationContext, auth_user_id: str | None = None) -> bool:
        import psycopg
        expires = datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("""INSERT INTO recommendation_sessions
                (recommendation_session_id,customer_id,auth_user_id,expires_at)
                VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING recommendation_session_id""",
                (session_id, context.customer_id, auth_user_id, expires))
            created = cursor.fetchone() is not None
            if created:
                for position, (property_id, snapshot) in enumerate(context.property_snapshots.items()):
                    cursor.execute("""INSERT INTO recommendation_session_properties
                        (recommendation_session_id,property_id,display_position,preference_snapshot,property_snapshot)
                        VALUES (%s,%s,%s,%s::jsonb,%s::jsonb)""", (session_id, property_id, position,
                        json.dumps(context.preference_snapshot), json.dumps(snapshot)))
        return created

    def claim_shown(self, session_id: UUID, property_id: str) -> bool:
        import psycopg
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("""UPDATE recommendation_session_properties SET shown_recorded=TRUE
                WHERE recommendation_session_id=%s AND property_id=%s AND shown_recorded=FALSE
                RETURNING property_id""", (session_id, property_id))
            return cursor.fetchone() is not None


class AppointmentGateway:
    """Thin client for authoritative Day 4 appointment workflows."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("DAY4_API_URL", "http://localhost:8004")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("DAY4_API_KEY", "")

    async def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        if not self.api_key:
            return 503, {"detail": "Appointment service is not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, f"{self.base_url}{path}", json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
        try:
            body = response.json()
        except ValueError:
            body = {"detail": "Appointment service returned an invalid response"}
        return response.status_code, body

    async def list_owned(self, appointment_ids: list[str]) -> list[dict[str, Any]]:
        results = []
        for appointment_id in appointment_ids:
            status, body = await self.request("GET", f"/appointments/{appointment_id}")
            if status == 200 and isinstance(body.get("appointment"), dict):
                results.append(body["appointment"])
        return results


class WebServices:
    def __init__(self, customer_service: Any, property_repository: Any,
                 interaction_repository: Any, deterministic_ranker: Any | None = None,
                 ml_service: Any | None = None, appointment_gateway: Any | None = None,
                 sessions: RecommendationSessionStore | None = None, auth_service: Any | None = None,
                 chat_store: Any | None = None, sara: Any | None = None) -> None:
        self.customers = customer_service
        self.properties = property_repository
        self.interactions = interaction_repository
        self.deterministic = deterministic_ranker or ExplainablePreferenceRanker()
        self.ml = ml_service or PropertyPreferenceModelService()
        self.appointments = appointment_gateway or AppointmentGateway()
        self.sessions = sessions or RecommendationSessionStore()
        self.auth = auth_service
        self.chat = None
        if chat_store is not None:
            from web_api.chat import ChatAdapter
            self.chat = ChatAdapter(self, chat_store, sara)

    @classmethod
    def from_environment(cls):
        from postgres_repository import PostgresPropertyRepository
        from web_api.auth import AuthRepository, AuthService
        customers = CustomerService(); auth_repository = AuthRepository(); auth_repository.initialize()
        from web_api.conversation_service import PostgresConversationStore
        chat_store = PostgresConversationStore()
        chat_store.initialize()
        return cls(customers, PostgresPropertyRepository(), InteractionRepository(),
                   sessions=PostgresRecommendationSessionStore(), auth_service=AuthService(auth_repository, customers),
                   chat_store=chat_store)

    async def recommendations(self, customer_id: str, limit: int, session_id: UUID | None,
                              auth_user_id: str | None = None):
        recommendation_id = session_id or uuid4()
        existing = await asyncio.to_thread(self.sessions.get, recommendation_id)
        if existing:
            if existing.customer_id != customer_id:
                raise PermissionError("recommendation session belongs to another customer")
            return recommendation_id, list(existing.property_snapshots.values())
        context = await asyncio.to_thread(self.customers.resolve_for_customer_id, customer_id)
        if not context.customer:
            raise LookupError("customer")
        preferences = context.preferences
        if not preferences:
            raise ValueError("preferences")
        rows = await asyncio.to_thread(
            self.properties.search,
            budget=preferences.budget_max, city=preferences.city, area=preferences.area,
            bedrooms=preferences.bedrooms, property_type=preferences.property_type,
            purpose=preferences.purpose, amenities=preferences.amenities or None, limit=limit,
        )
        profile = PreferenceProfile(
            customer_key=customer_id, city=preferences.city, area=preferences.area,
            budget=preferences.budget_max, bedrooms=preferences.bedrooms,
            property_type=preferences.property_type, purpose=preferences.purpose,
            amenities=list(preferences.amenities or []),
        )
        deterministic = self.deterministic.rank(rows, profile)
        ranked = self.ml.rank_properties(deterministic, profile)
        response_rows = [public_property(row) for row in ranked]
        if not existing:
            stored = RecommendationContext(
                customer_id=customer_id,
                property_snapshots={row["property_id"]: public_property(row) for row in ranked},
                preference_snapshot=preference_snapshot(preferences),
            )
            try:
                created = self.sessions.put(recommendation_id, stored, auth_user_id)
            except TypeError:
                self.sessions.put(recommendation_id, stored); created = True
            if created is False:
                existing = await asyncio.to_thread(self.sessions.get, recommendation_id)
                if not existing or existing.customer_id != customer_id:
                    raise PermissionError("recommendation session belongs to another customer")
                return recommendation_id, list(existing.property_snapshots.values())
            for row in ranked:
                claimer = getattr(self.sessions, "claim_shown", None)
                if claimer and not await asyncio.to_thread(claimer, recommendation_id, str(row["property_id"])):
                    continue
                await asyncio.to_thread(
                    self.interactions.record_interaction,
                    customer_id=customer_id, conversation_id=str(recommendation_id),
                    property_id=str(row["property_id"]), action="shown",
                    preference_snapshot=stored.preference_snapshot,
                    property_snapshot=property_snapshot(row),
                )
            stored.shown_recorded = True
        return recommendation_id, response_rows
