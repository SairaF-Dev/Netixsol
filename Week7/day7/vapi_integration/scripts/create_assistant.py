"""Create Sara assistant on VAPI — runs with the actual API key."""

import httpx
import json
import os
import sys

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "").strip()
if not VAPI_API_KEY:
    raise RuntimeError("VAPI_API_KEY is required; put it in vapi_integration/.env")

# Load Sara's system prompt from Day 1
PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "day1",
    "05_system_prompt", "system_prompt.md"
)
try:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        system_prompt = f.read()
    print(f"System prompt loaded ({len(system_prompt)} chars)")
except FileNotFoundError:
    system_prompt = (
        "You are Sara, a professional AI real estate sales agent for RealEstate Hub Pakistan. "
        "Speak in UrduLish — natural Pakistani Urdu mixed with English real estate terms. "
        "Be warm, helpful, professional. Never hallucinate property details. "
        "When customer wants to book/reschedule/cancel visit, use the provided tools. "
        "Always greet with: Assalam-o-Alaikum!"
    )
    print("Using default system prompt (Day 1 file not found)")

# VAPI Server URL — update this after starting ngrok
# For now we create assistant with placeholder; update via PATCH later
SERVER_URL = os.getenv("VAPI_SERVER_URL", "https://placeholder.ngrok.io")
WEBHOOK_URL = f"{SERVER_URL.rstrip('/')}/vapi/webhook"
WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "").strip()

HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

# ── Assistant config ──────────────────────────────────────────────────────────
assistant_payload = {
    "name": "Sara - RealEstate Hub",

    # Model: custom-llm → VAPI sends transcripts to OUR webhook server
    # When server URL is ready, this will route to our LangGraph agent
    "model": {
        "provider": "openai",          # fallback until server URL is set
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "book_appointment",
                    "description": "Property visit appointment book karo. Customer ne date/time confirm kar di ho to use karo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Customer ka poora naam"},
                            "client_phone": {"type": "string", "description": "Phone number with country code (+92...)"},
                            "client_email": {"type": "string", "description": "Customer email for confirmation and reminder (optional)"},
                            "property_id": {"type": "string", "description": "Verified property ID returned by search_properties"},
                            "property_name": {"type": "string", "description": "Property ka naam"},
                            "starts_at": {"type": "string", "description": "ISO 8601 datetime with timezone e.g. 2025-09-05T10:00:00+05:00"},
                            "meeting_notes": {"type": "string", "description": "Koi special notes"},
                        },
                        "required": ["client_name", "client_phone", "property_id", "property_name", "starts_at"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reschedule_appointment",
                    "description": "Existing appointment reschedule karo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "string"},
                            "starts_at": {"type": "string", "description": "Naya time ISO 8601 format mein"},
                        },
                        "required": ["appointment_id", "starts_at"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_appointment",
                    "description": "Appointment cancel karo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "string"},
                        },
                        "required": ["appointment_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Properties search karo customer requirements ke mutabiq",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City/area e.g. DHA Karachi"},
                            "max_price": {"type": "integer", "description": "Max budget PKR mein"},
                            "bedrooms": {"type": "integer"},
                            "purpose": {
                                "type": "string",
                                "enum": ["buy", "rent", "invest", "commercial"],
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
        ],
        "temperature": 0.7,
        "maxTokens": 500,
    },

    # STT: Deepgram Nova-3 (same as Day 3)
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "multi",
        "smartFormat": True,
        "numerals": True,
        "endpointing": 450,
        "keyterm": [
            "DHA", "DHA Phase 6", "Bahria Town", "apartment",
            "one bedroom", "crore", "lakh", "property visit",
            "appointment", "RealEstate Hub",
        ],
    },

    # TTS: ElevenLabs Rachel — warm female voice, no extra API key needed via VAPI
    "voice": {
        "provider": "11labs",
        "voiceId": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs Rachel
        "stability": 0.5,
        "similarityBoost": 0.75,
    },

    # Call behaviour
    "firstMessage": (
        "Assalam-o-Alaikum! RealEstate Hub se Sara baat kar rahi hoon. "
        "Main aap ki kis tarah help kar sakti hoon?"
    ),
    "endCallMessage": (
        "Bahut shukriya aap ki call ka! "
        "Koi aur sawal ho toh dobara call karein. Allah Hafiz!"
    ),
    "endCallPhrases": [
        "allah hafiz", "khuda hafiz", "bye", "goodbye",
        "shukriya bye", "ok bye", "theek hai bye"
    ],
    "maxDurationSeconds": 1800,
    "recordingEnabled": True,
    "backgroundSound": "off",
    "responseDelaySeconds": 0.5,

    # VAPI sends tool-calls and call lifecycle events here.
    "server": {
        "url": WEBHOOK_URL,
        "timeoutSeconds": 20,
        **({"secret": WEBHOOK_SECRET} if WEBHOOK_SECRET else {}),
    },
    "serverMessages": ["tool-calls", "end-of-call-report"],
}

# ── Create assistant ──────────────────────────────────────────────────────────
print("\nCreating Sara assistant on VAPI...")

resp = httpx.post(
    "https://api.vapi.ai/assistant",
    json=assistant_payload,
    headers=HEADERS,
    timeout=30,
)

if resp.status_code not in (200, 201):
    print(f"FAILED: {resp.status_code}")
    print(resp.text)
    sys.exit(1)

result = resp.json()
assistant_id = result["id"]

print(f"\n{'='*50}")
print(f"  Sara assistant created successfully!")
print(f"{'='*50}")
print(f"  Assistant ID : {assistant_id}")
print(f"  Name         : {result['name']}")
print(f"  Voice        : {result['voice']['voiceId']} ({result['voice']['provider']})")
print(f"  STT          : {result['transcriber']['model']} ({result['transcriber']['provider']})")
print(f"{'='*50}")

# Save to .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
with open(env_path, "r") as f:
    env_content = f.read()

env_content = env_content.replace(
    "VAPI_ASSISTANT_ID=",
    f"VAPI_ASSISTANT_ID={assistant_id}",
)

with open(env_path, "w") as f:
    f.write(env_content)

print(f"\n  .env updated with ASSISTANT_ID")

# Save full config
with open("sara_assistant_created.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"  Full config saved to: sara_assistant_created.json")

print(f"""
NEXT STEPS:
  1. Get a phone number: VAPI Dashboard -> Phone Numbers -> Buy (+1 US free)
  2. Assign Sara to that number in the dashboard
  3. Start ngrok: ngrok http 8007
  4. Update VAPI_SERVER_URL in .env with ngrok URL
  5. Start services and CALL THE NUMBER!
""")
