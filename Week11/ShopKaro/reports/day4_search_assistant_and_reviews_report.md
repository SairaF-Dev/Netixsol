# Day 4 Technical Report — Hybrid Search, Conversational UrduLish Shopping Assistant & Review Intelligence

**Project:** ShopKaro — AI Commerce Intelligence Platform (Week 11 Capstone)  
**Module Scope:** Day 4 (`25%` Total Capstone Weight: `15%` Search & Conversational Assistant + `10%` Review Intelligence)  
**Database & Artifacts:** [`data/processed/shopkaro.duckdb`](file:///d:/Netixsol/Week11/ShopKaro/data/processed/shopkaro.duckdb) (`review_intelligence_summary`, `seller_scorecards`), [`models/search_semantic_index.pkl`](file:///d:/Netixsol/Week11/ShopKaro/models/search_semantic_index.pkl)

---

## 1. Executive Summary

Day 4 delivers three interconnected NLP & Information Retrieval pillars tailored for Pakistani e-commerce:
1. **Task 1 — Multilingual Hybrid Search Engine ([`src/shopkaro/search/hybrid_search.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/search/hybrid_search.py)):**
   - Parses English, Urdu, and Roman Urdu (UrduLish) queries (*"shaadi ke liye red lehenga 20 hazaar tak"*, *"sasta gaming phone under 50000"*, *"Ammi ke liye Eid gift chahiye, 3000 tak"*), extracting structured price ceilings (`hazaar` = $1{,}000$, `lac` = $100{,}000$), categories, colors, occasions, and bilingual synonyms.
   - Fuses **Okapi BM25 (`k1=1.5, b=0.75`)** with a **TF-IDF + SVD semantic index** (latent semantic analysis, not a neural embedding model) via **Reciprocal Rank Fusion (RRF, $k=60$)** and a **hand-weighted feature re-ranker** (product type, category, colour, occasion, brand, budget, text overlap; not a neural cross-encoder).
   - **Benchmark: 50 development + 20 held-out labelled queries** (`src/shopkaro/search/benchmark.py`, results in `reports/day4_search_comparison.csv`, see section 2.1). Hybrid NDCG@10 **0.959** (dev) / **0.800** (held-out) vs keyword-only **0.788** / **0.580**.
2. **Task 2 — Personalized Search Re-Ranking ([`src/shopkaro/assistant/shopping_agent.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/assistant/shopping_agent.py)):**
   - Collaborative re-ranking of the top 200 hybrid results by each shopper's item-CF score. On held-out users NDCG@10 0.012 -> 0.064 (hit rate 6.2% -> 14.1%), mostly from revisited products; the earlier brand/price re-ranker had no measurable effect and its "+166.67%" claim was circular (section 2.2).
3. **Task 3 — Tool-Calling UrduLish Shopping Assistant & Zero-Hallucination Auditor ([`src/shopkaro/assistant/shopping_agent.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/assistant/shopping_agent.py)):**
   - Implements a 6-tool grounded agent (`search_products`, `get_recommendations`, `compare_products`, `add_to_cart`, `get_order_status`, `get_review_summary`) with multi-turn session memory and Roman Urdu ordinal coreference resolution (*"pehla aur doosra compare karo"*, *"pehla wala cart mein daal do"*).
   - Verified by `HallucinationAuditor`: **`0` hallucinated SKUs and `0` hallucinated prices** across a 6-turn UrduLish shopping conversation.
4. **Tasks 4 & 5 — Multilingual Review Intelligence & Actionable Seller Insights ([`src/shopkaro/reviews/intelligence.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/reviews/intelligence.py)):**
   - **Evaluation rewritten 2026-11-09** (section 4): earlier "100% / 1.000" scores were memorisation of 11 sentence templates. On 30 held-out hand-written reviews: sentiment accuracy **77%** (always-Positive baseline 40%, previous model 50%), aspect cells correct **89%** (baseline 78%, previous model 25%), spam F1 **0.89** (previous model 0.29).
   - **Task 4C (Unsupervised c-TF-IDF Topic Discovery):** Clusters all `8,000` reviews into `6` themes and tracks monthly topic trends.
   - **Task 5B (Seller & Management Insights):** computed from predictions; **1** product(s) flagged as unfairly penalised by courier delays (previously reported as 54 from generator labels).

---

## 2. Task 1 & Task 2: Hybrid Search & Personalized Re-Ranking

### 2.1 Offline Retrieval Benchmark (rewritten 2026-11-09)

> **Updated 2026-11-10:** results below were re-measured with the real libraries on Python 3.11; see `reports/library_migration_py311.md` for before/after numbers.

**Method.** 50 development queries + 20 held-out queries (English, Roman Urdu, Urdu script; typos, price
formats, brands, colours, occasions). Each query has a hand-written relevance spec (product type and budget are
hard; colour, occasion and brand are preferences), giving grades 0/1/2 for every catalogue product. NDCG@10 uses
gains 2^grade - 1 and an ideal ranking over the **whole in-stock catalogue**. The held-out queries were written
before any search changes and were never used for tuning.

**Correction.** The previous version reported hybrid NDCG@10 = 1.000 on 12 queries. That number came from a metric
bug (the ideal ranking only used relevant items the system itself returned, so one relevant result at rank 1 scored
1.0) and from judging relevance with the same constraints the hybrid parser filters on.

| Query set | Search method | NDCG@10 | MRR@10 | Precision@5 | Budget respected | Queries with no relevant result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Dev (50) | Keyword only (BM25) | 0.788 | 0.900 | 0.808 | 51% | 3 |
| Dev (50) | Semantic only | 0.685 | 0.860 | 0.796 | 35% | 4 |
| Dev (50) | **Hybrid** | **0.959** | **1.000** | **1.000** | **100%** | **0** |
| Held-out (20) | Keyword only (BM25) | 0.580 | 0.616 | 0.590 | 55% | 5 |
| Held-out (20) | Semantic only | 0.614 | 0.750 | 0.730 | 65% | 4 |
| Held-out (20) | **Hybrid** | **0.800** | **0.800** | **0.800** | **100%** | 4 |

**Significance (hybrid minus keyword, paired over the same queries).** Dev: +0.170 NDCG@10, 95% bootstrap CI
[+0.088, +0.261], better on 17 / worse on 2 / tied 31, sign test p = 0.0007. Held-out: +0.220, CI [+0.085, +0.377],
better on 7 / worse on 0, p = 0.016 (`reports/day4_search_significance.json`, per-query results in
`reports/day4_search_per_query.csv`). The brief's minimum target (hybrid beats keyword on NDCG@10) is met.

**What changed to get there** (hybrid scored 0.760 dev / 0.682 held-out before; the old parser let an occasion
word decide the category, so "shaadi ke liye waistcoat" returned wedding dresses):
product types are detected from the catalogue's own sub-category vocabulary with distinctiveness weights and fuzzy
spelling matching; occasions likewise from catalogue values; synonyms only translate (they no longer inject other
product types); "X se kam" budgets are parsed; a demo hack that injected hero products into every search and a
special case for "ammi" were removed.

**Known gaps (held-out failures, deliberately not patched):** words the lexicon does not know ("istri", "joote",
Urdu-script "jacket" / "mobile") return nothing relevant in any system. A neural multilingual embedding model
(multilingual-e5 / BGE-M3, named in the brief) is the real fix; it needs Python 3.11 for the libraries.

### 2.2 Why Hybrid Search Outperforms Single-Modality Retrieval
- **BM25 Failure Mode:** Fails on colloquial cross-lingual phrases (*"bachon ke liye school bag"*, *"garmiyon ke kapde"*) when exact English catalogue tokens differ, and ignores numerical price constraints (`20 hazaar tak` = `<= PKR 20,000`).
- **Semantic Vector Failure Mode:** Captures broad category similarity but blurs exact SKU specifications (`45W Fast Charger` vs `5G Smartphone`) and price ceilings.
- **Hybrid RRF + feature re-ranker:** Combines lexical precision and semantic recall via Reciprocal Rank Fusion:
  $$\text{RRF}(d) = \frac{w_{\text{bm25}}}{60 + \text{rank}_{\text{bm25}}(d)} + \frac{w_{\text{sem}}}{60 + \text{rank}_{\text{sem}}(d)}$$
  followed by a hand-weighted feature re-ranker that enforces parsed budget ceilings (`max_price_pkr`), category alignment, and occasion matches.

---

### 2.2 Personalised search (rewritten 2026-11-09)

**Old claim, withdrawn.** "+166.67% preferred-brand hit rate" was circular: the re-ranker boosts each user's
favourite brands and the metric counted favourite brands. It did not show that search got better for anyone.

**Method** (`src/shopkaro/search/personalization_eval.py`). RetailRocket has no search logs, so queries come from
later behaviour: for every profiled user with activity in the test window, one query per product type they
engaged with (query text = the product type, e.g. "Embroidered Lawn Suit"); relevant items = the products of that
type they engaged with in the test window, graded purchase 3 / add-to-cart 2 / view 1. User profiles and the
evaluation item-CF model use `train_interactions` only (the production recommender includes the test window and was
not used). Users are split 50/50 into dev and held-out halves by a hash of the user id.

**1. The previous re-ranker (brand / category / price profile) does nothing measurable.**

| Users | Plain hybrid NDCG@10 | Personalised NDCG@10 | Hit rate@10 | Difference (95% CI) | Better / worse | Sign test p |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| dev (165 users, 683 queries) | 0.0127 | 0.0140 | 2.9% -> 3.5% | +0.0012 [-0.0006, +0.0032] | 10/2 | 0.039 |
| holdout (174 users, 857 queries) | 0.0118 | 0.0113 | 6.2% -> 6.3% | -0.0006 [-0.0017, +0.0004] | 14/23 | 0.19 |

Two reasons: the user's products are in the 40 re-ranked candidates for only 19% of queries,
and brand / price were assigned to products at random when the catalogue was generated, so brand affinity carries
no signal in this data (category is constant within a product-type query).

**2. Collaborative re-ranking (shipped).** Take the top 200 hybrid candidates and re-rank with
`0.1 x search score + 0.9 x item-CF score for this user` (both min-max scaled). Pool size and weight were chosen on
the dev half from a 3 x 4 grid; the held-out half was evaluated once.

| Users | Plain hybrid NDCG@10 | Personalised NDCG@10 | Hit rate@10 | Difference (95% CI) | Better / worse | Sign test p |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| dev (165 users, 683 queries) | 0.0127 | 0.0736 | 2.9% -> 11.4% | +0.0608 [+0.0435, +0.0789] | 68/15 | 3.2e-09 |
| holdout (174 users, 857 queries) | 0.0118 | 0.0640 | 6.2% -> 14.1% | +0.0522 [+0.0392, +0.0662] | 93/24 | 8.9e-11 |

**Revisits vs discovery.** Counting only products the user had never interacted with in training:

| Users | Plain hybrid NDCG@10 | Personalised NDCG@10 | Hit rate@10 | Difference (95% CI) | Better / worse | Sign test p |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| dev (126 users, 606 queries) | 0.0121 | 0.0288 | 3.0% -> 6.6% | +0.0168 [+0.0063, +0.0277] | 31/15 | 0.026 |
| holdout (140 users, 764 queries) | 0.0132 | 0.0266 | 6.5% -> 8.6% | +0.0133 [+0.0060, +0.0215] | 38/26 | 0.17 |

So most of the gain is surfacing products the shopper already looked at (as in the A/B test); the gain on new
products is smaller (0.013 -> 0.027, bootstrap CI above zero, sign test not
significant). Absolute NDCG is low for every system because one product type has hundreds of candidates and a
user engages with one or two of them.

**Serving.** `/search?user_id=...` uses collaborative re-ranking for users with history (`personalization_method:
"item_cf_rerank"`), the persona profiles only for the demo personas, and plain search for unknown users. (Before,
any unknown user id was silently personalised as a "Luxury VIP".) Latency p95 15.5 ms vs 13.2 ms for plain search.

## 3. Task 3: Tool-Calling UrduLish Shopping Assistant

| Turn | User Utterance (UrduLish / English) | Invoked Tool(s) | Grounded Output Summary | Hallucination Check |
| :---: | :--- | :--- | :--- | :---: |
| **1** | *"Ammi ke liye Eid gift chahiye, 3000 tak"* | `search_products` | Returned `SK-00010` (Khaadi Shawl, `PKR 2,450`), `SK-00011` (J. Oud Gift Set, `PKR 2,800`), `SK-00012` (Saeed Ghani Basket, `PKR 2,250`) | **PASS (`0` errors)** |
| **2** | *"Pehla aur doosra compare karo"* | `compare_products` | Resolved `"pehla"` $\rightarrow$ `SK-00010` and `"doosra"` $\rightarrow$ `SK-00011`; compared price, rating, and occasion | **PASS (`0` errors)** |
| **3** | *"Pehla wala cart mein daal do"* | `add_to_cart` | Added `1x SK-00010` (`PKR 2,450`) to session cart | **PASS (`0` errors)** |
| **4** | *"SK-00010 ke reviews kaise hain?"* | `get_review_summary` | Reported genuine review count, rating, and 6-aspect sentiment breakdown | **PASS (`0` errors)** |
| **5** | *"Iske saath aur kya recommend karoge?"* | `get_recommendations` | Returned personalized cross-sell recommendations grounded in catalogue | **PASS (`0` errors)** |
| **6** | *"Mera order ORD-1001 kahan pohancha?"* | `get_order_status` | Retrieved order tracking status, courier delay, and items | **PASS (`0` errors)** |

---

## 4. Task 4 & Task 5: Multilingual Review Intelligence & Seller Diagnostics

### 4.1 Evaluation on hand-written reviews (rewritten 2026-11-09)

| Task | Set | Baseline | Previous trained model* | **Rule analyzer** |
| :--- | :--- | :---: | :---: | :---: |
| Sentiment accuracy (macro-F1) | Dev (60) | always Positive 40%; word count 83% | 53% (0.48) | 100% (1.00) |
| Sentiment accuracy (macro-F1) | **Held-out (30)** | always Positive 40%; word count 57% | 50% (0.41) | **77% (0.75)** |
| Aspects: cells correct (macro-F1) | Dev (60) | all "not mentioned" 78% (0.29) | 19% (0.14) | 98% (0.98) |
| Aspects: cells correct (macro-F1) | **Held-out (30)** | all "not mentioned" 78% (0.29) | 25% (0.24) | **89% (0.66)**; detection precision 1.00, recall 0.59 |
| Spam F1 (precision / recall) | Dev (16) | old regex 0.50 | 0.50 | 1.00 |
| Spam F1 (precision / recall) | **Held-out (10)** | old regex 0.57 | 0.29 | **0.89 (1.00 / 0.80)** |

\* TF-IDF + logistic regression / random forest trained on the synthetic corpus, measured once on the same
benchmark before it was replaced (it had reported 1.000 on a random split of the corpus; measured before two dev aspect labels were corrected).

**Why the old 1.000 scores were wrong.** The 8,000 synthetic reviews come from 11 sentence templates (777
distinct texts once brand and product names are filled in), so a random 80/20 split puts the same sentences in
training and test. The sentiment model was also given the star rating and delivery delay as inputs, and the
sentiment label is computed from exactly those two numbers. The spam "test set" was three fixed spam sentences
repeated ~130 times each. And the business insights (the "54 unfairly penalised gems") were computed from the
generator's labels, not from any model.

**What replaced it.**
- `src/shopkaro/reviews/benchmark.py`: 60 dev + 30 held-out reviews written by hand in English, Roman Urdu and
  Urdu script (equal thirds), with sentiment and per-aspect labels, plus 16 + 10 spam / hard-genuine examples
  (genuine reviews in capitals, with phone numbers, with the word "fake"). The held-out sets were written before
  any change and were not used for tuning; words that appear only in them were kept out of the rules.
- `src/shopkaro/reviews/lexicon_analyzer.py`: a transparent rule analyzer (clause splitting, negation in English
  and Urdu word order, aspect-specific words such as "mehnga" for price or "tang" for size, waiting-time
  expressions for delivery, spam signals). Trained models cannot learn from 11 templates; a multilingual neural
  model fine-tuned on real labelled reviews is the proper next step.
- Business insights (product summaries, seller tiers, "unfairly penalised" products) are now computed from the
  analyzer's predictions, as they would be on real reviews.

**Caveat.** One person wrote both the rules and the benchmark, so even the held-out score is likely optimistic; an
independent annotator would give a fairer number. 30 held-out reviews is small (accuracy +-15 points at 95%).

Per-language held-out sentiment accuracy and remaining held-out errors: `reports/day4_review_intelligence_metrics.csv`,
`reports/day4_review_benchmark_errors.json`.

**Clause-Aware Contrast Splitting Verification:**
- Input: *"Product bohot acha hai lekin delivery 10 din late aayi"*
  - Clause 1 (*"Product bohot acha hai"*): `quality = +1` (Positive)
  - Clause 2 (*"delivery 10 din late aayi"*): `delivery = -1` (Negative)
  - Output Vector: `{"quality": 1, "price": 0, "delivery": -1, "size_fit": 0, "packaging": 0, "seller": 0}`

### 4.3 Task 4C — Unsupervised c-TF-IDF Topic Discovery (`8,000` Reviews)

| Topic ID | Discovered Topic Name | Reviews ($n$) | Share (%) | Avg Rating | Dominant Language | Top c-TF-IDF Keywords |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **#3** | **Value for Money (Paisa Wasool) & Seller Praise** | `1,687` | `21.09%` | `4.13★` | `Roman_Urdu` | `hisaab se, price ke, quality kamaal, mehfooz, taawun` |
| **#2** | **Fabric & Stitching Quality Praise (Roman Urdu)** | `1,681` | `21.01%` | `4.52★` | `Roman_Urdu` | `bohot achi, kapra aur, finishing, tasveer jaisa, time par` |
| **#0** | **Urdu Script Quality & Value Reviews** | `1,678` | `20.97%` | `4.16★` | `Urdu` | `پراڈکٹ, شاندار, کوالٹی, پیکنگ, لاجواب, مناسب` |
| **#1** | **Fast Delivery & Authentic Product Praise (English)** | `1,420` | `17.75%` | `4.75★` | `English` | `quality, arrived days, fits perfectly, exceeded, expectations` |
| **#5** | **Late Courier Delivery & Sizing Complaints** | `1,082` | `13.53%` | `3.11★` | `Roman_Urdu` | `size thora, chhota hai, courier walon, 5 din, late` |
| **#4** | **Defective Quality & Torn Packaging Complaints** | `452` | `5.65%` | `1.16★` | `English` | `packaging, fake, seller, torn, overpriced, replacement request` |

### 4.4 Task 5A — Fake / Spam Review Detection

- Rules: URL or @handle; phone number together with a contact verb (WhatsApp, contact, call karein, واٹس ایپ);
  promo / referral / wholesale / earn-from-home offers; competitor promotion; bot phrases; repetitive text.
- Held-out (10 new examples): precision 1.00, recall 0.80, F1 0.89. No genuine review was flagged.
- On the synthetic corpus the rules flag the same 405 reviews (5.06%) the generator labelled as spam
  (145 `duplicate_bot`, 138 `extreme_burst`, 122 `promo_link`); that agreement is expected, not a quality measure.

### 4.5 Task 5B — De-Conflating Product Quality vs. 3PL Courier Penalties

**Courier vs product quality.** A product is flagged "unfairly penalised by the courier" when at least
65% of its genuine reviews praise quality, at least 35% complain about delivery, and its average rating is below
4.15. On predicted aspects this finds **1** product(s) (previously reported as 54, computed from generator
labels that marked delivery as negative even in reviews that never mention delivery: delivery complaints are
10% of reviews by prediction vs 22% by the generator's labels). 73 of 1,428 sellers are
`Courier_Bottlenecked_Seller` (previously 149). The thresholds were not changed to produce a larger number.

| SKU | Brand & Title | Raw Rating | Positive Quality (`+1`) | Negative Delivery (`-1`) | Recommended Management Action |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **`SK-00376`** | Khaadi — Khaadi Summer Embroidered Eid Lawn Maroon — U | `3.64★` | **`78.6%`** | **`35.7%`** | Switch 3PL Courier (High Product Quality, High Delivery Delay Penalty) |

- **Visual Artifact:** [`reports/figures/13_review_intelligence_and_absa.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/13_review_intelligence_and_absa.png)



---

## Note (2026-11-09): data regenerated
Product categories now follow RetailRocket's real category tree instead of being random per item, and all
artefacts were regenerated. Numbers in the tables above predate that change. Current results are in the CSVs in
`reports/`. Search was re-evaluated on 50 + 20 labelled queries (section 2.1). Review sentiment scores 1.000 on every language because synthetic reviews come from templates the classifier can memorise; this is not a real-world accuracy estimate.

### 4.6 Review insights for customers and management (added 2026-11-10)

- **"What customers say" per product** (`what_customers_say` in `review_intelligence_summary`, the
  `/reviews/summary/{product_id}` API and the dashboard product panel). One Roman Urdu sentence from the predicted
  aspects, e.g. *"Zyada tar customers (79%) ko cheez ki quality pasand aayi, lekin 21% ne kaha quality achi nahi thi.
  (14 reviews)"*. Numbers are shares of that product's genuine reviews.
- **Falling sentiment** (`reports/day4_falling_sentiment.csv`): positive share in the last 6 months vs the 6 before,
  only drops of 20+ points that are significant (one-sided Fisher test, p < 0.05; >= 4 reviews per period):
  **4 products** (without the significance test, 106 products crossed the 20-point line, mostly noise
  from 4-11 reviews). With hundreds of products tested, a few false alarms are expected: treat these as candidates for review, not proof.
- **Top complaints** by category (`day4_complaints_by_category.csv`, 11 categories) and by seller
  (`day4_complaints_by_seller.csv`, 101 sellers with >= 15 reviews). In this synthetic corpus every negative
  template also criticises quality, so "quality" tops most lists; on real reviews this table separates issues.
- **Weekly automated insight report** (`scripts/run_weekly_insight_report.py` -> `reports/weekly_insight_report.md`,
  numbers in `weekly_insight_facts.json`). SQL/pandas compute every number; the LLM (llm (gemini-3.1-flash-lite)) writes the prose;
  any number in the text that is not in the facts rejects the LLM text and a template is used.

### 4.7 Cross-encoder re-ranking of the top 50 (added 2026-11-10)

`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual) re-scores the top 50 feature-ranked results;
final = z(feature score) + 0.25 x z(cross-encoder score), weight chosen on the 50 dev queries
(0.9638 -> 0.9673). Held-out: **0.837** (0.832 without it; 2 queries better,
0 worse, not significant). Cost: ~0.7 s extra per search on a laptop CPU (average search
1007 ms). Switch off with `SEARCH_CROSS_ENCODER=off`. Personalised search skips it
(the item-CF score re-orders the pool anyway).
