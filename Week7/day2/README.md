# Week 7 Day 2  Knowledge Base, RAG & Property Intelligence

## Project Overview

This project implements a verified-data **Retrieval-Augmented Generation (RAG) pipeline** for **Sara**, a real estate AI voice assistant.

The main goal is to prevent hallucination of property information. Sara should answer property-related questions only when the information exists in the verified company knowledge base.

If verified information is unavailable, Sara responds:

> **"Verified information is currently unavailable."**

---

## Objectives

The Day 2 implementation focuses on:

* Building a real estate knowledge base
* Loading and processing company documents
* Splitting documents into retrieval-friendly chunks
* Generating embeddings
* Storing embeddings in ChromaDB
* Retrieving relevant knowledge
* Connecting the retriever to an LLM
* Generating grounded answers
* Evaluating different chunk sizes
* Evaluating hallucination behavior

---

## Project Structure

```text
week7_day2/
│
├── 01_knowledge_base/
│   └── datasets/
│       ├── properties.csv
│       ├── prices.csv
│       ├── locations.csv
│       ├── amenities.csv
│       ├── schools.csv
│       ├── hospitals.csv
│       ├── payment_plans.csv
│       ├── developers.csv
│       └── faqs.csv
│
├── 02_rag/
│   ├── documents/
│   │   ├── property_brochures/
│   │   ├── project_descriptions/
│   │   └── faqs/
│   │
│   ├── loader.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── retriever.py
│   └── rag_pipeline.py
│
├── 05_evaluation/
│   ├── evaluation_questions.csv
│   ├── retrieval_evaluation.py
│   ├── chunk_evaluation.py
│   ├── evaluate_rag.py
│   └── rag_results.csv
│
└── README.md
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

The knowledge base is designed so that the assistant can distinguish verified information from unsupported assumptions.

---

# 2. RAG Pipeline

The RAG pipeline consists of the following stages:

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

## Document Loader

The document loader reads the verified company documents from the `documents/` directory.

Currently, the pipeline loads **4 documents**.

---

## Chunking

Documents are divided into smaller chunks while preserving useful context.

The chunking strategy:

* Preserves markdown sections
* Keeps headings with their content
* Splits large sections using sentences
* Avoids breaking sentences unnecessarily
* Uses sentence overlap

### Chunk-size evaluation

Three chunk sizes were evaluated:

| Chunk Size | Chunks | Top-3 Source Hit Rate |
| ---------: | -----: | --------------------: |
|        256 |     18 |                  100% |
|        512 |     11 |                  100% |
|       1024 |      9 |                  100% |

All three configurations achieved a 100% source-hit rate on the evaluation questions.

**Selected configuration:**

```text
Chunk size: 512
Overlap: 1 sentence
```

512 was selected because it provides a good balance between contextual completeness and retrieval granularity.

---

# 3. Embeddings

The system uses a local Sentence Transformer embedding model to convert documents and user queries into numerical vectors.

This allows the system to perform semantic similarity search.

The embedding model runs locally and does not require sending the knowledge-base documents to an external embedding API.

---

# 4. Vector Store

**ChromaDB** is used as the vector database.

Each chunk is stored with:

* Chunk ID
* Document text
* Source document
* Embedding

Cosine distance is used for semantic similarity.

---

# 5. Retriever

The retriever performs semantic search against the ChromaDB collection.

Example:

```text
User:
What amenities are listed for Skyline Residences?

        ↓

Retriever

        ↓

skyline_residences.md

        ↓

Relevant verified context

        ↓

LLM
```

A cosine-distance threshold is also used to reject weak semantic matches.

This reduces the chance of irrelevant documents being passed to the LLM.

---

# 6. LLM Answer Generation

The retrieved context is passed to the LLM together with strict grounding instructions.

The assistant is instructed to:

1. Never invent property details.
2. Never invent prices or availability.
3. Never invent amenities or payment plans.
4. Never guarantee investment returns.
5. Use only verified company context.
6. Refuse unsupported questions.

Example:

### Question

```text
What amenities are listed for Skyline Residences?
```

### Answer

```text
The amenities listed for Skyline Residences include parking,
a shared swimming pool, a shared gym, and 24/7 security.
```

---

# 7. Hallucination Evaluation

A 20-question evaluation set was created to test the RAG system.

The questions cover:

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

## Evaluation Results

| Metric                   | Result |
| ------------------------ | -----: |
| Total Questions          |     20 |
| Passed                   |     20 |
| Failed                   |      0 |
| RAG Evaluation Pass Rate |   100% |
| Grounding Rate           |   100% |
| Hallucination Rate       |     0% |

---

# 8. Correct Refusal Behavior

The system correctly refuses to answer when verified information is unavailable.

Examples include:

```text
What payment plan is available for DHA-APT-001?
```

```text
What is the nearest hospital to Skyline Residences?
```

```text
What is the guaranteed annual return of Skyline Residences?
```

```text
Does Skyline Residences have a tennis court?
```

```text
What is the price of Moonlight Towers?
```

The assistant responds:

```text
Verified information is currently unavailable.
```

This is intentional behavior and is an important part of the anti-hallucination design.

---

# 9. Retrieval Evaluation

Known-source retrieval tests achieved:

```text
Known-source tests: 5
Source hit rate: 100%
```

The retriever successfully identified the expected source documents for the tested known-information queries.

---

# 10. Running the RAG Pipeline

Activate the virtual environment first:

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

---

# 11. Running RAG Evaluation

Navigate to the evaluation directory:

```powershell
cd ..\05_evaluation
```

Run:

```powershell
python evaluate_rag.py
```

Expected result:

```text
Total tests: 20
Tests passed: 20
Tests failed: 0
RAG evaluation pass rate: 100.00%
```

---

# 12. Running Chunk-size Evaluation

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
* Number of evaluation questions
* Top-3 source hit rate

---

# 13. Design Principles

The system follows these principles:

### Verified data first

Property information must come from the company knowledge base.

### No unsupported claims

The LLM must not fill missing information with guesses.

### Retrieval before generation

The LLM receives retrieved context before generating the answer.

### Explicit refusal

When verified information is unavailable, the system returns a controlled refusal.

### Traceability

Retrieved chunks retain their source document and chunk metadata.

---

# 14. Current Status

### Completed

* [x] Knowledge base
* [x] Document loader
* [x] Chunking
* [x] Embeddings
* [x] ChromaDB vector store
* [x] Semantic retriever
* [x] LLM integration
* [x] Grounded answer generation
* [x] Chunk-size evaluation
* [x] 20-question hallucination evaluation
* [x] Retrieval evaluation

### Remaining

* [ ] Structured SQL retrieval
* [ ] Structured-vs-semantic retrieval router
* [ ] Property recommendation engine
* [ ] Final integrated evaluation

---

# 15. Conclusion

The current RAG implementation successfully grounds generated responses in verified real estate information.

The evaluation achieved:

```text
Grounding Rate:       100%
Retrieval Accuracy:   100%
Hallucination Rate:     0%
RAG Evaluation:       100%
```

The next phase is to combine semantic RAG with structured retrieval so that exact business-critical information such as prices and availability can be retrieved directly from structured data rather than relying on semantic similarity alone.
