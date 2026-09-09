"""Browser VAPI transport; existing website routes remain the business boundary."""
import asyncio
import hmac
import json
import logging
import os
from uuid import UUID

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from web_api.auth import SESSION_COOKIE
from vapi_integration.retrieval_policy import RETRIEVAL_UNAVAILABLE
from web_api.schemas import ChatRequest, PreferencesUpdate, RecommendationRequest, MeAppointmentBook, AppointmentReschedule


class EmptyVoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CloseVoiceRequest(EmptyVoiceRequest):
    voice_session: str = Field(min_length=32, max_length=128)


def register_voice_routes(app, identity, svc, preferences, recommendations, book, reschedule, cancel, feedback):
    @app.post("/api/me/voice-sessions", status_code=201)
    async def start_voice(payload: EmptyVoiceRequest, request: Request, response: Response):
        current = identity(request)
        assistant = os.getenv("VAPI_ASSISTANT_ID", "").strip()
        store = svc(request).voice
        if not assistant or not store:
            raise HTTPException(503, "Browser voice is not configured")
        response.headers["Cache-Control"] = "no-store"
        customer = await asyncio.to_thread(svc(request).customers.resolve_for_customer_id, current.customer_id)
        session = await asyncio.to_thread(store.issue, current, request.cookies[SESSION_COOKIE], assistant)
        session["preferences"] = {key: getattr(customer.preferences, key, None) for key in
            ("city", "area", "budget_min", "budget_max", "bedrooms", "property_type", "purpose", "amenities")}
        return session

    @app.post("/api/me/voice-sessions/close", status_code=204)
    async def close_voice(payload: CloseVoiceRequest, request: Request):
        current = identity(request)
        if svc(request).voice:
            await asyncio.to_thread(svc(request).voice.close, payload.voice_session, current.user_id)

    @app.post("/api/internal/voice/webhook")
    async def voice_webhook(request: Request):
        expected = os.getenv("VAPI_WEBHOOK_SECRET", "")
        supplied = request.headers.get("x-vapi-secret", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            raise HTTPException(403, "Invalid webhook authentication")
        message = (await request.json()).get("message", {})
        call = message.get("call", {})
        token = call.get("assistantOverrides", {}).get("variableValues", {}).get("sara_voice_session")
        services = svc(request)
        if not services.voice:
            raise HTTPException(503, "Browser voice is unavailable")
        try:
            current, cid = await asyncio.to_thread(services.voice.resolve, token, call)
        except PermissionError:
            raise HTTPException(403, "Invalid voice session")
        # Set only after secret + persisted capability validation, never from JSON identity.
        request.state.voice_identity = current
        event = message.get("type")
        if event == "end-of-call-report" or (event == "status-update" and message.get("status") == "ended"):
            await asyncio.to_thread(services.voice.close, token)
            return {"status": "ok"}
        if event == "transcript" and message.get("role") == "user" and message.get("transcriptType") == "final":
            try:
                await services.chat.turn(current, ChatRequest(message=message.get("transcript", ""), conversation_id=cid),
                    lambda value: feedback(value, request), lambda value: book(value, request),
                    lambda aid, value: reschedule(aid, value, request), lambda aid: cancel(aid, request),
                    observe_only=True)
            except Exception:
                raise HTTPException(503, "Voice memory could not be updated")
            return {"status": "ok"}
        if event != "tool-calls":
            return {"status": "ignored"}
        results = []
        async with services.chat.store.turn(cid, current) as (_, saved):
            for tool in message.get("toolCallList") or message.get("toolCalls", []):
                fn = tool.get("function", {})
                name = tool.get("name") or fn.get("name", "")
                completed = saved.setdefault("voice_tool_results", {})
                tid = tool.get("id")
                if not isinstance(tid, str) or not tid or len(tid) > 200:
                    raise HTTPException(422, "Tool call ID is required")
                if tid in completed:
                    results.append(completed[tid])
                    continue
                if len(completed) >= 200:
                    raise HTTPException(429, "Start a new voice call")
                try:
                    args = tool.get("parameters") or fn.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    if not isinstance(args, dict):
                        raise ValueError()
                    if name == "search_properties":
                        from vapi_integration.customer_identity import property_location
                        updates = {field: args[key] for key, field in
                                   (("max_price", "budget_max"), ("bedrooms", "bedrooms"), ("property_type", "property_type"))
                                   if key in args and args[key] is not None}
                        if args.get("location"):
                            city, area = property_location(str(args["location"]))
                            if city:
                                updates["city"] = city
                            updates["area"] = area
                        if args.get("purpose"):
                            updates["purpose"] = {"buy": "purchase", "rent": "rental", "invest": "investment"}.get(args["purpose"], args["purpose"])
                        if updates:
                            await preferences(PreferencesUpdate(**updates), request)
                        data = await recommendations(RecommendationRequest(limit=3), request)
                        saved.update(recommendation_session_id=str(data["recommendation_session_id"]),
                                     property_order=[p["property_id"] for p in data["properties"]])
                        # No model mode, probability, or identity is sent to the assistant.
                        result = {"properties": data["properties"]}
                    elif name == "book_appointment":
                        pid = args.get("property_id")
                        await services.chat._recommendation(current, saved, pid)
                        result = await book(MeAppointmentBook(property_id=pid, starts_at=args.get("starts_at")), request)
                    elif name == "reschedule_appointment":
                        result = await reschedule(UUID(args["appointment_id"]), AppointmentReschedule(starts_at=args.get("starts_at")), request)
                    elif name == "cancel_appointment":
                        result = await cancel(UUID(args["appointment_id"]), request)
                    elif name == "list_available_locations":
                        # Reuse the existing verified-location tool, which has no customer mutations.
                        from vapi_integration.tool_handler import VapiToolHandler
                        from types import SimpleNamespace
                        result = await VapiToolHandler._list_available_locations(SimpleNamespace(repository=services.properties))
                    else:
                        result = "This tool is not available."
                    if name in {"book_appointment", "reschedule_appointment", "cancel_appointment"}:
                        appointment = result.get("appointment", {})
                        result = {"appointment": {k: appointment[k] for k in
                                  ("appointment_id", "status", "starts_at") if k in appointment}}
                except Exception as exc:
                    # Exception text can include credentials or user payloads.
                    logging.getLogger("web.voice").error("Voice tool %s failed: %s", name, type(exc).__name__)
                    result = (RETRIEVAL_UNAVAILABLE if name in {"search_properties", "list_available_locations"}
                              else "Request could not be confirmed. Check your preferences or appointment status on the website before retrying.")
                results.append({"name": name, "toolCallId": tool.get("id"), "result": json.dumps(result, default=str)})
                completed[tid] = results[-1]
        return {"results": results}
