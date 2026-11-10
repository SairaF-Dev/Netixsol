# ShopKaro AI — Day 2 Recommendation Engine & Merchandising Report

> **Updated 2026-11-10:** results below were re-measured with the real libraries on Python 3.11; see `reports/library_migration_py311.md` for before/after numbers.

**Stage:** Day 2 — Recommendation Engine (Weight: 20%)  
**Database:** [`data/processed/shopkaro.duckdb`](file:///d:/Netixsol/Week11/ShopKaro/data/processed/shopkaro.duckdb)  
**Comparison Table:** [`reports/day2_model_comparison.csv`](file:///d:/Netixsol/Week11/ShopKaro/reports/day2_model_comparison.csv)  
**Comparison Figure:** [`reports/figures/08_recommender_model_comparison.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/08_recommender_model_comparison.png)

---

## 1. Executive Summary

Day 2 replaces ShopKaro's static *"Best Sellers"* widget with a two-stage **Personalized Recommendation & Business Re-Ranking Engine** engineered for a `99.9940%` sparse Pakistani marketplace (`25,000` SKUs, `549,399` users, `1,394,328` chronological training interactions):

1. **Task 1 — Baselines (`baselines.py`):** Built and benchmarked `Most Popular Overall`, `Most Popular in User's Favourite Category`, and `Recently Trending (Last 7 Days)`.
2. **Task 2 — Collaborative Filtering (`collaborative.py`):** Implemented shrinkage-regularized **Item-to-Item Cosine CF** ("Similar Products" & "Customers Who Viewed This Also Viewed") and Hu–Koren–Volinsky **Implicit ALS Matrix Factorisation** ("Recommended For You"), tuned across 4 hyperparameter configurations on `val_interactions`.
3. **Task 3 — Content-Based, Hybrid Two-Tower & Cold-Start (`hybrid.py`):** Combined 64-dim SVD product text embeddings (`models/item_text_embeddings.npy`), category/brand/price-band user profiles, Item-CF, and Implicit ALS into a unified **Two-Tower Hybrid Recommender**, with explicit cold-start routing for `155,555` unseen users and `588` zero-click cold items.
4. **Task 4 — Comprehensive Offline Evaluation (`evaluation.py`):** Evaluated all 7 models on the strict chronological test set across `Precision@10`, `Recall@10`, `NDCG@10`, `MAP@10`, `HitRate@10`, `Catalogue Coverage`, `Intra-List Diversity (ILD@10)`, `Self-Information Novelty (Bits@10)`, and Cold-Start metrics.
5. **Task 5 — Business Re-Ranking, Association Rules & Roman Urdu Explanations (`reranking.py`):** Added out-of-stock & already-purchased removal, brand diversity capping (`max 2 per brand`), high-margin & active-sale boosts, Pre-Eid seasonal boosting, `48,484` mined **Frequently Bought Together** session association rules (`Support`, `Confidence`, `Lift`), and dynamic **Roman Urdu** explanations.

---

## 2. Full 7-Model Offline Evaluation (original Day 2 run; superseded by the 2026-11-10 addendum at the end) (`K = 10`, Chronological Test Set)

### 2.1 Ranking Accuracy Metrics (`5,000` Warm Test Users)

| # | Model Name | Family | Precision@10 | Recall@10 | NDCG@10 | MAP@10 | HitRate@10 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `Most Popular Overall` | Baseline | `0.00110` | `0.00643` | `0.00346` | `0.00213` | `1.06%` |
| **2** | `Most Popular in User's Favourite Category` | Baseline | `0.00190` | `0.01062` | `0.00734` | `0.00528` | `1.80%` |
| **3** | `Recently Trending (Last 7 Days)` | Baseline | `0.00054` | `0.00149` | `0.00082` | `0.00030` | `0.46%` |
| **4** | **`Item-to-Item CF (Cosine)`** | **Collaborative** | **`0.02012`** | **`0.13561`** | **`0.12715`** | **`0.11685`** | **`17.06%`** |
| **5** | **`Implicit Matrix Factorisation (ALS)`** | **Collaborative** | **`0.01916`** | **`0.13091`** | **`0.12413`** | **`0.11426`** | **`16.80%`** |
| **6** | `Content-Based (Text Embeddings)` | Content-Based | `0.01574` | `0.11454` | `0.11512` | `0.10844` | `14.46%` |
| **7** | **`Hybrid Two-Tower (CF + Content + Features)`** | **Hybrid** | **`0.01926`** | **`0.13047`** | **`0.12456`** | **`0.11491`** | **`16.62%`** |

### 2.2 Beyond-Accuracy & Cold-Start Metrics (`2,000` Cold Users, `588` Cold Items)

| # | Model Name | Catalogue Coverage | Intra-List Diversity (`ILD@10`) | Novelty (`Bits@10`) | Cold-User `NDCG@10` | Cold-Item `HitRate@10` |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `Most Popular Overall` | `0.040%` (10 SKUs) | `0.9213` | `9.218 bits` | `0.00309` | `0.00%` |
| **2** | `Most Popular in Favourite Category` | `0.440%` (110 SKUs) | `0.5111` | `10.226 bits` | `0.00309` | `0.00%` |
| **3** | `Recently Trending (Last 7 Days)` | `0.040%` (10 SKUs) | `0.9639` | `11.763 bits` | `0.00143` | `0.00%` |
| **4** | `Item-to-Item CF (Cosine)` | `33.080%` (8,270 SKUs) | `0.5552` | `11.129 bits` | `0.00309` | `0.00%` |
| **5** | `Implicit Matrix Factorisation (ALS)` | `34.724%` (8,681 SKUs) | `0.5413` | `11.266 bits` | `0.00309` | `0.00%` |
| **6** | **`Content-Based (Text Embeddings)`** | **`69.232%` (17,308 SKUs)** | `0.1057` | **`13.803 bits`** | `0.00309` | **`2.77%`** |
| **7** | **`Hybrid Two-Tower (CF + Content + Features)`** | **`31.188%` (7,797 SKUs)** | **`0.4905`** | **`11.096 bits`** | **`0.00839` (+171.5%)** | **`2.77%`** |

---

## 3. Task 2 Hyperparameter Tuning Summary (Implicit ALS on Validation Split)

| Config # | Latent Factors ($f$) | Regularization ($\lambda$) | Confidence Scaling ($\alpha$) | Iterations | Fit Time (s) | Val `NDCG@10` | Val `HitRate@10` |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `32` | `0.05` | `15.0` | `8` | `6.5s` | `0.22164` | `25.85%` |
| 2 | `64` | `0.08` | `25.0` | `10` | `9.2s` | `0.23912` | `28.10%` |
| 3 | `64` | `0.15` | `40.0` | `10` | `9.4s` | `0.24105` | `28.35%` |
| **4 (Selected)** | **`96`** | **`0.10`** | **`30.0`** | **`10`** | **`12.8s`** | **`0.24838`** | **`29.40%`** |

---

## 4. Task 5 Business Re-Ranking & Association Rules Impact (`300` Buyer Users)

| Merchandising Metric | Raw ML Candidates (Top-10) | After `BusinessReRanker` (Top-10) | Business Impact |
| :--- | :---: | :---: | :--- |
| **Max Items from a Single Brand in Top-10** | `7` items | **`2` items** | Eliminates single-brand monotony (`max_per_brand = 2`) |
| **Average Unique Brands in Top-10** | `6.91` brands | **`7.10` brands** | Higher cross-brand marketplace discovery |
| **Average Gross Margin (%)** | `35.10%` | **`36.74%`** | **`+1.64%` gross margin lift** via commercial weighting |
| **Promotional / On-Sale Item Share (%)** | `33.80%` | **`71.54%`** | Highlights active deals to price-sensitive shoppers |
| **Out-of-Stock Candidates Blocked** | — | **`1,448` blocked** | `0%` out-of-stock impressions in production |
| **Already-Purchased Candidates Filtered** | — | **`809` filtered** | Prevents recommending items already bought by the user |
| **Eid Festival Category Share (Normal vs. Pre-Eid)** | `61.36%` | **`66.46%`** | Automatic seasonal shift toward Lawn, Kurta, Khussa & Fragrances |
| **Mined Session Association Rules ($A \Rightarrow B$)** | — | **`48,484` rules** | Powers real-time *"Frequently Bought Together"* bundles |

### Sample Roman Urdu Explanations Generated by `BusinessReRanker` & `AssociationRulesEngine`
- **Smartphone Accessory Bundle (`SK-00013`: *Samsung Galaxy A55 5G* $\Rightarrow$ `SK-00014` & `SK-00015`):**
  > *"Kyun ke aap ne Samsung Galaxy dekha, yeh covers aur chargers bhi pasand kiye ja rahe hain."* (`Confidence = 0.34, Lift = 18.50`)
- **Pre-Eid Seasonal Recommendation (`SK-00001`: *Sapphire 3-Piece Unstitched Embroidered Lawn Suit*):**
  > *"Eid festive season ke liye Sapphire ka yeh 3-Piece Lawn Suit aap ki pasand ke mutabiq top choice hai."*
- **Recent Interaction + Promotional Discount (`SK-05090`: *Oxford Lunch Box & Water Bottle Set*):**
  > *"Kyun ke aap ne Bata School Lunch dekha, yeh Oxford Lunch Box & Water Bottle Set (20% OFF) bhi pasand kiya ja raha hai."*



---

## Addendum (2026-11-09): data fix, revisit effect, discovery evaluation and production serving

> **The tables above were produced before the 2026-11-09 data fix and are kept for history.** Current numbers are in
> `reports/day2_model_comparison.csv`, `reports/day2_discovery_evaluation.csv` and the recommender model card.

1. **Category fix.** Product categories were originally assigned to RetailRocket items at random, so only 12% of
   item-CF neighbours (and 12% of mined "bought together" rules) shared a category, i.e. pure chance. Categories now
   follow RetailRocket's real category tree (`src/shopkaro/data/category_mapping.py`): **71%** of CF neighbours and
   **97%** of mined rules share a category. All Day 2-5 artefacts were regenerated.
2. **Current comparison (5,000 users):** item-CF NDCG@10 **0.1307** (best), hybrid 0.1298, ALS 0.1278,
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


## Addendum (2026-11-10): real neural two-tower (PyTorch) and the current 8-model table

Model 7 was renamed **Hybrid Blend**: it is a hand-weighted mix of scores, not a trained two-tower. A real two-tower
was added as model 8 (`src/shopkaro/recommendations/two_tower.py`): item tower = ID + text + category + price-band
embeddings, user tower = weighted mean of history items, in-batch softmax with logQ correction, 20% item-ID dropout,
trained on `train_interactions` only; epochs and serving knobs chosen on `val_interactions`.

Current numbers (`reports/day2_model_comparison.csv`, 5,000 warm test users, K = 10):

| # | Model | NDCG@10 | Recall@10 | HitRate@10 | Coverage | Novelty | Cold-user NDCG | Cold-item HitRate |
|:-:|:--|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | Most Popular Overall | 0.0035 | 0.0066 | 1.1% | 0.04% | 9.2 | 0.0027 | 0% |
| 2 | Most Popular in Favourite Category | 0.0112 | 0.0192 | 3.2% | 0.44% | 10.3 | 0.0027 | 0% |
| 3 | Trending (7 days) | 0.0008 | 0.0015 | 0.5% | 0.04% | 11.8 | 0.0013 | 0% |
| 4 | Item-to-Item CF | 0.1307 | 0.1419 | 18.1% | 33.6% | 11.2 | 0.0027 | 0% |
| 5 | Implicit ALS | 0.1299 | 0.1464 | 18.9% | 28.0% | 11.8 | 0.0027 | 0% |
| 6 | Content-Based | 0.1207 | 0.1235 | 15.7% | 68.0% | 13.7 | 0.0027 | 7.3% |
| 7 | Hybrid Blend | 0.1333 | 0.1475 | 18.9% | 34.3% | 11.4 | **0.0227** | 7.3% |
| 8 | **Neural Two-Tower (PyTorch)** | **0.1357** | **0.1522** | **19.3%** | 52.3% | 12.8 | 0.0220 | **8.8%** |

- **Significance** (paired bootstrap, 2,000 resamples, `reports/day2_two_tower_significance.json`): two-tower vs
  hybrid blend +0.0024 NDCG (95% CI +0.0007..+0.0041, p = 0.002); vs item-CF +0.0049 (CI +0.0030..+0.0069).
- **Discovery protocol** (only items never seen in training; `reports/day2_discovery_evaluation.csv`): two-tower
  0.0257 NDCG@10 vs item-CF 0.0149 (+73%), ALS 0.0229, popularity 0.0024; catalogue coverage 43% vs 12% for item-CF.
  This is where the learned model helps most.
- **New users (fixed 2026-11-10):** the two-tower now uses the onboarding category: the category's most-interacted
  items form a pseudo-history for the user tower, items outside the category are filtered, and a popularity weight is
  added. Settings were chosen on 2,000 *validation* new users (n_seed 100, category bonus 5, pop_weight 4). Cold-user NDCG@10 went from
  0.0024 (popularity fallback) to **0.0220** (seed 42; 0.0228 +- 0.0007 over seeds 42-44), on par with the hybrid blend's 0.0227. A probe showed the tower adds ~9% (validation) over plain
  "popular in that category".
- **Cold-user test set made deterministic:** the query took the top 2,000 new users without a tie-break and a random
  `ANY_VALUE` category, so cold-user numbers moved between runs. Now ties break by user_id and the simulated onboarding
  answer is the category of the user's first event. Caveat for every model: that answer comes from the user's own test
  behaviour, so cold-user numbers are optimistic.
- **Reproducibility (fixed 2026-11-10):** same seed -> identical numbers in every script (fixed SQL ordering +
  tie-breaks, torch pinned to 8 threads). Seeds 42/43/44 (`reports/day2_two_tower_seeds.csv`): main NDCG@10
  0.1355 +- 0.0005, discovery 0.0244 +- 0.0012, new users 0.0228 +- 0.0007; every seed beats blend and item-CF on
  main and discovery.
- Production still serves item-CF (real-time click updates, 8 ms p95); see the recommender model card.
