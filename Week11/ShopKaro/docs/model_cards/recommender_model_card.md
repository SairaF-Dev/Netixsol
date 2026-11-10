# Model Card: ShopKaro Recommender (Item-to-Item CF + Business Re-Ranker)

_Last updated: 2026-11-09. All numbers below are reproducible with the commands in "How to reproduce"._

## Model details
- **Production model:** item-to-item collaborative filtering (shrunk cosine similarity, top-80 neighbours per item,
  log-dampened implicit weights), `src/shopkaro/recommendations/collaborative.py::ItemToItemCFRecommender`.
- **Why this model:** highest NDCG@10 of the 7 Day 2 models (table below). The ALS and hybrid models are within
  0.5 NDCG points of it, so the deciding factors were simplicity and cost: item-CF needs no per-user training, so a
  user's new clicks can be scored instantly (real-time personalisation) in a few milliseconds.
- **Serving pipeline** (`src/shopkaro/recommendations/serving.py`, `GET /recommendations/{user_id}`):
  1. User vector = stored history + live session clicks (`POST /events`; view=1, add-to-cart=3, purchase=6).
  2. Scores = user vector x item-item similarity matrix (same scoring code that was evaluated).
  3. `BusinessReRanker`: removes out-of-stock and already-bought items, max 2 items per brand, margin / sale
     boosts, optional festival boost (`?occasion=Eid|Ramadan|11.11|Shaadi|Winter`).
  4. Per-item explanation stating the actual reason: `revisit` (user viewed it before), `similar_to_history`
     (names the history item that contributed most), or `popular_in_category`.
- **Implementation note:** built with scipy / scikit-learn, not the `implicit` or LightFM libraries named in the
  brief. The "ALS" model is an SVD warm start + alternating ridge refinement; the "two-tower hybrid" is a weighted
  blend of CF, content and feature scores, not a trained neural two-tower model.

## Training data and splits
- Interactions: RetailRocket events mapped to a synthetic Pakistani catalogue of 25,000 products. Each product's
  Pakistani category comes from its real RetailRocket category subtree (`src/shopkaro/data/category_mapping.py`,
  table `category_mapping`), so products shoppers browse together share sensible categories.
- Chronological split (never random, so the model is never trained on the future it is tested on):

| Split | Dates | Interactions | Users |
|---|---|---|---|
| Train | 2025-03-01 to 2025-05-25 | 1,395,348 | 549,150 |
| Validation | 2025-05-25 to 2025-06-19 | 299,003 | 159,203 |
| Test | 2025-06-19 to 2025-07-17 | 299,004 | 162,386 |
| Cold-start test (users unseen in train) | 2025-06-19 to 2025-07-17 | 278,031 | 156,238 |

- The **serving** model is retrained daily on all history (`interactions_clean`, 849,398 users) by
  `scripts/precompute_recommendations.py`, after model selection on the splits above.

## Evaluation (K = 10)
### Main Day 2 protocol (`reports/day2_model_comparison.csv`, 5,000 warm test users)
A hit = any test-period interaction (views included) with a recommended item.

| Model | NDCG@10 | Recall@10 | Hit rate | Coverage | Cold-item hit rate |
|---|---|---|---|---|---|
| Most popular overall | 0.0034 | 0.0066 | 1.1% | 0.04% | 0% |
| Most popular in favourite category | 0.0115 | 0.0192 | 3.2% | 0.44% | 0% |
| Trending (7 days) | 0.0008 | 0.0015 | 0.5% | 0.04% | 0% |
| **Item-to-item CF (production)** | **0.1307** | **0.1419** | **18.1%** | 33.6% | 0% |
| ALS-style matrix factorisation | 0.1278 | 0.1384 | 18.0% | 35.2% | 0% |
| Content-based (text embeddings) | 0.1207 | 0.1235 | 15.7% | 68.0% | 7.3% |
| Hybrid (CF + content + features) | 0.1298 | 0.1406 | 18.1% | 32.8% | 7.3% |

### Important caveat: most of that gain is re-showing items the user already browsed
`scripts/run_day2_discovery_eval.py` -> `reports/day2_discovery_evaluation.csv` (5,000 warm test users):

| Protocol | Model | NDCG@10 |
|---|---|---|
| Main protocol | Most popular | 0.0035 |
| Main protocol | **Repeat the user's own history (no model)** | **0.1342** |
| Main protocol | Item-to-item CF | 0.1307 |
| **Discovery** (only items never seen in training; seen items not recommended) | Most popular | 0.0024 |
| **Discovery** | **Item-to-item CF** | **0.0149 (6.2x popularity)** |

**Reading this honestly:** on the main protocol a no-model "show your history" list scores as well as item-CF, so
the headline ~40x gain over popularity is mostly a revisit effect. On genuine discovery of new products item-CF
still beats popularity by **6.2x**, which meets the brief's target (>= +20% NDCG@10 over popularity). Production
therefore shows both kinds of items and labels each with its real reason (`reason_type`).

### Cold start
- **New users:** popularity, restricted to onboarding categories when given (`POST /onboarding/{user_id}`). After
  the first click (`POST /events`) the user is scored by item-CF on that click immediately.
- **New items:** item-CF cannot recommend an item with no interactions. `GET /similar/{product_id}` uses content
  (title + description) embeddings and works for new items. In the Day 2 table only content-based and hybrid models
  reached cold items (cold-item hit rate 7.3%).

### Latency (local, Windows, in-process test client)
Model compute p95: 8 ms (typical user), 22 ms (heaviest user, 2,921 history items), 1.5 ms (new visitor).
Through the API, uncached p95: 14-43 ms; cached ~10 ms. Target < 100 ms: met.

## Known limitations
- **Category coherence (fixed 2026-11-09).** Categories were originally random per item, so 12% of CF neighbours
  shared a category (= chance). After mapping RetailRocket's category tree: **71%** of top-10 CF neighbours and
  **97%** of mined "bought together" rules share a category; 54% of all co-browsed product pairs do.
- **Homepages of active users are mostly revisits.** The revisit boost (inherited from Day 2 tuning) fills the top
  slots with items the user already viewed. It maximises the main-protocol NDCG, but a production homepage would
  likely cap revisits (e.g. 4 of 10 slots) to leave room for discovery. Not implemented; a product decision.
- Session events and onboarding answers are in memory per API process (lost on restart). Use Redis for several workers.
- Stock levels are read at API start-up, not live.

## How to reproduce
```bash
python scripts/run_day2_task4.py              # main comparison table
python scripts/run_day2_discovery_eval.py     # discovery protocol + repeat-history baseline
python scripts/precompute_recommendations.py  # train serving artifact (models/item_cf_serving.joblib)
python -m pytest tests/test_realtime_recommendations.py
```
