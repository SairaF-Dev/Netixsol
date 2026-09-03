# Week 7  Day 5: LangGraph Orchestration & Tool Calling

A production-grade AI voice agent orchestration layer that coordinates the complete real estate sales workflow, integrating speech recognition, language understanding, property recommendations, and appointment booking into a unified agent graph.

## 🎯 Goals

✅ Design complete LangGraph state machine  
✅ Build nodes for greeting, intent detection, RAG retrieval, recommendation, and booking  
✅ Wrap Day 4 API as callable tools  
✅ Implement context memory and state persistence  
✅ Handle objections and fallback flows  
✅ Validate state transitions and safety rules  
✅ Create comprehensive test suite  
✅ Document workflow architecture  

## 📋 Features

### State Management
- Conversation history with turn tracking
- User profile (name, phone, preferences, budget)
- Property preferences (location, bedrooms, price range, purpose)
- Current intent and detected entities
- Appointment status and history
- RAG context and confidence scores

### Core Nodes
1. **Greeting** - Welcome and establish context
2. **Intent Detection** - Classify user intent (buyer, renter, investor, etc.)
3. **Clarification** - Ask follow-up questions if needed
4. **RAG Retrieval** - Get property info from knowledge base
5. **Recommendation** - Suggest properties based on preferences
6. **Objection Handling** - Address concerns (price, location, builder)
7. **Booking** - Schedule property visit through Day 4 API
8. **Reschedule** - Modify existing appointment
9. **Cancellation** - Cancel appointment
10. **Goodbye** - End conversation with summary

### Tool Integration
- `search_properties()` - Query property database
- `get_property_details()` - Retrieve specific property
- `book_appointment()` - Call Day 4 API
- `reschedule_appointment()` - Modify appointment
- `cancel_appointment()` - Cancel appointment
- `get_customer_history()` - Retrieve past interactions
- `save_customer_preference()` - Store for future use

### Memory & Context
- Session memory (current conversation)
- Customer memory (preferences, history)
- Property memory (frequently viewed)
- Appointment memory (scheduled visits)

### Safety & Validation
- Never recommend unavailable properties
- Verify appointment slot before booking
- Validate customer contact info
- Prevent duplicate bookings
- Track conversation state transitions

## 🏗️ Architecture

```
Voice Input (Deepgram/Whisper)
    ↓
LangGraph Agent
├─ Greeting Node
├─ Intent Detection Node
├─ RAG Retrieval Node
├─ Recommendation Node
├─ Booking Node (calls Day 4 API)
├─ Objection Handling Node
└─ Goodbye Node
    ↓
Text-to-Speech (Fish Audio/ElevenLabs)
    ↓
Voice Output
```

### State Flow

```
START
  ↓
GREETING → INTENT_DETECTION
  ↓
[Branch based on intent]
  ├─ BUYER → CLARIFICATION → RAG → RECOMMENDATION → BOOKING → GOODBYE
  ├─ RENTER → CLARIFICATION → RAG → RECOMMENDATION → BOOKING → GOODBYE
  ├─ INVESTOR → CLARIFICATION → RAG → RECOMMENDATION → BOOKING → GOODBYE
  ├─ RESCHEDULE → VERIFY_APPOINTMENT → RESCHEDULE → GOODBYE
  └─ CANCEL → VERIFY_APPOINTMENT → CANCELLATION → GOODBYE
  ↓
END
```

## 📦 Project Structure

```
day5/
├── src/day5_langgraph/
│   ├── __init__.py
│   ├── state.py                 # LangGraph StateDict
│   ├── nodes.py                 # Graph node implementations
│   ├── tools.py                 # Tool definitions (property search, booking)
│   ├── graph.py                 # Graph construction and routing
│   ├── memory.py                # Session and customer memory
│   ├── validators.py            # State and transition validation
│   ├── config.py                # Configuration
│   └── callbacks.py             # Logging and monitoring
├── tests/
│   ├── test_state.py
│   ├── test_nodes.py
│   ├── test_graph.py
│   ├── test_tools.py
│   └── test_e2e.py
├── docs/
│   ├── README.md                # This file
│   ├── ARCHITECTURE.md          # Detailed architecture
│   ├── STATE_DESIGN.md          # State machine design
│   ├── NODE_REFERENCE.md        # Node implementations
│   └── EXAMPLES.md              # Usage examples
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Day 4 API running (http://localhost:8004)
- Knowledge base and embeddings from Day 2

### Setup

```powershell
# Navigate to day5
cd day5

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure
Copy-Item .env.example .env
```

### Run Tests

```powershell
pytest -v
```

### Use the Agent

```python
from day5_langgraph.graph import build_agent

# Create agent
agent = build_agent()

# Run conversation
state = {
    "messages": [],
    "user_id": "user_123",
    "user_profile": {},
    "conversation_stage": "greeting"
}

result = agent.invoke(state)
print(result["messages"])
```

## 🔧 Configuration

### Environment Variables

```bash
# LLM
OPENAI_API_KEY=sk_xxx
OPENAI_MODEL=gpt-4-turbo

# Day 4 API
DAY4_API_URL=http://localhost:8004
DAY4_API_KEY=optional-api-key

# Memory
MEMORY_TYPE=in_memory|redis  # Default: in_memory
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO|DEBUG
LOG_FILE=./logs/agent.log

# Agent Config
TEMPERATURE=0.7
MAX_TOKENS=1024
TIMEOUT_SECONDS=30
```

See `.env.example` for full list.

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture and design decisions
- **[STATE_DESIGN.md](docs/STATE_DESIGN.md)** - State machine definition
- **[NODE_REFERENCE.md](docs/NODE_REFERENCE.md)** - All node implementations
- **[EXAMPLES.md](docs/EXAMPLES.md)** - Usage examples and conversational flows

## 🧪 Testing

```powershell
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_graph.py -v

# Run with coverage
pytest --cov=day5_langgraph tests/
```

Tests cover:
- ✅ State transitions
- ✅ Node logic
- ✅ Tool calling
- ✅ Memory management
- ✅ Error handling
- ✅ End-to-end workflows

## 📊 Key Concepts

### LangGraph State

```python
{
    "messages": [{"role": "user", "content": "..."}],
    "user_id": "uuid",
    "user_profile": {
        "name": "Ali Khan",
        "phone": "+923001234567",
        "location": "Karachi",
        "budget": 5000000
    },
    "conversation_stage": "intent_detection",
    "current_intent": "buyer_inquiry",
    "detected_properties": [...],
    "selected_property": {...},
    "appointment": {...},
    "conversation_log": [...]
}
```

### Node Example

```python
def intent_detection_node(state: State) -> State:
    """Detect user intent from conversation."""
    messages = state["messages"]
    last_message = messages[-1]["content"]
    
    # Use LLM to classify
    intent = llm_classify_intent(last_message)
    
    state["current_intent"] = intent
    state["conversation_stage"] = "clarification" if needs_clarification(intent) else "rag"
    
    return state
```

### Tool Example

```python
def book_appointment_tool(
    property_id: int,
    preferred_date: str,
    state: State
) -> dict:
    """Book property visit via Day 4 API."""
    
    day4_url = os.getenv("DAY4_API_URL")
    
    payload = {
        "client_name": state["user_profile"]["name"],
        "client_phone": state["user_profile"]["phone"],
        "property_id": property_id,
        "starts_at": preferred_date,
        ...
    }
    
    response = requests.post(f"{day4_url}/appointments", json=payload)
    return response.json()
```

## 🔗 Integration Points

### With Day 3 (Voice)
- Receives: Audio input, user context
- Sends: LLM response, action (book/reschedule/cancel)

### With Day 2 (RAG & Knowledge Base)
- Uses: ChromaDB embeddings, property database
- Calls: RAG search, property recommendations

### With Day 4 (Appointments)
- Calls: Book, reschedule, cancel endpoints
- Receives: Confirmation, conflict errors, warnings

## 🚨 Error Handling

### Graceful Degradation
- If RAG fails: Fall back to structured property search
- If Day 4 API fails: Ask user to call directly
- If LLM times out: Use rule-based fallback
- If memory fails: Continue with session memory only

### Recovery Flows
```
ERROR → Retry once → Fallback flow → Escalation to human
```

## 📈 Performance

### Latency Targets
- Intent detection: < 500ms
- RAG retrieval: < 1000ms
- Recommendation: < 800ms
- Booking: < 2000ms
- **Total conversation turn: < 3000ms**

### Optimization
- LLM caching for common intents
- RAG index pre-warming
- Connection pooling to Day 4
- Async operations throughout

## 🔐 Security

✅ Input sanitization  
✅ API key management  
✅ Rate limiting  
✅ Conversation logging with PII masking  
✅ Session isolation  
✅ State validation  

## 🎯 Next Steps

1. **Review Architecture**: Read [ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. **Understand State**: Study [STATE_DESIGN.md](docs/STATE_DESIGN.md)
3. **Review Nodes**: Check [NODE_REFERENCE.md](docs/NODE_REFERENCE.md)
4. **Run Tests**: `pytest -v`
5. **Try Examples**: See [EXAMPLES.md](docs/EXAMPLES.md)

---

**Day 5 builds the complete orchestration layer. Ready to start? 🚀**
