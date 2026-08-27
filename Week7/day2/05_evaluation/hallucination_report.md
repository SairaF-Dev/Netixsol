# Hallucination Evaluation Report

## 1. Objective

The objective of this evaluation is to verify that Sara, the real estate RAG assistant, answers questions only from verified company knowledge and does not invent property information.

The evaluation focuses on three key metrics:

* Grounding Rate
* Retrieval Accuracy
* Hallucination Rate

## 2. Evaluation Setup

A total of **20 questions** were evaluated.

The questions covered:

* Property amenities
* Property prices
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

The RAG pipeline used:

* Sentence Transformers for embeddings
* ChromaDB for vector storage
* Semantic retrieval
* LLM-based answer generation
* A strict system rule requiring answers to use verified context only

When verified information was unavailable, the assistant was required to respond:

> "Verified information is currently unavailable."

## 3. Evaluation Results

| Metric                   | Result |
| ------------------------ | -----: |
| Total Questions          |     20 |
| Passed Questions         |     20 |
| Failed Questions         |      0 |
| RAG Evaluation Pass Rate |   100% |
| Grounding Rate           |   100% |
| Hallucination Rate       |     0% |

## 4. Grounding Rate

**Grounding Rate = 100%**

All generated answers were supported by the retrieved verified context.

Examples:

* Skyline Residences amenities → answer matched the verified brochure.
* DHA Pearl Apartments price → answer matched the verified property data.
* Bahria Grand Apartments price → answer matched the verified brochure.
* Skyline developer → answer matched the verified source.
* Skyline swimming pool question → answer matched the verified context.

For questions where the required information was not available, the system correctly refused to provide an unsupported answer.

## 5. Retrieval Accuracy

The evaluation contained **5 known-source retrieval tests** in the earlier retrieval evaluation.

Results:

* Known-source tests: **5**
* Correct source retrievals: **5**
* Retrieval source-hit rate: **100%**

The chunk-size evaluation also produced a **100% top-3 source hit rate** for all tested chunk sizes:

| Chunk Size | Number of Chunks | Top-3 Source Hit Rate |
| ---------: | ---------------: | --------------------: |
|        256 |               18 |                  100% |
|        512 |               11 |                  100% |
|       1024 |                9 |                  100% |

A chunk size of **512 characters with 1-sentence overlap** was selected because it provides a balanced trade-off between contextual completeness and retrieval granularity.

## 6. Hallucination Rate

**Hallucination Rate = 0%**

No unsupported property facts were generated during the 20-question evaluation.

The system successfully refused questions involving unavailable or unsupported information.

Examples include:

* Payment plan for DHA-APT-001
* Payment plan for Skyline Residences
* Nearest hospital to Skyline Residences
* Guaranteed annual return
* Tennis court at Skyline Residences
* Price of Moonlight Towers

For these questions, the assistant returned:

> "Verified information is currently unavailable."

This behavior prevents the LLM from fabricating property information.

## 7. Important Safety Behavior

The system also explicitly prevents Sara from:

* Inventing property details
* Inventing prices
* Inventing availability
* Inventing amenities
* Inventing payment plans
* Guaranteeing investment returns

This is important for a real estate application because incorrect property information could mislead customers.

## 8. Final Conclusion

The current RAG system successfully passed all **20 hallucination evaluation questions**.

### Final Metrics

**Grounding Rate: 100%**

**Retrieval Accuracy: 100%**

**Hallucination Rate: 0%**

**Overall RAG Evaluation Pass Rate: 100%**

The evaluation demonstrates that the current RAG pipeline is able to ground answers in verified company information and appropriately refuse unsupported questions instead of generating fabricated property details.

However, these results are based on a relatively small demo knowledge base and a 20-question evaluation set. A production system should be evaluated with a larger and more diverse test dataset, including adversarial and ambiguous queries.
