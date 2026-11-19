# RAG Comparison (Day 2)

Evaluation set: `evaluations\rag_eval_set.jsonl` (100 questions: 50 statute, 30 case-law, 20 with no
answer in the corpus). Only reviewed questions are used: every question was checked against its source text by Claude (an AI model), not by a person; 16 drafts were dropped and 6 corrected during that review (see `evaluations/rag_eval_set_review.csv` and `evaluations/rag_eval_set_dropped.jsonl`).
Note: the Constitution PDF in the corpus is the 2012 edition (amended up to 28 Feb 2012), so later amendments are missing.
Recall@5 / MRR@5 count a hit when a top-5 chunk comes from the gold document (or the same legal
matter) and contains the gold section / paragraph or the gold quote. Citation accuracy, faithfulness
and refusals are measured on Gemini answers; faithfulness is judged by an LLM (gemini-3.5-flash-lite),
not by a person.

| Configuration                                           | Recall@5   | Recall@5 statute   | Recall@5 case-law   |   MRR@5 | Doc recall@5   | Citation accuracy   | Faithfulness   | Correct refusals   | False refusals   |
|---------------------------------------------------------|------------|--------------------|---------------------|---------|----------------|---------------------|----------------|--------------------|------------------|
| 1. Section-level chunks, vector search only             | 64%        | 68%                | 57%                 |    0.52 | 76%            | 56%                 | 98%            | 100%               | 26%              |
| 2. + Hybrid search (BM25 + vector, RRF)                 | 70%        | 74%                | 63%                 |    0.56 | 82%            | 64%                 | 98%            | 100%               | 18%              |
| 3. + Reranking (multilingual cross-encoder, top 30)     | 78%        | 74%                | 83%                 |    0.73 | 85%            | –                   | –              | –                  | –                |
| Naive: fixed 200-word chunks, vector search only, top 5 | 54%        | 56%                | 50%                 |    0.37 | 70%            | 42%                 | 99%            | 100%               | 41%              |
