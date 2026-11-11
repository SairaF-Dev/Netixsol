# Khan & Associates - Legal Chunking Strategy Comparison Report

## 1. Executive Summary
Legal documents (statutes, case law judgments, commercial contracts) possess strict hierarchical structures that make generic fixed-size chunking hazardous. Cutting across a statutory proviso, an exception clause, or a ratio decidendi destroys legal semantics.

This benchmark evaluated **3 chunking strategies** across a sample of Pakistani statutes, superior court judgments, and commercial contracts:
1. **Fixed-Size Chunking** (200 token window, 40 token overlap)
2. **Section-Level Chunking** (Section / Article / Ratio / Clause boundaries)
3. **Parent-Child Chunking** (Sub-clause child chunks indexed, full Section parents returned)

## 2. Benchmark Comparison Matrix

| Strategy                    | Total Chunks              | Avg Tokens                   |   Token StdDev | Boundary Preservation             | Metadata Completeness            | Retrieval Context                        |
|-----------------------------|---------------------------|------------------------------|----------------|-----------------------------------|----------------------------------|------------------------------------------|
| Fixed-Size (Sliding Window) | 24                        | 157.6                        |           46.4 | Poor (35% - cuts across sections) | Low (Generic offsets only)       | Truncated / Incomplete clauses           |
| Section-Level (Legal Aware) | 58                        | 87.4                         |           83.2 | 100% (Strict legal borders)       | High (Act, section, court, year) | High (Self-contained legal clauses)      |
| Parent-Child (Hierarchical) | 183 (Child) / 58 (Parent) | 26.0 (Child) / 87.4 (Parent) |           35.9 | 100% (Two-tier legal hierarchy)   | Maximum (Carries parent_id link) | Optimal (Child matched, Parent returned) |

## 3. In-Depth Architectural Evaluation

### A. Fixed-Size Chunking
* **Flaws**: Arbitrarily splits definitions from operative statutory clauses (e.g. separates PPC 302 punishment from PPC 299 definitions). Truncates contract indemnity clauses mid-sentence.
* **Risk**: High hallucination risk during RAG because surrounding statutory provisos are lost.

### B. Section-Level Legal Chunking
* **Strengths**: Every chunk corresponds to an autonomous legal unit (e.g. Section 497 CrPC, Article 199 Constitution, or Clause 5 Governing Law).
* **Metadata Richness**: Automatically attaches `act`, `section`, `court`, `year`, `matter_id`.
* **Fit**: Ideal for direct BM25 keyword matching and standard legal research queries.

### C. Parent-Child Chunking (Recommended for RAG)
* **Strengths**: Solves the retrieval tradeoff:
  - **Children** (~20-50 tokens) provide pinpoint semantic matching against specific user questions.
  - **Parents** (~150-400 tokens) provide the LLM with the full statutory section or contract clause upon retrieval.
* **Recommendation**: Khan & Associates should implement **Parent-Child Chunking** for vector embeddings combined with **Section-Level Chunking** for BM25 keyword queries.
