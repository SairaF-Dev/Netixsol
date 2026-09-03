# Week 7  Day 2 Report

## Knowledge Base, RAG & Property Intelligence

### Objective

Build the verified-data foundation required to prevent the real estate voice agent from hallucinating property details.

The core principle is:

> If verified company data does not contain the answer, the agent must abstain instead of guessing.

---

## 1. Knowledge Base

Created structured datasets for:

* Properties
* Prices
* Locations
* Amenities
* Schools
* Hospitals
* Payment plans
* Developers
* FAQs

The datasets use stable property IDs so related records can be joined reliably.

The knowledge base also includes document-based information for semantic retrieval, including:

* Property brochures
* Project descriptions
* FAQs

---

## 2. RAG Pipeline

Implemented a modular RAG pipeline consisting of:

```text
Document Loader
      ↓
Chunker
      ↓
Embedding
      ↓
ChromaDB Vector Store
      ↓
Retriever
      ↓
Answer Generation
```

Implemented components include:

* Document loader
* Sentence-based chunker
* Local embedding model
* Persistent ChromaDB vector store
* Incremental document indexing
* Semantic retriever
* Distance-based relevance filtering
* RAG answer-generation interface

The vector store supports incremental synchronization.

Unchanged documents are skipped, while new or modified documents are re-embedded and indexed.

---

## 3. Incremental Indexing

The vector store uses SHA-256 content hashing to detect document changes.

The indexing behavior is:

```text
New document
    → Embed and index

Unchanged document
    → Skip

Changed document
    → Delete old chunks
    → Re-embed
    → Insert updated chunks
```

This prevents unnecessary embedding operations and keeps the ChromaDB index synchronized with the document knowledge base.

Testing confirmed:

```text
Initial indexing:
4 documents
11 chunks
11 chunks embedded

Second run:
4 unchanged documents
0 chunks embedded

After modifying a document:
1 document updated
2 chunks re-embedded
```

---

## 4. ChromaDB Semantic Retrieval Test

The ChromaDB vector store was tested independently.

The test successfully demonstrated:

* Document indexing
* Semantic embedding
* Vector search
* Distance calculation
* Retrieval of semantically related chunks

Result:

```text
PASS: semantic retrieval works
```

The test initially exposed an outdated `add()` API call in the test script. This was corrected to use the implemented `sync_documents()` method.

---

## 5. Chunk Size Evaluation

Three chunk sizes were evaluated:

```text
256 characters
512 characters
1024 characters
```

Results:

| Chunk Size | Chunks Created | Top-3 Source Hit Rate |
| ---------: | -------------: | --------------------: |
|        256 |             18 |                  100% |
|        512 |             11 |                  100% |
|       1024 |              9 |                  100% |

All three configurations achieved a 100% top-3 source hit rate on the current evaluation questions.

A chunk size of **512 characters with 1-sentence overlap** was selected as the current configuration because it provides a practical balance between contextual completeness and retrieval granularity.

Because the current dataset is small, this selection should be re-evaluated when the production knowledge base becomes larger.

---

## 6. Structured vs Semantic Retrieval

The system separates exact business-data retrieval from semantic document retrieval.

### SQL / Structured Retrieval

SQL is used for deterministic business facts such as:

* Price
* Availability
* Bedrooms
* Property size
* Property ID
* Location
* Developer
* Amenities where exact filtering is required

Structured retrieval is preferred when the answer depends on exact values or filtering conditions.

### Vector / Semantic Retrieval

RAG is used for:

* Brochures
* Project descriptions
* FAQs
* Natural-language property information
* Semantic questions

This split is important because SQL provides deterministic filtering and exact values, while vector retrieval is better suited to semantic matching and unstructured documents.

---

## 7. Recommendation Engine

The recommendation engine supports property filtering and ranking based on:

* Budget
* City
* Area
* Bedrooms
* Purpose
* Amenities

Unavailable properties are filtered out before recommendation scoring.

The recommendation architecture separates:

```text
Filtering
    ↓
Scoring
    ↓
Ranking
    ↓
Recommendations
```

Investment goals are implemented as a grounded ranking signal using verified purpose/property-type facts. The engine does not estimate or guarantee ROI, yield, appreciation, or profit.

The system does not invent financial performance or guarantee investment returns.

---

## 8. Retrieval Evaluation

A separate retrieval evaluation was performed using **7 test questions**.

### Known-Source Tests

Five questions tested information known to exist in the knowledge base.

```text
Known-source tests: 5
Correct source retrievals: 5
Source hit rate: 100%
```

### Unknown-Information Tests

Two questions intentionally requested information that was not available:

1. Payment plan for `LHR-DHA-APT-001`
2. Price of a nonexistent property

The semantic retriever still returned nearby documents because vector search always attempts to find the closest available embeddings.

Results:

```text
Unknown-information tests: 2
Correctly rejected by retriever: 0
Unknown-query rejection rate: 0%
```

Overall retrieval evaluation:

```text
Tests: 7
Passed: 5
Failed: 2
Overall retrieval evaluation: 71.43%
```

This identifies an important limitation of pure semantic retrieval:

> Vector similarity does not guarantee that the retrieved document contains the requested fact.

---

## 9. RAG / Hallucination Evaluation

A separate **20-question RAG evaluation** was performed.

The evaluation covered:

* Exact factual questions
* Property prices
* Amenities
* Developers
* Locations
* Bedrooms
* Availability
* FAQ questions
* UrduLish queries
* Unsupported information
* Nonexistent properties
* Investment-return questions
* Payment-plan questions
* Hospital questions
* Unsupported amenities

### Results

| Metric                    |   Result |
| ------------------------- | -------: |
| Total questions           |       20 |
| Passed                    |       20 |
| Failed                    |        0 |
| RAG evaluation pass rate  | **100%** |
| Grounding rate            | **100%** |
| Answer hallucination rate |   **0%** |

Supported questions generated answers grounded in retrieved context.

Unsupported questions correctly returned:

> "Verified information is currently unavailable."

---

## 10. Grounded Answer Examples

The system successfully answered verified questions such as:

* Horizon Heights Apartment amenities
* Horizon Heights Apartment developer
* Horizon Heights Apartment location
* Horizon Heights Apartment bedrooms
* Horizon Heights Apartment availability
* Park View Residences price
* Bahria Grand Apartments price
* Bahria Grand Apartments developer
* Bahria Grand Apartments amenities
* Bahria Grand Apartments availability
* UrduLish swimming-pool query

The system also correctly refused unsupported questions such as:

* Payment plan for LHR-DHA-APT-001
* Payment plan for Horizon Heights Apartment
* Nearest hospital to Horizon Heights Apartment
* Guaranteed annual return
* Tennis court at Horizon Heights Apartment
* Price of Moonlight Towers

---

## 11. Hallucination Prevention

The current answer-generation layer prevents unsupported retrieved context from automatically becoming an answer.

For example, the retrieval evaluation showed that an unsupported query could still retrieve a semantically similar document.

However, the complete RAG evaluation correctly produced:

```text
Verified information is currently unavailable.
```

instead of fabricating an answer.

Therefore, the current architecture demonstrates an important safety boundary:

```text
Semantic similarity
        ↓
Retrieved context
        ↓
Grounding / verification
        ↓
Answer OR abstain
```

---

## 12. Reliability Policy

The central reliability policy is:

> If verified company data does not contain the answer, the agent must abstain instead of guessing.

Sara must not:

* Invent property details
* Invent prices
* Invent availability
* Invent amenities
* Invent payment plans
* Invent developer information
* Invent hospital information
* Guarantee investment returns
* Generate financial claims without verified company data

This is particularly important for a real estate voice agent because incorrect property information can directly mislead customers.

---

## 13. Current Evaluation Summary

The project currently demonstrates:

```text
Known-source retrieval accuracy:     100%
Chunk-size top-3 source hit rate:    100%
RAG evaluation pass rate:            100%
Grounding rate:                      100%
Answer hallucination rate:             0%

Overall retrieval evaluation:         71.43%
Unknown-query rejection rate:          0%
```

The distinction between these metrics is important.

The **100% grounding and 0% answer hallucination results** come from the complete 20-question RAG evaluation.

The **71.43% retrieval result** comes from a separate retrieval-level test that exposed weaknesses in rejecting unsupported semantic queries.

---

## 14. Limitations

The current evaluation is based on a relatively small demo knowledge base and a limited test dataset.

The retrieval system still requires improvement for:

* Unknown-query rejection
* Exact fact verification
* Ambiguous queries
* Adversarial queries
* Larger document collections
* More diverse UrduLish queries

The current ChromaDB evaluation also revealed that evaluation indexes must be isolated or cleaned between runs to prevent duplicate chunks from affecting retrieval measurements.

---

## 15. Day 2 Outcome

Week 7 Day 2 successfully established the verified knowledge foundation for the real estate voice agent.

Completed components include:

* Structured knowledge base
* Document knowledge base
* RAG pipeline
* Local embeddings
* ChromaDB vector store
* Incremental indexing
* Semantic retrieval
* Chunk-size evaluation
* Structured retrieval architecture
* Recommendation engine
* Retrieval evaluation
* 20-question RAG evaluation
* Grounding and hallucination testing
* Safe refusal behavior

The system currently demonstrates:

**100% grounding rate**

**0% answer hallucination rate**

**100% known-source retrieval accuracy**

The next stage is to connect these verified retrieval and recommendation capabilities to the **LangGraph voice-agent workflow**, while improving retrieval rejection and exact-fact verification for production reliability.


## Day 2 Completion Fixes

- Agent identity and property-agent assignments are now retrieved from PostgreSQL through `get_agent()` and `get_agents_for_property()`; agent names are never generated by the model.
- Recommendation scoring now accepts `investment_goal` and uses only verified purpose/property-type facts for ranking. Unsupported goals receive no evidence-free score, and the system does not calculate ROI, yield, appreciation, or future profit.
