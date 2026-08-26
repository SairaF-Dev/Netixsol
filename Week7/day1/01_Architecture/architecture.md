
# Real Estate AI Voice Agent (System Architecture)

## 1. Overview

The Real Estate AI Voice Agent is a production-oriented conversational voice
system designed to handle customer calls in natural Pakistani UrduLish.

The system follows this general pipeline:

Customer
→ Telephony
→ Speech-to-Text
→ FastAPI
→ LangGraph
→ LLM + State + Tools
→ Verified Result
→ Response Generation
→ Text-to-Speech
→ Telephony
→ Customer

The architecture separates conversation reasoning from business data and
external actions. The LLM does not act as the source of truth for dynamic
property or appointment information.

---

## 2. High-Level Architecture

```text

                         CUSTOMER
                            │
                            │ Phone Call
                            ▼
                     ┌──────────────┐
                     │  TELEPHONY   │
                     │   PROVIDER   │
                     └──────┬───────┘
                            │
                         Audio
                            │
                            ▼
                     ┌──────────────┐
                     │     STT      │
                     │   Deepgram   │
                     └──────┬───────┘
                            │
                           Text
                            │
                            ▼
                     ┌──────────────┐
                     │   FastAPI    │
                     │   Backend    │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  LangGraph   │
                     │ Orchestration│
                     └──────┬───────┘
                            │
                 ┌──────────┼──────────┐
                 │          │          │
                 ▼          ▼          ▼
              STATE        LLM       TOOLS
                            │
                         OpenAI
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
         PostgreSQL      ChromaDB      Calendar
         Properties        RAG           API
              │             │             │
              └─────────────┼─────────────┘
                            │
                            ▼
                    VERIFIED RESULTS
                            │
                            ▼
                  RESPONSE GENERATION
                            │
                            ▼
                     ┌──────────────┐
                     │     TTS      │
                     │ ElevenLabs   │
                     │     Sia      │
                     └──────┬───────┘
                            │
                          Audio
                            │
                            ▼
                       TELEPHONY
                            │
                            ▼
                         CUSTOMER
````

---

# 3. Component Responsibilities

## 3.1 Telephony

Telephony is responsible for receiving the customer's phone call and
handling the audio connection between the customer and the AI voice agent.

### Responsibilities

* Receive incoming calls
* Stream customer audio
* Send generated audio back to the caller
* Handle call lifecycle
* Detect call termination

The telephony layer should remain separate from the AI reasoning layer.

---

## 3.2 Speech-to-Text (STT)

The Speech-to-Text layer converts the customer's spoken UrduLish into text.

### Planned Technology

**Deepgram**

Example:

```text
Customer says:

"Mujhe DHA mein three crore tak apartment chahiye."

                 ↓

STT

                 ↓

"Mujhe DHA mein three crore tak apartment chahiye."
```

The resulting text is passed to the backend and agent workflow.

---

## 3.3 FastAPI

FastAPI acts as the backend/API boundary of the system.

It receives events from the telephony layer and communicates with the
LangGraph agent.

### Responsibilities

* Telephony webhooks
* API endpoints
* Request validation
* Authentication
* Service coordination
* Health checks
* Integration with external services

FastAPI should not contain the complete agent reasoning logic.

That responsibility belongs to LangGraph.

---

## 3.4 LangGraph

LangGraph is the orchestration layer.

It controls the conversation workflow and maintains the state of the
customer interaction.

A simplified flow is:

```text
Input
  ↓
Intent Detection
  ↓
Requirement Extraction
  ↓
Decision
  ↓
Tool / RAG
  ↓
Validation
  ↓
Response
```

Depending on the customer's request, LangGraph can route to different
operations.

For example:

```text
Customer:
"Mujhe DHA mein three crore ka apartment chahiye."

                ↓

          Intent Detection

                ↓

             Buyer

                ↓

        Property Search Tool

                ↓

           PostgreSQL

                ↓

       Available Properties

                ↓

         Recommendation

                ↓

          Response
```

---

# 4. Conversation State

The agent needs memory during the conversation.

For example:

```text
Customer:
"Mera budget three crore hai."

Agent:
"Ji bilkul."

Customer:
"DHA mein options hain?"

Customer does not repeat the budget.
```

The system should retain:

```text
budget = 3 crore
location = DHA
```

The state can contain:

```text
conversation_history
customer_profile
intent
budget
city
location
property_type
bedrooms
purpose
amenities
selected_property
appointment_status
tool_outputs
```

This allows the agent to understand follow-up statements naturally.

---

# 5. LLM

The LLM is responsible for language understanding and reasoning.

It can:

* Detect customer intent
* Extract requirements
* Understand UrduLish
* Decide which tool is required
* Interpret tool results
* Generate a natural response

Example:

```text
Customer:

"DHA mein koi apartment hai
three crore ke andar?"

             ↓

             LLM

             ↓

Intent:
Buyer

Location:
DHA

Property Type:
Apartment

Budget:
3 crore

             ↓

Property Search Tool
```

### Important

The LLM should **not invent property information**.

For example, if the database does not contain a property's price, the LLM
must not guess the price.

---

# 6. Structured Property Database

Structured property information will be stored in **PostgreSQL**.

Example data:

```text
Property
├── property_id
├── title
├── city
├── location
├── property_type
├── bedrooms
├── bathrooms
├── price
├── availability
├── area
├── amenities
├── developer_id
└── assigned_agent_id
```

SQL is appropriate for questions such as:

```text
DHA mein 3 crore tak apartments?

Lahore mein 1.5 lakh tak rentals?

3 bedrooms ke available apartments?

Available properties under 5 crore?
```

Example:

```sql
SELECT *
FROM properties
WHERE location = 'DHA'
  AND property_type = 'Apartment'
  AND price <= 30000000
  AND availability = TRUE;
```

The result becomes verified context for the LLM.

---

# 7. RAG / ChromaDB

Not every piece of information belongs in SQL.

Company documents such as:

* Property brochures
* FAQs
* Project descriptions
* Payment-plan documents
* Developer information
* Amenity descriptions

can be indexed into a vector database.

Planned vector database:

**ChromaDB**

Pipeline:

```text
Documents
    ↓
Document Loader
    ↓
Chunking
    ↓
Embeddings
    ↓
ChromaDB
    ↓
Retriever
    ↓
Relevant Context
    ↓
LLM
```

Example:

Customer:

> "Is project mein payment plan kya hai?"

This may be answered using RAG if the payment-plan information exists in the
company documents.

---

# 8. Structured Retrieval vs RAG

The system should not use RAG for everything.

### SQL

Use SQL for exact structured information:

```text
Price
Availability
Bedrooms
Property type
Location
Area
Plot size
Assigned agent
```

### RAG

Use RAG for semantic/document information:

```text
Brochures
FAQs
Project descriptions
Developer information
Payment-plan explanations
```

Therefore:

```text
                  Customer Query
                        │
                        ▼
                     LLM
                  /         \
                 /           \
          Structured       Semantic
              │                │
              ▼                ▼
         PostgreSQL         ChromaDB
              │                │
              └───────┬────────┘
                      ▼
                Verified Context
                      │
                      ▼
                  Response
```

---

# 9. Property Recommendation

The recommendation system uses customer requirements to find suitable
properties.

Important criteria include:

```text
Budget
Location
City
Property Type
Bedrooms
Purpose
Amenities
Investment Goal
Availability
```

Example:

```text
Customer Requirements

Budget: 3 crore
Location: DHA
Type: Apartment
Bedrooms: 3
Purpose: Living
```

The system searches the structured property database and ranks matching
available properties.

The agent should preferably present a small number of strong options rather
than reading dozens of properties.

---

# 10. Calendar Integration

Google Calendar is used for appointment management.

The agent should support:

```text
Booking
Rescheduling
Cancellation
Availability Checking
```

### Booking Flow

```text
Customer wants visit
        ↓
Identify property
        ↓
Ask preferred date/time
        ↓
Check Calendar
        ↓
Available?
   ┌────┴────┐
  YES        NO
   ↓          ↓
 Book       Offer
            alternatives
   ↓
Confirmation
```

### Critical Rule

The agent must never say:

> "Your appointment is booked."

until the Calendar operation actually succeeds.

---

# 11. Text-to-Speech

After the LLM generates the final response, the text is converted back into
speech.

Current selected candidate:

**ElevenLabs — Sia, Sweet & Smart Sales Professional**

Example:

```text
LLM Response:

"Ji bilkul, main DHA mein available apartments check karta hoon."

                 ↓

                TTS

                 ↓

             Audio Output

                 ↓

            Telephony

                 ↓

             Customer
```

The response should sound conversational rather than like a prerecorded
advertisement.

---

# 12. Workflow Automation

n8n handles downstream business automation.

The preferred architecture is:

```text
LangGraph
    ↓
Verified Business Event
    ↓
n8n
 ┌───────┼────────┐
 ↓       ↓        ↓
Email   CRM   Notification
```

Example:

```text
Appointment successfully booked
             ↓
          n8n
       /    |    \
      ↓     ↓     ↓
   Employee CRM Customer
    Email   Update Notification
```

n8n should not be used unnecessarily for every conversational action because
that would increase complexity and potentially add latency.

---

# 13. Complete End-to-End Example

### Customer

> "Assalam-o-Alaikum, mujhe DHA mein three crore tak apartment chahiye."

### Step 1: Telephony

Receives the call.

### Step 2: STT

Converts speech into text.

### Step 3: FastAPI

Receives the transcribed request.

### Step 4: LangGraph

Routes the request to the appropriate workflow.

### Step 5: LLM

Extracts:

```text
intent = buyer
location = DHA
budget = 3 crore
property_type = apartment
```

### Step 6: PostgreSQL

Searches verified available properties.

### Step 7: Recommendation

Selects suitable properties.

### Step 8: LLM

Converts the database results into a natural UrduLish response.

### Step 9: TTS

ElevenLabs converts the response into speech.

### Step 10: Telephony

Audio is returned to the customer.

---

# 14. Reliability Principles

The architecture follows these rules:

### Rule 1: LLM is not the database

The LLM should not be trusted for dynamic property facts.

### Rule 2: Tools verify reality

Property availability comes from the property database.

Appointment availability comes from Google Calendar.

### Rule 3: Never guess

If verified information is unavailable, ask, retrieve, or escalate.

### Rule 4: Confirm actions

Booking, rescheduling, and cancellation require successful tool confirmation.

### Rule 5: Maintain context

The customer should not have to repeat information unnecessarily.

### Rule 6: Keep voice responses short

A phone conversation requires concise responses rather than chatbot-style
paragraphs.

---

# 15. Production Architecture Summary

```text
                         CUSTOMER
                            │
                         Phone
                            ▼
                      TELEPHONY
                            │
                            ▼
                          STT
                            │
                            ▼
                         FASTAPI
                            │
                            ▼
                       LANGGRAPH
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
              STATE         LLM        TOOLS
                            │
                    ┌───────┼────────┐
                    ▼       ▼        ▼
                   SQL     RAG    Calendar
                    │       │        │
                    └───────┼────────┘
                            ▼
                     VERIFIED DATA
                            │
                            ▼
                       RESPONSE
                            │
                            ▼
                           TTS
                            │
                            ▼
                       TELEPHONY
                            │
                            ▼
                         CUSTOMER

                            │
                   Business Event
                            ▼
                           n8n
                    ┌───────┼───────┐
                    ▼       ▼       ▼
                  Email    CRM   Notification
```

## Key architectural principle

**The LLM decides what needs to happen; the tools determine what is actually true or what actually happened.**

For example:

> LLM: "Customer wants a 3-bedroom apartment in DHA under 3 crore."

→ PostgreSQL determines **which properties actually match**.

> LLM: "Customer wants a visit Saturday at 3 PM."

→ Google Calendar determines **whether that slot is actually available**.

That's the part that makes this architecture **production-oriented rather than just an LLM chatbot**.
