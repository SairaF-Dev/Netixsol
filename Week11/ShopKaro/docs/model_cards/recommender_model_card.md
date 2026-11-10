# Model Card: ShopKaro Recommender (Item-to-Item CF + Business Re-Ranker)

_Last updated: 2026-11-10. All numbers below are reproducible with the commands in "How to reproduce"._

## Model details
- **Production model:** item-to-item collaborative filtering (shrunk cosine similarity, top-80 neighbours per item,
  log-dampened implicit weights), `src/shopkaro/recommendations/collaborative.py::ItemToItemCFRecommender`.
- **Why this model:** chosen on Day 2 when it had the highest NDCG@10. The neural two-tower added on 2026-11-10 now
  scores higher (below), but item-CF stays in production for simplicity and cost: item-CF needs no per-user training, so a
  user's new clicks can be scored instantly (real-time personalisation) in a few milliseconds.
- **Serving pipeline** (`src/shopkaro/recommendations/serving.py`, `GET /recommendations/{user_id}`):
  1. User vector = stored history + live session clicks (`POST /events`; view=1, add-to-cart=3, purchase=6).
  2. Scores = user vector x item-item similarity matrix (same scoring code that was evaluated).
  3. `BusinessReRanker`: removes out-of-stock and already-bought items, max 2 items per brand, margin / sale
     boosts, optional festival boost (`?occasion=Eid|Ramadan|11.11|Shaadi|Winter`).
  4. Per-item explanation stating the actual reason: `revisit` (user viewed it before), `similar_to_history`
     (names the history item that contributed most), or `popular_in_category`.
- **Implementation note (updated 2026-11-10):** ALS uses the `implicit` library on Python 3.11 (scipy fallback
  elsewhere). Model 7 is now honestly named **Hybrid Blend**: a hand-weighted mix of CF, ALS, content and feature
  scores. Model 8 is a **real neural two-tower trained with PyTorch**
  (`src/shopkaro/recommendations/two_tower.py`), described below.

## Neural two-tower (model 8)
- **Item tower:** item-ID embedding (32-d) + 64-d text embedding (title/description) + category and price-band
  embeddings -> MLP -> L2-normalised 64-d vector.
- **User tower:** weighted mean of the user's history items (ID and text embeddings) -> MLP -> 64-d vector. No
  per-user ID, so any user with one click gets a vector.
- **Training:** train split only; leave-one-out (399k examples/epoch from users with >= 2 items); in-batch softmax,
  temperature 0.05, logQ popularity correction, duplicate targets masked; 20% item-ID dropout so the tower learns to
  embed brand-new items from content alone. Adam, lr 2e-3, batch 1024, ~35 s/epoch on an idle 10-thread CPU (much slower when the machine is busy).
- **Selection on validation only:** epochs (early stopping, patience 2) plus two serving knobs, `pop_weight`
  (how much log-popularity to add back after logQ training) and `revisit_boost` (same convention as the other
  models). Final run (seed 42): best epoch 7 of 9 (`reports/day2_two_tower_training_log.json`); it picked pop_weight 0.5
  and revisit_boost 40 (the largest grid value: on this data revisits are strong).
- **New users:** onboarding category -> pseudo-history of that category's 100 most-interacted items -> user tower;
  +5 bonus for items in the category, plus 4 x log-popularity (settings chosen on 2,000 validation new users).
- **Serving:** the trained weights are exported to numpy, so scoring needs no torch.
- **Not yet the production model.** Production still serves item-CF (real-time click updates, 8 ms p95, small
  artifact). Switching would need the user tower in the serving path and a latency check.
- **Reproducible:** retraining with the same seed now gives identical numbers (seed 42 = 0.1357 in the Day 2
  table, the discovery run and the seed run). Three fixes: SQL results put in a fixed order (DuckDB `GROUP BY` order
  changed between runs, and `LIMIT` without a tie-break changed the validation/test user sets), and torch pinned to
  8 threads while training (thread count changes float sums). Across seeds 42/43/44
  (`scripts/run_two_tower_seeds.py` -> `reports/day2_two_tower_seeds.csv`): main NDCG@10 **0.1355 +- 0.0005**
  (0.1349-0.1358), discovery 0.0244 +- 0.0012, new users 0.0228 +- 0.0007. Every seed beats the hybrid blend
  (0.1333) and item-CF (0.1307) on main and discovery; on new users it ties the blend (0.0227).

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
| Most popular in favourite category | 0.0112 | 0.0192 | 3.2% | 0.44% | 0% |
| Trending (7 days) | 0.0008 | 0.0015 | 0.5% | 0.04% | 0% |
| **Item-to-item CF (production)** | **0.1307** | **0.1419** | **18.1%** | 33.6% | 0% |
| ALS (`implicit`) | 0.1299 | 0.1464 | 18.9% | 28.0% | 0% |
| Content-based (text embeddings) | 0.1207 | 0.1235 | 15.7% | 68.0% | 7.3% |
| Hybrid blend (CF + ALS + content + features) | 0.1333 | 0.1475 | 18.9% | 34.3% | 7.3% |
| **Neural two-tower (PyTorch)** | **0.1357** | **0.1522** | **19.3%** | **52.3%** | **8.8%** |

Paired bootstrap over the 5,000 users (`reports/day2_two_tower_significance.json`, same seed-42 model):
two-tower minus hybrid blend = +0.0024 NDCG (95% CI +0.0007 to +0.0041, p = 0.002); minus item-CF = +0.0049
(CI +0.0030 to +0.0069); minus ALS = +0.0058 (CI +0.0036 to +0.0081). Small but statistically real.

### Important caveat: most of that gain is re-showing items the user already browsed
`scripts/run_day2_discovery_eval.py` -> `reports/day2_discovery_evaluation.csv` (5,000 warm test users):

| Protocol | Model | NDCG@10 |
|---|---|---|
| Main protocol | Most popular | 0.0035 |
| Main protocol | **Repeat the user's own history (no model)** | **0.1345** |
| Main protocol | Item-to-item CF | 0.1307 |
| **Discovery** (only items never seen in training; seen items not recommended) | Most popular | 0.0024 |
| **Discovery** | **Item-to-item CF** | **0.0149 (6.2x popularity)** |
| Discovery | ALS | 0.0229 (9.6x) |
| **Discovery** | **Neural two-tower** | **0.0257 (10.7x popularity, +73% vs item-CF)**, coverage 43% vs 12% |

**Reading this honestly:** on the main protocol a no-model "show your history" list scores as well as item-CF, so
the headline ~40x gain over popularity is mostly a revisit effect. On genuine discovery of new products item-CF
still beats popularity by **6.2x**, which meets the brief's target (>= +20% NDCG@10 over popularity). Production
therefore shows both kinds of items and labels each with its real reason (`reason_type`).

### Cold start
- **New users:** popularity, restricted to onboarding categories when given (`POST /onboarding/{user_id}`). After
  the first click (`POST /events`) the user is scored by item-CF on that click immediately.
- **New items:** item-CF cannot recommend an item with no interactions. `GET /similar/{product_id}` uses content
  (title + description) embeddings and works for new items. In the Day 2 table only content-based, hybrid blend and
  neural two-tower reached cold items (cold-item hit rate 7.3%, 7.3% and 8.8%).
- New users with an onboarding category: two-tower cold-user NDCG@10 0.0220 (seed 42; 0.0228 +- 0.0007 over 3 seeds)
  vs hybrid blend 0.0227 vs popularity 0.0027 (on par). The simulated onboarding answer is the category of the user's first test
  event, so these numbers are optimistic for all models.

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
python scripts/run_day2_task4.py              # main comparison table (trains the neural two-tower, needs torch)
python scripts/run_day2_discovery_eval.py     # discovery protocol + repeat-history baseline
python scripts/precompute_recommendations.py  # train serving artifact (models/item_cf_serving.joblib)
python -m pytest tests/test_realtime_recommendations.py
```
