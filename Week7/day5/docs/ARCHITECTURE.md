# Day 5 Architecture & Design

## Overview

Day 5 implements the orchestration layer that coordinates all components (Day 2 RAG, Day 3 voice, Day 4 appointments) into a unified AI voice agent using LangGraph.

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Voice Input Layer (Day 3)                │
│                  (Deepgram/Whisper/AssemblyAI)               │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│              LangGraph Agent (Day 5 - THIS)                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Conversation State Machine                              │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │ • User Profile & Preferences                     │   │ │
│  │  │ • Conversation History & Context                 │   │ │
│  │  │ • Current Intent & Entities                      │   │ │
│  │  │ • Detected Properties & Selected Property        │   │ │
│  │  │ • Appointment Status                             │   │ │
│  │  │ • Errors & Warnings                              │   │ │
│  │  └──────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Graph Nodes (State Processors)                          │ │
│  │  ├─ Greeting: Welcome & establish rapport              │ │
│  │  ├─ Intent Detection: Classify user intent              │ │
│  │  ├─ Clarification: Gather missing info                 │ │
│  │  ├─ RAG Retrieval: Search knowledge base               │ │
│  │  ├─ Recommendation: Suggest properties                 │ │
│  │  ├─ Objection Handling: Address concerns               │ │
│  │  ├─ Booking: Schedule visit (calls Day 4)              │ │
│  │  ├─ Reschedule: Modify appointment (calls Day 4)       │ │
│  │  ├─ Cancellation: Cancel appointment (calls Day 4)     │ │
│  │  └─ Goodbye: End conversation & summarize              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Tools (External Service Calls)                          │ │
│  │  ├─ search_properties() → Day 2 RAG                     │ │
│  │  ├─ book_appointment() → Day 4 API                      │ │
│  │  ├─ reschedule_appointment() → Day 4 API               │ │
│  │  ├─ cancel_appointment() → Day 4 API                   │ │
│  │  └─ get_customer_history() → PostgreSQL                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Memory Management                                       │ │
│  │  ├─ Session Memory (current conversation)              │ │
│  │  ├─ Customer Memory (preferences, history)             │ │
│  │  └─ Context Memory (RAG results, entities)             │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │  LLM (GPT-4/Claude)      │
    │  for intent detection    │
    │  and response generation │
    └──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│           Text-to-Speech Output Layer (Day 3)               │
│              (Fish Audio / ElevenLabs)                       │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
         Voice Output
```

## State Machine Design

### Core States

```
┌─────────┐
│ START   │
└────┬────┘
     │
     ▼
┌─────────────────┐
│ GREETING        │ → Welcome user, establish rapport
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ INTENT          │ → Classify user intent (buyer/renter/investor)
│ DETECTION       │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ CLARIFICATION   │ → Gather missing information
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ RAG             │ → Search property knowledge base
│ RETRIEVAL       │
└────┬────────────┘
     │
     ▼
┌──────────────────────┐
│ RECOMMENDATION       │ → Recommend matching properties
└────┬─────────────────┘
     │
     ├─► BOOKING ─────────────► GOODBYE ──┐
     │                                      │
     ├─► OBJECTION ────► BOOKING ──► GOODBYE
     │                                     │
     ├─► RESCHEDULE ─────► GOODBYE ──┐    │
     │                                │    │
     └─► CANCELLATION ─── GOODBYE ────┴────┴──► END
```

### Transition Logic

```
GREETING
  ↓
INTENT_DETECTION
  ├─ intent in {BUYER, RENTER, INVESTOR, COMMERCIAL} → CLARIFICATION
  ├─ intent = RESCHEDULE → RESCHEDULE
  ├─ intent = CANCEL → CANCELLATION
  └─ intent = OFF_TOPIC → GOODBYE

CLARIFICATION
  ├─ all required info collected → RAG_RETRIEVAL
  └─ still needs info → stay in CLARIFICATION

RAG_RETRIEVAL
  ├─ properties found → RECOMMENDATION
  └─ no properties → GOODBYE

RECOMMENDATION
  ├─ user accepts property → BOOKING
  ├─ user has objections → OBJECTION_HANDLING
  └─ user not interested → GOODBYE

OBJECTION_HANDLING
  ├─ objection addressed → RECOMMENDATION
  └─ cannot address → GOODBYE

BOOKING
  ├─ successfully booked → GOODBYE
  ├─ conflict detected → propose alternative
  └─ booking failed → GOODBYE

RESCHEDULE/CANCELLATION
  ├─ successfully completed → GOODBYE
  └─ failed → GOODBYE

GOODBYE
  → END
```

## State Schema

```python
class AgentState:
    # Session
    session_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Conversation
    messages: List[Message]  # Full conversation history
    conversation_stage: ConversationStage
    
    # User
    user_profile: UserProfile
        - name, phone, email
        - location, budget_min, budget_max
        - bedrooms, purpose (buy/rent/invest)
        - preferences, history
    
    # Current Interaction
    current_intent: UserIntent
    intent_confidence: float
    clarification_needed: bool
    clarification_questions: List[str]
    
    # Properties
    detected_properties: List[PropertyMatch]
    selected_property: PropertyMatch
    rag_context: str
    rag_confidence: float
    
    # Booking
    appointment: Appointment
    proposed_datetime: str
    booking_status: str
    
    # Objections
    objections: List[str]
    objection_responses: List[str]
    
    # Metadata
    conversation_log: List[dict]
    errors: List[str]
    warnings: List[str]
```

## Node Implementations

### Greeting Node
```python
def greeting_node(state: AgentState) -> dict:
    # Generate warm greeting in UrduLish
    # Establish rapport
    # Transition → INTENT_DETECTION
```

### Intent Detection Node
```python
def intent_detection_node(state: AgentState) -> dict:
    # Parse user message
    # Use LLM to classify intent
    # Extract entities (budget, location, etc.)
    # Decide next stage based on intent
```

### Clarification Node
```python
def clarification_node(state: AgentState) -> dict:
    # Identify missing information
    # Generate clarification questions
    # Ask for missing fields one by one
    # Transition → RAG when complete
```

### RAG Retrieval Node
```python
async def rag_retrieval_node(state: AgentState) -> dict:
    # Build search query from user preferences
    # Call Day 2 knowledge base
    # Filter properties
    # Store results in state
    # Transition → RECOMMENDATION
```

### Recommendation Node
```python
async def recommendation_node(state: AgentState) -> dict:
    # Score properties based on user preferences
    # Select best match
    # Generate persuasive recommendation
    # Transition → BOOKING or ask for clarification
```

### Booking Node
```python
async def booking_node(state: AgentState) -> dict:
    # Propose date/time (using calendar availability)
    # Confirm user details
    # Call Day 4 API to create appointment
    # Handle errors (slot conflict, validation failures)
    # Transition → GOODBYE
```

## Tool Integration

### Tool Executor Pattern

```python
class ToolExecutor:
    async def execute(self, tool_name: str, **kwargs) -> dict:
        # Route to appropriate tool
        # Call Day 4 API or knowledge base
        # Handle errors gracefully
        # Return structured result
```

### Available Tools

1. **search_properties(location, min_price, max_price, bedrooms, purpose)**
   - Calls Day 2 RAG pipeline
   - Returns list of PropertyMatch objects

2. **book_appointment(client_name, phone, property_id, starts_at)**
   - Calls Day 4 POST /appointments
   - Returns confirmation or error

3. **reschedule_appointment(appointment_id, starts_at)**
   - Calls Day 4 PATCH /appointments/{id}/reschedule
   - Returns updated appointment or error

4. **cancel_appointment(appointment_id)**
   - Calls Day 4 DELETE /appointments/{id}
   - Returns confirmation or error

5. **get_customer_history(phone, limit)**
   - Queries PostgreSQL for past appointments
   - Returns historical appointments

## Memory Management

### Session Memory
- Stores current conversation state
- Resets on new session
- Size-limited (max 50 messages)

### Customer Memory
- Persistent customer preferences
- Appointment history
- Stored in PostgreSQL
- Keyed by phone number

### Context Memory
- RAG search results
- Extracted entities
- Active conversation context
- TTL-based cleanup

## Error Handling Strategy

### Graceful Degradation

```
Tool Call Fails
    │
    ├─ Retry once (with backoff)
    │
    ├─ If still fails:
    │   ├─ For RAG failures → Use rule-based search
    │   ├─ For Day 4 failures → Ask user to call directly
    │   ├─ For LLM failures → Use template-based responses
    │   └─ For memory failures → Continue without history
    │
    └─ Log error, continue conversation
```

### Recovery Flows

```
Intent Detection Fails
  → Ask user to clarify intent

RAG Returns No Results
  → Offer to search by different criteria

Property Booking Fails
  → Propose alternative dates
  → Offer to take manual booking

User Provides Invalid Info
  → Re-ask for that specific field
  → Provide format hints
```

## Validation Rules

### Input Validation
- Phone number format and length
- Email address validity
- Budget values (must be positive)
- Timezone-aware datetime
- Property ID exists

### State Transitions
- Can only transition to valid next states
- Cannot skip required stages
- Cannot go backwards (generally)
- Validate data completeness before transition

### Safety Rules
- Never book unavailable slots
- Never recommend unavailable properties
- Prevent duplicate bookings
- Validate user contact info
- Rate-limit API calls

## Performance Optimization

### Caching Strategy
```
LLM Intent Classifications
  → Cache common phrases
  → TTL: 1 hour

Property Search Results
  → Cache for same user profile
  → TTL: 30 minutes

Customer History
  → Cache per phone number
  → TTL: 24 hours
```

### Async Operations
- All I/O operations are async
- Parallel tool execution when safe
- Connection pooling for databases
- Timeout enforcement (30s per call)

### Latency Targets
```
Greeting:           < 500ms
Intent Detection:   < 500ms
Clarification:      < 300ms
RAG Retrieval:      < 1000ms
Recommendation:     < 800ms
Booking:            < 2000ms
────────────────────────────
Total per turn:     < 3000ms
```

## Integration Boundaries

### With Day 2 (RAG)
```
Day 5 (Agent) → search_properties() → Day 2 (RAG)
                                      └─ ChromaDB
                                      └─ Property DB
                                      └─ Recommendation Engine
Day 5 ← PropertyMatch[] ← Day 2
```

### With Day 3 (Voice)
```
Voice Input → Day 5 (Agent) ← Streaming Audio
             ├─ Intent Detection
             ├─ Property Search
             └─ Booking
             ↓
      Text Response → Text-to-Speech → Voice Output
```

### With Day 4 (Appointments)
```
Day 5 (Agent) → POST /appointments → Day 4 (Workflows)
                                     ├─ Calendar Availability Check
                                     ├─ Create Event
                                     └─ Send Email
                ← Appointment{} ←
```

## Scalability Considerations

### Horizontal Scaling
- Stateless node processing (state in external memory)
- Distributed session store (Redis)
- Load balancer for API endpoints
- Message queue for async tasks

### Vertical Scaling
- Connection pooling
- Caching layers
- Index optimization
- Query optimization

### Cost Optimization
- Batch LLM calls where possible
- Reuse embeddings
- Cache frequently accessed data
- Monitor token usage

---

**Next**: Review [STATE_DESIGN.md](STATE_DESIGN.md) for detailed state machine design
