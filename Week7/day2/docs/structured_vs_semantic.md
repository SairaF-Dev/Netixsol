# Structured vs. Semantic Retrieval — Justification

## The split

| Use SQL (structured) | Use Vector Search (semantic) |
|---|---|
| Prices | Brochures / long descriptions |
| Availability status | FAQs |
| Plot/property size | Developer reputation blurbs |
| Agent names & contact | General "what's it like" questions |

## Why

**Structured facts have exactly one correct, current value.** A price or availability status changes over time and must reflect the live database — not a cached embedding of "similar sounding" text. If a customer asks "is P007 still available?", vector search would happily return a *similar* property description with high cosine similarity even though the correct answer (`Sold`, from `properties.status`) has nothing to do with textual similarity. Only an exact-match SQL lookup (`retrieval/structured_retrieval.py`) gives the guaranteed-correct answer.

**Semantic content has no single correct row.** "DHA Phase 6 ka bungalow kaisa hai?" doesn't map to one field — the useful answer is a blend of size, feel, and nearby amenities, phrased naturally. That's what embeddings + retrieval are for: finding the *most relevant* free text, not the *exact* one.

## Concretely, in this project

- `Q19` in the evaluation set ("Bahria Town 5 Marla house ka rent kitna hai?") is a deliberate test case: the correct answer lives in `prices.monthly_rent_pkr` (structured), NOT in any FAQ or brochure chunk. When only semantic retrieval is used, the pipeline has no correct source to ground on and — as the evaluation results show — it currently answers from a mismatched FAQ chunk instead of refusing or routing to SQL. This is exactly the hallucination failure mode the structured/semantic split exists to prevent.
- The fix (for the production agent, beyond this offline demo pipeline): the LLM's tool-calling layer should route price/availability/size/agent questions to `structured_retrieval.py` functions as tools, and only fall back to the RAG pipeline for descriptive/FAQ questions. See `evaluation/results.json` (Q19) for the failure this justifies fixing.
