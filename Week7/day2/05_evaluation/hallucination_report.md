# Hallucination Evaluation Report

## 1. Objective

The objective of this evaluation is to verify that **Sara**, the real estate RAG assistant, answers questions only from verified company knowledge and does not invent property information.

The evaluation focuses on three key metrics:

* **Grounding Rate**
* **Retrieval Accuracy**
* **Hallucination Rate**

The primary goal is to ensure that unsupported property information is not fabricated.

---

## 2. Evaluation Setup

A total of **20 questions** were evaluated.

The evaluation covered:

* Property amenities
* Property prices
* Developers
* Locations
* Bedrooms
* Availability
* Payment plans
* Investment returns
* Nearby hospitals
* Unsupported amenities
* Nonexistent properties
* UrduLish queries

The RAG pipeline used:

* Sentence Transformers for local embeddings
* ChromaDB for vector storage
* Semantic retrieval
* Context-based answer generation
* A strict grounding rule requiring answers to use verified context only

When verified information was unavailable, the assistant was required to respond:

> "Verified information is currently unavailable."

---

## 3. RAG Evaluation Results

The complete RAG evaluation contained **20 test questions**.

| Metric                    |   Result |
| ------------------------- | -------: |
| Total Questions           |       20 |
| Passed Questions          |       20 |
| Failed Questions          |        0 |
| RAG Evaluation Pass Rate  | **100%** |
| Grounding Rate            | **100%** |
| Answer Hallucination Rate |   **0%** |

All 20 questions produced either a grounded answer or an appropriate refusal when verified information was unavailable.

---

## 4. Grounding Rate

### Grounding Rate = 100%

All generated answers in the 20-question evaluation were supported by retrieved verified context.

Examples include:

* **Skyline Residences amenities** → The answer matched the verified brochure.
* **DHA Pearl Apartments price** → The answer matched the verified property information.
* **Bahria Grand Apartments price** → The answer matched the verified property information.
* **Skyline developer** → The answer matched the verified source.
* **Skyline swimming pool** → The answer matched the verified context.
* **Skyline location** → The answer matched the verified brochure.
* **Bahria Grand Apartments availability** → The answer matched the verified information.

For questions where the required information was unavailable, Sara refused to provide an unsupported answer.

---

## 5. Retrieval Accuracy

A separate retrieval evaluation was performed using **7 test cases**.

### Known-source retrieval

Five tests contained information that was present in the knowledge base.

| Metric                    |   Result |
| ------------------------- | -------: |
| Known-source tests        |        5 |
| Correct source retrievals |        5 |
| Source Hit Rate           | **100%** |

All five known-information queries retrieved the expected source.

### Chunk Size Evaluation

Three chunk sizes were evaluated:

| Chunk Size | Chunks Created | Top-3 Source Hit Rate |
| ---------: | -------------: | --------------------: |
|        256 |             18 |              **100%** |
|        512 |             11 |              **100%** |
|       1024 |              9 |              **100%** |

A chunk size of **512 characters with 1-sentence overlap** was selected as the current configuration because it provides a reasonable balance between contextual completeness and retrieval granularity.

---

## 6. Unknown-Information Retrieval

The retrieval evaluation also tested whether the retriever could avoid returning relevant-looking context for information that does not exist in the knowledge base.

Two unknown-information queries were tested:

1. `What payment plan is available for DHA-APT-001?`
2. `What is the price of a property that does not exist?`

The current semantic retriever returned nearby documents for both queries.

| Metric                          |     Result |
| ------------------------------- | ---------: |
| Unknown-information tests       |          2 |
| Correctly rejected by retriever |          0 |
| Unknown-query rejection rate    |     **0%** |
| Overall retrieval evaluation    | **71.43%** |

This result is an important limitation of pure vector similarity retrieval.

A semantic retriever always attempts to find the closest available vectors. A low enough distance does not necessarily mean that the retrieved document contains the requested fact.

Therefore:

> **Vector similarity does not guarantee factual relevance.**

This limitation does not mean that Sara generated hallucinated answers.

The final RAG answer-generation layer correctly detected the absence of verified information and returned:

> "Verified information is currently unavailable."

---

## 7. Hallucination Rate

### Answer Hallucination Rate = 0%

No unsupported property facts were generated during the 20-question RAG evaluation.

The system correctly refused questions involving unavailable or unsupported information.

Examples include:

* Payment plan for DHA-APT-001
* Payment plan for Skyline Residences
* Nearest hospital to Skyline Residences
* Guaranteed annual return
* Tennis court at Skyline Residences
* Price of Moonlight Towers

For these questions, Sara returned:

> "Verified information is currently unavailable."

This behavior prevents the language model from fabricating property information when the knowledge base does not contain the required fact.

---

## 8. Important Safety Behavior

The current system is designed to prevent Sara from:

* Inventing property details
* Inventing prices
* Inventing availability
* Inventing amenities
* Inventing payment plans
* Inventing developer information
* Guaranteeing investment returns
* Providing unsupported hospital or location information

This is especially important for a real estate application because inaccurate property information could mislead customers.

---

## 9. Retrieval vs. Answer-Level Evaluation

The evaluation demonstrates an important distinction between **retrieval quality** and **answer grounding**.

The retrieval evaluation achieved:

* **100% known-source retrieval accuracy**
* **0% unknown-query rejection rate**
* **71.43% overall retrieval evaluation**

However, the complete RAG evaluation achieved:

* **20/20 passed**
* **100% grounding rate**
* **0% answer hallucination rate**

This means the current system can retrieve semantically similar information even when the exact requested fact is unavailable, but the final answer-generation layer successfully prevents that irrelevant context from becoming a fabricated answer.

---

## 10. Final Metrics

### Current RAG Performance

| Metric                          |     Result |
| ------------------------------- | ---------: |
| RAG Evaluation                  |  **20/20** |
| RAG Evaluation Pass Rate        |   **100%** |
| Grounding Rate                  |   **100%** |
| Answer Hallucination Rate       |     **0%** |
| Known-source Retrieval Accuracy |   **100%** |
| Unknown-query Rejection Rate    |     **0%** |
| Overall Retrieval Evaluation    | **71.43%** |

---

## 11. Conclusion

The current RAG system successfully passed all **20 hallucination and grounding evaluation questions**.

The strongest result is the **0% answer hallucination rate**. Sara consistently grounded supported answers in verified company information and refused to provide unsupported facts.

The retrieval evaluation also identified a limitation: semantic retrieval can return the nearest available document even when the requested information does not exist in the knowledge base.

Therefore, the current architecture successfully demonstrates:

1. Verified knowledge retrieval
2. Grounded answer generation
3. Safe refusal for unavailable information
4. Protection against unsupported property claims

For a production system, the retrieval layer should be further improved using techniques such as:

* Better relevance thresholds
* Metadata filtering
* Structured SQL retrieval for exact property facts
* Hybrid retrieval
* Query classification
* Reranking
* Stronger negative/adversarial evaluation datasets

The current results are based on a relatively small demo knowledge base and a 20-question evaluation set. A production deployment should be evaluated with a larger and more diverse dataset containing ambiguous, adversarial, multilingual, and previously unseen queries.

### Final Assessment

**Grounding Rate: 100%**

**Answer Hallucination Rate: 0%**

**Known-source Retrieval Accuracy: 100%**

**Overall Retrieval Evaluation: 71.43%**

The system demonstrates strong answer-level hallucination prevention while identifying clear opportunities to improve retrieval-level rejection of unsupported queries.
