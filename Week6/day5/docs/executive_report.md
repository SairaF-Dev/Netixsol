# AFL Assistant — Executive Report

## 1. Product Goal
The product is a domain-locked AFL assistant combining grounded AFL conversation with machine-learning predictions. It is designed to answer supported AFL questions, retrieve historical statistics from structured data, and provide match-winner/top-player predictions without presenting model output as certainty.

## 2. Architecture
The system uses LangGraph for controlled orchestration. A deterministic guardrail checks for prompt-injection patterns before the LLM router. The router selects factual, retrieval, prediction or off-topic paths. Retrieval uses structured AFL snapshots. Prediction tools call the trained Week 6 models. Validation prevents unsupported results from being presented. A formatter produces the final response.

## 3. Evaluation
The project includes 25+ regression cases covering factual Q&A, prediction sanity, guardrails/injection and multi-turn behavior. Run the evaluation against the real Week 6 artifacts and record the generated pass rates in the final report.

## 4. Benchmark
The recommended baseline is a ladder-position-based naive predictor: choose the team with the better prior ladder rank. Evaluate it on the same historical test period as the ML model. Report identical metrics for a fair comparison.

## 5. Known Limitations
- Prediction quality is limited by the training data and feature design.
- The supplied artifacts do not provide a live fixture/date resolver.
- Current retrieval is structured and intentionally narrower than general semantic search.
- The top-player model produces a ranking rather than certainty.
- Guardrail patterns cover common injection styles but cannot guarantee resistance to every future phrasing.
- Data freshness depends on the weekly refresh process.

## 6. Recommended Next Steps
Add a live fixture feed, expand retrieval coverage, add stronger adversarial evaluation, track calibration and drift, and automate the weekly data/model refresh pipeline.
