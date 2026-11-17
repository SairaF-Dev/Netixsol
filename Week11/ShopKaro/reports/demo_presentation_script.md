# ShopKaro 10-Minute Stakeholder Demonstration Script

**Audience:** ShopKaro CEO, Head of Product, VP of Supply Chain  
**Format:** live walkthrough of the Streamlit dashboard (`http://localhost:8501`, or the deployed link) backed by the
FastAPI serving layer. Record it as the 10-minute demo video (brief, Day 5 Task 4).  
**Checked against the running app on 2026-11-17:** every product, price and number below is what the app returns today.

## Before you record

- Start the stack (`docker compose up`, or API + `streamlit run src/shopkaro/dashboard/app.py`) and open the
  storefront once so the models are loaded; the first assistant reply can take ~15 s while the LLM warms up.
- Set `LLM_API_KEY` so the assistant runs on Gemini; without it the rule-based assistant answers instead (same tools,
  plainer wording).
- Reset the assistant conversation and empty the bag before you start.
- Screen at 1080p, browser zoom 90%, one tab only.

## Brief checklist → where it is shown

| Brief item | Minute |
| :-- | :-- |
| Two different users seeing different homepages | 1:00 |
| New user (cold start) getting sensible recommendations | 2:30 |
| UrduLish search: "eid ke liye lawn suit under 5000" | 3:15 |
| Shopping assistant finding **and comparing** products | 4:30 |
| Review summary for a product | 6:00 |
| Demand forecast with intervals and a stock-out alert before Eid | 7:00 |
| A/B test results and estimated revenue uplift | 8:30 |
| Business impact estimate (conversion, stock-outs prevented, dead stock) | 9:15 |

---

## 0:00 – 1:00 | The problem

- **Say:** *"Assalam-o-Alaikum. ShopKaro had four problems: every shopper saw the same homepage, keyword search failed
  on Roman Urdu, inventory was guesswork so lawn ran out before Eid, and nobody read the reviews. This is the platform
  that addresses all four, running live."*
- **Do:** show the storefront home page.

## 1:00 – 2:30 | Two customers, two homepages

- **Do:** ☰ (top left) → **LOGIN** → tab **⚙️ Persona Simulation** → pick **🌙 Eid & Festive Lawn Shopper**
  (real customer `USR-928443`) → **Apply Profile Settings**.
- **Show:** the "Recommended for you" row is Eid lawn and shawls — Khaadi 2-piece lawn (PKR 4,550, 20% off),
  Alkaram and Sana Safinaz embroidered shawls, Limelight 3-piece lawn.
- **Do:** switch persona to **📱 Smartphone & Electronics Buyer** (`USR-368401`) → Apply.
- **Show:** the same row is now Baseus back covers (PKR 560), Audionic earbuds, a Redmi 5G phone, a Samsung 45W charger.
- **Say:** *"Same page, two real customers from the data, two completely different feeds. Each card says why in Roman
  Urdu. Notice most say 'Aap ne yeh pehle dekha tha' — the engine is good at bringing people back to items they were
  already considering; I'll come back to what that means for revenue."*

## 2:30 – 3:15 | A brand-new visitor (cold start)

- **Do:** switch persona to **🆕 New Visitor (cold start)** → Apply.
- **Show:** a mix of each category's best sellers — Khaadi festive lawn, a Polo school bag, a Redmi power bank,
  Edenrobe and Bonanza kurtas — each labelled "… mein ShopKaro ke maqbool products mein se ek".
- **Say:** *"No history, no blank page. A new visitor gets the most popular items across categories; once they pick a
  category at onboarding or click anything, the feed personalises from that click."*

## 3:15 – 4:30 | UrduLish search

- **Do:** switch back to the Eid shopper, type **`eid ke liye lawn suit under 5000`** in the top search box and press
  Enter (or click the chip **👗 Eid Lawn Suit ≤ 5k**, which runs the same query).
- **Show:** the top results are all women's lawn under PKR 5,000 — Sapphire 3-piece embroidered lawn (PKR 4,450),
  Khaadi festive 3-piece (PKR 3,890), Alkaram Studio 3-piece suits (PKR 3,400–4,600).
- **Say:** *"The parser read 'under 5000' as a price ceiling, 'lawn suit' as the category and 'eid' as the occasion.
  Behind it: BM25 keyword search plus multilingual-e5 vector search, fused with reciprocal rank fusion and re-ranked by
  a cross-encoder. On 20 held-out labelled queries written after the system was built, it scores NDCG@10 0.893 against 0.498
  for keyword search alone (0.962 vs 0.788 on the 50 development queries)."*
- Optional (if time): click the chip **💻 Coding Laptop <= 1.5 Lac**.

## 4:30 – 6:00 | Shopping assistant: find, compare, add to cart

- **Do:** open **✨ Ask AI** (top bar) → click chip **🎁 Gift under 3000** ("Ammi ke liye Eid gift chahiye, 3000 tak").
- **Show:** three options, all within budget: Khaadi embroidered shawl **SK-00010 (PKR 2,450)**, J. oud & rose perfume
  set **SK-00011 (PKR 2,800)**, Saeed Ghani gift basket **SK-00012 (PKR 2,250)**.
- **Do:** click chip **👗 Compare dresses** ("Pehla aur doosra compare karo").
- **Show:** a comparison table — shawl 4.44★ / 81% positive vs perfume 3.71★ / 64% positive.
- **Do:** type **`Pehla wala cart mein daal do`**.
- **Show:** the bag badge updates; total **PKR 2,450**.
- **Say:** *"Every product, price and stock level comes from a tool call. Before a reply is shown, an auditor checks
  every SKU and price in it against the tool results — including that each product carries its own price. If the LLM
  gets one wrong, it is asked to correct itself, and if it still fails, the customer gets the tool's own answer
  instead."*

## 6:00 – 7:00 | Review summary

- **Do:** in the assistant, click chip **⭐ Check reviews** ("SK-00010 ke reviews kaise hain?"), or click **⭐ Details**
  on the shawl's product card.
- **Show:** 16 genuine reviews, 4.4★, 81% positive; 94% praise the quality; delivery complaints 6%; the "What customers
  say" line in Roman Urdu, and the six aspect bars (quality, price, delivery, size/fit, packaging, seller).
- **Say:** *"Reviews arrive in English, Urdu and Roman Urdu. We score six aspects separately, so 'kapra acha hai lekin
  delivery late thi' counts as good quality and bad delivery — a slow courier does not drag down a good product. On 30
  hand-written reviews the system never saw, it gets the overall sentiment right 77% of the time, against 40% for
  always guessing positive."*

## 7:00 – 8:30 | Forecast with intervals and an Eid stock-out alert

- **Do:** bottom of the left sidebar → tick **🏢 Enterprise & Merchant Console** → view **📦 Supply Chain & Demand
  Forecasting** → in "Select SKU to Inspect Demand Trajectory" pick **SK-00051** (Sapphire chiffon dupatta suit, Eid
  festive collection).
- **Show:** the 30-day fan chart with P10 / P50 / P90, and the alert card.
- **Say:** *"Next 30 days: 2,680 units expected, up to 3,730 in a strong Eid. We have 309 in stock — 2.8 days of
  demand — below the reorder point of 440, so it is flagged CRITICAL_STOCKOUT_RISK with a purchase order of 2,475 units.
  The model knows the festival dates; how much Eid lifts lawn it learned from past sales. Its error is 15% WAPE
  against 42% for the seasonal-naive baseline. Our first version accidentally used the data generator's own formula
  and showed an unrealistic 6% error — we found it, removed it, and a test now stops it coming back."*
- **Show:** the alert table: 129 stock-out risks, 94 festival-surge watches, 7 overstock / dead-capital alerts.

## 8:30 – 9:15 | A/B test

- **Do:** view **📊 A/B Testing & ABSA Reviews**.
- **Say:** *"We replayed four weeks of real shopper behaviour — 162,386 visitors, half shown popular items, half shown
  personalised recommendations from a model that never saw those four weeks. Homepage clicks went up about 3x and
  homepage purchases from 7 to 42 buyers, which is significant, so by the rule we fixed in advance the decision is
  SHIP. But 37 of those 42 bought something they had already looked at: the gain is bringing people back, not yet
  selling things they had never found. Estimated value: about PKR 8 million a month, with a wide range of 1 to 15
  million."*

## 9:15 – 10:00 | Business impact and close

- **Say:** *"In one sentence each: conversion — homepage buyers up from 7 to 42 in the replay; stock-outs — replaying
  2025, forecast-driven ordering lost 83% fewer units than re-ordering on last month's sales, with 15% less stock;
  dead stock — 7 slow movers are flagged for discount today. These come from replays on partly synthetic data; the
  next step is a live A/B test with real traffic. Thank you."*

---

**Facts to keep straight if asked**

- The served homepage model is item-to-item CF; the neural two-tower is more accurate offline (NDCG@10 0.1362 vs
  0.1307) and is one setting away (`RECOMMENDER=two_tower`).
- Personas are real customer IDs from the interaction data; there are no invented customer names.
- Sales history and reviews are partly synthetic (documented in the reports); interactions are RetailRocket and orders
  are Olist, mapped to Pakistani categories and PKR prices.
