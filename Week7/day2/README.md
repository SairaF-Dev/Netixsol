# Week 7 Day 2 Knowledge Base, RAG & Property Intelligence

## Project Overview

This project implements a verified-data **Retrieval-Augmented Generation (RAG) and property intelligence system** for **Sara**, a real estate AI voice assistant.

The main goal is to prevent hallucination of property information. Sara should answer property-related questions only when the information exists in the verified company knowledge base.

If verified information is unavailable, Sara responds:

> **"Verified information is currently unavailable."**

The system separates **structured retrieval** from **semantic retrieval** so that exact business facts can be handled deterministically while unstructured knowledge can be searched semantically.

---

# Objectives

The Day 2 implementation focuses on:

* Building a real estate knowledge base
* Loading and processing company documents
* Splitting documents into retrieval-friendly chunks
* Generating local embeddings
* Storing embeddings in ChromaDB
* Performing semantic retrieval
* Performing structured SQL retrieval
* Routing queries between structured and semantic retrieval
* Generating grounded answers
* Recommending properties based on user requirements
* Evaluating different chunk sizes
* Evaluating retrieval quality
* Evaluating hallucination behavior

---

# Project Structure

```text
week7_day2/

├── 01_knowledge_base/
│   ├── amenities.csv
│   ├── developers.csv
│   ├── faqs.csv
│   ├── hospitals.csv
│   ├── locations.csv
│   ├── payment_plans.csv
│   ├── prices.csv
│   ├── properties.csv
│   ├── schools.csv
│   └── knowledge_base_schema.md
│
├── 02_rag/
│   ├── documents/
│   │   ├── faqs/
│   │   ├── project_descriptions/
│   │   └── property_brochures/
│   │
│   ├── loader.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── metadata.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── rag_pipeline.py
│   └── test_chroma.py
│
├── 03_structured_retrieval/
│   ├── postgres_repository.py
│   ├── property_queries.sql
│   ├── schema.sql
│   ├── seed.sql
│   ├── retrieval_strategy.md
│   └── test_postgres_repository.py
│
├── 04_recommendation/
│   ├── filters.py
│   ├── scoring.py
│   ├── recommendation_engine.py
│   ├── recommendation_examples.md
│   └── test_recommendation_engine.py
│
├── 05_evaluation/
│   ├── evaluation_questions.csv
│   ├── chunk_evaluation.py
│   ├── retrieval_evaluation.py
│   ├── evaluate_rag.py
│   ├── rag_results.csv
│   └── hallucination_report.md
│
├── 06_documentation/
│   └── day2_report.md
│
└── 07_integration/
    ├── answer_composer.py
    ├── knowledge_router.py
    ├── knowledge_service.py
    ├── query_router.py
    ├── structured_query_parser.py
    └── tests
```

---

# 1. Knowledge Base

The knowledge base contains verified demo company information related to real estate properties.

The datasets cover:

* Properties
* Prices
* Locations
* Amenities
* Schools
* Nearby hospitals
* Payment plans
* Developers
* FAQs

Stable property IDs are used to connect related records across datasets.

The knowledge base is divided into two major information types:

```text
Structured business facts
        +
Unstructured company knowledge
```

Structured data is used for exact property facts, while documents are used for semantic knowledge.

---

# 2. RAG Pipeline

The RAG pipeline consists of:

```text
Documents
    ↓
Document Loader
    ↓
Chunking
    ↓
Embeddings
    ↓
ChromaDB Vector Store
    ↓
Semantic Retriever
    ↓
Relevant Context
    ↓
LLM
    ↓
Grounded Answer
```

Implemented components include:

* Document loader
* Markdown document processing
* Sentence-aware chunking
* Local Sentence Transformer embeddings
* Persistent ChromaDB vector store
* Incremental indexing
* Semantic retrieval
* Distance-based relevance filtering
* Grounded answer generation

---

# 3. Document Loader

The document loader reads verified company documents from the `02_rag/documents/` directory.

The current document knowledge base contains:

```text
4 documents
```

These include:

* Property brochures
* Project descriptions
* FAQs

---

# 4. Chunking

Documents are divided into smaller retrieval-friendly chunks.

The chunking strategy:

* Preserves useful context
* Keeps headings with their content
* Splits large sections using sentences
* Avoids unnecessary sentence breaks
* Supports sentence overlap

## Chunk-size Evaluation

Three chunk sizes were evaluated:

| Chunk Size | Chunks | Top-3 Source Hit Rate |
| ---------: | -----: | --------------------: |
|        256 |     18 |                  100% |
|        512 |     11 |                  100% |
|       1024 |      9 |                  100% |

All three configurations achieved a **100% top-3 source hit rate** on the current chunk evaluation questions.

### Selected Configuration

```text
Chunk size: 512
Overlap: 1 sentence
```

512 was selected as the current configuration because it provides a practical balance between contextual completeness and retrieval granularity.

Because the current dataset is small, this choice should be re-evaluated as the production knowledge base grows.

---

# 5. Embeddings

The system uses a local **Sentence Transformer** embedding model.

Documents and user queries are converted into numerical vectors so that semantic similarity can be measured.

The embedding model runs locally, avoiding the need to send company knowledge-base documents to an external embedding API.

The same embedding model is used for:

```text
Documents → document embeddings

User query → query embedding
```

---

# 6. ChromaDB Vector Store

**ChromaDB** is used as the persistent vector database.

Each indexed chunk stores:

* Chunk ID
* Document text
* Source document
* Document hash
* Property name
* Property ID
* Document type
* Embedding

Cosine distance is used for semantic similarity.

## Incremental Indexing

The vector store uses document content hashing to detect changes.

```text
New document
    ↓
Embed + index

Unchanged document
    ↓
Skip

Changed document
    ↓
Delete old chunks
    ↓
Re-embed
    ↓
Insert updated chunks
```

Testing confirmed that unchanged documents are skipped and modified documents are re-indexed.

---

# 7. Semantic Retriever

The retriever performs semantic search against ChromaDB.

Example:

```text
User:
What amenities are listed for Horizon Heights Apartment?

        ↓

Semantic Retriever

        ↓

skyline_residences.md

        ↓

Relevant verified context

        ↓

LLM

        ↓

Grounded answer
```

A cosine-distance threshold is used to remove weak semantic matches.

However, semantic retrieval has an important limitation:

> A vector database always attempts to return the closest available documents. A close vector distance does not guarantee that the requested fact actually exists in the retrieved document.

This was identified during the retrieval evaluation.

---

# 8. Structured Retrieval

Structured retrieval was implemented separately from semantic retrieval.

PostgreSQL is used as the source of truth for exact property facts.

Structured retrieval is appropriate for:

* Property ID
* Price
* Availability
* Bedrooms
* Property size
* Location
* Developer
* Amenities
* Other exact business fields

Example:

```text
User:
What is the price of LHR-DHA-APT-001?

        ↓

Structured Query Parser

        ↓

PostgreSQL

        ↓

Exact property record

        ↓

Verified answer
```

This avoids relying on semantic similarity for business-critical numeric or categorical information.

---

# 9. Structured vs Semantic Retrieval

The system follows this retrieval strategy:

| Information Type                    | Retrieval Method |
| ----------------------------------- | ---------------- |
| Price                               | SQL              |
| Availability                        | SQL              |
| Property ID                         | SQL              |
| Bedrooms                            | SQL              |
| Property size                       | SQL              |
| Exact location                      | SQL              |
| Exact developer                     | SQL              |
| Brochures                           | RAG              |
| Project descriptions                | RAG              |
| FAQs                                | RAG              |
| Natural-language semantic questions | RAG              |

The split is important because:

**SQL provides deterministic retrieval and filtering**, while **vector retrieval provides semantic matching over unstructured documents**.

For exact business facts, deterministic structured retrieval is preferred.

---

# 10. Recommendation Engine

The recommendation engine supports property matching based on:

* Budget
* City
* Area
* Bedrooms
* Purpose
* Amenities
* Investment goals

The recommendation flow is:

```text
User Requirements
        ↓
Property Filters
        ↓
Available Properties
        ↓
Scoring
        ↓
Ranking
        ↓
Recommendations
```

Unavailable properties are filtered out before scoring.

Investment goals are supported as a grounded ranking preference using verified purpose/property-type facts. The system does not invent financial performance or guarantee investment returns.

---

# 11. Integration Layer

The integration layer connects the different knowledge sources.

The architecture separates:

```text
User Query
    ↓
Query Router
    ↓
Knowledge Router
    ├── Structured Retrieval
    │       ↓
    │   PostgreSQL
    │
    └── Semantic Retrieval
            ↓
        ChromaDB
    ↓
Knowledge Service
    ↓
Answer Composer
    ↓
Grounded Response
```

This allows Sara to use the appropriate retrieval mechanism depending on the type of question.

---

# 12. LLM Answer Generation

Retrieved verified context is passed to the LLM together with strict grounding instructions.

The assistant is instructed to:

1. Never invent property details.
2. Never invent prices or availability.
3. Never invent amenities or payment plans.
4. Never guarantee investment returns.
5. Use verified company information only.
6. Refuse unsupported questions.

Example:

### Question

```text
What amenities are listed for Horizon Heights Apartment?
```

### Answer

```text
The amenities listed for Horizon Heights Apartment include parking,
a shared swimming pool, a shared gym, and 24/7 security.
```

---

# 13. Hallucination Evaluation

A 20-question RAG evaluation set was created.

The evaluation covers:

* Property amenities
* Prices
* Developers
* Locations
* Bedrooms
* Availability
* Payment plans
* Investment returns
* Hospitals
* Unsupported amenities
* Nonexistent properties
* UrduLish queries

## RAG Evaluation Results

| Metric                    |   Result |
| ------------------------- | -------: |
| Total Questions           |       20 |
| Passed                    |       20 |
| Failed                    |        0 |
| RAG Evaluation Pass Rate  | **100%** |
| Grounding Rate            | **100%** |
| Answer Hallucination Rate |   **0%** |

All 20 tests passed.

Supported questions produced grounded answers, while unsupported questions produced the controlled refusal.

---

# 14. Correct Refusal Behavior

The system correctly refuses to answer when verified information is unavailable.

Examples include:

```text
What payment plan is available for LHR-DHA-APT-001?
```

```text
What is the nearest hospital to Horizon Heights Apartment?
```

```text
What is the guaranteed annual return of Horizon Heights Apartment?
```

```text
Does Horizon Heights Apartment have a tennis court?
```

```text
What is the price of Moonlight Towers?
```

The assistant responds:

```text
Verified information is currently unavailable.
```

This is intentional behavior and is a central part of the anti-hallucination design.

---

# 15. Retrieval Evaluation

Known-source retrieval tests achieved:

```text
Known-source tests: 5
Correct source retrievals: 5
Source hit rate: 100%
```

The retriever successfully identified the expected source documents for all tested known-information queries.

However, two intentionally unsupported queries exposed a limitation in the current semantic retriever.

```text
Unknown-information tests: 2
Correctly rejected: 0
Unknown-query rejection rate: 0%
```

The overall retrieval evaluation was:

```text
Total tests: 7
Tests passed: 5
Tests failed: 2
Overall retrieval evaluation: 71.43%
```

The failures occurred because semantic retrieval returned the closest available documents even though those documents did not contain the requested facts.

This does **not** mean the final RAG system hallucinated. The complete 20-question RAG evaluation correctly refused those unsupported questions.

---

# 16. Retrieval vs. Grounding

The evaluation demonstrates an important distinction:

```text
Retrieval similarity
        ≠
Factual correctness
```

The retriever may return semantically similar context for an unsupported question.

The answer-generation layer must therefore verify whether the retrieved context actually supports the requested fact.

The current pipeline behaves as:

```text
Query
  ↓
Retrieve
  ↓
Verify available evidence
  ↓
Supported? ── Yes ──→ Generate grounded answer
     │
     No
     ↓
Abstain
```

This design is responsible for the successful 20/20 RAG evaluation.

---

# 17. Design Principles

### Verified Data First

Property information must come from verified company data.

### Structured Facts Use SQL

Exact business-critical values should come from deterministic structured retrieval.

### Semantic Knowledge Uses RAG

Brochures, descriptions, and FAQs are better suited to semantic retrieval.

### Retrieval Before Generation

The LLM receives retrieved evidence before generating an answer.

### No Unsupported Claims

The LLM must not fill missing information with guesses.

### Explicit Refusal

When verified information is unavailable, the system returns a controlled refusal.

### Traceability

Retrieved chunks retain source and metadata information.

### Incremental Indexing

Unchanged documents are skipped to avoid unnecessary re-embedding.

---

# 18. Running the RAG Pipeline

Activate the virtual environment:

```powershell
.venv\Scripts\activate
```

Navigate to the RAG directory:

```powershell
cd 02_rag
```

Run:

```powershell
python rag_pipeline.py
```

The pipeline loads documents, synchronizes the ChromaDB index, retrieves context, and generates answers for the configured questions.

---

# 19. Running ChromaDB Tests

From the RAG directory:

```powershell
python test_chroma.py
```

The test verifies:

* Vector-store indexing
* Embedding generation
* Semantic retrieval
* ChromaDB search

Expected result:

```text
PASS: semantic retrieval works
```

---

# 20. Running Chunk-size Evaluation

Navigate to the evaluation directory:

```powershell
cd ..\05_evaluation
```

Run:

```powershell
python chunk_evaluation.py
```

This evaluates:

```text
256
512
1024
```

and reports:

* Number of chunks
* Overlap
* Evaluation questions
* Top-3 source hit rate

---

# 21. Running Retrieval Evaluation

From `05_evaluation`:

```powershell
python retrieval_evaluation.py
```

This evaluates:

* Known-source retrieval
* Unknown-information retrieval
* Source hit rate
* Unknown-query rejection
* Overall retrieval performance

The current measured result is:

```text
Known-source source hit rate: 100%
Unknown-query rejection rate: 0%
Overall retrieval evaluation: 71.43%
```

---

# 22. Running Full RAG Evaluation

Run:

```powershell
python evaluate_rag.py
```

Expected current result:

```text
Total tests: 20
Tests passed: 20
Tests failed: 0
RAG evaluation pass rate: 100.00%
```

The current evaluation also reports:

```text
Grounding Rate: 100%
Answer Hallucination Rate: 0%
```

---

# 23. Current Status

### Completed

* [x] Knowledge base
* [x] Document loader
* [x] Chunking
* [x] Local embeddings
* [x] ChromaDB vector store
* [x] Incremental indexing
* [x] Semantic retriever
* [x] LLM integration
* [x] Grounded answer generation
* [x] Chunk-size evaluation
* [x] Structured PostgreSQL retrieval
* [x] Structured query parser
* [x] Retrieval routing
* [x] Recommendation engine
* [x] Retrieval evaluation
* [x] 20-question RAG evaluation
* [x] Hallucination evaluation
* [x] Safe refusal behavior

### Remaining Improvements

* [ ] Improve unknown-query rejection
* [ ] Add stronger hybrid retrieval
* [ ] Add reranking for semantic results
* [ ] Expand adversarial evaluation
* [ ] Perform final end-to-end evaluation after integration with the voice agent

---

# 24. Final Evaluation Summary

The current system has demonstrated:

```text
Known-source Retrieval Accuracy:   100%
Chunk Evaluation Top-3 Hit Rate:   100%
RAG Evaluation Pass Rate:          100%
Grounding Rate:                    100%
Answer Hallucination Rate:           0%

Overall Retrieval Evaluation:       71.43%
Unknown-query Rejection Rate:        0%
```

The **100% grounding and 0% hallucination results** are based on the complete 20-question RAG evaluation.

The **71.43% retrieval evaluation** identifies a separate weakness: pure semantic retrieval can return nearby documents for unsupported questions.

This is why exact business facts should be handled through structured retrieval wherever possible.

---

# 25. Conclusion

Week 7 Day 2 successfully established the verified knowledge and property-intelligence foundation for Sara.

The implementation now contains:

* A structured real estate knowledge base
* Document-based semantic knowledge
* Local embeddings
* Persistent ChromaDB retrieval
* Incremental indexing
* Structured PostgreSQL retrieval
* Retrieval routing
* Property recommendation
* Grounded answer generation
* Retrieval evaluation
* Chunk-size evaluation
* Hallucination evaluation
* Safe refusal behavior

The strongest result is the **20/20 RAG evaluation with 100% grounding and 0% answer hallucination**.

The main remaining technical weakness is **unknown-query rejection at the retrieval layer**. This should be improved before treating the retrieval system as production-grade.

The next phase is to connect these verified retrieval and recommendation capabilities to the **LangGraph real estate voice agent**, allowing Sara to combine structured facts, semantic knowledge, recommendations, workflows, and voice interaction in a single production-oriented system.


## Senior-fixed source authority

- PostgreSQL owns exact structured property facts.
- RAG owns FAQs, brochure summaries, descriptions, and semantic company knowledge.
- `python 02_rag/validate_documents.py` validates semantic documents.
- `python src/data_validation.py` validates CSV relationships and developer project names.
- RAG evaluation uses canonical IDs/names from the structured knowledge base.
