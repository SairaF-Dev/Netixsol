# Understanding Day 4 — Hybrid Search, Conversational UrduLish Shopping Assistant & Review Intelligence

This guide explains the architectural decisions, mathematical formulations, and Pakistani e-commerce domain adaptations implemented across **Day 4 (`25%` of the Capstone grade)**.

---

## 1. Architecture Overview

```
                     ┌──────────────────────────────────────────────────────────┐
                     │          User Input (English / Urdu / Roman Urdu)        │
                     └───────────────┬──────────────────────────┬───────────────┘
                                     │                          │
                     ┌───────────────▼──────────────┐   ┌───────▼───────────────────────┐
                     │  Task 1 & 2: Hybrid Search   │   │ Task 3: UrduLish Shopping Bot │
                     │  - UrduLishQueryParser       │   │ - 6 Grounded Catalogue Tools  │
                     │  - Okapi BM25 + 96-D Vector  │   │ - Multi-Turn Ordinal Memory   │
                     │  - RRF (k=60) + CrossEncoder │   │ - Zero-Hallucination Auditor  │
                     │  - PersonalizedSearchReRanker│   └───────────────────────────────┘
                     └──────────────────────────────┘
                                     │
                     ┌───────────────▼──────────────────────────────────────────┐
                     │  Task 4 & 5: Multilingual Review Intelligence Pipeline   │
                     │  - Task 4A: 3-Language Sentiment + Contrast Splitting    │
                     │  - Task 4B: 6-Aspect ABSA (quality, price, delivery...)  │
                     │  - Task 4C: Unsupervised c-TF-IDF Topic Discovery        │
                     │  - Task 5A: Multi-Signal Spam / Bot Review Detector      │
                     │  - Task 5B: Seller Scorecards & 3PL Courier De-Conflation│
                     └──────────────────────────────────────────────────────────┘
```

---

## 2. Task 1: Hybrid Search Engine ([`src/shopkaro/search/hybrid_search.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/search/hybrid_search.py))

### 2.1 `UrduLishQueryParser`
Pakistani shoppers rarely type clean English keyword queries. Instead, they combine Roman Urdu grammar, English nouns, and South Asian numeric units:
- *"shaadi ke liye red lehenga 20 hazaar tak"* $\rightarrow$ `max_price_pkr = 20000.0`, `occasion = "Shaadi/Wedding"`, `color = "Red"`, `category = "Bridal & Formal Wear"`.
- *"laptop for coding under 1.5 lac"* $\rightarrow$ `max_price_pkr = 150000.0`, `category = "Laptops & Computing"`.
- *"Ammi ke liye Eid gift chahiye, 3000 tak"* $\rightarrow$ `max_price_pkr = 3000.0`, `occasion = "Eid"`.

### 2.2 Okapi BM25 + Subword Semantic Vector + Reciprocal Rank Fusion (RRF)
1. **Okapi BM25 (`k1 = 1.5, b = 0.75`):**
   $$\text{BM25}(Q, D) = \sum_{q \in Q} \text{IDF}(q) \cdot \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
2. **96-D Semantic Vector Index:** Combines word n-grams `(1, 2)` and character boundary n-grams `(3, 5)` projected via `TruncatedSVD(n_components=96)` so spelling variations in Roman Urdu (*kameez / qameez*, *bachon / bacho*) map to nearby vectors.
3. **Reciprocal Rank Fusion (RRF, $k=60$):**
   $$\text{RRF}(d) = \frac{w_{\text{bm25}}}{60 + r_{\text{bm25}}(d)} + \frac{w_{\text{sem}}}{60 + r_{\text{sem}}(d)}$$
4. **Cross-Encoder Re-Ranker:** Scores top-100 RRF candidates on exact budget compliance (`price_pkr <= max_price_pkr`), category match, color/occasion match, and phrase overlap, boosting `NDCG@10` from `0.8457` (BM25) and `0.7480` (Vector) to **`1.0000`** with **`100%` budget compliance**.

---

## 3. Task 2 & Task 3: Personalized Re-Ranking & Conversational Agent ([`src/shopkaro/assistant/shopping_agent.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/assistant/shopping_agent.py))

### 3.1 `PersonalizedSearchReRanker` (rewritten 2026-11-09)
- **What ships:** for shoppers with history, the top 200 hybrid results are re-ranked by
  `0.1 x search score + 0.9 x item-CF score` (how strongly products co-occur with what this shopper engaged with).
  Search still decides *what* matches the query (type, budget); the shopper's history decides the *order*.
- **How we know it works:** queries rebuilt from each user's later behaviour (one per product type they engaged
  with in the test window), relevance = what they actually engaged with. Held-out users: NDCG@10
  0.012 -> 0.064. Mostly revisits; on never-seen products
  0.013 -> 0.027 (weaker evidence).
- **What did not work:** the old brand / category / price profile blend had no measurable effect, because brand and
  price are random in the synthetic catalogue. Its "+166.67% preferred-brand hit rate" measured the re-ranker against
  its own objective (circular).
- **Interview answer:** "We validated personalisation against future behaviour, found our feature-based re-ranker
  did nothing, replaced it with collaborative evidence, chose its two parameters on half the users and confirmed on
  the other half."

### 3.2 `UrduLishShoppingAssistant` & `HallucinationAuditor`
- **6 Grounded Tools:** `search_products`, `get_recommendations`, `compare_products`, `add_to_cart`, `get_order_status`, `get_review_summary`.
- **Ordinal Coreference Resolution:** Maps Roman Urdu ordinals (*"pehla"* $\rightarrow$ index `0`, *"doosra"* $\rightarrow$ index `1`, *"teesra"* $\rightarrow$ index `2`) against `session.last_shown_products` so multi-turn follow-ups (*"Pehla aur doosra compare karo"*, *"Pehla wala cart mein daal do"*) work naturally without repeating SKU IDs.
- **Zero-Hallucination Guarantee:** `HallucinationAuditor` extracts every `SK-XXXXX` ID and `PKR X,XXX` price cited in the assistant's response and verifies them against the tool outputs and DuckDB `product_catalogue`.

---

## 4. Tasks 4 & 5: Multilingual Review Intelligence ([`src/shopkaro/reviews/intelligence.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/reviews/intelligence.py))

### 4.1 Clause-Aware Contrast Splitting for Mixed Sentiment & 6-Aspect ABSA
A classic failure mode in standard sentiment analysis is treating a contrastive sentence as a single bag of words:
> *"Product bohot acha hai **lekin** delivery 10 din late aayi"*

The analyzer (`lexicon_analyzer.py`) splits any review at punctuation and contrast words (`lekin`, `magar`, `par`, `but`, `however`, `مگر`, `لیکن`) and evaluates aspect keywords within each clause independently:
- **Clause 1:** *"Product bohot acha hai"* $\rightarrow$ Aspect `quality` matched (`"product"`), Polarity = `+1` (`"acha"`).
- **Clause 2:** *"delivery 10 din late aayi"* $\rightarrow$ Aspect `delivery` matched (`"delivery"`), Polarity = `-1` (`"late"`, and "10 din" counts as a long wait).

### 4.2 Unsupervised Topic Discovery via c-TF-IDF
Following the BERTopic paradigm, reviews are embedded into a 24-D dense semantic space, clustered via K-Means ($K=6$), and summarized using **Class-based TF-IDF (c-TF-IDF)**:
$$\text{c-TF-IDF}_{t, c} = \frac{f_{t, c}}{\sum_{w} f_{w, c}} \cdot \log\left(1 + \frac{A}{\sum_{c'} f_{t, c'}}\right)$$
where $f_{t,c}$ is the frequency of term $t$ in cluster $c$ and $A$ is the average number of words per cluster.

### 4.3 De-Conflating Intrinsic Product Quality vs. 3PL Courier Delays
`SellerInsightsEngine` drops reviews predicted as spam and computes, per product, the share of reviews praising
quality (`quality_pos_pct`) and complaining about delivery (`delivery_neg_pct`), both from the analyzer's
predictions. A product with >= 65% quality praise, >= 35% delivery complaints and rating < 4.15 is flagged
"unfairly penalised by courier". Currently 1 product qualifies. An earlier figure of 54 was computed from the
generator's labels, which marked delivery negative even in reviews that never mention it.

### 4.4 How good is it, honestly? (added 2026-11-09)
The synthetic corpus is 11 templates, so the old "100% accuracy" was memorisation (the sentiment model was even
given the star rating that defines the label). On 30 hand-written held-out reviews the rule analyzer
(`lexicon_analyzer.py`) gets 77% sentiment accuracy (always-Positive: 40%, old model: 50%), 89% of aspect cells
right (predicting "nothing mentioned": 78%, old model: 25%) and spam F1 0.89 (old model: 0.29).
Interview answer: "Our training data could not support a learned model, so we measured on hand-written text,
showed the learned model failed, and shipped transparent rules with an honest held-out number. With real
labelled reviews we would fine-tune a multilingual transformer."

---

## 5. Verification Commands

```powershell
# Run Day 4 Task 1 (Hybrid Search Benchmark)
.\.venv\Scripts\python.exe scripts/run_day4_task1.py
.\.venv\Scripts\python.exe -m pytest tests/test_day4_task1.py -v

# Run Day 4 Tasks 2 & 3 (Personalized Re-Ranking + UrduLish Shopping Assistant)
.\.venv\Scripts\python.exe scripts/run_day4_task2_task3.py
.\.venv\Scripts\python.exe -m pytest tests/test_day4_task2_task3.py -v

# Run Day 4 Tasks 4 & 5 (Review Intelligence, 6-Aspect ABSA, Spam Detection & Insights)
.\.venv\Scripts\python.exe scripts/run_day4_task4_task5.py
.\.venv\Scripts\python.exe -m pytest tests/test_day4_task4_task5.py -v
```

