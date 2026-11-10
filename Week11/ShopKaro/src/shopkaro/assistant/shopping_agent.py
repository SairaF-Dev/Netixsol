"""
Day 4 — Task 2 & Task 3: Personalized Search Re-Ranking & Tool-Calling UrduLish Shopping Assistant.

Implements:
1. `PersonalizedSearchReRanker` (Task 2):
   - Re-ranks `HybridSearchEngine` results using the user's historical category affinity,
     brand affinity, price-band compatibility, and RFM segment persona.
2. `ShopKaroToolRegistry` (Task 3 — 6 Grounded E-Commerce Tools):
   - `search_products`: Hybrid search + personalized re-ranking with PKR budget & attribute filters.
   - `get_recommendations`: Personalized / Gift / Occasion recommendations with Roman Urdu reasons.
   - `compare_products`: Side-by-side product specs, PKR prices, stock, and review aspect ratings.
   - `add_to_cart`: Live stock check, session cart management, PKR subtotal, and cross-sell bundle hint.
   - `get_order_status`: Real-time order status, courier tracking (TCS / Leopards / Trax), and ETA.
   - `get_review_summary`: Aggregated star rating, sentiment breakdown, 6-aspect scores, and quotes.
3. `UrduLishShoppingAssistant` & `HallucinationAuditor` (Task 3):
   - Multi-turn conversational memory (`last_shown_products`, `cart`, `active_filters`),
     Roman Urdu coreference resolution ("pehla aur doosra compare karo", "cart mein daal do"),
     and strict zero-hallucination verification (`0` fabricated SKUs or prices).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.search.hybrid_search import HybridSearchEngine, ParsedSearchQuery


@dataclass
class UserSearchProfile:
    """User taste profile for Task 2 Personalized Search Re-Ranking."""

    user_id: str
    persona_name: str
    preferred_categories: dict[str, float]
    preferred_brands: dict[str, float]
    avg_item_price_pkr: float
    price_sensitivity: str  # "budget", "mid", "luxury"


@dataclass
class PersonalizationEvalSummary:
    """
    Sanity check that the two demo personas receive different results (price level, brands, overlap).
    NOT evidence that personalisation improves search: the brand-hit "uplift" counts the persona's own preferred
    brands, which the re-ranker boosts by construction. Quality is measured against real users' later behaviour in
    `shopkaro.search.personalization_eval` (reports/day4_personalized_search_eval.json).
    """

    queries_tested: int
    avg_top5_overlap_luxury_vs_budget_pct: float
    luxury_persona_avg_top5_price_pkr: float
    budget_persona_avg_top5_price_pkr: float
    personalized_brand_hit_rate_uplift_pct: float


@dataclass
class HallucinationAuditResult:
    """Verification record ensuring zero hallucinated products or prices in assistant replies."""

    mentioned_product_ids: list[str]
    valid_product_ids: list[str]
    hallucinated_product_ids: list[str]
    mentioned_prices_pkr: list[float]
    hallucinated_prices_pkr: list[float]
    passed_zero_hallucination_check: bool


@dataclass
class AssistantTurnResponse:
    """Structured output for a single conversational turn of `UrduLishShoppingAssistant`."""

    session_id: str
    turn_index: int
    user_message: str
    detected_intent: str
    invoked_tools: list[str]
    tool_outputs: dict[str, Any]
    assistant_reply_urdulish: str
    shown_product_ids: list[str]
    cart_item_count: int
    cart_total_pkr: float
    hallucination_audit: HallucinationAuditResult
    engine: str = "rules"  # "llm" | "rules" | "rules_fallback"
    fallback_reason: str | None = None


@dataclass
class ConversationSessionState:
    """Multi-turn session memory for the UrduLish Shopping Assistant."""

    session_id: str
    user_id: str = "USR-DEMO-01"
    last_shown_products: list[dict[str, Any]] = field(default_factory=list)
    active_filters: dict[str, Any] = field(default_factory=dict)
    cart: list[dict[str, Any]] = field(default_factory=list)
    turn_history: list[AssistantTurnResponse] = field(default_factory=list)


# ============================================================================
# Task 2: Personalized Search Re-Ranker
# ============================================================================
class PersonalizedSearchReRanker:
    """
    Day 4 — Task 2: Personalized Search Re-Ranking Layer.

    Blends query-document relevance s_search(q, i) from `HybridSearchEngine` with user profile
    compatibility s_user(u, i) across brand affinity, category affinity, and log-price tier:
        s_final(q, u, i) = (1 - λ) * s_search(q, i) + λ * s_user(u, i)
    """

    def __init__(
        self,
        search_engine: HybridSearchEngine,
        personalization_weight: float = 0.38,
    ) -> None:
        self.search_engine = search_engine
        self.personalization_weight = personalization_weight
        self.user_profiles: dict[str, UserSearchProfile] = {}
        # Collaborative re-ranking (set by the serving layer to its RealtimeItemCFRecommender). Pool and weight were
        # chosen on dev users and confirmed on held-out users (shopkaro.search.personalization_eval).
        self.cf_recommender: Any = None
        self.cf_pool = 200
        self.cf_weight = 0.9
        self.persona_weight = 0.5
        self._init_curated_personas()

    def _search_cf_reranked(self, query: str, user_id: str, k: int) -> list[dict[str, Any]]:
        rt = self.cf_recommender
        # No cross-encoder here: the item-CF score (weight 0.9) re-orders the whole pool anyway.
        pool, _ = self.search_engine.search_hybrid(query=query, k=self.cf_pool, only_in_stock=True, cross_encode=False)
        if not pool:
            return []
        scores_u = rt.cf._score_user_vector(
            user_id=user_id, exclude_seen=False, only_in_stock=True, u_vec=rt.user_vector(user_id)
        )
        s_search = np.array([float(c["score"]) for c in pool])
        s_cf = np.array(
            [float(scores_u[rt.cf.item_to_col[c["product_id"]]]) if c["product_id"] in rt.cf.item_to_col else 0.0 for c in pool]
        )
        ns = (s_search - s_search.min()) / max(float(s_search.max() - s_search.min()), 1e-9)
        nc = (s_cf - s_cf.min()) / max(float(s_cf.max() - s_cf.min()), 1e-9)
        final = (1.0 - self.cf_weight) * ns + self.cf_weight * nc
        order = np.argsort(-final, kind="stable")[:k]
        out = []
        for rank, i in enumerate(order, start=1):
            item = dict(pool[i])
            item["raw_search_score"] = round(float(pool[i]["score"]), 4)
            item["personalization_score"] = round(float(nc[i]), 4)
            item["score"] = round(float(final[i]), 4)
            item["personalized_for"] = "your browsing history (item-CF)"
            item["rank"] = rank
            out.append(item)
        return out

    def _init_curated_personas(self) -> None:
        """Register canonical Pakistani shopper personas alongside database user profiles."""
        self.user_profiles["PERSONA_LUXURY_VIP"] = UserSearchProfile(
            user_id="PERSONA_LUXURY_VIP",
            persona_name="Loyal Luxury & Designer Buyer",
            preferred_categories={
                "Women's Lawn & Unstitched": 0.45,
                "Bridal & Formal Wear": 0.35,
                "Laptops & Computing": 0.20,
            },
            preferred_brands={
                "Sapphire": 1.0,
                "Maria B": 1.0,
                "Asim Jofa": 0.9,
                "Apple": 1.0,
                "Lenovo": 0.9,
                "Samsung": 0.9,
            },
            avg_item_price_pkr=9500.0,
            price_sensitivity="luxury",
        )
        self.user_profiles["PERSONA_BUDGET_HUNTER"] = UserSearchProfile(
            user_id="PERSONA_BUDGET_HUNTER",
            persona_name="Value & Discount Bargain Hunter",
            preferred_categories={
                "Women's Lawn & Unstitched": 0.50,
                "Kids & School Supplies": 0.30,
                "Smartphones & Accessories": 0.20,
            },
            preferred_brands={
                "Beechtree": 1.0,
                "Bonanza Satrangi": 0.95,
                "Limelight": 0.9,
                "Polo Kids": 0.9,
                "Infinix": 0.9,
                "Xiaomi Redmi": 0.9,
            },
            avg_item_price_pkr=2100.0,
            price_sensitivity="budget",
        )
        self.user_profiles["PERSONA_TECH_STUDENT"] = UserSearchProfile(
            user_id="PERSONA_TECH_STUDENT",
            persona_name="University CS & Tech Enthusiast",
            preferred_categories={
                "Laptops & Computing": 0.55,
                "Smartphones & Accessories": 0.45,
            },
            preferred_brands={
                "Lenovo": 1.0,
                "HP": 0.95,
                "Dell": 0.85,
                "Samsung": 0.9,
                "Anker": 0.9,
                "Baseus": 0.85,
            },
            avg_item_price_pkr=65000.0,
            price_sensitivity="mid",
        )

    def fit_user_profiles_from_duckdb(
        self,
        con: duckdb.DuckDBPyConnection,
        max_users: int = 5000,
    ) -> PersonalizedSearchReRanker:
        """Build historical category, brand, and price profiles for top active users in DuckDB."""
        df = con.execute(
            f"""
            WITH top_u AS (
                SELECT user_id, SUM(implicit_weight) AS w_sum
                FROM train_interactions
                GROUP BY user_id
                ORDER BY w_sum DESC, user_id
                LIMIT {int(max_users)}
            )
            SELECT
                t.user_id,
                t.category,
                t.brand,
                AVG(t.price_pkr) AS avg_price,
                SUM(t.implicit_weight) AS weight
            FROM train_interactions t
            JOIN top_u u ON t.user_id = u.user_id
            GROUP BY t.user_id, t.category, t.brand;
            """
        ).df()

        for uid, grp in df.groupby("user_id"):
            uid_str = str(uid)
            tot_w = max(float(grp["weight"].sum()), 1.0)
            cat_w = (
                grp.groupby("category")["weight"]
                .sum()
                .div(tot_w)
                .to_dict()
            )
            brand_w = (
                grp.groupby("brand")["weight"]
                .sum()
                .div(tot_w)
                .to_dict()
            )
            avg_p = float(np.average(grp["avg_price"], weights=grp["weight"]))
            sens = "budget" if avg_p < 3200 else ("luxury" if avg_p > 12000 else "mid")
            self.user_profiles[uid_str] = UserSearchProfile(
                user_id=uid_str,
                persona_name=f"Warm User ({sens.title()})",
                preferred_categories={str(k): float(v) for k, v in cat_w.items()},
                preferred_brands={str(k): float(v) for k, v in brand_w.items()},
                avg_item_price_pkr=round(avg_p, 2),
                price_sensitivity=sens,
            )
        return self

    def search_personalized(
        self,
        query: str,
        user_id: str | None = None,
        k: int = 10,
        candidate_pool: int = 40,
    ) -> tuple[list[dict[str, Any]], ParsedSearchQuery]:
        """
        Retrieve candidates from `HybridSearchEngine` and re-rank for `user_id`.

        - Users with interaction history (known to `cf_recommender`): collaborative re-ranking of the top
          `cf_pool` candidates, final = (1 - cf_weight) * search + cf_weight * item-CF score (both min-max scaled).
          On held-out users this raised NDCG@10 from 0.012 to 0.064 (reports/day4_personalized_search_eval.json).
        - Curated demo personas: the brand / category / price profile blend below (no measurable effect on real
          users, kept only for the persona demos).
        - Anyone else: plain hybrid search (not personalised).
        """
        rt = self.cf_recommender
        if rt is not None and user_id and not str(user_id).startswith("PERSONA_") and rt.is_known(str(user_id)):
            return self._search_cf_reranked(query, str(user_id), k), self.search_engine.parser.parse(query)

        candidates, parsed = self.search_engine.search_hybrid(
            query=query,
            k=candidate_pool,
            only_in_stock=True,
        )
        if not user_id or user_id not in self.user_profiles or not candidates:
            return candidates[:k], parsed

        profile = self.user_profiles[user_id]
        raw_scores = np.array([float(c["score"]) for c in candidates], dtype=np.float32)
        s_min, s_max = float(raw_scores.min()), float(raw_scores.max())
        span = max(s_max - s_min, 1e-6)

        # Demo personas express a RELATIVE price preference within this query's candidates (luxury -> pricier end,
        # budget -> cheaper end). A fixed price anchor (e.g. "luxury = PKR 9,500") pulled luxury shoppers towards
        # the cheapest bridal dresses, because every bridal candidate costs more than the anchor.
        is_persona = str(user_id).startswith("PERSONA_")
        # Demo personas get a stronger blend (0.5) so their results visibly differ; real users use item-CF above.
        weight = self.persona_weight if is_persona else self.personalization_weight
        prices = np.array([float(c["price_pkr"]) for c in candidates])
        price_pct = (prices.argsort().argsort() / max(len(prices) - 1, 1)) if len(prices) > 1 else np.zeros(1)

        reranked: list[dict[str, Any]] = []
        for c_idx, cand in enumerate(candidates):
            q_norm = (float(cand["score"]) - s_min) / span
            cat = str(cand["category"])
            brand = str(cand["brand"])
            price = float(cand["price_pkr"])
            on_sale = bool(cand["on_sale"])

            cat_aff = float(profile.preferred_categories.get(cat, 0.0))
            brand_aff = float(profile.preferred_brands.get(brand, 0.0))

            if is_persona:
                pct = float(price_pct[c_idx])
                price_compat = {"luxury": pct, "budget": 1.0 - pct}.get(profile.price_sensitivity, 1.0 - abs(pct - 0.5) * 2)
            else:
                # Gaussian log-price compatibility around the user's historical average price
                log_diff = abs(np.log1p(price) - np.log1p(max(profile.avg_item_price_pkr, 500.0)))
                price_compat = float(np.exp(-0.85 * (log_diff ** 2)))

            if profile.price_sensitivity == "budget":
                tier_bonus = 0.25 * (1.0 / (1.0 + price / 3000.0)) + (0.15 if on_sale else 0.0)
            elif profile.price_sensitivity == "luxury":
                tier_bonus = 0.25 * min(price / 8000.0, 1.0)
            else:
                tier_bonus = 0.10 * price_compat

            user_score = (
                0.35 * brand_aff
                + 0.20 * cat_aff
                + 0.25 * price_compat
                + 0.20 * tier_bonus
            )
            final_sc = (
                (1.0 - weight) * q_norm
                + weight * user_score
            )
            item_copy = dict(cand)
            item_copy["raw_search_score"] = round(float(cand["score"]), 4)
            item_copy["personalization_score"] = round(float(user_score), 4)
            item_copy["score"] = round(float(final_sc), 4)
            item_copy["personalized_for"] = profile.persona_name
            reranked.append(item_copy)

        reranked.sort(key=lambda x: float(x["score"]), reverse=True)
        for idx, item in enumerate(reranked[:k], start=1):
            item["rank"] = idx
        return reranked[:k], parsed


# ============================================================================
# Task 3: The 6 Grounded E-Commerce Backend Tools + Hallucination Auditor
# ============================================================================
class ShopKaroToolRegistry:
    """
    Implements the 6 backend tools required by the UrduLish Shopping Assistant:
    1. `search_products`
    2. `get_recommendations`
    3. `compare_products`
    4. `add_to_cart`
    5. `get_order_status`
    6. `get_review_summary`
    """

    def __init__(
        self,
        db_path: Path,
        search_engine: HybridSearchEngine,
        personalizer: PersonalizedSearchReRanker,
    ) -> None:
        self.db_path = db_path
        self.search_engine = search_engine
        self.personalizer = personalizer
        self.catalog_map: dict[str, dict[str, Any]] = {
            str(r["product_id"]): r for r in search_engine.records
        }
        self._load_reviews_and_orders()

    def _load_reviews_and_orders(self) -> None:
        con = duckdb.connect(str(self.db_path), read_only=True)
        self.reviews_df = con.execute(
            """
            SELECT
                product_id,
                order_id,
                rating,
                sentiment_label,
                language,
                review_title,
                review_text,
                delivery_delay_days,
                aspect_quality,
                aspect_price,
                aspect_delivery,
                aspect_size_fit,
                aspect_packaging,
                aspect_seller,
                is_fake_spam
            FROM reviews
            WHERE is_fake_spam = FALSE;
            """
        ).df()
        con.close()

        # Pre-index sample realistic Pakistani order tracking records from Olist orders + Hero SKUs
        self.order_tracking_db: dict[str, dict[str, Any]] = {
            "ORD-1001": {
                "order_id": "ORD-1001",
                "customer_city": "Lahore",
                "courier_partner": "TCS Express",
                "tracking_number": "TCS-8849201-LHR",
                "order_status": "In Transit — Arrived at Lahore Gulberg Hub",
                "estimated_delivery": "Tomorrow by 6:00 PM",
                "payment_method": "Cash on Delivery (COD)",
                "items": [
                    {
                        "product_id": "SK-00001",
                        "title": self.catalog_map["SK-00001"]["title"],
                        "price_pkr": float(self.catalog_map["SK-00001"]["price_pkr"]),
                        "qty": 1,
                    }
                ],
                "total_pkr": float(self.catalog_map["SK-00001"]["price_pkr"]),
            },
            "ORD-1002": {
                "order_id": "ORD-1002",
                "customer_city": "Karachi",
                "courier_partner": "Leopards Courier",
                "tracking_number": "LCS-5521904-KHI",
                "order_status": "Out for Delivery — Rider Assigned (DHA Phase 6)",
                "estimated_delivery": "Today within 3 hours",
                "payment_method": "JazzCash / EasyPaisa Paid",
                "items": [
                    {
                        "product_id": "SK-00013",
                        "title": self.catalog_map["SK-00013"]["title"],
                        "price_pkr": float(self.catalog_map["SK-00013"]["price_pkr"]),
                        "qty": 1,
                    },
                    {
                        "product_id": "SK-00015",
                        "title": self.catalog_map["SK-00015"]["title"],
                        "price_pkr": float(self.catalog_map["SK-00015"]["price_pkr"]),
                        "qty": 1,
                    },
                ],
                "total_pkr": float(
                    self.catalog_map["SK-00013"]["price_pkr"]
                    + self.catalog_map["SK-00015"]["price_pkr"]
                ),
            },
        }
        # Also index real `order_id`s from `reviews_df`
        for _, row in self.reviews_df.head(50).iterrows():
            oid = str(row["order_id"])
            pid = str(row["product_id"])
            if oid not in self.order_tracking_db and pid in self.catalog_map:
                delay = int(row["delivery_delay_days"])
                status = (
                    "Delivered on Time"
                    if delay <= 0
                    else f"Delivered ({delay}d courier delay)"
                )
                self.order_tracking_db[oid] = {
                    "order_id": oid,
                    "customer_city": "Islamabad",
                    "courier_partner": "Trax Logistics",
                    "tracking_number": f"TRX-{oid[:8].upper()}",
                    "order_status": status,
                    "estimated_delivery": "Delivered",
                    "payment_method": "Cash on Delivery (COD)",
                    "items": [
                        {
                            "product_id": pid,
                            "title": self.catalog_map[pid]["title"],
                            "price_pkr": float(self.catalog_map[pid]["price_pkr"]),
                            "qty": 1,
                        }
                    ],
                    "total_pkr": float(self.catalog_map[pid]["price_pkr"]),
                }

    # Tool 1: search_products
    def search_products(
        self,
        query: str,
        user_id: str | None = None,
        max_price_pkr: float | None = None,
        category: str | None = None,
        k: int = 5,
    ) -> dict[str, Any]:
        results, parsed = self.personalizer.search_personalized(
            query=query,
            user_id=user_id,
            k=25,
        )
        effective_max = max_price_pkr if max_price_pkr is not None else parsed.max_price_pkr
        effective_cat = category if category is not None else parsed.category_hint

        filtered = []
        for r in results:
            if effective_max is not None and float(r["price_pkr"]) > effective_max:
                continue
            if (
                effective_cat is not None
                and "ammi" not in query.lower()
                and r["category"] != effective_cat
            ):
                continue
            filtered.append(r)

        # If nothing satisfies the budget/category, return the closest matches but say so explicitly,
        # so callers never present over-budget items as if they matched.
        constraints_relaxed = not filtered and bool(results)
        if not filtered:
            filtered = results[:k]

        return {
            "tool": "search_products",
            "query": query,
            "parsed_constraints": asdict(parsed),
            "effective_max_price_pkr": effective_max,
            "effective_category": effective_cat,
            "constraints_relaxed": constraints_relaxed,
            "results": filtered[:k],
        }

    # Tool 2: get_recommendations
    def get_recommendations(
        self,
        occasion: str | None = None,
        max_budget_pkr: float | None = None,
        recipient_hint: str | None = None,
        category: str | None = None,
        k: int = 5,
    ) -> dict[str, Any]:
        """Return curated & personalized gift/occasion recommendations."""
        synthetic_q_parts = []
        if recipient_hint:
            synthetic_q_parts.append(recipient_hint)
        if occasion:
            synthetic_q_parts.append(occasion)
        if category:
            synthetic_q_parts.append(category)
        if max_budget_pkr is not None:
            synthetic_q_parts.append(f"under {int(max_budget_pkr)}")

        q_str = " ".join(synthetic_q_parts) if synthetic_q_parts else "eid festive best sellers"

        # If asking for Ammi Eid Gift under 3000, prioritize our curated hero gift items (SK-00010, SK-00011, SK-00012)
        recs: list[dict[str, Any]] = []
        if recipient_hint and "ammi" in recipient_hint.lower():
            for pid in ["SK-00010", "SK-00011", "SK-00012", "SK-00001", "SK-00002"]:
                if pid in self.catalog_map:
                    meta = self.catalog_map[pid]
                    if not meta["in_stock"]:
                        continue
                    if max_budget_pkr is not None and float(meta["price_pkr"]) > max_budget_pkr:
                        continue
                    recs.append(
                        {
                            "rank": len(recs) + 1,
                            "product_id": pid,
                            "title": str(meta["title"]),
                            "category": str(meta["category"]),
                            "sub_category": str(meta["sub_category"]),
                            "brand": str(meta["brand"]),
                            "price_pkr": float(meta["price_pkr"]),
                            "on_sale": bool(meta["on_sale"]),
                            "discount_pct": float(meta["discount_pct"]),
                            "in_stock": bool(meta["in_stock"]),
                            "reason_urdulish": (
                                f"Ammi ke Eid gift ke liye {meta['brand']} ka yeh {meta['sub_category']} "
                                f"(PKR {float(meta['price_pkr']):,.0f}) behtareen aur bohot pasandida intikhab hai."
                            ),
                        }
                    )

        if len(recs) < k:
            search_res = self.search_products(
                query=q_str,
                max_price_pkr=max_budget_pkr,
                category=category,
                k=k,
            )["results"]
            seen = {r["product_id"] for r in recs}
            for item in search_res:
                if item["product_id"] not in seen:
                    item_copy = dict(item)
                    item_copy["rank"] = len(recs) + 1
                    item_copy["reason_urdulish"] = (
                        f"{item['brand']} ka yeh {item['sub_category']} aap ke budget aur occasion ke mutabiq top choice hai."
                    )
                    recs.append(item_copy)
                if len(recs) >= k:
                    break

        return {
            "tool": "get_recommendations",
            "occasion": occasion or "Eid / Festive",
            "max_budget_pkr": max_budget_pkr,
            "recommendations": recs[:k],
        }

    # Tool 3: compare_products
    def compare_products(self, product_ids: list[str]) -> dict[str, Any]:
        """Compare 2 to 4 products side-by-side on price, specs, stock, and customer review ratings."""
        comparison_rows: list[dict[str, Any]] = []
        for pid in product_ids[:4]:
            meta = self.catalog_map.get(pid)
            if not meta:
                continue
            rev_summary = self.get_review_summary(pid)
            comparison_rows.append(
                {
                    "product_id": pid,
                    "title": str(meta["title"]),
                    "brand": str(meta["brand"]),
                    "category": str(meta["category"]),
                    "sub_category": str(meta["sub_category"]),
                    "color": str(meta["color"]),
                    "occasion": str(meta["occasion"]),
                    "price_pkr": float(meta["price_pkr"]),
                    "on_sale": bool(meta["on_sale"]),
                    "discount_pct": float(meta["discount_pct"]),
                    "in_stock": bool(meta["in_stock"]),
                    "avg_rating": rev_summary["avg_rating"],
                    "review_count": rev_summary["total_reviews"],
                    "positive_sentiment_pct": rev_summary["positive_pct"],
                }
            )

        winner_pid = None
        if comparison_rows:
            # Pick best value-for-money + rating winner
            # Unreviewed products (avg_rating None) rank below any reviewed product
            best = max(
                comparison_rows,
                key=lambda x: (
                    float(x["avg_rating"]) if x["avg_rating"] is not None else -1.0,
                    -float(x["price_pkr"]),
                ),
            )
            winner_pid = best["product_id"]

        return {
            "tool": "compare_products",
            "compared_products": comparison_rows,
            "recommended_winner_id": winner_pid,
        }

    # Tool 4: add_to_cart
    def add_to_cart(
        self,
        session: ConversationSessionState,
        product_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """Verify live stock, add item to session cart, compute PKR total, and suggest cross-sell."""
        meta = self.catalog_map.get(product_id)
        if not meta:
            return {
                "tool": "add_to_cart",
                "success": False,
                "error": f"Product {product_id} not found in ShopKaro catalogue.",
            }
        if not bool(meta["in_stock"]) or int(meta.get("stock_qty", 0)) < quantity:
            return {
                "tool": "add_to_cart",
                "success": False,
                "error": f"Product {product_id} ({meta['title']}) is currently out of stock.",
            }

        unit_price = float(meta["price_pkr"])
        line_total = unit_price * quantity

        # Update if already in cart
        updated = False
        for item in session.cart:
            if item["product_id"] == product_id:
                item["quantity"] += quantity
                item["line_total_pkr"] = item["quantity"] * unit_price
                updated = True
                break
        if not updated:
            session.cart.append(
                {
                    "product_id": product_id,
                    "title": str(meta["title"]),
                    "brand": str(meta["brand"]),
                    "unit_price_pkr": unit_price,
                    "quantity": quantity,
                    "line_total_pkr": line_total,
                }
            )

        cart_total = sum(float(i["line_total_pkr"]) for i in session.cart)
        return {
            "tool": "add_to_cart",
            "success": True,
            "added_product": {
                "product_id": product_id,
                "title": str(meta["title"]),
                "brand": str(meta["brand"]),
                "price_pkr": unit_price,
                "quantity": quantity,
            },
            "cart_item_count": sum(int(i["quantity"]) for i in session.cart),
            "cart_total_pkr": cart_total,
        }

    # Tool 5: get_order_status
    def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Lookup order delivery status, courier partner, and items."""
        clean_id = order_id.strip().upper()
        if clean_id in self.order_tracking_db:
            return {
                "tool": "get_order_status",
                "found": True,
                "order": self.order_tracking_db[clean_id],
            }
        # Never substitute another customer's order for an unknown ID.
        return {
            "tool": "get_order_status",
            "found": False,
            "order_id": clean_id,
            "error": f"Order {clean_id} not found. Please check the order ID (format ORD-1234).",
        }

    # Tool 6: get_review_summary
    def get_review_summary(self, product_id: str) -> dict[str, Any]:
        """Summarize verified non-spam customer reviews, ratings, and aspect scores for `product_id`."""
        meta = self.catalog_map.get(product_id, {})
        sub = self.reviews_df[self.reviews_df["product_id"] == product_id]

        if not meta:
            return {
                "tool": "get_review_summary",
                "product_id": product_id,
                "found": False,
                "error": f"Product {product_id} not found in ShopKaro catalogue.",
            }
        if sub.empty:
            # No reviews yet: report that honestly instead of inventing a rating or quotes.
            return {
                "tool": "get_review_summary",
                "product_id": product_id,
                "found": True,
                "title": str(meta.get("title", product_id)),
                "brand": str(meta.get("brand", "")),
                "price_pkr": float(meta.get("price_pkr", 0.0)),
                "total_reviews": 0,
                "avg_rating": None,
                "positive_pct": None,
                "negative_pct": None,
                "aspect_scores": {},
                "sample_quotes": [],
            }

        tot = len(sub)
        avg_r = round(float(sub["rating"].mean()), 2)
        pos_pct = round(float((sub["sentiment_label"] == "Positive").mean() * 100.0), 1)
        neg_pct = round(float((sub["sentiment_label"] == "Negative").mean() * 100.0), 1)

        aspects = {
            "quality": round(float(sub["aspect_quality"].mean()), 2),
            "price_value": round(float(sub["aspect_price"].mean()), 2),
            "delivery": round(float(sub["aspect_delivery"].mean()), 2),
            "size_fit": round(float(sub["aspect_size_fit"].mean()), 2),
            "packaging": round(float(sub["aspect_packaging"].mean()), 2),
        }
        quotes = sub["review_text"].astype(str).head(3).tolist()

        return {
            "tool": "get_review_summary",
            "product_id": product_id,
            "found": True,
            "title": str(meta.get("title", product_id)),
            "brand": str(meta.get("brand", "")),
            "price_pkr": float(meta.get("price_pkr", 0.0)),
            "total_reviews": tot,
            "avg_rating": avg_r,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "aspect_scores": aspects,
            "sample_quotes": quotes,
        }


class HallucinationAuditor:
    """
    Verifies that every product ID (`SK-XXXXX`) and PKR price mentioned in the assistant's
    response exists in the grounded tool outputs returned during the conversation.
    """

    @staticmethod
    def verify_response(
        response_text: str,
        allowed_products: dict[str, float],
        extra_valid_prices: set[float] | None = None,
    ) -> HallucinationAuditResult:
        mentioned_pids = re.findall(r"\bSK-\d{5}\b", response_text)
        valid_pids = [pid for pid in mentioned_pids if pid in allowed_products]
        hallucinated_pids = [pid for pid in mentioned_pids if pid not in allowed_products]

        # Extract PKR amounts: prefix form ("PKR 2,450", "Rs. 138,000") and
        # suffix form ("2,450 rupay", "4500 PKR", "2,450/-")
        prefix = re.findall(r"(?:PKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", response_text, flags=re.I)
        suffix = re.findall(
            r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(?:PKR\b|rupay\b|rupaye\b|rupees?\b|/-)",
            response_text,
            flags=re.I,
        )
        mentioned_prices = [
            float(p.replace(",", "").rstrip(".")) for p in prefix + suffix if p.replace(",", "").rstrip(".")
        ]

        valid_price_set = {round(float(v), 0) for v in allowed_products.values()}
        if extra_valid_prices:
            valid_price_set.update({round(float(v), 0) for v in extra_valid_prices})

        hallucinated_prices = [
            p for p in mentioned_prices if round(p, 0) not in valid_price_set
        ]

        return HallucinationAuditResult(
            mentioned_product_ids=mentioned_pids,
            valid_product_ids=valid_pids,
            hallucinated_product_ids=hallucinated_pids,
            mentioned_prices_pkr=mentioned_prices,
            hallucinated_prices_pkr=hallucinated_prices,
            passed_zero_hallucination_check=(
                len(hallucinated_pids) == 0 and len(hallucinated_prices) == 0
            ),
        )


# ============================================================================
# Task 3: Multi-Turn UrduLish Conversational Shopping Assistant
# ============================================================================
class UrduLishShoppingAssistant:
    """
    Multi-turn conversational shopping assistant supporting Roman Urdu ("UrduLish"),
    English, and Urdu script with 6 grounded tools and zero-hallucination guardrails.
    """

    def __init__(self, tools: ShopKaroToolRegistry) -> None:
        self.tools = tools
        self.sessions: dict[str, ConversationSessionState] = {}

    def get_or_create_session(
        self, session_id: str, user_id: str = "USR-DEMO-01"
    ) -> ConversationSessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSessionState(
                session_id=session_id,
                user_id=user_id,
            )
        return self.sessions[session_id]

    def _resolve_product_references(
        self,
        message: str,
        session: ConversationSessionState,
    ) -> list[str]:
        """
        Resolve explicit `SK-XXXXX` IDs or conversational ordinals in Roman Urdu & English
        ("pehla", "doosra", "teesra", "first", "second", "third", "dono") from `session.last_shown_products`.
        """
        explicit = re.findall(r"\bSK-\d{5}\b", message.upper())
        if explicit:
            return explicit

        msg_l = message.lower()
        shown = session.last_shown_products
        if not shown:
            return []

        resolved: list[str] = []
        ordinal_map = [
            (0, ["pehla", "pehle", "pehli", "first", "#1", "1st", "option 1"]),
            (1, ["doosra", "dusra", "doosre", "second", "#2", "2nd", "option 2"]),
            (2, ["teesra", "tisra", "third", "#3", "3rd", "option 3"]),
        ]
        for idx, words in ordinal_map:
            if idx < len(shown) and any(w in msg_l for w in words):
                resolved.append(str(shown[idx]["product_id"]))

        if not resolved and any(w in msg_l for w in ["dono", "both", "compare"]):
            resolved = [str(p["product_id"]) for p in shown[:2]]
        elif not resolved and len(shown) > 0:
            resolved = [str(shown[0]["product_id"])]

        return resolved

    def chat(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "USR-DEMO-01",
    ) -> AssistantTurnResponse:
        session = self.get_or_create_session(session_id=session_id, user_id=user_id)
        turn_idx = len(session.turn_history) + 1
        msg_l = user_message.lower().strip()

        invoked_tools: list[str] = []
        tool_outputs: dict[str, Any] = {}
        allowed_products: dict[str, float] = {
            str(p["product_id"]): float(p["price_pkr"]) for p in session.last_shown_products
        }
        extra_prices: set[float] = set()
        shown_ids: list[str] = []

        # 1. Detect Intent: Order Status ("order status", "mera order kahan hai", "ORD-...")
        if any(w in msg_l for w in ["order status", "mera order", "tracking", "ord-", "delivery status"]):
            intent = "order_status_inquiry"
            m_ord = re.search(r"\b(ORD-\d+)\b", user_message, flags=re.I)
            ord_out: dict[str, Any] | None = None
            if m_ord:
                invoked_tools.append("get_order_status")
                ord_out = self.tools.get_order_status(m_ord.group(1).upper())
                tool_outputs["get_order_status"] = ord_out

            if ord_out is None:
                reply = "Zaroor! Apna order ID bata dein (jaise ORD-1001), main foran status check karta hoon."
            elif not ord_out.get("found"):
                reply = f"Maazrat! {ord_out['error']}"
            else:
                ord_data = ord_out["order"]
                extra_prices.add(float(ord_data["total_pkr"]))
                for itm in ord_data["items"]:
                    allowed_products[itm["product_id"]] = float(itm["price_pkr"])

                first_item = ord_data["items"][0]
                reply = (
                    f"Assalam-o-Alaikum! Aap ke order **{ord_data['order_id']}** "
                    f"({first_item['product_id']}: {first_item['title']}, PKR {ord_data['total_pkr']:,.0f}) "
                    f"ka current status hai: **{ord_data['order_status']}** via {ord_data['courier_partner']} "
                    f"(Tracking: `{ord_data['tracking_number']}`). Expected delivery: {ord_data['estimated_delivery']}."
                )

        # 2. Detect Intent: Add to Cart ("cart mein daal", "add to cart", "buy kar", "kharidna hai")
        elif any(w in msg_l for w in ["cart mein", "add to cart", "cart me", "buy kar", "order kar do"]):
            intent = "add_to_cart"
            target_pids = self._resolve_product_references(user_message, session)
            target_pid = target_pids[0] if target_pids else "SK-00010"

            invoked_tools.append("add_to_cart")
            cart_out = self.tools.add_to_cart(session, product_id=target_pid, quantity=1)
            tool_outputs["add_to_cart"] = cart_out

            if cart_out.get("success"):
                added = cart_out["added_product"]
                allowed_products[added["product_id"]] = float(added["price_pkr"])
                extra_prices.add(float(cart_out["cart_total_pkr"]))
                shown_ids = [added["product_id"]]
                reply = (
                    f"Jee bilkul! **{added['product_id']}** ({added['title']} — PKR {added['price_pkr']:,.0f}) "
                    f"aap ke cart mein add kar diya gaya hai. "
                    f"Aap ke cart mein ab {cart_out['cart_item_count']} item(s) hain aur total bill "
                    f"**PKR {cart_out['cart_total_pkr']:,.0f}** hai."
                )
            else:
                reply = f"Maazrat! {cart_out.get('error', 'Item could not be added.')}"

        # 3. Detect Intent: Product Comparison ("compare", "muqabla", "farak", "konsa behtar")
        elif any(w in msg_l for w in ["compare", "muqabla", "farak", "difference", "versus", " vs "]):
            intent = "compare_products"
            target_pids = self._resolve_product_references(user_message, session)
            if len(target_pids) < 2 and len(session.last_shown_products) >= 2:
                target_pids = [
                    str(session.last_shown_products[0]["product_id"]),
                    str(session.last_shown_products[1]["product_id"]),
                ]
            elif len(target_pids) < 2:
                target_pids = ["SK-00008", "SK-00009"]

            invoked_tools.append("compare_products")
            comp_out = self.tools.compare_products(target_pids)
            tool_outputs["compare_products"] = comp_out

            items = comp_out["compared_products"]
            for itm in items:
                allowed_products[itm["product_id"]] = float(itm["price_pkr"])
            shown_ids = [itm["product_id"] for itm in items]

            lines = ["Yeh raha dono products ka side-by-side muqabla (comparison):"]
            for itm in items:
                rating_txt = (
                    f"Rating: {itm['avg_rating']}/5.0 ({itm['positive_sentiment_pct']}% positive reviews)"
                    if itm["avg_rating"] is not None
                    else "Abhi tak koi review nahi"
                )
                lines.append(
                    f"- **{itm['product_id']} ({itm['brand']})**: {itm['title']} | "
                    f"Qeemat: **PKR {itm['price_pkr']:,.0f}** | {rating_txt}"
                )
            winner_id = comp_out.get("recommended_winner_id")
            if winner_id:
                lines.append(
                    f"Meri tajweez: **{winner_id}** rating aur value-for-money ke lihaaz se behtareen intikhab hai!"
                )
            reply = "\n".join(lines)

        # 4. Detect Intent: Review Summary ("reviews", "rating", "feedback", "kaisay hain")
        elif any(w in msg_l for w in ["review", "reviews", "rating", "feedback", "kaisay hain", "kaisa hai"]):
            intent = "review_summary"
            target_pids = self._resolve_product_references(user_message, session)
            target_pid = target_pids[0] if target_pids else "SK-00001"

            invoked_tools.append("get_review_summary")
            rev_out = self.tools.get_review_summary(target_pid)
            tool_outputs["get_review_summary"] = rev_out

            if not rev_out.get("found"):
                reply = f"Maazrat! {rev_out['error']}"
            elif rev_out["total_reviews"] == 0:
                allowed_products[target_pid] = float(rev_out["price_pkr"])
                shown_ids = [target_pid]
                reply = (
                    f"**{target_pid}** ({rev_out['title']} — PKR {rev_out['price_pkr']:,.0f}) "
                    f"ke abhi tak koi verified customer reviews nahi hain."
                )
            else:
                allowed_products[target_pid] = float(rev_out["price_pkr"])
                shown_ids = [target_pid]
                lines = [
                    f"**{target_pid}** ({rev_out['title']} — PKR {rev_out['price_pkr']:,.0f}) ke "
                    f"total **{rev_out['total_reviews']} verified customer reviews** hain:",
                    f"- Average Rating: **{rev_out['avg_rating']}/5.0** ({rev_out['positive_pct']}% Positive)",
                ]
                if rev_out["sample_quotes"]:
                    lines.append(f"- Customer Quote: *\"{rev_out['sample_quotes'][0]}\"*")
                reply = "\n".join(lines)

        # 5. Detect Intent: Gift / Personalized Recommendations ("gift", "suggest", "recommend", "ammi ke liye")
        elif any(w in msg_l for w in ["gift", "recommend", "suggest", "ammi", "tahfa", "mashwara"]):
            intent = "personalized_recommendation"
            assert self.tools.search_engine.parser is not None
            parsed = self.tools.search_engine.parser.parse(user_message)
            max_p = parsed.max_price_pkr or session.active_filters.get("max_price_pkr")
            if max_p:
                session.active_filters["max_price_pkr"] = max_p

            invoked_tools.append("get_recommendations")
            rec_out = self.tools.get_recommendations(
                occasion=parsed.occasion_hint or "Eid",
                max_budget_pkr=max_p,
                recipient_hint="ammi" if "ammi" in msg_l else None,
                category=parsed.category_hint,
                k=3,
            )
            tool_outputs["get_recommendations"] = rec_out

            recs = rec_out["recommendations"]
            session.last_shown_products = recs
            for r in recs:
                allowed_products[r["product_id"]] = float(r["price_pkr"])
            if max_p:
                extra_prices.add(float(max_p))
            shown_ids = [r["product_id"] for r in recs]

            lines = [
                f"Jee zaroor! Aap ki request ke mutabiq top {len(recs)} recommendations hazir hain:"
            ]
            for idx, r in enumerate(recs, start=1):
                lines.append(
                    f"{idx}. **{r['product_id']}** — {r['title']} ({r['brand']}) | "
                    f"**PKR {r['price_pkr']:,.0f}**\n   *{r['reason_urdulish']}*"
                )
            lines.append(
                "Kya aap in mein se kisi ko compare karna chahein ge ya cart mein add karein?"
            )
            reply = "\n".join(lines)

        # 6. Default Intent: Product Search ("search_products")
        else:
            intent = "product_search"
            invoked_tools.append("search_products")
            search_out = self.tools.search_products(
                query=user_message,
                user_id=user_id,
                k=3,
            )
            tool_outputs["search_products"] = search_out

            results = search_out["results"]
            session.last_shown_products = results
            for r in results:
                allowed_products[r["product_id"]] = float(r["price_pkr"])
            shown_ids = [r["product_id"] for r in results]

            lines = [f"Aap ki search ke mutabiq top {len(results)} in-stock products yeh hain:"]
            for idx, r in enumerate(results, start=1):
                sale_tag = f" ({int(r['discount_pct'])}% OFF)" if r["on_sale"] else ""
                lines.append(
                    f"{idx}. **{r['product_id']}** — {r['title']} ({r['brand']} | {r['category']}) "
                    f"| **PKR {r['price_pkr']:,.0f}**{sale_tag}"
                )
            lines.append(
                "Aap 'pehla aur doosra compare karo', 'reviews dikhao', ya 'cart mein daal do' keh sakte hain!"
            )
            reply = "\n".join(lines)

        # Run Zero-Hallucination Guardrail Audit
        audit = HallucinationAuditor.verify_response(
            response_text=reply,
            allowed_products=allowed_products,
            extra_valid_prices=extra_prices,
        )

        cart_cnt = sum(int(i["quantity"]) for i in session.cart)
        cart_tot = sum(float(i["line_total_pkr"]) for i in session.cart)

        turn_resp = AssistantTurnResponse(
            session_id=session_id,
            turn_index=turn_idx,
            user_message=user_message,
            detected_intent=intent,
            invoked_tools=invoked_tools,
            tool_outputs=tool_outputs,
            assistant_reply_urdulish=reply,
            shown_product_ids=shown_ids,
            cart_item_count=cart_cnt,
            cart_total_pkr=cart_tot,
            hallucination_audit=audit,
        )
        session.turn_history.append(turn_resp)
        return turn_resp


def run_day4_task2_task3_personalizer_and_assistant(
    db_path: Path | None = None,
) -> tuple[
    PersonalizationEvalSummary,
    list[AssistantTurnResponse],
    UrduLishShoppingAssistant,
]:
    """
    Execute Day 4 — Tasks 2 & 3:
    1. Fit `HybridSearchEngine` and `PersonalizedSearchReRanker`.
    2. Evaluate Luxury vs Budget persona search divergence across 6 broad queries.
    3. Run a 5-turn UrduLish conversation exercising all 6 tools and verify 0 hallucinations.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

    search_engine = HybridSearchEngine(rrf_k=60).fit_from_duckdb(con)
    personalizer = PersonalizedSearchReRanker(
        search_engine=search_engine,
        personalization_weight=0.40,
    ).fit_user_profiles_from_duckdb(con, max_users=2000)
    con.close()

    # Evaluate Task 2: Luxury vs Budget Persona Re-Ranking across 6 queries
    test_queries = [
        "eid lawn suit",
        "festive dress",
        "smartphone 5g",
        "kids school bag",
        "bridal wedding dress",
        "perfume gift set",
    ]
    overlaps: list[float] = []
    lux_prices: list[float] = []
    bud_prices: list[float] = []
    brand_hits_raw: list[float] = []
    brand_hits_pers: list[float] = []

    lux_brands = set(personalizer.user_profiles["PERSONA_LUXURY_VIP"].preferred_brands.keys())

    for q in test_queries:
        raw_res, _ = search_engine.search_hybrid(q, k=5)
        lux_res, _ = personalizer.search_personalized(q, user_id="PERSONA_LUXURY_VIP", k=5)
        bud_res, _ = personalizer.search_personalized(q, user_id="PERSONA_BUDGET_HUNTER", k=5)

        lux_ids = {r["product_id"] for r in lux_res}
        bud_ids = {r["product_id"] for r in bud_res}
        overlaps.append(len(lux_ids & bud_ids) / 5.0 * 100.0)

        lux_prices.append(float(np.mean([float(r["price_pkr"]) for r in lux_res])))
        bud_prices.append(float(np.mean([float(r["price_pkr"]) for r in bud_res])))

        brand_hits_raw.append(
            float(np.mean([100.0 if r["brand"] in lux_brands else 0.0 for r in raw_res]))
        )
        brand_hits_pers.append(
            float(np.mean([100.0 if r["brand"] in lux_brands else 0.0 for r in lux_res]))
        )

    raw_bh = max(float(np.mean(brand_hits_raw)), 1.0)
    pers_bh = float(np.mean(brand_hits_pers))
    pers_summary = PersonalizationEvalSummary(
        queries_tested=len(test_queries),
        avg_top5_overlap_luxury_vs_budget_pct=round(float(np.mean(overlaps)), 2),
        luxury_persona_avg_top5_price_pkr=round(float(np.mean(lux_prices)), 2),
        budget_persona_avg_top5_price_pkr=round(float(np.mean(bud_prices)), 2),
        personalized_brand_hit_rate_uplift_pct=round((pers_bh - raw_bh) / raw_bh * 100.0, 2),
    )

    # Execute Task 3: 6-Turn Multi-Tool UrduLish Conversation
    tools = ShopKaroToolRegistry(
        db_path=target_db,
        search_engine=search_engine,
        personalizer=personalizer,
    )
    assistant = UrduLishShoppingAssistant(tools=tools)

    scripted_turns = [
        "Ammi ke liye Eid gift chahiye, 3000 tak",
        "Pehla aur doosra compare karo",
        "Pehle wale ke customer reviews kaisay hain?",
        "Bohat acha! Pehla wala cart mein daal do",
        "Acha aur coding ke liye laptop dikhao under 1.5 lac",
        "Mera pichla order ORD-1001 kahan pohancha? Order status batao",
    ]

    conversation_turns: list[AssistantTurnResponse] = []
    for msg in scripted_turns:
        turn_out = assistant.chat(
            session_id="SES-CAPSTONE-DEMO",
            user_message=msg,
            user_id="PERSONA_LUXURY_VIP",
        )
        conversation_turns.append(turn_out)

    return pers_summary, conversation_turns, assistant

