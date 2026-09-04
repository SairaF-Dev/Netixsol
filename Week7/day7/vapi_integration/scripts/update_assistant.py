"""Attach the existing Sara assistant to the public webhook server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx


ROOT = Path(__file__).resolve().parents[1]
DAY7_ROOT = ROOT.parent
if str(DAY7_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY7_ROOT))

from vapi_integration.webhook_server import _get_sara_tools


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def assistant_id() -> str:
    configured = os.getenv("VAPI_ASSISTANT_ID", "").strip()
    if configured:
        return configured
    saved = ROOT / "sara_assistant_created.json"
    if saved.exists():
        return str(json.loads(saved.read_text(encoding="utf-8")).get("id", "")).strip()
    return ""


def main() -> None:
    load_dotenv()
    api_key = os.getenv("VAPI_API_KEY", "").strip()
    public_url = os.getenv("VAPI_SERVER_URL", "").strip().rstrip("/")
    current_assistant_id = assistant_id()
    webhook_secret = os.getenv("VAPI_WEBHOOK_SECRET", "").strip()

    parsed = urlparse(public_url)
    if not api_key:
        raise SystemExit("VAPI_API_KEY is missing from .env")
    if not current_assistant_id:
        raise SystemExit("VAPI_ASSISTANT_ID is missing and saved assistant JSON has no id")
    if parsed.scheme != "https" or not parsed.netloc or "placeholder" in parsed.netloc:
        raise SystemExit("VAPI_SERVER_URL must be a real public HTTPS URL")

    webhook_url = f"{public_url}/vapi/webhook"
    headers = {"Authorization": f"Bearer {api_key}"}
    current_response = httpx.get(
        f"https://api.vapi.ai/assistant/{current_assistant_id}",
        headers=headers,
        timeout=30,
    )
    current_response.raise_for_status()
    current_model = current_response.json().get("model", {})
    tools = _get_sara_tools()
    for tool in tools:
        function = tool.get("function", {})
        if function.get("name") == "book_appointment":
            properties = function.setdefault("parameters", {}).setdefault("properties", {})
            properties["client_email"] = {
                "type": "string",
                "description": "Customer email for confirmation and reminder (optional)",
            }
    server = {"url": webhook_url, "timeoutSeconds": 20}
    if webhook_secret:
        # Legacy secret remains supported by VAPI and is sent as
        # X-Vapi-Secret, which our FastAPI endpoint validates.
        server["secret"] = webhook_secret
    payload = {
        "server": server,
        "serverMessages": ["tool-calls", "end-of-call-report"],
    }
    if current_model:
        messages = current_model.get("messages") or []
        retrieval_rules = (
            "\n\nVERIFIED PROPERTY DATA RULES:\n"
            "- You must call search_properties before naming, pricing, describing, "
            "or claiming availability of any property.\n"
            "- Property facts may only come from the latest search_properties tool result.\n"
            "- Never invent or infer a property, price, ID, location, bedroom count, "
            "amenity, developer, or availability.\n"
            "- If the tool returns no match or a database error, say exactly that in "
            "natural UrduLish and ask whether the caller wants to adjust criteria.\n"
            "- Never promise that you are searching without actually calling the tool.\n"
            "- Preserve property IDs from tool results for appointment booking."
            "\n- If asked which cities or locations are available, call "
            "list_available_locations before naming any city and repeat only its results."
        )
        if messages and "VERIFIED PROPERTY DATA RULES:" not in messages[0].get("content", ""):
            messages[0]["content"] = messages[0].get("content", "") + retrieval_rules
        else:
            messages = [{"role": "system", "content": retrieval_rules.strip()}]
        payload["model"] = {
            key: current_model[key]
            for key in ("provider", "model", "temperature", "maxTokens")
            if key in current_model
        }
        payload["model"]["messages"] = messages
        payload["model"]["tools"] = tools
    response = httpx.patch(
        f"https://api.vapi.ai/assistant/{current_assistant_id}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if response.is_error:
        raise SystemExit(f"VAPI update failed ({response.status_code}): {response.text}")

    result = response.json()
    configured_url = (result.get("server") or {}).get("url", "")
    print(f"Updated Sara assistant {current_assistant_id}")
    print(f"Webhook: {configured_url}")


if __name__ == "__main__":
    main()
