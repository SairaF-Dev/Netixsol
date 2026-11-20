# Citation Verification (Day 2, Task 5)

Every citation in the Gemini answers was checked by code (no LLM), against the passages the
model was given and the structured corpus:

1. **source**: the passage number exists among the retrieved passages;
2. **attribution**: the Act / case named matches that passage's document;
3. **reference**: the cited section / article / paragraph exists in that document;
4. **quote**: the quoted words appear verbatim in that passage (whitespace, quote marks,
   footnote marks and Urdu letter forms normalised).

A citation failing any check is removed; an answer left without citations becomes
"No sufficient source found". Citations giving only a page or chapter are counted as
imprecise, and section numbers cited from Urdu OCR pages (which carry none) as
unverifiable; neither counts as fabricated, but both are removed. Questions: the reviewed evaluation set.
Per-citation results: `evaluations\rag_runs\citation_checks.jsonl`.

| Configuration                                              |   Citations | Verified   | Fabricated   | Imprecise or unverifiable   | Failed checks                                        |   Fabricated shown to user |   Answers turned into refusal | Citation accuracy after   |
|------------------------------------------------------------|-------------|------------|--------------|-----------------------------|------------------------------------------------------|----------------------------|-------------------------------|---------------------------|
| 0. Naive: fixed 200-word chunks, vector search only, top 5 |          53 | 36 (68%)   | 5 (9%)       | 12 (23%)                    | attribution 4, imprecise 10, quote 1, unverifiable 2 |                          0 |                            13 | 39%                       |
| 1. Section-level chunks, vector search only                |          67 | 62 (93%)   | 4 (6%)       | 1 (1%)                      | attribution 1, quote 3, unverifiable 1               |                          0 |                             5 | 52%                       |
| 2. + Hybrid search (BM25 + vector, RRF)                    |          77 | 72 (94%)   | 2 (3%)       | 3 (4%)                      | imprecise 1, quote 2, unverifiable 2                 |                          0 |                             4 | 62%                       |
| 3. + Reranking (multilingual cross-encoder, top 30)        |          86 | 77 (90%)   | 4 (5%)       | 5 (6%)                      | imprecise 3, quote 4, unverifiable 2                 |                          0 |                             6 | 68%                       |
| 4. + Query rewriting (Gemini, English legal query)         |          99 | 89 (90%)   | 6 (6%)       | 4 (4%)                      | attribution 1, imprecise 4, quote 5                  |                          0 |                             6 | 80%                       |
| 5. + HyDE (Gemini hypothetical answer passage)             |          96 | 88 (92%)   | 3 (3%)       | 5 (5%)                      | imprecise 5, quote 3                                 |                          0 |                             7 | 80%                       |
