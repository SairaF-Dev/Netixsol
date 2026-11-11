# Khan & Associates - Legal Chunking Strategy Comparison Report

## 1. Executive Summary
Legal documents (statutes, case law judgments, commercial contracts) possess strict hierarchical structures that make generic fixed-size chunking hazardous. Cutting across a statutory proviso, an exception clause, or a ratio decidendi destroys legal semantics.

This benchmark evaluates **3 chunking strategies** on 12 generated instructional
documents (3 statutes, 5 judgments, and 4 contracts). They are not authoritative
legal sources. `Avg Tokens` and `Token StdDev` are whitespace word counts, not
model-token counts. Boundary preservation and retrieval relevance are not scored.

1. **Fixed-Size Chunking** (200-word window, 40-word overlap)
2. **Section-Level Chunking** (Section / Article / Ratio / Clause boundaries)
3. **Parent-Child Chunking** (Sub-clause child chunks indexed, full Section parents returned)

## 2. Benchmark Comparison Matrix

| Strategy                    | Total Chunks              | Avg Tokens                   |   Token StdDev | Boundary Preservation                               | Metadata Completeness            | Retrieval Context                         |
|-----------------------------|---------------------------|------------------------------|----------------|-----------------------------------------------------|----------------------------------|-------------------------------------------|
| Fixed-Size (Sliding Window) | 24                        | 157.6                        |           46.4 | Not measured; windows may split legal units         | Offsets only                     | Window-sized text                         |
| Section-Level (Legal Aware) | 58                        | 87.4                         |           83.2 | Structure-aware; not independently scored           | Document-specific legal metadata | One chunk per legal structure unit        |
| Parent-Child (Hierarchical) | 183 (Child) / 58 (Parent) | 26.0 (Child) / 87.4 (Parent) |           35.9 | Parent hierarchy retained; not independently scored | Child chunks carry parent_id     | Child match with parent context available |

## 3. Design Notes (not measured retrieval results)

### A. Fixed-Size Chunking
* **Tradeoff**: A fixed window can separate a provision from adjacent context.

### B. Section-Level Legal Chunking
* **Strengths**: Every chunk corresponds to an autonomous legal unit (e.g. Section 497 CrPC, Article 199 Constitution, or Clause 5 Governing Law).
* **Metadata Richness**: Automatically attaches `act`, `section`, `court`, `year`, `matter_id`.
* **Fit**: Ideal for direct BM25 keyword matching and standard legal research queries.

### C. Parent-Child Chunking (Recommended for RAG)
* **Potential benefit**: Provides a retrieval tradeoff:
  - **Children** (~20-50 tokens) provide pinpoint semantic matching against specific user questions.
  - **Parents** (~150-400 tokens) provide the LLM with the full statutory section or contract clause upon retrieval.
* **Recommendation**: Evaluate **Parent-Child Chunking** for vector retrieval and **Section-Level Chunking** for BM25 against a judged relevance set before production use.
