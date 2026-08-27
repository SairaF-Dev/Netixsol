# Retrieval Strategy — Real Estate Voice Agent

## 1. Purpose

The retrieval layer ensures that Sara answers property-related questions using verified company data.

The system uses three retrieval approaches:

1. **Structured Retrieval** — PostgreSQL
2. **Semantic Retrieval** — RAG / ChromaDB
3. **Recommendation Retrieval** — PostgreSQL + recommendation engine

The LLM must not invent property information.

---

## 2. Retrieval Decision

### Use PostgreSQL when the user asks for structured property data

Examples:

* Find properties under 30 million PKR.
* Show 3-bedroom apartments in Lahore.
* Which properties are available?
* What is the price of DHA-APT-001?
* Show rental apartments in Islamabad.
* Find properties in DHA Phase 6.
* Show available houses with 4 bedrooms.

These queries require exact filtering, sorting, or numerical comparison.

**Source of truth:** PostgreSQL.

---

### Use RAG when the user asks for unstructured knowledge

Examples:

* What amenities does Skyline Residences have?
* Does Skyline Residences have a swimming pool?
* What is the payment plan?
* What are the company's property policies?
* Can Sara guarantee investment returns?
* What documents are required for booking?

These questions are answered using verified knowledge documents indexed in ChromaDB.

**Source of truth:** RAG knowledge base.

---

### Use Recommendation Engine for property recommendations

Examples:

* I have a budget of 40 million. What do you recommend?
* Mujhe Lahore mein 3 bedroom apartment chahiye.
* Show me the best options for investment.
* Which property is best for my family?
* Mere budget mein DHA mein koi achi property hai?

The recommendation engine should first retrieve eligible properties from PostgreSQL and then rank them according to the user's requirements.

**Source of truth:** PostgreSQL + recommendation scoring.

The LLM must not independently select properties that were not returned by the retrieval system.

---

## 3. Source-of-Truth Rules

Property facts must always come from verified company data.

The system must follow these rules:

* Never invent a property.
* Never invent a price.
* Never invent availability.
* Never invent amenities.
* Never invent payment plans.
* Never claim an unavailable property is available.
* Never guarantee investment returns.
* Never generate a property ID that does not exist.
* Never use LLM knowledge as the source of property facts.

If the database or knowledge base does not contain the requested information, Sara should explicitly state that the information is unavailable and offer an appropriate next step.

---

## 4. Structured Retrieval Flow

```text
User Query
    ↓
Intent / Requirement Extraction
    ↓
Structured Filters
    ↓
PostgreSQL
    ↓
Verified Property Records
    ↓
Recommendation / Response Layer
```

Typical filters include:

* budget
* city
* area
* bedrooms
* property type
* purpose
* availability

SQL parameters must always be passed separately from the SQL query.

This prevents SQL injection and keeps the retrieval layer dynamic.

---

## 5. RAG Retrieval Flow

```text
User Query
    ↓
Query Embedding
    ↓
ChromaDB Semantic Search
    ↓
Distance / Relevance Filtering
    ↓
Relevant Knowledge Chunks
    ↓
LLM Response
```

Only sufficiently relevant chunks should be included in the LLM context.

Weak semantic matches must be rejected rather than used as evidence.

---

## 6. Recommendation Flow

```text
User Requirements
       ↓
Requirement Extraction
       ↓
PostgreSQL Filtering
       ↓
Eligible Properties
       ↓
Recommendation Scoring
       ↓
Ranked Properties
       ↓
Sara's Response
```

The recommendation engine must only rank properties returned by PostgreSQL.

For example:

```text
Budget: 40M
City: Lahore
Bedrooms: 3
Purpose: Purchase

        ↓

PostgreSQL

        ↓

Eligible:
- Bahria Grand Apartments — 30.5M
- Horizon Heights Apartment — 36M
- Gulberg Central Residences — 38.5M

        ↓

Recommendation Engine

        ↓

Rank properties according to user preferences
```

---

## 7. Handling No Results

No-result behavior is important because it prevents hallucination.

If PostgreSQL returns no properties:

```text
PostgreSQL
    ↓
0 results
    ↓
Do NOT ask the LLM to invent alternatives
    ↓
Return a controlled no-result response
```

Sara should explain that no matching property was found and, when appropriate, ask whether the user wants to relax one requirement.

For example:

> "I couldn't find an available 3-bedroom property in Lahore within that budget. Would you like me to increase the budget or show 2-bedroom options?"

---

## 8. Handling Unknown Properties

If a user asks:

> "What is the price of ABC Heights?"

and `ABC Heights` does not exist in the verified data:

```text
Property lookup
      ↓
No matching property
      ↓
No price available
      ↓
Do not hallucinate
```

Sara should clearly state that the property could not be found in the company's verified records.

---

## 9. Handling Ambiguous Queries

If the user provides incomplete requirements, the system should not guess critical filters.

Example:

> "Show me a good apartment."

Possible clarification:

> "Sure. What's your preferred city and budget?"

However, unnecessary clarification should be avoided when enough information is already available.

---

## 10. LLM Responsibility

The LLM is responsible for:

* Understanding natural-language requests.
* Extracting user requirements.
* Selecting the appropriate retrieval tool.
* Explaining retrieved results naturally.
* Speaking in human-like UrduLish.
* Asking for clarification when necessary.

The LLM is **not** responsible for:

* Maintaining property records.
* Inventing property data.
* Calculating database availability.
* Deciding whether a property exists.
* Creating unsupported prices or amenities.

---

## 11. Production Principle

The system follows:

**Retrieve first → Verify → Reason → Respond**

Not:

**Reason → Guess → Respond**

This ensures that Sara remains grounded in verified company data and minimizes hallucination risk.
