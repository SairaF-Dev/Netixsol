# Day 3 Production Architecture

## Grounding principle

> **LLM decides what the user means; verified data decides what is true.**

## Runtime flow

```text
CLI / Streamlit / REST / Voice
              ↓
      Conversation controls
              ↓
 Deterministic safe fact handlers
              ↓
     Semantic NLU (OpenRouter)
              ↓
 Verified location normalization
              ↓
 Conversation State + Query Planner
              ↓
        Source-of-truth routing
              ↓
┌─────────────────────────────┬─────────────────────────────┐
│ Day 2 PostgreSQL            │ Day 2 RAG                   │
│ structured mutable facts    │ semantic knowledge          │
│                             │                             │
│ price                       │ FAQ/policy                  │
│ availability                │ brochure overview           │
│ bedrooms / size             │ project description         │
│ amenities                   │ company/process knowledge   │
│ developer                   │                             │
│ payment plans               │                             │
│ schools / hospitals         │                             │
│ assigned agents             │                             │
└─────────────────────────────┴─────────────────────────────┘
              ↓
        Grounded formatter
              ↓
       Optional OpenAI TTS
```

## Dependency composition

`SaraRuntime` is the single composition point for:

- shared `Day2Adapter`
- shared lazy Day 2 RAG service
- per-conversation `SaraChatbot`

Each chatbot gets independent memory and an internal turn lock.

## Day 2 RAG connection

`Day2RAGService` loads:

```text
DAY2_ROOT/02_rag/rag_pipeline.py
```

only when RAG is first needed.

This deliberately reuses Day 2's own loader/chunker/embeddings/vector
store/retriever/query policy instead of creating a second competing RAG
implementation in Day 3.

If Day 2 returns:

```text
structured_fact_requires_postgresql
```

Sara treats that as no RAG answer and keeps the structured-data boundary.

## Conversation collection policy

Default missing-field order:

1. Purpose
2. City
3. Budget
4. Area

The order is slot-driven. Existing user-supplied values are skipped.

Budget comes before area so area choices can be filtered against actual
verified affordable inventory.

## Session/concurrency model

REST chat/voice uses opaque session IDs and a bounded TTL session store.

Each bot serializes its own turns using an `RLock`, preventing concurrent
requests for the same session from racing conversation-state mutations.

Different sessions remain independent.

For multi-worker/multi-instance production deployment, move session state
to Redis or another shared backend.

## Health model

- `/health` = lightweight process liveness
- `/ready` = dependency readiness with a live PostgreSQL `SELECT 1` check

Liveness never requires database/provider initialization.

## Voice status

Current implementation:

```text
audio upload → STT → Sara → TTS
```

It is turn-based.

Implemented:
- bounded audio upload
- provider timeout/retry limits
- empty-transcript recovery
- sync SDK calls off FastAPI event loop
- per-stage latency metrics

Not implemented:
- true audio streaming
- barge-in
- TTS cancellation
- telephony transport

## Scheduling boundary

Day 3 recognizes booking/reschedule/cancel requests and creates a pending
action only.

Day 4 must perform actual Calendar/Email/CRM/n8n work before a booking is
reported as confirmed.
