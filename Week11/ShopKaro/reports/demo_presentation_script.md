# ShopKaro 10-Minute Stakeholder Demonstration Script

**Target Audience:** ShopKaro CEO, Head of Product, and VP of Supply Chain  
**Presenter:** AI Commerce Intelligence Platform Lead  
**Format:** Live Walkthrough of Streamlit Production UI (`http://localhost:8501`) & FastAPI Serving Engine  
**Duration:** 10 Minutes Total

---

## ⏱️ Minute 0:00 – 1:30 | Executive Introduction & The Core Problem
- **Speaker:** *"Assalam-o-Alaikum leadership team. Today we present the ShopKaro AI Commerce Intelligence Platform. ShopKaro faced four critical bottlenecks: low conversion because every shopper saw identical static homepages, broken keyword search failing on Roman Urdu queries, inventory guesswork causing pre-Eid stockouts, and unread customer reviews conflating product quality with courier delays. Today, we show you the live production platform that solves all four in real time."*
- **Action:** Open browser on `http://localhost:8501`. Show the top announcement ticker (`🚚 Free Express Delivery • COD Available`) and commercial `ShopKaro.PK` header.

---

## ⏱️ Minute 1:30 – 3:30 | Personalized Homepages & Cold-Start Demonstration
- **Speaker:** *"First, let's look at personalization. In the sidebar, I am switching to Customer #15442 (Hamza Khan, VIP Luxury & Electronics buyer). Notice the feed dynamically populates with high-end tech, luxury unstitched lawn, and premium designer wear.*
- **Action:** Select `15442 (VIP Luxury)` $\rightarrow$ Observe homepage recommendations.
- **Speaker:** *"Now, let's switch to Customer #22110 (Bargain Hunter). Instantly, the Two-Tower engine shifts the feed to discounted essentials, flash deals, and budget-friendly Pakistani lawn.*
- **Action:** Select `22110 (Bargain Hunter)` $\rightarrow$ Point out discounted ribbons and prices.
- **Speaker:** *"What about a completely new user who just arrived? We switch to Customer #999999 (Cold-Start Anonymous Visitor). Without any historical data, the system does not crash or show blanks; it executes our cold-start fallback heuristic, presenting top-rated Pakistani bestsellers with high conversion probabilities."*
- **Action:** Select `999999 (Cold-Start New Visitor)` $\rightarrow$ Show sensible top-rated onboarding feed.

---

## ⏱️ Minute 3:30 – 5:00 | UrduLish Hybrid Search & Query Parsing
- **Speaker:** *"Next, let's test how ShopKaro handles natural language queries from Pakistani shoppers. A customer types in Roman Urdu: 'eid ke liye lawn suit under 5000'. Traditional keyword search would fail or return zero hits."*
- **Action:** Type or click preset chip `👗 Sapphire Modest Lawn <= 5k`.
- **Speaker:** *"Watch the instant parsing in the filter bar: the engine automatically extracts Price Ceiling: PKR 5,000, Category: Women's Lawn, and Occasion: Eid. It runs Okapi BM25 plus 96-D Subword Vector search with Reciprocal Rank Fusion, returning authentic 3-piece emerald lawn suits from Sapphire and Khaadi."*
- **Action:** Point out the clean search pills and the authentic Pakistani lawn photography.

---

## ⏱️ Minute 5:00 – 6:30 | UrduLish Shopping Concierge with Grounded Tools
- **Speaker:** *"Now let's switch to our conversational UrduLish Shopping Concierge in View 2. Pakistani shoppers often want interactive guidance."*
- **Action:** In sidebar, switch view to `💬 AI Shopping Concierge`. Click preset `"Ammi ke liye Eid gift chahiye, 3000 tak"`.
- **Speaker:** *"The agent understands Roman Urdu intent, executes the `search_products` tool against our verified catalogue, and recommends Khaadi Embroidered Shawls and J. Oud sets within the exact 3,000 PKR budget. Every price, stock quantity, and SKU is 100% grounded — zero hallucinations."*
- **Action:** Type `"Pehla wala cart mein daal do"` $\rightarrow$ Observe cart badge update to PKR 2,450.

---

## ⏱️ Minute 6:30 – 8:00 | 6-Aspect ABSA & Courier Delay De-Biasing
- **Speaker:** *"Let's examine customer reviews. When we click '⭐ Reviews' on a product, we don't just see a single star score. We see a 6-aspect breakdown: Fabric & Craftsmanship, Value for Money, Courier Delivery, True to Size, Packaging, and Seller Service.*
- **Action:** Return to Storefront and click `⭐ Reviews` on `SK-00389`.
- **Speaker:** *"Notice how we separate courier problems from product problems. Type a review like 'Kapra acha hai lekin delivery 10 din late aayi': quality is scored positive and delivery negative, so a slow courier does not drag down a good product. We tested this on 30 reviews written by hand that the system had never seen: it gets the overall sentiment right about three times in four."*
- **Action:** Point out the visual green satisfaction progress bars and verified buyer testimonials.

---

## ⏱️ Minute 8:00 – 9:15 | Supply Chain Control Tower & Eid Stockout Prevention
- **Speaker:** *"Now for the operations team. In View 3, we open the Supply Chain & Inventory Control Tower."*
- **Action:** In sidebar, select `📦 Supply Chain & Inventory Console`.
- **Speaker:** *"Here is our 30-day probabilistic demand fan chart. Rather than a single guess, we forecast P10 (minimum), P50 (expected), and P90 (high-surge scenario). Pick SK-00051 (Sapphire lawn): 309 units on hand is only 2.7 days of expected pre-Eid demand, below its reorder point of 467, so the system flags CRITICAL_STOCKOUT_RISK and recommends a purchase order of 2,472 units. And in a replay of 2025, ordering this way lost 96% fewer units over Ramadan and Eid than re-ordering on last month's sales, on synthetic demand."*
- **Action:** Point out the shaded P10–P90 green surge band and the automated ERP replenishment card.

---

## ⏱️ Minute 9:15 – 10:00 | A/B Test Results, Business ROI & Executive Handover
- **Speaker:** *"Finally, does it make money? We tested it by replaying four weeks of real shopper behaviour: 162,000 visitors, half shown popular items, half shown personalised recommendations from a model that never saw those four weeks."*
- **Action:** Select `📊 Executive A/B Testing & ABSA Analytics`.
- **Speaker:** *"Homepage clicks tripled and homepage purchases went from 7 to 42 buyers, which is statistically significant, so by the rule we fixed in advance the answer is ship. But look at why: 37 of those 42 bought something they had already looked at. The homepage is bringing people back to items they were considering. That is worth roughly 8 million rupees a month, with a wide range. What we have not proven yet is that it sells products people had not found themselves; the live test will measure that. Thank you."*

