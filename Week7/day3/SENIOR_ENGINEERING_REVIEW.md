# Senior Agentic AI Engineering Review — Day 3

## Executive assessment

The uploaded project already had a strong grounding principle, verified
location handling, useful conversational memory and session isolation.

The most important remaining gap was architectural: the `RagBridge`
existed but the actual finalized Day 2 RAG pipeline was still not wired
into normal CLI/API/Streamlit startup.

This review preserves the working conversation engine and strengthens the
runtime around it rather than replacing it with a new framework.

## Baseline before this review

Existing regression suite:

**21/21 passing**

Strong areas already present:

- Purpose → City → Budget → Area collection order
- verified Day 2 location grounding
- conservative typo recovery
- required/preferred/excluded/flexible memory
- result pagination
- ambiguous-location protection
- option digit collision protection
- per-session REST memory
- sync voice work moved off FastAPI event loop
- fail-closed placeholder RAG bridge
- no bundled secrets/virtualenv in the uploaded reviewed ZIP

## Findings and fixes

### 1. Critical — Day 2 RAG was still not actually connected

**Finding**

`RagBridge` accepted an injected service but normal application startup
constructed `SaraChatbot(Day2Adapter())` without one.

Therefore FAQ/brochure answers failed closed even though Day 2 had a
working RAG pipeline.

**Fix**

Added:

- `src/sara_agent/day2_rag_service.py`
- `src/sara_agent/runtime.py`

The integration loads the actual:

```text
DAY2_ROOT/02_rag/rag_pipeline.py
```

and therefore reuses Day 2:

- loader/chunker
- embeddings
- Chroma vector store
- retriever
- structured-vs-semantic query policy
- grounded answer generation

The service is lazy so SentenceTransformer/Chroma do not slow every
application startup.

The same RAG service is shared across conversation sessions; mutable
conversation state is not shared.

### 2. Critical — hidden amenity parser misclassified unrelated questions

New regression tests found:

```text
Is it available?
```

could be parsed as an amenity called `is it`.

Likewise:

```text
payment plan kya hai?
```

could be parsed as an amenity called `payment plan`.

This could return a confident but irrelevant amenities response before
the NLU layer was even reached.

**Fix**

Tightened amenity parsing with:

- reserved payment/investment/maintenance topics
- leftover pronoun/question-word rejection
- deterministic structured-fact precedence

Availability now reaches the availability path. Payment plans reach the
structured payment-plan lookup.

### 3. High — mutable selected-property facts could become stale

Selected search results were stored in conversation memory. Availability
could change after the search while Sara kept answering from the old row.

**Fix**

Before selected-property details/availability/objection/fact responses,
Sara now attempts an exact PostgreSQL refresh by `property_id` and merges
the latest exact record over the richer search row.

Availability explicitly states that the latest verified PostgreSQL row is
being used.

### 4. High — structured child facts were incomplete at Day 3 boundary

Added Day 2 adapter methods for exact:

- current amenities
- payment plans
- developer
- assigned agents

These queries/adapter calls remain structured and never come from RAG or
LLM generation.

Payment-plan/developer/assigned-agent questions can now be answered
deterministically after a property is selected.

### 5. High — same-session concurrent turns could race

The session store itself was thread-safe, but two concurrent requests
using the same bot could mutate one `ConversationState` simultaneously.

**Fix**

Each `SaraChatbot` now owns an `RLock` and serializes `handle_message`
turns.

Different sessions still execute independently.

### 6. High — provider token/timeout behavior was too implicit

NLU used a hard-coded `max_tokens=650` and provider timeout/retry behavior
was not explicitly bounded.

**Fix**

Added:

```env
SARA_NLU_MAX_TOKENS=320
SARA_LLM_TIMEOUT_SECONDS=20
SARA_LLM_MAX_RETRIES=1
```

Voice provider also gets bounded timeout/retry/TTS text settings.

This reduces cost/credit surprises and prevents long provider hangs.

### 7. Medium — session IDs accepted trivial client-chosen keys

A client could send values such as `customer1` and use them as server
session keys.

**Fix**

Server-generated sessions now use cryptographically random URL-safe IDs.
Only sufficiently long opaque URL-safe IDs are accepted on later turns.
Legacy 32-character hex IDs remain compatible.

This is hardening, not authentication. Production customer identity still
requires an authentication/authorization layer.

### 8. Medium — liveness and readiness needed separation

Calling a health endpoint should not fail just because PostgreSQL/RAG
configuration is missing.

**Fix**

- `/health` = lightweight process liveness
- `/ready` = Sara dependency readiness, including a live PostgreSQL `SELECT 1` check

### 9. Medium — duplicated application wiring risk

CLI/API/Streamlit previously constructed their dependencies separately,
making it easy for one interface to forget RAG.

**Fix**

Added `SaraRuntime`, the single dependency composition point.

CLI, API and Streamlit now use it.

### 10. Medium — voice error exposure/reliability

Uncaught provider failures surfaced as generic server 500s.

**Fix**

Voice provider exceptions are logged server-side and the API returns a
controlled 502 response without leaking API/provider details.

Empty STT transcripts get a natural retry response rather than being
treated as a normal property turn.

## New regression coverage

The expanded suite now covers:

- lazy Day 2 RAG pipeline contract
- structured RAG refusal propagation
- project overview through RAG without prior selection
- live availability refresh
- deterministic payment-plan lookup
- invalid/trivial session-ID rejection
- previous location/memory/edge-case/session behavior

Final local automated suite after review:

**30/30 passing**

## Architecture after review

```text
User text / transcript
        ↓
Conversation controls + deterministic safe handlers
        ↓
Semantic NLU (OpenRouter)
        ↓
Query planner + conversation state
        ↓
     Routing boundary
        ↓
┌───────────────────────────┬──────────────────────────┐
│ Structured mutable facts  │ Semantic knowledge       │
│ Day 2 PostgreSQL          │ Day 2 RAG                │
│                           │                          │
│ price                     │ FAQs                     │
│ availability              │ brochure overview        │
│ amenities                 │ project description      │
│ developer                 │ process/company policy   │
│ payment plan              │                          │
│ nearby entities           │                          │
│ agent assignment          │                          │
└───────────────────────────┴──────────────────────────┘
        ↓
Grounded UrduLish response
        ↓
Optional turn-based TTS
```

## Remaining limitations

### 1. True streaming/barge-in is not implemented

The voice endpoint remains a turn-based upload:

```text
STT → agent → TTS
```

This should not be presented as a true real-time interruption-capable
voice stack.

### 2. Scheduling is still a Day 4 handoff

Sara recognizes schedule/reschedule/cancel intent but does not create fake
calendar confirmations.

### 3. In-memory sessions are single-process

For multiple workers/instances use Redis or another shared session store.

### 4. Authentication/authorization is not implemented

Opaque session IDs reduce accidental fixation but are not user auth.

### 5. `chatbot.py` remains large

It is now protected by policy/service modules, but a future refactor
should move deterministic selected-property fact handling and location
handling into separate services.

### 6. RAG quality depends on the configured Day 2 build

This package intentionally references `DAY2_ROOT` instead of copying Day 2
knowledge into Day 3. Use the finalized Day 2 version whose retrieval and
RAG behavior evaluation passed.

### 7. Large inventory location discovery

The adapter prefers repository-native distinct location methods. When the
Day 2 repository does not expose them, its fallback scan remains bounded.
For large production inventory, add native distinct-list methods to Day 2.

## Recommendation

This build is appropriate as a strong Day 3 capstone layer:

- structured facts are database-grounded
- semantic questions are connected to the verified Day 2 RAG
- conversation memory is isolated and serialized
- capability claims remain honest
- provider failures fail closed

The next architectural expansion should be Day 4 Calendar/Email/n8n/CRM,
not more business logic inside the LLM prompt.
