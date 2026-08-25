# Week 7 Day 2: Knowledge Base, RAG & Property Intelligence

Real estate voice agent capstone — CM-IT. Covers all 5 Day 2 tasks: knowledge base datasets, RAG pipeline, structured vs. semantic retrieval, recommendation engine, and hallucination evaluation.

## Folder structure

```
week7-day2/
├── data/                        # Task 1 — Knowledge Base
│   ├── properties.csv           # 15 sample listings
│   ├── prices.csv                # price/rent, negotiability, advance %
│   ├── locations.csv             # geo + distance-to-airport/city-center + security rating
│   ├── amenities.csv             # gated community, gym, pool, generator, etc.
│   ├── schools.csv                # nearby schools per area
│   ├── hospitals.csv              # nearby hospitals per area
│   ├── payment_plans.csv          # installment plans for under-construction properties
│   ├── developers.csv             # developer track record
│   ├── faqs.json                  # 10 UrduLish FAQ pairs (semantic content)
│   └── brochures.json             # long-form UrduLish property descriptions (semantic content)
│
├── database/                    # Structured store (Task 3, SQL half)
│   ├── schema.sql                 # relational schema — properties, prices, amenities, etc.
│   └── seed_db.py                 # builds real_estate.db from the CSVs above
│
├── rag/                         # Task 2 — RAG Pipeline
│   ├── loader.py                  # Document Loader (loads faqs.json + brochures.json)
│   ├── chunking.py                # fixed-size + sentence-boundary chunking
│   ├── embeddings.py              # TF-IDF (offline) + OpenAI (production) embedders
│   ├── vectorstore.py             # in-memory store + ChromaDB wrapper
│   ├── retriever.py               # embed query -> vector search
│   ├── generator.py               # grounded answer generation (Claude/OpenAI + offline fallback)
│   └── pipeline.py                # ties all of the above together — RUN THIS to test the RAG pipeline
│
├── retrieval/                   # Task 3 — Structured vs Semantic split
│   ├── structured_retrieval.py    # SQL: price, availability, size, agent name
│   └── semantic_retrieval.py      # Vector: brochures, descriptions, FAQs
│
├── recommendation/              # Task 4 — Recommendation Engine
│   └── recommender.py             # budget/city/bedrooms hard filter + amenity/investment soft scoring
│
├── evaluation/                  # Task 5 — Hallucination Evaluation
│   ├── questions.json             # 20 test questions (14 answerable, 6 deliberately not)
│   ├── evaluate.py                # RUN THIS — computes grounding/retrieval/hallucination rates
│   └── results.json               # generated after running evaluate.py
│
├── docs/
│   ├── chunk_size_evaluation.md   # Task 2 — chunk size comparison, actually measured
│   └── structured_vs_semantic.md  # Task 3 — why the split, with a concrete failure case (Q19)
│
└── requirements.txt
```

## How to run

Everything runs **offline, with zero API keys**, using a TF-IDF embedder + in-memory vector store + a rule-based fallback generator — so you can test/grade the pipeline without any credits. Swap to the production backends (`OpenAIEmbedder`, `ChromaVectorStore`, `generate_answer_openai`/`generate_answer_anthropic`) by setting `EMBEDDER_BACKEND=openai` and using the real generator functions once you deploy.

```bash
# 1. Build the structured database from the CSVs
python database/seed_db.py

# 2. Test structured retrieval (SQL)
python retrieval/structured_retrieval.py

# 3. Test semantic retrieval (vector search)
python retrieval/semantic_retrieval.py

# 4. Run the full RAG pipeline (loader -> chunk -> embed -> store -> retrieve -> generate)
python rag/pipeline.py

# 5. Run the recommendation engine
python recommendation/recommender.py

# 6. Run the hallucination evaluation (produces evaluation/results.json)
python evaluation/evaluate.py
```

All six have already been run once during development — every script executes cleanly end to end.

## Key results (from this run)

- **RAG pipeline**: 14 documents → 32 chunks (sentence chunking, 200-char target).
- **Chunk size sweep**: 100/200/400 chars tested; see `docs/chunk_size_evaluation.md` — 200 chars kept as production default despite 400 scoring higher on this tiny corpus (explained honestly in the doc — it's a corpus-size artifact, not a real signal).
- **Hallucination evaluation** (`evaluation/results.json`):
  - Grounding rate: 92.9% (13/14 answerable questions retrieved the correct source)
  - Hallucination rate: 100% on the 6 deliberately-unanswerable questions — the offline fallback generator has **no confidence threshold enforced**, so it always returns its best-guess chunk instead of refusing. This is a genuine, useful finding: it demonstrates exactly why `generator.py`'s `SYSTEM_PROMPT` guardrail ("agar context mein answer nahi hai, saaf keh dein") matters once a real LLM is in the loop — the LLM is expected to apply that refusal rule; the rule-based `generate_answer_no_context_fallback()` used for this offline demo does not, and `min_score` in that function needs raising (or a stricter fallback) before this offline path could be trusted standalone.
  - `Q19` specifically shows the structured/semantic failure case documented in `docs/structured_vs_semantic.md` — a price question got routed to semantic retrieval and returned a wrong-topic FAQ instead of the correct structured answer or a refusal.

## Note on production LLM integration

`rag/generator.py` includes working `generate_answer_anthropic()` and `generate_answer_openai()` functions — these are what the deployed voice agent should use (they carry the anti-hallucination system prompt). The offline fallback in `pipeline.py`/`evaluate.py` exists only so this repo is fully runnable and gradeable without API keys; it is intentionally not what should ship.
