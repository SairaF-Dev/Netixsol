
## Architecture

```
📱 Caller dials phone number
        ↓
   VAPI Platform
   ├── STT: Deepgram Nova-3 (transcript)
   ├── Barge-in detection (interruption)
   └── TTS: ElevenLabs / Fish Audio (voice)
        ↕  HTTP POST
   ┌─────────────────────────────────┐
   │   webhook_server.py (port 8007) │  ← This package
   │   FastAPI + session_manager     │
   └─────────────┬───────────────────┘
                 ↓
   Day 3: Sara LangGraph Nodes
   (intent, memory, search, objection, booking)
                 ↓
   Day 4: Appointment API (port 8004)
   (Calendar + Email + CRM + n8n)
                 ↓
   Day 2: RAG + ChromaDB
   (property knowledge base)
```

---

## Step 1 — Prerequisites

```powershell
# Python 3.11+
cd day7/vapi_integration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Step 2 — VAPI Account Setup

1. **Sign up**: [vapi.ai](https://vapi.ai) (free tier available)
2. **Get API Key**: Dashboard → Settings → API Keys → Copy
3. **Get a Phone Number**:
   - Dashboard → Phone Numbers → Buy Number
   - Free US number available on free tier
   - For Pakistan (+92): Import via Twilio (optional for demo)

---

## Step 3 — Configure Environment

```powershell
# Copy template
cp .env.example .env
```

Edit `.env`:
```env
VAPI_API_KEY=vapi_xxxxxxxxxxxxxxxx
VAPI_SERVER_URL=https://your-ngrok-url.ngrok.io   # Step 4 mein milega
VAPI_VOICE_ID=21m00Tcm4TlvDq8ikWAM                # ElevenLabs Rachel voice
DAY4_API_URL=http://localhost:8004
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## Step 4 — Expose Server Publicly (ngrok)

VAPI needs a public HTTPS URL to call your webhook.

```powershell
# Install ngrok: https://ngrok.com/download
ngrok http 8007
# Copy the https://xxxx.ngrok.io URL → paste in .env as VAPI_SERVER_URL
```

For production, deploy to Railway/Render instead.

---

## Step 5 — Start All Services

Open 3 terminals:

**Terminal 1 — Day 4 Appointment API**
```powershell
cd day4
.\.venv\Scripts\Activate.ps1
uvicorn api.main:app --port 8004 --reload
```

**Terminal 2 — VAPI Webhook Server**
```powershell
cd day7/vapi_integration
.\.venv\Scripts\Activate.ps1
uvicorn webhook_server:app --port 8007 --reload
```

**Terminal 3 — ngrok**
```powershell
ngrok http 8007
```

---

## Step 6 — Register Sara on VAPI

```powershell
cd day7/vapi_integration
python scripts/create_assistant.py
# Output: ✅ Assistant ID: asst_xxxxxxxxxxxx
# → Copy this to your .env: VAPI_ASSISTANT_ID=asst_xxxxxxxxxxxx
```

---

## Step 7 — Assign Phone Number

1. VAPI Dashboard → Phone Numbers
2. Click your phone number
3. Assistant → Select "Sara - RealEstate Hub"
4. Save

---

## Step 8 — Test!

```powershell
# Quick health check
curl http://localhost:8007/health

# Run tests
pytest tests/ -v
```

**Call the phone number!** Sara will answer in UrduLish. 🎉

---

## What VAPI Sends to Your Server

### On Every Call Event (POST /vapi/webhook)

| Event Type | When | What Your Server Does |
|------------|------|-----------------------|
| `assistant-request` | Before call connects | Returns Sara's full config |
| `call-start` | Call answered | Creates session, logs caller |
| `transcript` | User speaks | Runs LangGraph, returns response text |
| `tool-calls` | Agent calls a tool | Calls Day 4 API, returns result |
| `end-of-call-report` | Call ends | Logs to CRM, closes session |

---

## Conversation Flow (Live Call)

```
[Caller dials number]
  → VAPI answers
  → Sends "assistant-request" to /vapi/webhook
  → Your server returns Sara's config
  → VAPI plays firstMessage:
      "Assalam-o-Alaikum! RealEstate Hub se Sara..."

[Caller speaks: "DHA mein 3 bedroom flat chahiye"]
  → VAPI transcribes via Deepgram
  → Sends "transcript" event to your server
  → session_manager.process_turn() runs Day 3 LangGraph:
      node_intent_detection() → "search"
      node_property_search() → finds DHA properties
      node_recommendation() → picks top match
  → Returns: "Bilkul sir! DHA Phase 6 mein ek..."
  → VAPI converts text to speech via ElevenLabs
  → Caller hears Sara's voice

[Caller: "Theek hai, appointment book karo kal 10 baje"]
  → VAPI detects tool call needed: "book_appointment"
  → Sends "tool-calls" event
  → tool_handler.execute("book_appointment", {...})
  → Calls Day 4 API: POST /appointments
  → Google Calendar event created ✅
  → Email sent to agent ✅
  → Returns: "Appointment book ho gayi! Kal 10 baje..."
  → VAPI speaks result

[Caller: "Shukriya, Allah Hafiz"]
  → VAPI detects end phrase
  → Plays endCallMessage
  → Sends "end-of-call-report"
  → Session closed, full transcript logged to CRM
```

---

## Monitoring

```powershell
# Live logs
uvicorn webhook_server:app --port 8007 --log-level info

# VAPI dashboard shows:
# - All calls with recordings
# - Transcripts
# - Latency per turn
# - Success/failure rates
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| VAPI can't reach server | Check ngrok is running, URL in .env is correct |
| "403 Invalid secret" | Check VAPI_WEBHOOK_SECRET matches in VAPI dashboard |
| Tool call fails | Make sure Day 4 is running on port 8004 |
| Sara speaks English only | Check system_prompt.md is loading correctly |
| High latency (>3s) | Switch LLM to gpt-4o-mini, reduce system prompt length |

---

## Production Deployment

For production (not localhost + ngrok):

```bash
# Deploy to Railway
railway up --service sara-vapi-webhook

# Or Docker
docker build -t sara-vapi .
docker run -p 8007:8007 --env-file .env sara-vapi
```

Update `VAPI_SERVER_URL` in VAPI dashboard with your production URL.

---

## Files in This Package

```
day7/vapi_integration/
├── webhook_server.py      ← Main FastAPI server (VAPI events)
├── session_manager.py     ← Per-call state + LangGraph routing
├── tool_handler.py        ← Executes Day 4 appointment tools
├── models.py              ← Pydantic models for VAPI payloads
├── requirements.txt       ← Dependencies
├── .env.example           ← Config template
├── scripts/
│   └── create_assistant.py ← One-time VAPI setup script
└── tests/
    └── test_webhook_server.py ← Integration tests
```

