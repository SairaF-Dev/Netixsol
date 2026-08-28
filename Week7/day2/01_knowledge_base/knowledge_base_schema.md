# Knowledge Base Schema

The Day 2 knowledge base separates **exact business facts** from **unstructured semantic knowledge**.

This separation allows Sara to use the appropriate retrieval system for each type of information.

---

## 1. Structured Datasets

The structured knowledge base contains verified property records that can be stored and queried through PostgreSQL.

* `properties.csv` — core property records, including property IDs, types, bedrooms, sizes, and availability.
* `prices.csv` — verified property prices and transaction types.
* `locations.csv` — normalized cities, areas, and property locations.
* `amenities.csv` — property-level amenities.
* `schools.csv` — nearby or associated schools.
* `hospitals.csv` — nearby or associated hospitals.
* `payment_plans.csv` — payment-plan information and related property IDs.
* `developers.csv` — developer and project information.
* `faqs.csv` — frequently asked questions and verified answers.

Stable property identifiers are used to connect related records across datasets.

---

## 2. Structured Data → PostgreSQL

Structured data is intended for exact lookups, filtering, comparison, and sorting.

Examples include:

* Property ID
* Price
* Availability
* Bedrooms
* Property size
* City
* Area
* Property type
* Developer
* Payment-plan values

Example query:

```text
Find available 3-bedroom apartments in Lahore under 30 million PKR.
```

This should be handled by PostgreSQL rather than semantic similarity search.

```text
User Query
    ↓
Requirement Extraction
    ↓
SQL Filters
    ↓
PostgreSQL
    ↓
Verified Property Records
```

---

## 3. Semantic Documents → RAG

Unstructured knowledge is stored as documents and indexed in ChromaDB.

Examples include:

* Property brochures
* Project descriptions
* Company policies
* Booking information
* FAQ explanations
* Natural-language property information

These documents are loaded, chunked, embedded, and indexed for semantic retrieval.

```text
Documents
    ↓
Chunking
    ↓
Embeddings
    ↓
ChromaDB
    ↓
Semantic Retrieval
    ↓
Relevant Context
```

RAG is useful when the user's question depends on meaning rather than exact database filtering.

Example:

```text
"Does Skyline Residences offer a family-friendly environment?"
```

---

## 4. Source-of-Truth Policy

For production use, **prices, availability, property IDs, and other business-critical facts must come from the authoritative company database or API**.

The included datasets are **demo data created for the Week 7 capstone**.

They must not be presented as:

* Live market data
* Real-time availability
* Current market prices
* Guaranteed investment information

Sara must clearly distinguish demo/verified company data from external or unsupported information.

---

## 5. Structured vs Semantic Retrieval

| Information     | Retrieval Method     | Source of Truth    |
| --------------- | -------------------- | ------------------ |
| Price           | PostgreSQL           | Company database   |
| Availability    | PostgreSQL           | Company database   |
| Property ID     | PostgreSQL           | Company database   |
| Bedrooms        | PostgreSQL           | Company database   |
| Property size   | PostgreSQL           | Company database   |
| City / Area     | PostgreSQL           | Company database   |
| Recommendations | PostgreSQL + scoring | Company database   |
| Brochures       | RAG / ChromaDB       | Verified documents |
| Descriptions    | RAG / ChromaDB       | Verified documents |
| Policies        | RAG / ChromaDB       | Verified documents |
| Semantic FAQs   | RAG / ChromaDB       | Verified documents |

---

## 6. Design Rule

The core architecture follows:

> **Structured facts → PostgreSQL**
>
> **Unstructured knowledge → RAG / ChromaDB**

The LLM should never replace either retrieval system.

It is responsible for understanding the user's request and presenting verified results naturally, but it must not invent facts when retrieval does not provide sufficient evidence.

---

## 7. Anti-Hallucination Rule

If the requested information cannot be verified from the appropriate source:

```text
No verified evidence
        ↓
Do not guess
        ↓
Controlled refusal
```

Sara should respond:

```text
Verified information is currently unavailable.
```

This rule is especially important for:

* Prices
* Availability
* Payment plans
* Property existence
* Investment returns
* Property recommendations
