# Latency and cost (Day 5)

Measured on 2026-11-24 on Windows laptop, Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, with the Gemini answer cache **off** (every call real). Gemini time is the time inside the API call; the free tier's spacing between calls is excluded, so the figures are what a paid key would see. Cost uses the list price of Gemini 3.5 Flash-Lite (standard tier, checked 2026-11-24): $0.30 per 1M input and $2.50 per 1M output tokens. On the free tier the cost is 0, and a question asked before costs nothing (answers are cached).

## Research question (app default: `rerank`), 20 questions

| Stage | Median | 90th percentile |
|---|---|---|
| Retrieval (hybrid search + reranker, on the server) | 10970 ms | 11206 ms |
| Answer (Gemini) | 2.8 s | 16.2 s |
| Citation check (code) | 2 ms | 10 ms |
| Conclusion check (Gemini) | 5.0 s | 128.3 s |
| **End to end** | **16.6 s** | **104.7 s** |

* Gemini calls per question: 1.6; tokens per question: 3,799 in, 278 out.
* **Cost per question: $0.00183** - about **$1.83 per 1,000 questions**.
* **Gemini was overloaded during this run**: 25 calls were refused with 503 "high demand" and retried. The waits for those retries are not counted, but the calls that did go through were slow, so the 90th percentiles mostly show Google's load that day; the medians are the better guide.
* One-time start: loading the models and the index takes 23.3 s after the server starts.
* By question type (end to end, median): statute 47.9 s, case law 19.5 s, no answer 13.6 s.

## Retrieval only, all 100 evaluation questions (no Gemini)

| Configuration | Median | 90th percentile |
|---|---|---|
| naive | 341 ms | 444 ms |
| section | 16 ms | 20 ms |
| hybrid | 203 ms | 289 ms |
| rerank | 10035 ms | 10193 ms |

The reranker costs the most time but is what lifts recall@5 from 0.70 to 0.78 and MRR from 0.56 to 0.73 (`rag_comparison_report.md`). It reads 30 (question, passage) pairs of up to 512 tokens each on the CPU. Tried on this laptop: fewer threads is slower (14-18 s); the 8-bit model file published with the model saves about 1 s but changes the order of the top 5; ONNX Runtime's memory arena saves about 4 s but makes memory grow with every search (5.4 GB after 100, which is why it is off). A server CPU, or a GPU, is the real fix. Query rewriting and HyDE score higher still (recall@5 0.94) but add a Gemini call before the search - one more wait of several seconds and one more request per question against the free daily quota - which is why the app's default is `rerank`.

## Case-law graph, 6 questions

Median 616 ms, 90th percentile 629 ms (Neo4j AuraDB over the internet). Gemini calls: 0 (linked questions run a ready-made query; no LLM).

| Question | Method | Results | Time |
|---|---|---|---|
| Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Penal Code? | local | 8 | 624 ms |
| Which judges presided over proceedings referencing Article 129 of the Qanun-e-Shahadat Order, 1984? | local | 9 | 608 ms |
| Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997? | local | 10 | 513 ms |
| Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution? | local | 4 | 601 ms |
| Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad Ahmad Khan? | local | 3 | 629 ms |
| Which precedent is cited the most in the corpus? | global | 4 | 747 ms |

## Contract review

| Contract | Playbook findings | Gemini calls | Gemini time | Tokens in / out | Cost |
|---|---|---|---|---|---|
| CONT_SYNTH_001 | 14 | 1 | 13.6 s | 3,007 / 1,722 | $0.00521 |
| CUAD_REAL_001 | 14 | 1 | 6.6 s | 8,129 / 1,860 | $0.00709 |

Cost per review: about $0.0061.

## Free tier in practice

The free key allows about 500 requests a day. At 1.6 calls per research question that is about 312 new questions a day (repeated questions are free), or mixed with reviews and drafts somewhat fewer. The free tier also limits requests per minute, which the app respects by spacing calls 4 s apart - on the free key a research question therefore takes a few seconds longer than the figures above.
