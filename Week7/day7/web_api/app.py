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
DAY3_ROOT = DAY7_ROOT.parent / "day3"
DAY2_ROOT = DAY7_ROOT.parent / "day2"
DAY2_REPOSITORY = DAY2_ROOT / "03_structured_retrieval"
load_dotenv(DAY7_ROOT / "vapi_integration" / ".env", override=False)
if (DAY3_ROOT / ".env").exists():
    load_dotenv(DAY3_ROOT / ".env", override=False)
if (DAY2_ROOT / ".env").exists():
    load_dotenv(DAY2_ROOT / ".env", override=False)
for path in (str(DAY7_ROOT), str(DAY3_ROOT), str(DAY2_REPOSITORY)):
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

    origins = [value.strip() for value in os.getenv("SARA_WEB_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if value.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, _exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal service error"})

    def svc(request: Request) -> WebServices:
        return request.app.state.services

    def identity(request: Request):
        if getattr(request.state, "voice_identity", None) is not None:
            return request.state.voice_identity
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

    @app.get("/api/agent/leads")
    async def get_agent_leads(request: Request):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get("http://127.0.0.1:8000/leads?limit=50")
                if res.status_code == 200:
                    data = res.json()
                    leads = data.get("leads", [])
                    if leads:
                        return leads
        except Exception:
            pass

        import psycopg, os
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return []
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            c.customer_id,
                            c.full_name,
                            c.phone_normalized,
                            COALESCE(cp.city, 'Lahore'),
                            COALESCE(cp.area, 'DHA'),
                            COALESCE(cp.budget_max, 30000000),
                            COALESCE(cp.property_type, 'House'),
                            COALESCE(cp.purpose, 'Purchase'),
                            (SELECT COUNT(*) FROM customer_interactions ci WHERE ci.customer_id = c.customer_id)
                        FROM customers c
                        LEFT JOIN customer_preferences cp ON c.customer_id = cp.customer_id
                        WHERE c.full_name IS NOT NULL 
                          AND c.full_name NOT LIKE '%Test%' 
                          AND c.full_name NOT LIKE '%Diagnostic%' 
                          AND c.full_name NOT LIKE '%CORS%' 
                          AND c.full_name NOT LIKE '%Chat%' 
                          AND c.full_name NOT LIKE '%Appointment%'
                          AND c.full_name NOT LIKE '%Phase Eight%'
                          AND c.full_name NOT LIKE '%Buyer%'
                        ORDER BY c.created_at DESC
                        LIMIT 15;
                    """)
                    rows = cur.fetchall()
                    result = []
                    for r in rows:
                        calls = max(1, min(10, int(r[8]) if r[8] else 1))
                        dur = max(3, calls * 3)
                        b_val = float(r[5])
                        visit = 1 if b_val >= 35000000 else 0
                        src = "Call" if "+9231" in str(r[2]) else "WhatsApp"
                        result.append({
                            "id": str(r[0]),
                            "name": str(r[1]).strip().title(),
                            "phone": str(r[2]),
                            "city": str(r[3]).strip().title(),
                            "location": str(r[4]).strip(),
                            "budget_pkr": b_val,
                            "property_type": str(r[6]).strip().title(),
                            "purpose": str(r[7]).strip().title(),
                            "lead_source": src,
                            "calls": calls,
                            "duration_min": dur,
                            "visit_booked": visit,
                        })
                    return result
        except Exception as exc:
            logging.getLogger("sara.leads").warning("Failed to fetch agent leads: %s", exc)
            return []

    @app.post("/api/properties/search", response_model=list[PropertyResponse])
    async def search_properties(payload: PropertySearchRequest, request: Request):
        services = svc(request)
        filters = payload.model_dump(exclude={"customer_id", "limit", "offset"}, exclude_none=True)
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
            rows = await asyncio.to_thread(
                services.properties.search_catalog,
                budget=filters.pop("budget_max", None),
                limit=payload.limit,
                offset=payload.offset,
                **filters,
            )
            total_count = int(rows[0].get("catalog_total", 0)) if rows else 0
            return [{**public_property(row), "total_count": total_count} for row in rows]
        except Exception:
            raise HTTPException(503, "Property search is temporarily unavailable")

    @app.get("/api/properties/{property_id}", response_model=PropertyResponse)
    async def get_property(property_id: str, request: Request):
        properties = svc(request).properties
        try:
            row = await asyncio.to_thread(properties.get_property, property_id)
            if row is None:
                row = await asyncio.to_thread(properties.get_catalog_property, property_id)
        except Exception:
            raise HTTPException(503, "Property details are temporarily unavailable")
        if not row:
            raise HTTPException(404, "Property was not found")
        return public_property(row)

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
        if not property_data:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"http://127.0.0.1:8000/properties/{payload.property_id}")
                    if resp.status_code == 200:
                        property_data = resp.json()
            except Exception:
                pass
        if not property_data or not property_data.get("available"):
            raise HTTPException(422, "Verified available property not found")

        ptype = property_data.get("property_type") or "House"
        loc = property_data.get("area") or property_data.get("location") or ""
        city = property_data.get("city") or "Lahore"
        prov = property_data.get("province_name") or ("Punjab" if city.lower() in ["lahore", "faisalabad", "rawalpindi"] else "Sindh" if city.lower() == "karachi" else "Islamabad Capital Territory")
        area_str = str(property_data.get("area") or "")
        if not area_str or area_str == loc:
            if property_data.get("plot_size"):
                area_str = f"{property_data.get('plot_size')} {property_data.get('plot_unit') or 'Marla'}"
            elif property_data.get("area_marla"):
                area_str = f"{property_data.get('area_marla')} Marla"
            else:
                area_str = "1 Kanal"

        beds = property_data.get("bedrooms")
        baths = property_data.get("bathrooms") or property_data.get("baths")
        agency = property_data.get("agency") or property_data.get("developer_name") or "Mash Allah Estate & Builders"
        agent = property_data.get("agent") or "Azam Ali"
        price_val = str(property_data.get("price")) if property_data.get("price") is not None else None
        agent_email_slug = "".join(c for c in agent.lower().replace(" ", ".") if c.isalnum() or c == ".")

        body = {
            "client_name": customer.customer.full_name or "Website customer",
            "client_phone": customer.customer.phone_normalized or "",
            "client_email": customer.customer.email,
            "employee_name": agent,
            "employee_email": f"{agent_email_slug}@realestatehub.pk" if agent_email_slug else "support@realestatehub.pk",
            "property_id": str(payload.property_id),
            "property_name": property_data.get("property_name") or property_data.get("name") or f"{beds or ''} Bed {ptype} in {loc}, {city}".strip(),
            "starts_at": payload.starts_at.isoformat(),
            "duration_minutes": payload.duration_minutes,
            "meeting_notes": payload.meeting_notes,
            "property_type": ptype,
            "location": loc,
            "city": city,
            "province_name": prov,
            "area": area_str,
            "bedrooms": beds,
            "bathrooms": baths,
            "baths": baths,
            "purpose": property_data.get("purpose") or "For Sale",
            "price": price_val,
            "agency": agency,
            "agent": agent,
            "page_url": property_data.get("page_url"),
            "latitude": property_data.get("latitude"),
            "longitude": property_data.get("longitude"),
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
        appts = await listing(ids)
        for appt in appts:
            req = appt.get("request", {})
            pid = req.get("property_id")
            if pid:
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(f"http://127.0.0.1:8000/properties/{pid}")
                        if resp.status_code == 200:
                            pdata = resp.json()
                            appt["property_details"] = pdata
                            # Hydrate real dataset attributes
                            if pdata.get("agency"):
                                req["agency"] = pdata.get("agency")
                            if pdata.get("agent"):
                                req["agent"] = pdata.get("agent")
                                req["employee_name"] = pdata.get("agent")
                                req["employee_email"] = f"{pdata['agent'].lower().replace(' ', '.')}@realestatehub.pk"
                            req["price"] = pdata.get("price")
                            req["price_pkr"] = pdata.get("price_pkr")
                            req["area"] = pdata.get("area")
                            req["area_marla"] = pdata.get("area_marla")
                            req["purpose"] = pdata.get("purpose")
                            req["city"] = pdata.get("city")
                            req["location"] = pdata.get("location")
                            req["province_name"] = pdata.get("province_name")
                            req["bedrooms"] = pdata.get("bedrooms")
                            req["bathrooms"] = pdata.get("bathrooms")
                            req["baths"] = pdata.get("baths")
                            req["latitude"] = pdata.get("latitude")
                            req["longitude"] = pdata.get("longitude")
                            req["page_url"] = pdata.get("page_url")
                except Exception:
                    pass
        return {"appointments": appts}

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

    from web_api.voice import register_voice_routes
    register_voice_routes(app, identity, svc, update_my_preferences, my_recommendations,
                          my_appointment, reschedule, cancel, my_interaction)
    return app


app = create_app()
