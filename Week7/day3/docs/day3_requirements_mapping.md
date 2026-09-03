# Week 7 Day 3 Requirement Mapping

## Task 1 — Voice Pipeline

Implemented:
- `src/sara_agent/voice.py`
- `/voice/turn`
- STT / agent / TTS stage latency
- bounded audio size
- provider timeout/retry configuration
- empty-transcript recovery
- sync provider work off FastAPI event loop
- voice-friendly shorter property batches

Accurately not implemented:
- true audio/token streaming
- barge-in / TTS cancellation
- telephony transport

## Task 2 — Natural Conversation

Implemented:
- open-ended Sara greeting
- Purpose → City → Budget → Area default requirement flow
- one useful missing requirement at a time
- corrections and constraint relaxation
- verified fuzzy location typo recovery
- safe number/ordinal option selection
- progressive result batches
- repeat/reset/human-escalation controls
- grounded no-result recovery
- concise UrduLish responses

## Task 3 — Context Memory

Implemented:
- hard requirements
- soft preferences
- exclusions
- explicit flexible fields
- selected result references
- result pagination
- stale-result invalidation
- city-change area invalidation
- per-session memory isolation
- same-session turn serialization

## Task 4 — Objection Handling

Implemented in `objections.py`.

Responses may reuse freshly re-read structured facts while avoiding:
- guaranteed ROI
- future appreciation claims
- unsupported developer reputation
- invented maintenance facts

## Task 5 — Human Evaluation

Included:
- `evaluation/human_evaluation.csv`
- `evaluation/latency_targets.md`

## Verified source integration

### PostgreSQL
Used for:
- prices/availability
- property facts
- amenities
- developers
- payment plans
- nearby schools/hospitals
- assigned agents

### RAG
Concrete lazy connection implemented through:
- `src/sara_agent/day2_rag_service.py`
- `src/sara_agent/rag_bridge.py`

RAG uses the finalized Day 2 `02_rag/rag_pipeline.py`.

It is appropriate for:
- FAQs
- brochures
- project descriptions
- company/process knowledge

If Day 2 query policy says a question requires PostgreSQL, RAG fails
closed rather than becoming a second source for that structured fact.

## Scheduling

Scheduling intents remain Day 4 handoffs. Day 3 never fabricates final
calendar confirmation.
