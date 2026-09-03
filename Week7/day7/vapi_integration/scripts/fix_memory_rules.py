"""Update VAPI assistant with improved system prompt that avoids re-asking confirmed info."""
import os
import httpx

VAPI_KEY = os.environ.get("VAPI_API_KEY", "").strip()
if not VAPI_KEY:
    raise RuntimeError("VAPI_API_KEY is required")
ASSISTANT_ID = "8da8a05f-109c-4a75-8261-3009caaf4afe"

headers = {"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"}

# Critical addition to system prompt — explicit memory rules
MEMORY_ADDITION = """

---

# CRITICAL MEMORY RULE — READ CAREFULLY

Once the customer has confirmed ANY piece of information, NEVER ask for it again.

## Confirmed Information Tracking:

If customer says "purchase karna hai" OR "kharidna hai" OR "buy karna hai" OR "lena hai"
→ intent = PURCHASE. Do NOT ask again "kharidari ke liye ya kiraye pe?"

If customer says "kiraye pe lena hai" OR "rent chahiye"
→ intent = RENT. Do NOT ask again.

If customer says a number like "3 crore" OR "50 lakh" OR "1 crore"
→ budget is confirmed. Do NOT ask again.

If customer says "4 bedroom" OR "3 bed" OR "2 kamray"
→ bedrooms confirmed. Do NOT ask again.

If customer says a city like "Lahore" OR "Karachi" OR "Islamabad"
→ city confirmed. Do NOT ask again.

## Example of WRONG behavior:
Customer: "Purchase karna hai"
Sara: "Aap kharidari ke liye ya kiraye pe lena chahte hain?" ← WRONG! Already told you!

## Example of RIGHT behavior:
Customer: "Purchase karna hai"
Sara: "Ji bilkul, purchase ke liye. Aapka approximate budget kya hai?" ← CORRECT!

## When Speech is Unclear:
If you heard something that could be "purchase" or "buy" — ASSUME purchase, confirm briefly:
"Purchase ke liye, sahi samjha?" — then move on. Do NOT go back to the original question.

"""

# Get current assistant to preserve system prompt
r_get = httpx.get(
    f"https://api.vapi.ai/assistant/{ASSISTANT_ID}",
    headers=headers,
    timeout=15,
)
current = r_get.json()
current_messages = current.get("model", {}).get("messages", [])

# Find and update system message
updated_messages = []
for msg in current_messages:
    if msg.get("role") == "system":
        msg["content"] = msg["content"] + MEMORY_ADDITION
    updated_messages.append(msg)

payload = {
    "model": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "messages": updated_messages,
        "temperature": 0.5,  # Lower = more consistent, less repetitive
        "maxTokens": 400,
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
    print("System prompt updated with memory rules!")
    print("Sara ab confirmed info dobara nahi puchegi.")
else:
    print("Error:", r.text[:300])
