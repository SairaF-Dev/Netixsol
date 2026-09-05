from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

DAY7_ROOT = Path(__file__).resolve().parents[1]
DAY2_REPOSITORY = DAY7_ROOT.parent / "day2" / "03_structured_retrieval"
load_dotenv(DAY7_ROOT / "vapi_integration" / ".env", override=False)
for path in (str(DAY7_ROOT), str(DAY2_REPOSITORY)):
    if path not in sys.path:
        sys.path.insert(0, path)

from web_api.schemas import (
    AppointmentBook, AppointmentReschedule, CustomerCreate, CustomerResponse,
    AuthMeResponse, LoginRequest, MeAppointmentBook, MeInteractionCreate, RegisterRequest,
    InteractionCreate, InteractionResponse, PreferencesResponse, PreferencesUpdate,
    PropertyResponse, PropertySearchRequest, RecommendationRequest, RecommendationResponse,
    ChatRequest, ChatResponse,
)
from web_api.services import RecommendationSessionExpired, WebServices, public_property
from web_api.auth import DuplicateRegistration, InvalidCredentials, SESSION_COOKIE


def _customer_response(customer) -> dict:
    return {"customer_id": customer.customer_id, "full_name": customer.full_name,
            "email": customer.email, "phone": customer.phone_normalized}


def _preferences_response(customer_id: str, preferences) -> dict:
    if preferences is None:
        return {"customer_id": customer_id, "amenities": []}
    return {key: getattr(preferences, key) for key in PreferencesResponse.model_fields}


def create_app(services: WebServices | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = WebServices.from_environment()
        yield

    app = FastAPI(
        title="Sara Shared Website API", version="0.6.0",
        description="Development API backed by Sara's existing verified services.",
        lifespan=None if services else lifespan,
    )
    if services:
        app.state.services = services
    origins = [value.strip() for value in os.getenv("SARA_WEB_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if value.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])

    @app.middleware("http")
    async def csrf_protection(request: Request, call_next):
        exempt = {"/api/auth/login", "/api/auth/register"}
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path not in exempt:
            services = getattr(request.app.state, "services", None)
            auth = getattr(services, "auth", None)
            token = request.cookies.get(SESSION_COOKIE)
            validator = getattr(auth, "validate_csrf", None)
            if token and validator and not await asyncio.to_thread(validator, token, request.headers.get("X-CSRF-Token")):
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
        return await call_next(request)

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, _exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal service error"})

    def svc(request: Request) -> WebServices:
        return request.app.state.services

    def identity(request: Request):
        services = svc(request)
        if not services.auth:
            raise HTTPException(503, "Authentication is not configured")
        current = services.auth.authenticate(request.cookies.get(SESSION_COOKIE))
        if not current:
            raise HTTPException(401, "Authentication required")
        return current

    def authorize_customer(request: Request, customer_id: UUID):
        services = svc(request)
        if services.auth is None:  # Explicit dependency-injected development/test compatibility.
            return None
        current = identity(request)
        if current.customer_id != str(customer_id):
            raise HTTPException(403, "Access denied")
        return current

    def set_session_cookie(response: Response, token: str, expires) -> None:
        secure = os.getenv("SARA_AUTH_SECURE_COOKIE", "0") == "1"
        same_site = os.getenv("SARA_AUTH_SAMESITE", "lax").lower()
        if os.getenv("SARA_ENV", "development").lower() == "production" and not secure:
            raise RuntimeError("Production authentication cookies must be Secure")
        if same_site not in {"lax", "strict", "none"} or (same_site == "none" and not secure):
            raise RuntimeError("Invalid authentication cookie policy")
        response.set_cookie(
            SESSION_COOKIE, token, httponly=True,
            secure=secure, samesite=same_site, expires=expires,
            path=os.getenv("SARA_AUTH_COOKIE_PATH", "/"),
            domain=os.getenv("SARA_AUTH_COOKIE_DOMAIN") or None,
        )

    @app.post("/api/auth/register", response_model=AuthMeResponse, status_code=201)
    async def register(payload: RegisterRequest, response: Response, request: Request):
        services = svc(request)
        if not services.auth:
            raise HTTPException(503, "Authentication is not configured")
        limiter = getattr(services.auth, "rate_allowed", None)
        if limiter and not await asyncio.to_thread(limiter, "register", payload.email, request.client.host if request.client else ""):
            raise HTTPException(429, "Too many authentication attempts")
        try:
            token, expires, current = await asyncio.to_thread(services.auth.register, payload.full_name, payload.email, payload.phone, payload.password)
        except DuplicateRegistration:
            raise HTTPException(409, "Registration could not be completed")
        except ValueError:
            raise HTTPException(422, "Registration could not be completed")
        set_session_cookie(response, token, expires)
        return current

    @app.post("/api/auth/login", response_model=AuthMeResponse)
    async def login(payload: LoginRequest, response: Response, request: Request):
        services = svc(request)
        if not services.auth:
            raise HTTPException(503, "Authentication is not configured")
        limiter = getattr(services.auth, "rate_allowed", None)
        if limiter and not await asyncio.to_thread(limiter, "login", payload.email, request.client.host if request.client else ""):
            raise HTTPException(429, "Too many authentication attempts")
        try:
            token, expires, current = await asyncio.to_thread(services.auth.login, payload.email, payload.password)
        except InvalidCredentials:
            raise HTTPException(401, "Invalid email or password")
        set_session_cookie(response, token, expires)
        return current

    @app.post("/api/auth/logout", status_code=204)
    async def logout(response: Response, request: Request):
        services = svc(request)
        if services.auth:
            await asyncio.to_thread(services.auth.logout, request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(SESSION_COOKIE, path="/")

    @app.get("/api/auth/csrf")
    async def csrf(request: Request):
        identity(request)
        token = request.cookies.get(SESSION_COOKIE)
        return {"csrf_token": await asyncio.to_thread(svc(request).auth.issue_csrf, token)}

    @app.get("/api/auth/sessions")
    async def auth_sessions(request: Request):
        current = identity(request)
        return {"sessions": await asyncio.to_thread(svc(request).auth.repository.list_sessions, current.user_id)}

    @app.post("/api/auth/logout-all", status_code=204)
    async def logout_all(response: Response, request: Request):
        current = identity(request)
        await asyncio.to_thread(svc(request).auth.logout_all, current.user_id)
        response.delete_cookie(SESSION_COOKIE, path="/")

    @app.get("/api/auth/me", response_model=AuthMeResponse)
    async def me(request: Request):
        return identity(request)

    @app.get("/health")
    async def health(request: Request):
        services = svc(request)
        try:
            await asyncio.to_thread(services.properties.list_available_cities)
            database = "ok"
        except Exception:
            database = "unavailable"
        ml = services.ml.health()
        return {"status": "ok" if database == "ok" else "degraded", "database": database,
                "ml_mode": ml["mode"], "ml_artifact_loaded": bool(ml["loaded"]),
                "synthetic_development_model": True}

    @app.post("/api/customers", response_model=CustomerResponse, status_code=201)
    async def create_customer(payload: CustomerCreate, request: Request):
        try:
            context = await asyncio.to_thread(svc(request).customers.create_or_get_test_customer, full_name=payload.full_name, email=payload.email, phone=payload.phone)
        except ValueError:
            raise HTTPException(422, "Invalid customer identity")
        return _customer_response(context.customer)

    @app.get("/api/customers/{customer_id}", response_model=CustomerResponse)
    async def get_customer(customer_id: UUID, request: Request):
        authorize_customer(request, customer_id)
        context = await asyncio.to_thread(svc(request).customers.resolve_for_customer_id, str(customer_id))
        if not context.customer:
            raise HTTPException(404, "Customer not found")
        return _customer_response(context.customer)

    @app.get("/api/customers/{customer_id}/preferences", response_model=PreferencesResponse)
    async def get_preferences(customer_id: UUID, request: Request):
        authorize_customer(request, customer_id)
        context = await asyncio.to_thread(svc(request).customers.resolve_for_customer_id, str(customer_id))
        if not context.customer:
            raise HTTPException(404, "Customer not found")
        return _preferences_response(str(customer_id), context.preferences)

    @app.patch("/api/customers/{customer_id}/preferences", response_model=PreferencesResponse)
    @app.put("/api/customers/{customer_id}/preferences", response_model=PreferencesResponse)
    async def update_preferences(customer_id: UUID, payload: PreferencesUpdate, request: Request):
        authorize_customer(request, customer_id)
        services = svc(request)
        context = await asyncio.to_thread(services.customers.resolve_for_customer_id, str(customer_id))
        if not context.customer:
            raise HTTPException(404, "Customer not found")
        updates = payload.model_dump(exclude_unset=True)
        existing = context.preferences
        minimum = updates.get("budget_min", getattr(existing, "budget_min", None))
        maximum = updates.get("budget_max", getattr(existing, "budget_max", None))
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(422, "budget_min cannot exceed budget_max")
        result = await asyncio.to_thread(services.customers.update_preferences, str(customer_id), updates)
        return _preferences_response(str(customer_id), result)

    @app.post("/api/properties/search", response_model=list[PropertyResponse])
    async def search_properties(payload: PropertySearchRequest, request: Request):
        services = svc(request)
        filters = payload.model_dump(exclude={"customer_id", "limit"}, exclude_none=True)
        if payload.customer_id:
            authorize_customer(request, payload.customer_id)
            context = await asyncio.to_thread(services.customers.resolve_for_customer_id, str(payload.customer_id))
            if not context.customer:
                raise HTTPException(404, "Customer not found")
            if context.preferences:
                for field in ("city", "area", "budget_max", "bedrooms", "property_type", "purpose", "amenities"):
                    value = getattr(context.preferences, field)
                    if value not in (None, []):
                        filters.setdefault(field, value)
        try:
            rows = await asyncio.to_thread(services.properties.search, budget=filters.pop("budget_max", None), limit=payload.limit, **filters)
            return [public_property(row) for row in rows]
        except Exception:
            raise HTTPException(503, "Property search is temporarily unavailable")

    @app.post("/api/customers/{customer_id}/recommendations", response_model=RecommendationResponse)
    async def recommendations(customer_id: UUID, payload: RecommendationRequest, request: Request):
        authorize_customer(request, customer_id)
        services = svc(request)
        try:
            session_id, rows = await services.recommendations(str(customer_id), payload.limit, payload.recommendation_session_id)
        except LookupError:
            raise HTTPException(404, "Customer not found")
        except ValueError:
            raise HTTPException(409, "Customer preferences are required")
        except PermissionError:
            raise HTTPException(409, "Recommendation session is not valid for this customer")
        except Exception:
            raise HTTPException(503, "Recommendations are temporarily unavailable")
        return {"recommendation_session_id": session_id, "ml_mode": services.ml.mode, "properties": rows}

    @app.post("/api/interactions", response_model=InteractionResponse, status_code=201)
    async def interaction(payload: InteractionCreate, request: Request):
        authorize_customer(request, payload.customer_id)
        services = svc(request)
        context = services.sessions.get(payload.recommendation_session_id)
        if not context or context.customer_id != str(payload.customer_id):
            raise HTTPException(409, "Recommendation context is invalid")
        snapshot = context.property_snapshots.get(payload.property_id)
        if not snapshot:
            raise HTTPException(422, "Property was not returned in this recommendation")
        try:
            event = await asyncio.to_thread(
                services.interactions.record_interaction,
                customer_id=str(payload.customer_id), conversation_id=str(payload.recommendation_session_id),
                property_id=payload.property_id, action=payload.action,
                preference_snapshot=context.preference_snapshot, property_snapshot=snapshot,
            )
        except ValueError:
            raise HTTPException(422, "Property is not eligible for this interaction")
        except Exception:
            raise HTTPException(503, "Interaction could not be recorded")
        return {"interaction_id": event.interaction_id, "customer_id": event.customer_id,
                "property_id": event.property_id, "action": event.action}

    @app.post("/api/appointments", status_code=201)
    async def book_appointment(payload: AppointmentBook, request: Request):
        current = authorize_customer(request, payload.customer_id)
        services = svc(request)
        customer = await asyncio.to_thread(services.customers.resolve_for_customer_id, str(payload.customer_id))
        if not customer.customer:
            raise HTTPException(404, "Customer not found")
        property_data = await asyncio.to_thread(services.properties.get_property, payload.property_id)
        if not property_data or not property_data.get("available"):
            raise HTTPException(422, "Verified available property not found")
        body = {
            "client_name": customer.customer.full_name or "Website customer",
            "client_phone": customer.customer.phone_normalized or "",
            "client_email": customer.customer.email,
            "employee_name": os.getenv("SARA_APPOINTMENT_EMPLOYEE_NAME", "Sara AI Agent"),
            "employee_email": os.getenv("SARA_APPOINTMENT_EMPLOYEE_EMAIL", "sara@realestatehub.pk"),
            "property_id": payload.property_id, "property_name": property_data.get("property_name") or property_data.get("name"),
            "starts_at": payload.starts_at.isoformat(), "duration_minutes": payload.duration_minutes,
            "meeting_notes": payload.meeting_notes,
        }
        status, response = await services.appointments.request("POST", "/appointments", body)
        if status >= 400:
            raise HTTPException(status, response.get("detail", "Appointment request failed"))
        appointment = response.get("appointment", {}) if isinstance(response, dict) else {}
        appointment_id = appointment.get("appointment_id") if isinstance(appointment, dict) else None
        if current and appointment_id:
            await asyncio.to_thread(services.auth.repository.own_appointment, current.user_id, str(appointment_id))
        return response

    @app.patch("/api/appointments/{appointment_id}/reschedule")
    async def reschedule(appointment_id: UUID, payload: AppointmentReschedule, request: Request):
        services = svc(request); current = identity(request) if services.auth else None
        if current and not await asyncio.to_thread(services.auth.repository.owns_appointment, current.user_id, str(appointment_id)):
            raise HTTPException(404, "Appointment not found")
        status, response = await services.appointments.request("PATCH", f"/appointments/{appointment_id}/reschedule", {"starts_at": payload.starts_at.isoformat()})
        if status >= 400:
            raise HTTPException(status, response.get("detail", "Appointment request failed"))
        return response

    @app.delete("/api/appointments/{appointment_id}")
    async def cancel(appointment_id: UUID, request: Request):
        services = svc(request); current = identity(request) if services.auth else None
        if current and not await asyncio.to_thread(services.auth.repository.owns_appointment, current.user_id, str(appointment_id)):
            raise HTTPException(404, "Appointment not found")
        status, response = await services.appointments.request("DELETE", f"/appointments/{appointment_id}")
        if status >= 400:
            raise HTTPException(status, response.get("detail", "Appointment request failed"))
        return response

    @app.get("/api/me/preferences", response_model=PreferencesResponse)
    async def my_preferences(request: Request):
        current = identity(request)
        context = await asyncio.to_thread(svc(request).customers.resolve_for_customer_id, current.customer_id)
        return _preferences_response(current.customer_id, context.preferences)

    @app.patch("/api/me/preferences", response_model=PreferencesResponse)
    async def update_my_preferences(payload: PreferencesUpdate, request: Request):
        current = identity(request); services = svc(request)
        context = await asyncio.to_thread(services.customers.resolve_for_customer_id, current.customer_id)
        updates = payload.model_dump(exclude_unset=True)
        minimum = updates.get("budget_min", getattr(context.preferences, "budget_min", None))
        maximum = updates.get("budget_max", getattr(context.preferences, "budget_max", None))
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(422, "budget_min cannot exceed budget_max")
        result = await asyncio.to_thread(services.customers.update_preferences, current.customer_id, updates)
        return _preferences_response(current.customer_id, result)

    @app.post("/api/me/recommendations", response_model=RecommendationResponse)
    async def my_recommendations(payload: RecommendationRequest, request: Request):
        current = identity(request); services = svc(request)
        try:
            session_id, rows = await services.recommendations(current.customer_id, payload.limit, payload.recommendation_session_id, current.user_id)
        except RecommendationSessionExpired:
            raise HTTPException(410, "Recommendation session has expired")
        except PermissionError:
            raise HTTPException(409, "Recommendation session is not valid for this customer")
        except ValueError:
            raise HTTPException(409, "Customer preferences are required")
        except Exception:
            raise HTTPException(503, "Recommendations are temporarily unavailable")
        return {"recommendation_session_id": session_id, "ml_mode": services.ml.mode, "properties": rows}

    @app.post("/api/me/properties/search", response_model=list[PropertyResponse])
    async def my_property_search(payload: PropertySearchRequest, request: Request):
        current = identity(request)
        owned = payload.model_copy(update={"customer_id": UUID(current.customer_id)})
        return await search_properties(owned, request)

    @app.post("/api/me/interactions", response_model=InteractionResponse, status_code=201)
    async def my_interaction(payload: MeInteractionCreate, request: Request):
        current = identity(request); services = svc(request)
        try:
            context = await asyncio.to_thread(services.sessions.get, payload.recommendation_session_id)
        except RecommendationSessionExpired:
            raise HTTPException(410, "Recommendation session has expired")
        if not context or context.customer_id != current.customer_id:
            raise HTTPException(409, "Recommendation context is invalid")
        snapshot = context.property_snapshots.get(payload.property_id)
        if not snapshot:
            raise HTTPException(422, "Property was not returned in this recommendation")
        event = await asyncio.to_thread(services.interactions.record_interaction, customer_id=current.customer_id, conversation_id=str(payload.recommendation_session_id), property_id=payload.property_id, action=payload.action, preference_snapshot=context.preference_snapshot, property_snapshot=snapshot)
        return {"interaction_id": event.interaction_id, "customer_id": event.customer_id, "property_id": event.property_id, "action": event.action}

    @app.post("/api/me/appointments", status_code=201)
    async def my_appointment(payload: MeAppointmentBook, request: Request):
        current = identity(request)
        legacy = AppointmentBook(customer_id=current.customer_id, **payload.model_dump())
        return await book_appointment(legacy, request)

    @app.get("/api/me/appointments")
    async def my_appointments(request: Request):
        current = identity(request); services = svc(request)
        ids = await asyncio.to_thread(services.auth.repository.list_appointment_ids, current.user_id)
        listing = getattr(services.appointments, "list_owned", None)
        if not listing:
            return {"appointments": []}
        return {"appointments": await listing(ids)}

    @app.post("/api/me/chat", response_model=ChatResponse, response_model_exclude_none=True)
    async def my_chat(payload: ChatRequest, request: Request):
        from web_api.conversation_service import ConversationDenied, ConversationExpired
        current = identity(request)
        adapter = svc(request).chat
        if adapter is None:
            raise HTTPException(503, "Sara chat is temporarily unavailable")
        try:
            return await adapter.turn(
                current, payload,
                lambda value: my_interaction(value, request),
                lambda value: my_appointment(value, request),
                lambda appointment_id, value: reschedule(appointment_id, value, request),
                lambda appointment_id: cancel(appointment_id, request),
            )
        except ConversationDenied:
            raise HTTPException(404, "Conversation not found")
        except ConversationExpired:
            raise HTTPException(410, "Conversation has expired. Start a new conversation.")
        except RecommendationSessionExpired:
            raise HTTPException(410, "Recommendation session has expired. Request new options.")
        except PermissionError:
            raise HTTPException(409, "Chat context is invalid. Request new options.")
        except HTTPException as exc:
            # Existing Day 4 routes may contain provider details; never echo them in chat.
            safe = {404: "Requested item not found", 409: "Request could not be completed. Check the current details.",
                    410: "Recommendation session has expired. Request new options.",
                    422: "Please confirm the property or appointment details."}
            raise HTTPException(exc.status_code if exc.status_code in safe else 503,
                                safe.get(exc.status_code, "Sara's service is temporarily unavailable"))
        except Exception as exc:
            logging.getLogger("sara.chat").warning("Chat turn failed: %s (cause=%s, status=%s)",
                type(exc).__name__, type(exc.__cause__).__name__, getattr(exc.__cause__, "status_code", None))
            raise HTTPException(503, "Sara chat is temporarily unavailable. Please try again.")

    return app


app = create_app()
