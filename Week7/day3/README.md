# Week 7 — Day 3: Sara Real Estate Voice Agent

Production-oriented UrduLish conversational layer backed by verified
Week 7 Day 2 data.

## Core engineering rule

**The LLM decides what the user means. Verified company systems decide
what is true.**

Exact property facts never come from model memory.

### PostgreSQL owns structured facts

- price and verification date
- availability/status
- property type and bedrooms/bathrooms
- plot/covered area
- amenities
- developer
- payment plans
- nearby schools/hospitals
- assigned agent/contact records

### Day 2 RAG owns semantic knowledge

- FAQs
- project descriptions
- brochures/project overviews
- company/process knowledge

If Day 2 RAG says a question requires PostgreSQL, Sara does not use the
brochure as an alternate source for that exact fact.

## Main capabilities

- Human-style UrduLish property conversation
- Purpose → City → Budget → Area default collection
- Required / preferred / excluded / flexible constraints
- Verified city/area normalization and conservative typo recovery
- Multi-turn corrections and stale-result invalidation
- Progressive result batches (`aur options`)
- Safe option-number parsing (`DHA Phase 6` is not option 6)
- Verified selected-property facts
- Current availability refresh before answering
- Structured amenities/payment-plan/developer/assigned-agent lookups
- Verified comparisons
- Grounded no-result recovery
- Objection handling without guaranteed ROI/reputation claims
- Prompt-injection refusal for invented facts
- Day 4 booking/reschedule/cancel handoff
- CLI, Streamlit and FastAPI interfaces
- Per-session API conversation memory
- Per-bot turn serialization for concurrent same-session requests
- Turn-based STT → agent → TTS with latency metrics
- Concrete lazy connection to the finalized Day 2 RAG pipeline

## Setup

```powershell
python -m venv realestate_env
.\realestate_env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` with your own values.

**Never commit, zip, or share a populated `.env`.**

`DAY2_ROOT` should point to the finalized Day 2 project, for example:

```env
DAY2_ROOT=../Week7_Day2_Senior_Fixed_v2
```

The Day 2 project should contain:

```text
02_rag/
03_structured_retrieval/
04_recommendation/     # optional at Day 3 runtime
```

## RAG configuration

RAG is enabled by default and loaded lazily on the first semantic
FAQ/brochure question.

Useful settings:

```env
SARA_RAG_ENABLED=1
SARA_RAG_REQUIRED=0
SARA_RAG_WARM_ON_STARTUP=0
SARA_RAG_CHUNK_SIZE=512
SARA_RAG_TOP_K=3
RAG_MAX_TOKENS=160
```

`SARA_RAG_REQUIRED=0` means a temporary RAG failure does not take down
PostgreSQL property search. Sara fails closed for the semantic answer.

Check the connection:

```powershell
python scripts\check_rag.py
```

## Run tests

```powershell
pytest -q
```

## CLI

```powershell
python app.py
```

## Streamlit

```powershell
streamlit run ui\streamlit_app.py
```

## API

```powershell
uvicorn api.main:app --reload
```

### Liveness

```text
GET /health
```

Liveness stays lightweight and does not require database/RAG startup.

### Runtime readiness

```text
GET /ready
```

Checks runtime dependencies and performs a live PostgreSQL `SELECT 1` readiness probe.

### REST chat sessions

`POST /chat`

```json
{
  "message": "Lahore mein apartment purchase ke liye chahiye",
  "session_id": null
}
```

The first response returns an opaque `session_id`. Reuse it for later
turns in the same conversation.

Different sessions do not share memory. Trivial client-chosen IDs such as
`customer1` are not accepted as storage keys.

## Voice status

The push-to-talk path uses the configured STT and TTS providers around the
Sara agent. Deepgram Nova-3 is the recommended production STT provider.

```text
audio upload
   ↓
Deepgram STT (or configured fallback)
   ↓
Sara agent
   ↓
Configured TTS provider
```

### Deepgram UrduLish configuration

UrduLish switches between Hindustani and English inside the same sentence.
Use Nova-3 multilingual mode rather than forcing the monolingual Urdu model:

```env
VOICE_STT_PROVIDER=deepgram
DEEPGRAM_MODEL=nova-3
DEEPGRAM_LANGUAGE=multi
DEEPGRAM_SMART_FORMAT=1
```

`DEEPGRAM_KEYTERMS` contains separate comma-delimited terms and phrases. The
adapter sends every item as a repeated `keyterm` query parameter, including
budget phrases such as `teen crore` and intents such as `property purchase`.
Set `DEEPGRAM_LANGUAGE=ur` only for calls expected to contain Urdu without
English code-switching.

On the fixed UrduLish validation sample, multilingual mode returned
`Lahore main property purchase high. Budget teen crore high.` at 0.9966
confidence. The previous monolingual Urdu configuration produced phonetic
errors for `purchase` and `crore`.

### Deepgram TTS configuration

Deepgram Flux is the active TTS provider for both push-to-talk and streaming.
Priya is a calm female Indian-English voice selected for Roman UrduLish:

```env
VOICE_TTS_PROVIDER=deepgram
SARA_TTS_PROVIDER=deepgram
SARA_TTS_FALLBACK_PROVIDER=edge-tts
SARA_VOICE_GREETING_ENABLED=1
DEEPGRAM_API_KEY=
DEEPGRAM_TTS_MODEL=flux-priya-en
DEEPGRAM_TTS_ENCODING=mp3
DEEPGRAM_TTS_SPEED=1.0
DEEPGRAM_TTS_EXPRESSIVITY=0
DEEPGRAM_TTS_TIMEOUT_SECONDS=45
```

The adapter calls Deepgram's `/v2/speak` endpoint and streams browser-native
MP3 chunks. Flux currently speaks English, so the Indian accent improves Roman
UrduLish delivery but is not a native Urdu voice. Fish Audio remains available
by setting both provider variables to `fish-audio`. Keep API keys only in
`.env`; never add them to source control.

When a live call becomes ready, Sara immediately introduces herself as the
caller's real-estate agent and asks what type of property they need. The greeting
uses the normal TTS and barge-in path, so meaningful caller speech can interrupt
it. Set `SARA_VOICE_GREETING_ENABLED=0` to disable it or
`SARA_VOICE_GREETING=...` to customize the wording.

`POST /voice/turn` remains a stable turn-based fallback. `/live-voice` and
`/ws/voice` provide the live two-way path: the microphone stays open while Sara
speaks, confirmed user speech cancels current playback, and subsequent audio is
processed as the next turn. Devanagari and Urdu-script STT output is normalized
to Roman UrduLish before it reaches the UI and agent.

Synchronous provider work is kept off the FastAPI event loop. Provider
timeouts/retries and upload/TTS sizes are bounded.

Deepgram TTS is attempted first. If it fails before sending audio, the live and
turn-based pipelines automatically use Edge neural TTS; the browser voice is a
final audible fallback. Telephony integration remains future work.

## Day 4 handoff

Visit booking, rescheduling and cancellation are recognized intents, but
Day 3 does not fake completion. Final confirmation must come from the
Calendar/Email/workflow integration.

## Important ambiguity rule

A project name can represent multiple property/unit records. A semantic
question such as:

```text
Tell me about Horizon Heights Apartment
```

may use RAG.

An exact mutable fact such as price/availability should use a selected
property/property ID or another unambiguous structured reference rather
than silently choosing one unit.
