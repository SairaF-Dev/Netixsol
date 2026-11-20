# RAG Comparison (Day 2)

Evaluation set: `evaluations\rag_eval_set.jsonl` (100 questions: 50 statute, 30 case-law, 20 with no
answer in the corpus). Only reviewed questions are used: every question was checked against its source text by Claude (an AI model), not by a person; 16 drafts were dropped and 6 corrected during that review (see `evaluations/rag_eval_set_review.csv` and `evaluations/rag_eval_set_dropped.jsonl`).
The Constitution in the corpus is the Ministry of Law 2025 edition (amended up to the 27th Amendment).
"–" = not measured yet: steps 4-7 were first run for retrieval only (`--no-llm`), because free-tier
Gemini allows 500 requests a day; their answer metrics are added after the next full run.
Recall@5 / MRR@5 count a hit when a top-5 chunk comes from the gold document (or the same legal
matter) and contains the gold section / paragraph or the gold quote. Citation accuracy, faithfulness
and refusals are measured on Gemini answers; faithfulness is judged by an LLM (gemini-3.5-flash-lite),
not by a person.

| Configuration                                                        | Recall@5   | Recall@5 statute   | Recall@5 case-law   |   MRR@5 | Doc recall@5   | Citation accuracy   | Faithfulness   | Correct refusals   | False refusals   |
|----------------------------------------------------------------------|------------|--------------------|---------------------|---------|----------------|---------------------|----------------|--------------------|------------------|
| 0. Naive: fixed 200-word chunks, vector search only, top 5           | 54%        | 56%                | 50%                 |    0.37 | 70%            | 42%                 | 99%            | 100%               | 41%              |
| 1. Section-level chunks, vector search only                          | 64%        | 68%                | 57%                 |    0.52 | 76%            | 56%                 | 98%            | 100%               | 26%              |
| 2. + Hybrid search (BM25 + vector, RRF)                              | 70%        | 74%                | 63%                 |    0.56 | 82%            | 64%                 | 98%            | 100%               | 18%              |
| 3. + Reranking (multilingual cross-encoder, top 30)                  | 78%        | 74%                | 83%                 |    0.73 | 85%            | 70%                 | 98%            | 100%               | 15%              |
| 4. + Query rewriting (Gemini, English legal query)                   | 94%        | 94%                | 93%                 |    0.85 | 95%            | 84%                 | 99%            | 95%                | 2%               |
| 5. + HyDE (Gemini hypothetical answer passage)                       | 94%        | 96%                | 90%                 |    0.85 | 96%            | 84%                 | 100%           | 95%                | 2%               |
| 6. + Metadata filters (Act/section/court from the question)          | 92%        | 96%                | 87%                 |    0.84 | 96%            | –                   | –              | –                  | –                |
| 7. + Parent-child retrieval (80-word children, parent unit returned) | 91%        | 94%                | 87%                 |    0.82 | 96%            | –                   | –              | –                  | –                |
