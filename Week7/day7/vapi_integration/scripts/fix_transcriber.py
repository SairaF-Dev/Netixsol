"""Switch an existing Vapi assistant to Urdu/English transcription."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()
VAPI_KEY = os.environ.get("VAPI_API_KEY")
ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
if not VAPI_KEY or not ASSISTANT_ID:
    raise RuntimeError("VAPI_API_KEY and VAPI_ASSISTANT_ID are required")

headers = {"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"}

# Fix: Use 'multi' language — recognizes BOTH Urdu + English words correctly
# "property" will stay "property", "DHA" stays "DHA", Urdu words also recognized
payload = {
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "multi",        # auto-detect Urdu + English mix
        "smartFormat": True,
        "numerals": True,
        "endpointing": 450,
        "keyterm": [
            "DHA", "DHA Phase 6", "Bahria Town", "Lahore", "Karachi",
            "Islamabad", "apartment", "one bedroom", "crore", "lakh",
            "property visit", "appointment", "RealEstate Hub", "Sara",
        ],
    }
}

r = httpx.patch(
    f"https://api.vapi.ai/assistant/{ASSISTANT_ID}",
    json=payload,
    headers=headers,
    timeout=15,
)

print("Status:", r.status_code)
if r.status_code == 200:
    t = r.json().get("transcriber", {})
    print("Transcriber updated!")
    print("  Model   :", t.get("model"))
    print("  Language:", t.get("language"))
    print("  Keyterms:", len(t.get("keyterm", [])), "terms added")
    print("\nAb 'property' sahi likha jayega, 'poppy' nahi!")
else:
    print("Error:", r.text[:400])
