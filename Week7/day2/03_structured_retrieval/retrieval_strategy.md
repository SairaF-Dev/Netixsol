# Retrieval Strategy  (Real Estate Voice Agent)

## 1. Purpose

The retrieval layer ensures that Sara answers property-related questions using verified company data.

The system uses three retrieval approaches:

1. **Structured Retrieval** — PostgreSQL
2. **Semantic Retrieval** — RAG / ChromaDB
3. **Recommendation Retrieval** — PostgreSQL + Recommendation Engine

The LLM must never invent property information.

---

## 2. Retrieval Decision

### 2.1 Structured Retrieval — PostgreSQL

Use PostgreSQL when the user asks for exact, structured, filterable, or numerical property information.

Examples:

* Find properties under 30 million PKR.
* Show 3-bedroom apartments in Lahore.
* Which properties are available?
* What is the price of DHA-APT-001?
* Show rental apartments in Islamabad.
* Find properties in DHA Phase 6.
* Show available houses with 4 bedrooms.
* What is the property size?
* What payment plan is associated with property ID DHA-APT-001?

These queries require exact filtering, comparison, sorting, or lookup.

**Source of truth:** PostgreSQL.

---

### 2.2 Semantic Retrieval — RAG / ChromaDB

Use RAG when the user asks about unstructured or descriptive knowledge contained in verified documents.

Examples:

* What amenities does Skyline Residences have?
* Does Skyline Residences have a swimming pool?
* What are the company's property policies?
* Can Sara guarantee investment returns?
* What documents are required for booking?
* Tell me about Skyline Residences.

These questions are answered using verified knowledge documents indexed in ChromaDB.

**Source of truth:** Verified RAG knowledge base.

> Exact numerical or transactional facts should still be retrieved from PostgreSQL when they are available there.

---

### 2.3 Recommendation Retrieval

Use the recommendation engine when the user asks Sara to suggest or compare properties.

Examples:

* I have a budget of 40 million. What do you recommend?
* Mujhe Lahore mein 3 bedroom apartment chahiye.
* Show me the best options for investment.
* Which property is best for my family?
* Mere budget mein DHA mein koi achi property hai?

The recommendation engine should:

1. Extract user requirements.
2. Retrieve eligible properties from PostgreSQL.
3. Filter unavailable or incompatible properties.
4. Score eligible properties.
5. Return ranked candidates.
6. Allow the LLM to explain only those returned candidates.

**Source of truth:** PostgreSQL + recommendation scoring.

The LLM must never independently select a property that was not returned by the recommendation engine.

---

# 3. Source-of-Truth Rules

Property facts must always come from verified company data.

The system must:

* Never invent a property.
* Never invent a price.
* Never invent availability.
* Never invent property size.
* Never invent bedrooms.
* Never invent amenities.
* Never invent payment plans.
* Never claim an unavailable property is available.
* Never generate a property ID that does not exist.
* Never guarantee investment returns.
* Never use the LLM's pretrained knowledge as the source of property facts.

If the requested information does not exist in the verified database or knowledge base, Sara must explicitly state that the information is unavailable.

For example:

> "Verified information is currently unavailable."

---

# 4. Structured Retrieval Flow

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

* Budget
* City
* Area
* Bedrooms
* Property type
* Purpose
* Availability
* Property ID
* Size

SQL parameters must always be passed separately from the SQL query.

This keeps retrieval dynamic and helps prevent SQL injection.

---

# 5. RAG Retrieval Flow

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

Only sufficiently relevant chunks should be passed to the LLM.

A vector database returning a document does **not** automatically mean that the document is valid evidence.

Weak semantic matches must be rejected.

This is especially important for unknown questions.

---

# 6. Recommendation Flow

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

Example:

```text
Budget: 40M
City: Lahore
Bedrooms: 3
Purpose: Purchase

        ↓

PostgreSQL

        ↓

Eligible Properties

- Bahria Grand Apartments
- Horizon Heights Apartment
- Gulberg Central Residences

        ↓

Recommendation Engine

        ↓

Rank according to user preferences

        ↓

Sara explains the ranked results
```

The LLM must not add properties that are absent from the retrieved candidate list.

---

# 7. Handling No Results

No-result behavior is a critical anti-hallucination mechanism.

If PostgreSQL returns zero matching properties:

```text
PostgreSQL
    ↓
0 results
    ↓
Do NOT ask the LLM to invent alternatives
    ↓
Controlled no-result response
```

Sara should explain that no matching property was found and, when appropriate, offer to relax one requirement.

Example:

> "I couldn't find an available 3-bedroom property in Lahore within that budget. Would you like me to increase the budget or show 2-bedroom options?"

Any suggested alternatives must be generated from a new database query, not from the LLM's memory.

---

# 8. Handling Unknown Properties

If the user asks:

> "What is the price of ABC Heights?"

and `ABC Heights` does not exist in the verified data:

```text
Property Lookup
      ↓
No Matching Property
      ↓
No Verified Price
      ↓
Do Not Hallucinate
      ↓
Controlled Response
```

Sara should clearly state that the property could not be found in the company's verified records.

Example:

> "I couldn't find ABC Heights in the company's verified property records."

---

# 9. Handling Ambiguous Queries

If the user provides incomplete requirements, the system should not guess critical filters.

Example:

> "Show me a good apartment."

Sara can ask:

> "Sure. What's your preferred city and budget?"

However, unnecessary clarification should be avoided when enough information is already available.

For example, if the user says:

> "Show me 3-bedroom apartments in Lahore under 40 million."

There is enough information to perform the database search immediately.

---

# 10. LLM Responsibility

The LLM is responsible for:

* Understanding natural-language requests.
* Extracting user requirements.
* Selecting the appropriate retrieval tool.
* Explaining retrieved results naturally.
* Speaking in human-like UrduLish.
* Asking for clarification when necessary.
* Presenting verified retrieval results conversationally.

The LLM is **not** responsible for:

* Maintaining property records.
* Inventing property data.
* Determining whether a property exists.
* Calculating database availability.
* Creating unsupported prices.
* Creating unsupported amenities.
* Creating unsupported payment plans.
* Selecting properties outside the retrieved candidate set.

---

# 11. Retrieval Relevance and Abstention

A successful retrieval system must handle both known and unknown information.

For known information:

```text
Relevant Query
    ↓
Relevant Evidence Retrieved
    ↓
Answer
```

For unsupported information:

```text
Unknown Query
    ↓
No sufficiently relevant evidence
    ↓
Abstain
```

The system must therefore evaluate not only **source-hit accuracy**, but also whether irrelevant or weakly related documents are incorrectly accepted as evidence.

This is important because semantic search will usually return something, even when the requested information does not exist.

---

# 12. Production Retrieval Architecture

The final architecture is:

```text
                         User
                           ↓
                    Sara Voice Agent
                           ↓
                  Intent / Query Router
                           ↓
          ┌────────────────┼────────────────┐
          ↓                ↓                ↓
     Structured        Semantic        Recommendation
      Retrieval         Retrieval         Retrieval
          ↓                ↓                ↓
     PostgreSQL        ChromaDB       PostgreSQL
          ↓                ↓                ↓
       Verified        Verified       Eligible
       Records         Context       Properties
          └────────────────┼────────────────┘
                           ↓
                    Verification Layer
                           ↓
                    Grounded Response
                           ↓
                         Sara
```

---

# 13. Why This Split?

The split between structured and semantic retrieval exists because different information requires different retrieval methods.

### PostgreSQL

Best for:

* Exact prices
* Availability
* Bedrooms
* Property sizes
* Property IDs
* Cities
* Areas
* Numerical filtering
* Sorting
* Recommendations

### ChromaDB / RAG

Best for:

* Brochures
* Descriptions
* FAQs
* Policies
* Natural-language explanations
* Semantic questions

### Recommendation Engine

Best for:

* Budget matching
* Requirement matching
* Candidate ranking
* Multi-criteria property selection

This architecture prevents the LLM from being used as a database.

---

# 14. Core Production Principle

The system follows:

**Retrieve → Verify → Reason → Respond**

Not:

**Reason → Guess → Respond**

The LLM is therefore the conversational layer, not the source of truth.

---

# 15. Day 2 Retrieval Status

### Completed

* [x] Knowledge base created
* [x] Document loader
* [x] Chunking
* [x] Local embeddings
* [x] ChromaDB vector store
* [x] Semantic retriever
* [x] LLM answer generation
* [x] Chunk-size evaluation
* [x] 20-question RAG evaluation
* [x] Retrieval evaluation
* [x] PostgreSQL repository foundation

### Remaining

* [ ] Final PostgreSQL structured queries
* [ ] Structured-vs-semantic query router
* [ ] Recommendation scoring implementation
* [ ] Integration of structured retrieval with the RAG pipeline
* [ ] Final combined evaluation

---

# 16. Current Evaluation Note

The 20-question RAG answer-generation evaluation currently achieved:

```text
Total tests: 20
Passed: 20
Failed: 0
RAG evaluation pass rate: 100%
```

However, the separate retrieval evaluation exposed an important weakness:

```text
Known-source tests: 5
Source hit rate: 100%

Unknown-information tests: 2
Unknown-query pass rate: 0%
```

The two failures occurred because ChromaDB still returned semantically similar documents for unsupported questions.

This does **not** mean that the final RAG answers hallucinated—the answer-generation layer correctly refused both unsupported questions. However, the retrieval layer itself needs improvement before calling the retrieval system production-ready.

The next technical improvement should therefore focus on **better relevance/abstention handling**, rather than artificially changing the evaluation to make the score higher.

---

# 17. Conclusion

The Day 2 system now has a clear retrieval architecture:

* PostgreSQL handles exact structured facts.
* ChromaDB handles semantic knowledge.
* The recommendation engine handles multi-criteria property matching.
* The LLM explains verified results but does not act as the source of truth.
* Unsupported information triggers controlled abstention.
* Retrieved properties are the only properties Sara is allowed to recommend.

The current evaluation demonstrates strong answer-level grounding, while the retrieval evaluation has identified a genuine weakness in unknown-query detection.

This is the correct direction for a production-grade real estate voice agent: **improve the system based on failed tests instead of hiding them.**
