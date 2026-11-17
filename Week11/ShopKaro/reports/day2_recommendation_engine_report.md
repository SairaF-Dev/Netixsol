# ShopKaro AI — Day 2 Recommendation Engine & Merchandising Report

> **Updated 2026-11-17:** every number in sections 1–4 was re-measured on the current data (per-product-type prices
> and brands, rebuilt 2026-11-16). The addenda in section 5 explain *why* the numbers moved (category fix, neural
> two-tower) and are kept for history.

**Stage:** Day 2 — Recommendation Engine (Weight: 20%)  
**Database:** `data/processed/shopkaro.duckdb`  
**Comparison table:** `reports/day2_model_comparison.csv` · **Discovery table:** `reports/day2_discovery_evaluation.csv`  
**Comparison figure:** `reports/figures/08_recommender_model_comparison.png`

---

## 1. Executive Summary

Day 2 replaces ShopKaro's static *"Best Sellers"* widget with a two-stage **personalised recommendation and business
re-ranking engine** on a very sparse Pakistani marketplace: `25,000` SKUs, `549,150` training users and `1,395,348`
chronological training interactions (about 99.99% of the user × item matrix is empty).

1. **Task 1 — Baselines (`baselines.py`):** Most Popular Overall, Most Popular in the User's Favourite Category, and
   Recently Trending (last 7 days).
2. **Task 2 — Collaborative filtering (`collaborative.py`):** shrinkage-regularised item-to-item cosine CF ("Similar
   Products") and implicit ALS matrix factorisation ("Recommended For You"), tuned over 4 configurations on
   `val_interactions`.
3. **Task 3 — Content, hybrid and cold start (`hybrid.py`, `two_tower.py`):** a content model on 64-dim text
   embeddings, a hand-weighted **Hybrid Blend** (item-CF + ALS + content + features), and a trained **Neural
   Two-Tower (PyTorch)**. Cold-start routing covers `155,661` test users never seen in training and `585` test items
   with zero training clicks.
4. **Task 4 — Offline evaluation (`evaluation.py`):** all 8 models on the chronological test set: Precision, Recall,
   NDCG, MAP and HitRate @10, catalogue coverage, intra-list diversity, novelty and cold-start metrics, plus a
   discovery protocol and paired-bootstrap significance.
5. **Task 5 — Business re-ranking (`reranking.py`):** out-of-stock and already-purchased removal, brand cap
   (`max 2 per brand`), margin and sale boosts, Pre-Eid boost, `48,609` mined **Frequently Bought Together** rules,
   and Roman Urdu explanations.

**Headline:** the neural two-tower is the most accurate model (NDCG@10 **0.1362**, significantly above the hybrid
blend and item-CF) and the best on genuine discovery (**0.0260**, +75% over item-CF). Item-CF is the default served
model because it is simple and fast; the two-tower is served with `RECOMMENDER=two_tower`.

---

## 2. Offline Evaluation — 8 Models (`K = 10`, chronological test set)

### 2.1 Ranking accuracy (`5,000` warm test users)

| # | Model | Family | Precision@10 | Recall@10 | NDCG@10 | MAP@10 | HitRate@10 |
| :-: | :-- | :-- | :-: | :-: | :-: | :-: | :-: |
| 1 | Most Popular Overall | Baseline | 0.0011 | 0.0066 | 0.0035 | 0.0021 | 1.1% |
| 2 | Most Popular in Favourite Category | Baseline | 0.0035 | 0.0192 | 0.0113 | 0.0072 | 3.2% |
| 3 | Recently Trending (7 days) | Baseline | 0.0006 | 0.0015 | 0.0008 | 0.0003 | 0.5% |
| 4 | Item-to-Item CF (Cosine) | Collaborative | 0.0214 | 0.1419 | 0.1307 | 0.1189 | 18.1% |
| 5 | Implicit ALS | Collaborative | 0.0223 | 0.1464 | 0.1299 | 0.1159 | 18.9% |
| 6 | Content-Based (Text Embeddings) | Content | 0.0177 | 0.1239 | 0.1210 | 0.1124 | 15.7% |
| 7 | Hybrid Blend | Hybrid | 0.0228 | 0.1488 | 0.1339 | 0.1204 | 19.1% |
| 8 | **Neural Two-Tower (PyTorch)** | Neural | **0.0233** | **0.1527** | **0.1362** | **0.1222** | **19.5%** |

### 2.2 Beyond accuracy and cold start (`2,000` new users; cold items = test items with no training clicks)

| # | Model | Catalogue Coverage | ILD@10 | Novelty (bits) | Cold-user NDCG@10 | Cold-item HitRate@10 |
| :-: | :-- | :-: | :-: | :-: | :-: | :-: |
| 1 | Most Popular Overall | 0.04% | 0.923 | 9.2 | 0.0027 | 0% |
| 2 | Most Popular in Favourite Category | 0.44% | 0.496 | 10.3 | 0.0027 | 0% |
| 3 | Recently Trending (7 days) | 0.04% | 0.880 | 11.8 | 0.0013 | 0% |
| 4 | Item-to-Item CF | 33.6% | 0.494 | 11.2 | 0.0027 | 0% |
| 5 | Implicit ALS | 28.0% | 0.589 | 11.8 | 0.0027 | 0% |
| 6 | Content-Based | **65.0%** | 0.098 | **13.6** | 0.0027 | 5.2% |
| 7 | Hybrid Blend | 34.5% | 0.462 | 11.5 | **0.0231** | 5.2% |
| 8 | Neural Two-Tower | 50.2% | 0.553 | 12.7 | 0.0227 | **7.6%** |

**Reading the tables**

- **Significance** (paired bootstrap, 2,000 resamples, `reports/day2_two_tower_significance.json`, written by
  `scripts/run_day2_task4.py` on the same users as the table): two-tower vs hybrid blend +0.0024 NDCG
  (95% CI +0.0007..+0.0040, p = 0.001); vs item-CF +0.0055; vs ALS +0.0063.
- **Revisit effect:** a no-model "repeat the user's own history" list scores about as well as item-CF on this
  protocol, so most of the gain over popularity here comes from users re-viewing items. The **discovery protocol**
  (only never-seen items count) removes that: two-tower **0.0260**, ALS 0.0229, item-CF 0.0149, popularity 0.0024.
- **Content-based** has the highest coverage and novelty but the lowest diversity (0.098): its ten nearest
  neighbours are usually ten near-identical items.
- **Cold users:** models without onboarding fall back to popularity (0.0027). The hybrid blend and the two-tower use
  the onboarding category and reach about 0.023 (roughly 8x). Caveat: the simulated onboarding answer is taken from
  the user's own first test event, so these numbers are optimistic.
- **Seeds 42/43/44** (`reports/day2_two_tower_seeds.csv`): main NDCG 0.1360 ± 0.0004, discovery 0.0257 ± 0.0004,
  new users 0.0226 ± 0.0007. Every seed beats the blend and item-CF on main and discovery.

---

## 3. Task 2 — Implicit ALS Tuning (validation split)

| Config | Factors | Regularisation | Alpha | Iterations | Fit time | Val NDCG@10 | Val HitRate@10 |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 1 | 32 | 0.05 | 15 | 6 | 10.6 s | 0.2421 | 44.7% |
| 2 | 64 | 0.10 | 25 | 10 | 18.2 s | 0.2424 | 46.1% |
| 3 | 64 | 0.50 | 40 | 12 | 22.0 s | 0.2399 | 45.9% |
| **4 (selected)** | **96** | **0.10** | **30** | **10** | **18.9 s** | **0.2466** | **46.9%** |

The configurations are close (0.240–0.247). Config 4 is chosen on validation and then scored once on test
(NDCG@10 0.1299). Validation scores are higher than test scores because the validation window sits right after the
training data.

---

## 4. Task 5 — Business Re-Ranking and Association Rules (`300` buyer users, top-10)

| Merchandising metric | Raw ML top-10 | After `BusinessReRanker` | Effect |
| :-- | :-: | :-: | :-- |
| Max items from one brand | 9 | **2** | Brand cap (`max_per_brand = 2`); the candidate pool widens when too few brands are available |
| Average unique brands | 5.51 | **6.40** | More brands per list |
| Average gross margin | 35.01% | **36.51%** | +1.5 percentage points from the margin boost |
| On-sale item share | 27.3% | **66.3%** | Active deals surfaced |
| Out-of-stock candidates removed | — | **1,841** | No out-of-stock impressions |
| Already-purchased candidates removed | — | **414** | No "buy it again" for one-off items |
| Eid-category share (normal → Pre-Eid mode) | 60.9% | **63.0%** | Seasonal shift towards festive categories |
| Mined session rules (A ⇒ B) | — | **48,609** | Powers "Frequently Bought Together" |

These are offline list properties, not measured revenue. The margin and sale boosts trade a little relevance for
commercial goals; Day 5's A/B simulation measures the combined effect.

### Sample output (from `scripts/run_day2_task5.py`)

- **Pre-Eid recommendation** (`SK-07193`, Republic Womenswear velvet formal shawl, PKR 16,150, on sale):
  > *"Eid festive season ke liye Republic Womenswear ka yeh Velvet Formal Shawl aap ki pasand ke mutabiq top choice hai."*
- **Phone accessory bundle** (`SK-00013` Samsung Galaxy A55 5G ⇒ `SK-00014` Samsung accessory PKR 4,200 and
  `SK-00015` Baseus accessory PKR 1,450):
  > *"Kyun ke aap ne Samsung Galaxy dekha, yeh covers aur chargers bhi pasand kiye ja rahe hain."*

  This pair is a **curated** bundle rule (`rule_source = Curated_Accessory_Bundle_FP_Growth`), not mined from sessions.
- **Limitation of mined rules:** rules between rare items can show very high lift on tiny support, e.g. the Sapphire
  lawn suit (`SK-00001`) ⇒ an Anker charger (confidence 0.10, lift 1,035). A minimum-support or same-category filter
  would make the widget more sensible.

---

## 5. History

The two addenda below record how the results got here. Numbers quoted inside them are from the date in their
heading; sections 1–4 above are current.

### Addendum (2026-11-09): data fix, revisit effect, discovery evaluation and production serving

1. **Category fix.** Product categories were originally assigned to RetailRocket items at random, so only 12% of
   item-CF neighbours (and 12% of mined "bought together" rules) shared a category, i.e. pure chance. Categories now
   follow RetailRocket's real category tree (`src/shopkaro/data/category_mapping.py`): **71%** of CF neighbours and
   **97%** of mined rules share a category. All Day 2-5 artefacts were regenerated.
2. **Comparison on 2026-11-09 (5,000 users):** item-CF NDCG@10 **0.1307** (best), hybrid 0.1298, ALS 0.1278,
   content 0.1207, favourite-category popularity 0.0115, popularity 0.0034.
3. **Revisit effect.** The main protocol counts any test interaction as a hit, including re-views of items already
   browsed. A no-model "repeat the user's own history" list scores **0.1345**, about the same as item-CF, so most of
   the gain over popularity on this protocol is a revisit effect.
4. **Discovery protocol** (only items never seen in training; seen items excluded): item-CF **0.0149** vs
   popularity **0.0024**, i.e. **6.2x**. The brief's target (>= +20% NDCG@10 over popularity) is met on genuine discovery.
5. **Determinism fixes:** evaluation users and catalogue items are now selected with ID tie-breakers, so reruns give
   identical numbers. Tests now run on a temporary copy of the data (`tests/conftest.py`) and no longer overwrite
   these reports with smaller test samples (the earlier 500-user CSV was such a test artefact).
6. **Production model:** item-to-item CF, served in real time with live session clicks and the business re-ranker,
   with per-item explanations stating the real reason. See `docs/model_cards/recommender_model_card.md`.


### Addendum (2026-11-10): real neural two-tower (PyTorch) and the 8-model table

Model 7 was renamed **Hybrid Blend**: it is a hand-weighted mix of scores, not a trained two-tower. A real two-tower
was added as model 8 (`src/shopkaro/recommendations/two_tower.py`): item tower = ID + text + category + price-band
embeddings, user tower = weighted mean of history items, in-batch softmax with logQ correction, 20% item-ID dropout,
trained on `train_interactions` only; epochs and serving knobs chosen on `val_interactions`.

Numbers after the two-tower was added (re-measured 2026-11-16 on the current data; same as section 2):

| # | Model | NDCG@10 | Recall@10 | HitRate@10 | Coverage | Novelty | Cold-user NDCG | Cold-item HitRate |
|:-:|:--|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | Most Popular Overall | 0.0035 | 0.0066 | 1.1% | 0.04% | 9.2 | 0.0027 | 0% |
| 2 | Most Popular in Favourite Category | 0.0112 | 0.0192 | 3.2% | 0.44% | 10.3 | 0.0027 | 0% |
| 3 | Trending (7 days) | 0.0008 | 0.0015 | 0.5% | 0.04% | 11.8 | 0.0013 | 0% |
| 4 | Item-to-Item CF | 0.1307 | 0.1419 | 18.1% | 33.6% | 11.2 | 0.0027 | 0% |
| 5 | Implicit ALS | 0.1299 | 0.1464 | 18.9% | 28.0% | 11.8 | 0.0027 | 0% |
| 6 | Content-Based | 0.1210 | 0.1239 | 15.7% | 65.0% | 13.6 | 0.0027 | 5.2% |
| 7 | Hybrid Blend | 0.1339 | 0.1488 | 19.1% | 34.5% | 11.5 | **0.0231** | 5.2% |
| 8 | **Neural Two-Tower (PyTorch)** | **0.1362** | **0.1527** | **19.5%** | 50.2% | 12.7 | 0.0227 | **7.6%** |

- **Significance** (paired bootstrap, 2,000 resamples, `reports/day2_two_tower_significance.json`): two-tower vs
  hybrid blend +0.0024 NDCG (95% CI +0.0007..+0.0040, p = 0.001); vs item-CF +0.0055 (CI +0.0036..+0.0074).
- **Discovery protocol** (only items never seen in training; `reports/day2_discovery_evaluation.csv`): two-tower
  0.0260 NDCG@10 vs item-CF 0.0149 (+75%), ALS 0.0229, popularity 0.0024; catalogue coverage 40% vs 12% for item-CF.
  This is where the learned model helps most.
- **New users (fixed 2026-11-10):** the two-tower now uses the onboarding category: the category's most-interacted
  items form a pseudo-history for the user tower, items outside the category are filtered, and a popularity weight is
  added. Settings were chosen on 2,000 *validation* new users (n_seed 100, pop_weight 4; category bonus 1000 for seed 42, 5 for seeds 43/44). Cold-user NDCG@10 went from
  0.0024 (popularity fallback) to **0.0227** (seed 42; 0.0226 +- 0.0007 over seeds 42-44), on par with the hybrid blend's 0.0231. A probe showed the tower adds ~9% (validation) over plain
  "popular in that category".
- **Cold-user test set made deterministic:** the query took the top 2,000 new users without a tie-break and a random
  `ANY_VALUE` category, so cold-user numbers moved between runs. Now ties break by user_id and the simulated onboarding
  answer is the category of the user's first event. Caveat for every model: that answer comes from the user's own test
  behaviour, so cold-user numbers are optimistic.
- **Reproducibility (fixed 2026-11-10):** same seed -> identical numbers in every script (fixed SQL ordering +
  tie-breaks, torch pinned to 8 threads). Seeds 42/43/44 (`reports/day2_two_tower_seeds.csv`): main NDCG@10
  0.1360 +- 0.0004, discovery 0.0257 +- 0.0004, new users 0.0226 +- 0.0007; every seed beats blend and item-CF on
  main and discovery.
- Serving: item-CF by default; the two-tower is served with `RECOMMENDER=two_tower` (live clicks, onboarding,
  p95 4.8 ms uncached end-to-end; `reports/recommender_serving_latency.json`). See the recommender model card.
