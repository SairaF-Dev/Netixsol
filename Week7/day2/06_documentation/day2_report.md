# Week 7 — Day 2 Report

## Knowledge Base, RAG & Property Intelligence

### Objective

Build the verified-data foundation required to prevent the real estate
voice agent from hallucinating property details.

### 1. Knowledge Base

Created datasets for:

- Properties
- Prices
- Locations
- Amenities
- Schools
- Hospitals
- Payment plans
- Developers
- FAQs

The datasets use stable property IDs so related records can be joined.

### 2. RAG Pipeline

Implemented modular components for:

```text
Loader
→ Chunker
→ Embedding
→ Vector Store
→ Retriever
→ Answer-generation interface
```

The prototype includes local deterministic embeddings and a simple vector
store so the retrieval pipeline can be tested without requiring an
external API.

For production, the embedding and vector-store layers should be
replaced with the selected production providers.

### 3. Chunk Size Evaluation

The evaluation compares:

```text
256 characters
512 characters
1024 characters
```

The purpose is to measure the effect of chunk size on retrieval quality.

The final chunk size should be selected using measured retrieval results
rather than assuming that one size is universally best.

### 4. Structured vs Semantic Retrieval

SQL is used for exact business facts such as:

- Price
- Availability
- Bedrooms
- Property size
- Property ID

RAG is used for:

- Brochures
- Descriptions
- FAQs
- Semantic amenity/project information

This split is important because SQL provides deterministic filtering,
while vector retrieval is better for semantic matching.

### 5. Recommendation Engine

The recommendation engine supports:

- Budget
- City
- Area
- Bedrooms
- Purpose
- Amenities

It filters unavailable properties and ranks the remaining candidates.

Investment goals are included in the interface for future business-rule
scoring; the system does not invent financial performance or guarantee
returns.

### 6. Hallucination Evaluation

A 20-question evaluation set was created covering:

- Exact factual questions
- Semantic questions
- FAQ questions
- Guardrail questions
- An intentionally unsupported question

Metrics defined:

```text
Retrieval Accuracy
Grounding Rate
Hallucination Rate
```

The final grounding and hallucination metrics must be calculated against
actual generated LLM responses. Retrieval source-hit testing alone is
not sufficient to claim a hallucination rate.

### 7. Reliability Policy

The central policy is:

> If verified company data does not contain the answer, the agent must
> abstain instead of guessing.

### 8. Day 2 Outcome

The project now has the knowledge and retrieval foundation required for
the next stage: connecting the verified retrieval and recommendation
tools to the LangGraph voice agent.
