"""
Day 5 — Task 1: Real-Time FastAPI Serving with Sub-100ms Hybrid Redis / TTL Caching.

Endpoints exposed (paths follow the Week 11 brief, Day 5 Task 1):
- GET  /health                        -> Service health, loaded DuckDB tables, and cache backend status
- GET  /metrics                       -> Per-endpoint latency percentiles (p50, p95, p99) & cache hit rate
- GET  /recommendations/{user_id}     -> Personalized + business-re-ranked recommendations (alias: /recommend/{user_id})
- GET  /similar/{product_id}          -> Content-based similar products (cosine over item text embeddings)
- GET  /bought-together/{product_id}  -> Frequently bought together (session co-occurrence rules)
- GET  /search?q=...                  -> Hybrid search + optional user personalization
- POST /assistant/chat                -> Multi-turn UrduLish shopping assistant (alias: /chat)
- GET  /forecast/{product_id}         -> 30-day P10/P50/P90 demand forecast & inventory scorecard
- GET  /inventory/alerts              -> Stock-out / overstock / festival-surge alerts
- GET  /reviews/summary/{product_id}  -> Review intelligence summary (alias: /reviews/{product_id})
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
import json
import os
import threading
import time
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException, Query, Request
import numpy as np
from pydantic import BaseModel, Field

from shopkaro.assistant.llm_agent import LLMShoppingAssistant, build_shopping_assistant
from shopkaro.assistant.shopping_agent import (
    PersonalizedSearchReRanker,
    ShopKaroToolRegistry,
    UrduLishShoppingAssistant,
)
from shopkaro.config.settings import settings
from shopkaro.recommendations.reranking import (
    FESTIVAL_BOOST_MAP,
    AssociationRulesEngine,
    BusinessReRanker,
)
from shopkaro.recommendations.serving import (
    RealtimeItemCFRecommender,
    SessionEventStore,
    explanation_text,
    load_or_train,
)
from shopkaro.search.hybrid_search import HybridSearchEngine



def _rating_or_none(value: Any) -> float | None:
    """Average star rating, or None for products without reviews (NaN from the LEFT JOIN)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if v != v else round(v, 2)

class HybridTTLCache:
    """
    Two-tier cache:
    1. Attempts optional Redis connection if REDIS_URL is set and reachable.
    2. Always maintains a thread-safe in-memory OrderedDict LRU + TTL cache
       guaranteeing <1ms cache hits even in standalone/sandbox environments.
    """

    def __init__(self, max_size: int = 4096, default_ttl_seconds: int = 300) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.backend_name = "InMemory_LRU_TTL"
        self._redis_client: Any = None

        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                import redis  # type: ignore

                client = redis.from_url(
                    redis_url, socket_connect_timeout=0.3, socket_timeout=0.3
                )
                client.ping()
                self._redis_client = client
                self.backend_name = "Redis_With_InMemory_L1"
            except Exception:
                self._redis_client = None
                self.backend_name = "InMemory_LRU_TTL (Redis_Fallback)"

    def get(self, key: str) -> Any | None:
        now = time.perf_counter()
        with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                expires_at, val = entry
                if now <= expires_at:
                    self._store.move_to_end(key)
                    self.hits += 1
                    return val
                del self._store[key]

        if self._redis_client is not None:
            try:
                raw = self._redis_client.get(key)
                if raw is not None:
                    val = json.loads(raw)
                    with self._lock:
                        self._store[key] = (now + self.default_ttl, val)
                        self.hits += 1
                    return val
            except Exception:
                pass

        with self._lock:
            self.misses += 1
        return None

    def clear(self) -> None:
        """Drop all in-process entries (Redis entries expire by TTL). Used by tests and after data refreshes."""
        with self._lock:
            self._store.clear()

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.perf_counter() + ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (expires_at, value)
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)

        if self._redis_client is not None:
            try:
                self._redis_client.setex(key, ttl, json.dumps(value))
            except Exception:
                pass

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100.0) if total > 0 else 0.0
        return {
            "backend": self.backend_name,
            "entries": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(hit_rate, 2),
        }


SLA_ROUTE_PREFIXES = ("/recommendations", "/recommend")  # routes held to the brief's < 100 ms target


class LatencyTelemetry:
    """Thread-safe latency tracker computing p50, p95, p99, and mean latency per route."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples: dict[str, list[float]] = {}

    def record(self, route: str, latency_ms: float) -> None:
        with self._lock:
            bucket = self._samples.setdefault(route, [])
            bucket.append(latency_ms)
            if len(bucket) > 2000:
                del bucket[:500]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            per_route: dict[str, Any] = {}
            all_vals: list[float] = []
            for route, vals in self._samples.items():
                if not vals:
                    continue
                arr = np.asarray(vals, dtype=np.float64)
                all_vals.extend(vals)
                per_route[route] = {
                    "requests": int(len(arr)),
                    "mean_ms": round(float(np.mean(arr)), 2),
                    "p50_ms": round(float(np.percentile(arr, 50)), 2),
                    "p95_ms": round(float(np.percentile(arr, 95)), 2),
                    "p99_ms": round(float(np.percentile(arr, 99)), 2),
                }
            # The brief's latency target (< 100 ms) is for RECOMMENDATIONS; search (neural embeddings + cross-encoder)
            # and the assistant are slower by design and are reported per route, not held to that target.
            rec_vals = [v for r, vals in self._samples.items() if r.startswith(SLA_ROUTE_PREFIXES) for v in vals]
            rec_p95 = round(float(np.percentile(rec_vals, 95)), 2) if rec_vals else None
            if all_vals:
                arr_all = np.asarray(all_vals, dtype=np.float64)
                overall = {
                    "total_requests": int(len(arr_all)),
                    "mean_ms": round(float(np.mean(arr_all)), 2),
                    "p50_ms": round(float(np.percentile(arr_all, 50)), 2),
                    "p95_ms": round(float(np.percentile(arr_all, 95)), 2),
                    "p99_ms": round(float(np.percentile(arr_all, 99)), 2),
                }
            else:
                overall = {"total_requests": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
            overall["sla_scope"] = "recommendation routes, p95 < 100 ms"
            overall["recommendation_p95_ms"] = rec_p95
            overall["sla_p95_under_100ms_met"] = None if rec_p95 is None else bool(rec_p95 < 100.0)
            return {"overall": overall, "routes": per_route}


def _normalize_sku(product_id: str | int) -> str:
    if isinstance(product_id, int) or (isinstance(product_id, str) and product_id.isdigit()):
        return f"SK-{int(product_id):05d}"
    s = str(product_id).strip().upper()
    return s


class ShopKaroServingContainer:
    """
    Pre-loads indices and DuckDB lookup tables into memory once so that all
    serving endpoints respond in <50ms uncached and <2ms cached.
    """

    def __init__(self) -> None:
        self.cache = HybridTTLCache(max_size=4096, default_ttl_seconds=300)
        self.telemetry = LatencyTelemetry()
        self._initialized = False
        self._init_lock = threading.Lock()

        # Loaded components
        self.tables_available: list[str] = []
        self.search_engine: HybridSearchEngine | None = None
        self.personalizer: PersonalizedSearchReRanker | None = None
        self.tool_registry: ShopKaroToolRegistry | None = None
        self.assistant: UrduLishShoppingAssistant | LLMShoppingAssistant | None = None

        # Pre-indexed fast dictionaries for <5ms serving
        self.catalogue_by_sku: dict[str, dict[str, Any]] = {}
        self.user_segment_map: dict[str, dict[str, Any]] = {}
        self.forecast_map: dict[str, list[dict[str, Any]]] = {}
        self.inventory_alert_map: dict[str, dict[str, Any]] = {}
        self.review_summary_map: dict[str, dict[str, Any]] = {}
        self.recent_reviews_map: dict[str, list[dict[str, Any]]] = {}

        # Similar-products & frequently-bought-together components
        self.item_embeddings: np.ndarray | None = None
        self.sku_to_item_idx: dict[str, int] = {}
        self.item_idx_to_sku: dict[int, str] = {}
        self.fbt_engine: AssociationRulesEngine | None = None

        # Real-time item-CF recommender (Day 2 model, served with live session clicks)
        self.session_events = SessionEventStore()
        self.realtime_recommender: RealtimeItemCFRecommender | None = None
        self.business_reranker: BusinessReRanker | None = None
        self.recommender_info: dict[str, Any] = {}

    def ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return

            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            self.tables_available = [r[0] for r in con.execute("SHOW TABLES").fetchall()]

            # 1. Initialize Hybrid Search Engine, Personalizer & UrduLish Shopping Assistant
            self.search_engine = HybridSearchEngine(rrf_k=60).fit_from_duckdb(con)
            self.personalizer = PersonalizedSearchReRanker(
                search_engine=self.search_engine,
                personalization_weight=0.38,
            ).fit_user_profiles_from_duckdb(con, max_users=3000)

            # 2. Load Catalogue lookup maps
            cat_df = con.execute(
                """
                SELECT
                    p.product_id,
                    p.title,
                    p.category,
                    p.sub_category,
                    p.brand,
                    p.color,
                    p.occasion,
                    p.price_pkr,
                    p.price_band,
                    p.discount_pct,
                    p.on_sale,
                    p.margin_pct,
                    p.stock_qty,
                    r.avg_rating AS avg_rating,  -- NULL when the product has no reviews (never invent one)
                    COALESCE(r.genuine_review_count, 0) AS review_count
                FROM product_catalogue p
                LEFT JOIN review_intelligence_summary r
                  ON p.product_id = r.product_id
                """
            ).df()

            for rec in cat_df.to_dict("records"):
                sku = str(rec["product_id"])
                self.catalogue_by_sku[sku] = rec

            # Load customer segments
            seg_df = con.execute(
                """
                SELECT
                    CAST(user_id AS VARCHAR) AS user_id,
                    segment_name,
                    monetary_intent_pkr,
                    frequency_sessions
                FROM customer_segments
                """
            ).df()
            for rec in seg_df.to_dict("records"):
                self.user_segment_map[str(rec["user_id"])] = rec

            # Load Day 3 30-day probabilistic forecasts & inventory alerts
            if "sku_forecasts_30d" in self.tables_available:
                fc_df = con.execute("SELECT * FROM sku_forecasts_30d ORDER BY forecast_date").df()
                for pid, grp in fc_df.groupby("product_id"):
                    sku_key = _normalize_sku(pid)
                    rows = []
                    for r in grp.to_dict("records"):
                        r["forecast_date"] = str(r["forecast_date"])[:10]
                        rows.append(r)
                    self.forecast_map[sku_key] = rows

            if "inventory_alerts" in self.tables_available:
                al_df = con.execute("SELECT * FROM inventory_alerts").df()
                for rec in al_df.to_dict("records"):
                    sku_key = _normalize_sku(rec["product_id"])
                    self.inventory_alert_map[sku_key] = rec

            # Load Day 4 review intelligence summaries
            if "review_intelligence_summary" in self.tables_available:
                rev_sum_df = con.execute("SELECT * FROM review_intelligence_summary").df()
                for rec in rev_sum_df.to_dict("records"):
                    sku_key = _normalize_sku(rec["product_id"])
                    self.review_summary_map[sku_key] = rec

            rev_raw_df = con.execute(
                """
                SELECT
                    product_id, review_id, language, rating, sentiment_label,
                    review_title, review_text, delivery_delay_days
                FROM reviews
                WHERE is_fake_spam = FALSE
                ORDER BY review_date DESC
                """
            ).df()
            for pid, grp in rev_raw_df.groupby("product_id"):
                self.recent_reviews_map[_normalize_sku(pid)] = grp.head(5).to_dict("records")

            # Item text embeddings (Day 1 Task 5, L2-normalised) for GET /similar
            emb_path = settings.models_dir / "item_text_embeddings.npy"
            if emb_path.exists():
                self.item_embeddings = np.load(emb_path)
                for idx, pid in con.execute("SELECT item_idx, product_id FROM item_id_map").fetchall():
                    if 0 <= int(idx) < len(self.item_embeddings):
                        self.sku_to_item_idx[str(pid)] = int(idx)
                        self.item_idx_to_sku[int(idx)] = str(pid)

            # Session co-occurrence association rules (Day 2 Task 5) for GET /bought-together
            self.fbt_engine = AssociationRulesEngine(
                min_pair_count=3, min_confidence=0.05
            ).fit_from_duckdb(con)

            con.close()

            self.tool_registry = ShopKaroToolRegistry(
                db_path=settings.duckdb_path,
                search_engine=self.search_engine,
                personalizer=self.personalizer,
            )
            self.assistant = build_shopping_assistant(self.tool_registry)

            # Recommender: batch artifact from scripts/precompute_recommendations.py (or train now)
            rec_con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            try:
                artifact, load_mode = load_or_train(rec_con)
            finally:
                rec_con.close()
            self.realtime_recommender = RealtimeItemCFRecommender(artifact.model, self.session_events)
            self.personalizer.cf_recommender = self.realtime_recommender  # collaborative search re-ranking
            self.business_reranker = BusinessReRanker(
                base_recommender=self.realtime_recommender,
                catalogue_df=cat_df,
                user_purchased=artifact.model.user_seen_items,
            )
            self.recommender_info = {**artifact.info(), "load_mode": load_mode}
            self._initialized = True

    def recommend_for_user(
        self,
        user_id: str | int,
        top_k: int = 10,
        occasion: str | None = None,
    ) -> dict[str, Any]:
        """
        Personalised recommendations:
        1. Candidates: item-CF scores from the user's history + live session clicks
           (cold start: popularity, restricted to onboarding categories if the user gave any).
        2. BusinessReRanker: drop out-of-stock & already-bought items, max 2 per brand,
           margin / sale / festival boosts.
        3. Per-item explanation stating the real reason (revisit / similar to X / popular).
        """
        self.ensure_initialized()
        assert self.realtime_recommender is not None and self.business_reranker is not None
        rt = self.realtime_recommender
        uid = str(user_id)

        # "Eid", "Shaadi / Wedding", "11.11 Sale", "Ramadan Preparation" -> festival key; else no boost
        festival = next((f for f in FESTIVAL_BOOST_MAP if occasion and f.lower() in occasion.lower()), None)
        is_cold_start = not rt.is_known(uid)
        onboarding = self.session_events.preferences(uid) if is_cold_start else []
        u_vec = rt.user_vector(uid)

        recs, rerank_stats = self.business_reranker.rerank_for_user(
            user_id=uid,
            k=top_k,
            candidate_pool_size=max(80, top_k * 8),
            active_festival=festival,
        )
        reasons = rt.explain_many(uid, [r["product_id"] for r in recs])

        recommendations: list[dict[str, Any]] = []
        for r in recs:
            item = self.catalogue_by_sku.get(r["product_id"], {})
            reason = reasons[r["product_id"]]
            exp_ru, exp_en = explanation_text(reason, {**item, **r}, self.catalogue_by_sku)
            if festival and str(r.get("category")) in FESTIVAL_BOOST_MAP[festival]:
                exp_ru += f" ({festival} special)"
                exp_en += f" ({festival} pick)"
            recommendations.append(
                {
                    "rank": r["rank"],
                    "product_id": r["product_id"],
                    "title": r["title"],
                    "brand": r["brand"],
                    "category": r["category"],
                    "price_pkr": float(r["price_pkr"]),
                    "on_sale": bool(r["on_sale"]),
                    "discount_pct": float(r["discount_pct"]),
                    "stock_qty": int(item.get("stock_qty", 0)),
                    "avg_rating": _rating_or_none(item.get("avg_rating")),
                    "review_count": int(item.get("review_count", 0) or 0),
                    "model_score": float(r["raw_ml_score"]),
                    "rerank_score": float(r["reranked_score"]),
                    "reason_type": reason["reason_type"],
                    "because_of_product_id": reason["because_of"],
                    "explanation_roman_urdu": exp_ru,
                    "explanation_en": exp_en,
                }
            )

        if not is_cold_start:
            strategy = "item_cf_realtime+business_reranker"
        elif onboarding:
            strategy = "cold_start_onboarding_popularity+business_reranker"
        else:
            strategy = "cold_start_popularity+business_reranker"
        seg = self.user_segment_map.get(uid)
        return {
            "user_id": user_id,
            "segment_name": str(seg["segment_name"]) if seg is not None else ("New visitor" if is_cold_start else "Unsegmented"),
            "is_cold_start": is_cold_start,
            "favorite_category": rt.favourite_category(u_vec) or (onboarding[0] if onboarding else "All_Categories"),
            "ranking_strategy": strategy,
            "history_items": rt.history_size(uid),
            "session_events": len(self.session_events.events(uid)),
            "onboarding_categories": onboarding,
            "business_rules_applied": {
                "in_stock_only": True,
                "exclude_already_purchased": True,
                "max_per_brand": self.business_reranker.max_per_brand,
                "festival_boost": festival or "None",
                **rerank_stats,
            },
            "model": self.recommender_info,
            "count": len(recommendations),
            "recommendations": recommendations,
        }

    def _product_card(self, sku: str) -> dict[str, Any]:
        item = self.catalogue_by_sku[sku]
        return {
            "product_id": sku,
            "title": str(item["title"]),
            "brand": str(item["brand"]),
            "category": str(item["category"]),
            "price_pkr": float(item["price_pkr"]),
            "stock_qty": int(item["stock_qty"]),
            "avg_rating": _rating_or_none(item.get("avg_rating")),
            "review_count": int(item.get("review_count", 0) or 0),
        }

    def similar_items(self, sku: str, top_k: int = 10, in_stock_only: bool = True) -> list[dict[str, Any]]:
        """Content-based neighbours: cosine similarity over L2-normalised item text embeddings."""
        self.ensure_initialized()
        idx = self.sku_to_item_idx.get(sku)
        if self.item_embeddings is None or idx is None:
            return []
        scores = self.item_embeddings @ self.item_embeddings[idx]
        scores[idx] = -np.inf
        # Over-fetch so stock filtering and title de-duplication still leave top_k results
        n_fetch = min(top_k * 20, len(scores) - 1)
        candidate_idx = np.argpartition(-scores, n_fetch)[:n_fetch]
        candidate_idx = candidate_idx[np.argsort(-scores[candidate_idx])]
        results: list[dict[str, Any]] = []
        # Catalogue reuses titles across SKUs; show each title once so the list is actually diverse
        seen_titles: set[str] = {str(self.catalogue_by_sku.get(sku, {}).get("title", ""))}
        for ci in candidate_idx:
            cand_sku = self.item_idx_to_sku.get(int(ci))
            if cand_sku is None or cand_sku not in self.catalogue_by_sku:
                continue
            card = self._product_card(cand_sku)
            if in_stock_only and card["stock_qty"] <= 0:
                continue
            if card["title"] in seen_titles:
                continue
            seen_titles.add(card["title"])
            card["similarity"] = round(float(scores[ci]), 4)
            results.append(card)
            if len(results) >= top_k:
                break
        return results

    def bought_together(self, sku: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Frequently-bought-together items. Only mined session rules carry real support/confidence/lift."""
        self.ensure_initialized()
        assert self.fbt_engine is not None
        rows = self.fbt_engine.get_frequently_bought_together(sku, k=top_k)
        out: list[dict[str, Any]] = []
        for r in rows:
            rec = asdict(r) if not isinstance(r, dict) else dict(r)
            is_mined = rec.get("rule_source") == "Session_Basket_FP_Growth"
            out.append(
                {
                    "product_id": rec["consequent_id"],
                    "title": rec["consequent_title"],
                    "brand": rec["consequent_brand"],
                    "category": rec["consequent_category"],
                    "price_pkr": float(rec["consequent_price_pkr"]),
                    "rule_source": rec["rule_source"],
                    "mined_from_data": is_mined,
                    # Curated/complement rules have no measured statistics -> report None, not invented values
                    "support": float(rec["support"]) if is_mined else None,
                    "confidence": float(rec["confidence"]) if is_mined else None,
                    "lift": float(rec["lift"]) if is_mined else None,
                    "explanation_roman_urdu": rec["explanation_roman_urdu"],
                }
            )
        return out


serving_container = ShopKaroServingContainer()

app = FastAPI(
    title="ShopKaro — AI Commerce Intelligence API",
    description=(
        "Real-Time FastAPI Serving for Recommendations, Hybrid UrduLish Search, "
        "Probabilistic Demand Forecasting, Conversational Shopping Assistant, and Review Intelligence."
    ),
    version="1.0.0",
)


class ChatRequest(BaseModel):
    """Request schema for POST /chat."""

    message: str = Field(..., min_length=1, description="Customer query in Roman Urdu, Urdu, or English.")
    session_id: str = Field(default="default-session", description="Multi-turn conversation session ID.")
    user_id: int | str | None = Field(default=15442, description="Optional customer user_id for personalization.")


@app.middleware("http")
async def latency_tracking_middleware(request: Request, call_next: Any) -> Any:
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    # Group latency by route template (e.g. "/similar/{product_id}"), not by raw URL
    matched_route = request.scope.get("route")
    route_key = getattr(matched_route, "path", request.url.path)
    serving_container.telemetry.record(route_key, elapsed_ms)
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Liveness and readiness check returning loaded DuckDB tables and cache status."""
    serving_container.ensure_initialized()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "duckdb_connected": settings.duckdb_path.exists(),
        "assistant_engine": (
            f"llm ({settings.llm_model})"
            if isinstance(serving_container.assistant, LLMShoppingAssistant)
            else "rules"
        ),
        "tables_count": len(serving_container.tables_available),
        "cache": serving_container.cache.stats(),
    }


@app.get("/metrics")
def metrics_endpoint() -> dict[str, Any]:
    """Operational telemetry endpoint reporting p50/p95/p99 latencies and cache hit rates."""
    serving_container.ensure_initialized()
    return {
        "service": settings.app_name,
        "cache": serving_container.cache.stats(),
        "latency": serving_container.telemetry.summary(),
    }


@app.get("/recommendations/{user_id}")
@app.get("/recommend/{user_id}", include_in_schema=False)
def get_recommendations_endpoint(
    user_id: str,
    top_k: int = Query(default=10, ge=1, le=50),
    occasion: str | None = Query(default=None),
) -> dict[str, Any]:
    """
    Personalised recommendations (item-CF on history + live session clicks, then business re-ranking).
    Cached per user; the key includes the user's event version, so a new click via POST /events
    makes the next request recompute instead of serving a stale cached list.
    """
    serving_container.ensure_initialized()
    version = serving_container.session_events.version(str(user_id))
    cache_key = f"rec:{user_id}:{top_k}:{(occasion or 'none').lower()}:v{version}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    payload = serving_container.recommend_for_user(
        user_id=user_id, top_k=top_k, occasion=occasion
    )
    serving_container.cache.set(cache_key, payload, ttl_seconds=300)
    return {**payload, "cache_hit": False}


class EventRequest(BaseModel):
    """A live shopper event, e.g. sent by the storefront on every product view."""

    user_id: str = Field(..., min_length=1, description="Known user ID (USR-...) or a new visitor ID.")
    product_id: str = Field(..., min_length=1, description="Product ID like SK-00010.")
    event_type: str = Field(default="view", description="view | addtocart | transaction")


class OnboardingRequest(BaseModel):
    """Cold-start onboarding answers: which categories the new shopper is interested in."""

    categories: list[str] = Field(..., min_length=1, max_length=5)


@app.post("/events")
def record_event_endpoint(req: EventRequest) -> dict[str, Any]:
    """Record a live click. The user's next /recommendations call reflects it immediately."""
    serving_container.ensure_initialized()
    sku = _require_known_sku(req.product_id)
    try:
        version = serving_container.session_events.add(req.user_id, sku, req.event_type.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "user_id": req.user_id,
        "product_id": sku,
        "event_type": req.event_type.lower(),
        "session_events": len(serving_container.session_events.events(req.user_id)),
        "version": version,
    }


@app.post("/onboarding/{user_id}")
def onboarding_endpoint(user_id: str, req: OnboardingRequest) -> dict[str, Any]:
    """Store a new visitor's category interests; used until they have their own clicks."""
    serving_container.ensure_initialized()
    rt = serving_container.realtime_recommender
    assert rt is not None
    valid = set(rt.cf.cat_to_cols)
    unknown = [c for c in req.categories if c not in valid]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown categories {unknown}. Valid: {sorted(valid)}",
        )
    version = serving_container.session_events.set_preferences(user_id, req.categories)
    return {"user_id": user_id, "onboarding_categories": req.categories, "version": version}


def _require_known_sku(product_id: str) -> str:
    sku_key = _normalize_sku(product_id)
    if sku_key not in serving_container.catalogue_by_sku:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_id}' (normalized '{sku_key}') not found.",
        )
    return sku_key


@app.get("/similar/{product_id}")
def get_similar_products_endpoint(
    product_id: str,
    top_k: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """'Similar products': cosine similarity over item title+description embeddings (works for new items too)."""
    serving_container.ensure_initialized()
    sku_key = _require_known_sku(product_id)
    cache_key = f"similar:{sku_key}:{top_k}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    payload = {
        "product_id": sku_key,
        "source": serving_container._product_card(sku_key),
        "method": "content_cosine_item_text_embeddings",
        "results": serving_container.similar_items(sku_key, top_k=top_k),
    }
    payload["count"] = len(payload["results"])
    serving_container.cache.set(cache_key, payload, ttl_seconds=3600)
    return {**payload, "cache_hit": False}


@app.get("/bought-together/{product_id}")
def get_bought_together_endpoint(
    product_id: str,
    top_k: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """'Frequently bought together': session co-occurrence association rules + complement fallbacks."""
    serving_container.ensure_initialized()
    sku_key = _require_known_sku(product_id)
    cache_key = f"fbt:{sku_key}:{top_k}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    results = serving_container.bought_together(sku_key, top_k=top_k)
    payload = {
        "product_id": sku_key,
        "source": serving_container._product_card(sku_key),
        "count": len(results),
        "results": results,
    }
    serving_container.cache.set(cache_key, payload, ttl_seconds=3600)
    return {**payload, "cache_hit": False}


def _with_review_stats(item: dict[str, Any]) -> dict[str, Any]:
    """Attach the real average rating / review count (None / 0 when the product has no reviews)."""
    cat = serving_container.catalogue_by_sku.get(str(item.get("product_id")), {})
    return {
        **item,
        "avg_rating": _rating_or_none(cat.get("avg_rating")),
        "review_count": int(cat.get("review_count", 0) or 0),
    }


@app.get("/search")
def search_products_endpoint(
    q: str = Query(..., min_length=1, description="Search query in Roman Urdu, English, or Urdu"),
    top_k: int = Query(default=10, ge=1, le=50),
    user_id: int | str | None = Query(default=None),
) -> dict[str, Any]:
    """Hybrid search (BM25 + TF-IDF/SVD + RRF + feature re-ranker); with a known user_id, collaborative re-ranking."""
    serving_container.ensure_initialized()
    # Include the user's live-event version: personalised results change as the session's clicks change.
    events_v = serving_container.session_events.version(str(user_id)) if user_id is not None else 0
    cache_key = f"search:{q.strip().lower()}:{top_k}:{user_id or 'anon'}:{events_v}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    assert serving_container.search_engine is not None
    assert serving_container.personalizer is not None

    pers = serving_container.personalizer
    uid_key = str(user_id) if user_id is not None else ""
    rt = pers.cf_recommender
    if rt is not None and uid_key and not uid_key.startswith("PERSONA_") and rt.is_known(uid_key):
        method = "item_cf_rerank"
    elif uid_key in pers.user_profiles:
        method = "persona_profile"
    else:
        method = None  # unknown user: plain hybrid search (previously silently treated as a "Luxury VIP")

    if method is not None:
        results, parsed = pers.search_personalized(query=q, user_id=uid_key, k=top_k)
        results = [_with_review_stats(r) for r in results]
        payload = {
            "query": q,
            "personalized": True,
            "personalization_method": method,
            "user_id": user_id,
            "persona_used": uid_key,
            "parsed_constraints": {
                "max_price_pkr": parsed.max_price_pkr,
                "min_price_pkr": parsed.min_price_pkr,
                "detected_category": parsed.category_hint,
                "detected_color": parsed.color_hint,
                "detected_occasion": parsed.occasion_hint,
                "detected_brand": parsed.brand_hint,
            },
            "count": len(results),
            "results": results,
        }
    else:
        results, parsed = serving_container.search_engine.search_hybrid(
            query=q, k=top_k, only_in_stock=True
        )
        results = [_with_review_stats(r) for r in results]
        payload = {
            "query": q,
            "personalized": False,
            "personalization_method": None,
            "user_id": user_id,
            "parsed_constraints": {
                "max_price_pkr": parsed.max_price_pkr,
                "min_price_pkr": parsed.min_price_pkr,
                "detected_category": parsed.category_hint,
                "detected_color": parsed.color_hint,
                "detected_occasion": parsed.occasion_hint,
                "detected_brand": parsed.brand_hint,
            },
            "count": len(results),
            "results": results,
        }

    serving_container.cache.set(cache_key, payload, ttl_seconds=300)
    return {**payload, "cache_hit": False}


@app.get("/forecast/{product_id}")
def get_forecast_endpoint(product_id: str) -> dict[str, Any]:
    """Return 30-day probabilistic P10/P50/P90 demand forecast and inventory alert scorecard."""
    serving_container.ensure_initialized()
    sku_key = _normalize_sku(product_id)
    cache_key = f"forecast:{sku_key}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    alert_info = serving_container.inventory_alert_map.get(sku_key)
    daily_forecasts = serving_container.forecast_map.get(sku_key, [])

    if alert_info is None and not daily_forecasts:
        cat_item = serving_container.catalogue_by_sku.get(sku_key)
        if cat_item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_id}' (normalized '{sku_key}') not found.",
            )
        payload = {
            "product_id": sku_key,
            "title": cat_item["title"],
            "category": cat_item["category"],
            "brand": cat_item["brand"],
            "forecast_tier": "Long_Tail_Catalogue_SKU",
            "current_stock_units": int(cat_item["stock_qty"]),
            "forecast_30d_p10_units": 0.0,
            "forecast_30d_p50_units": 0.0,
            "forecast_30d_p90_units": 0.0,
            "safety_stock_units": 0.0,
            "reorder_point_units": 0.0,
            "days_of_inventory": 30.0,
            "alert_status": "HEALTHY_STOCK",
            "recommended_order_qty": 0,
            "recommended_action": "Standard Replenishment SLA",
            "horizon_days": 0,
            "daily_forecasts": [],
        }
    else:
        p10_sum = round(float(sum(float(r.get("p10_units", 0.0)) for r in daily_forecasts)), 1)
        p50_sum = (
            round(float(alert_info["forecast_30d_p50"]), 1)
            if alert_info and "forecast_30d_p50" in alert_info
            else round(float(sum(float(r.get("p50_units", 0.0)) for r in daily_forecasts)), 1)
        )
        p90_sum = (
            round(float(alert_info["forecast_30d_p90"]), 1)
            if alert_info and "forecast_30d_p90" in alert_info
            else round(float(sum(float(r.get("p90_units", 0.0)) for r in daily_forecasts)), 1)
        )
        payload = {
            "product_id": sku_key,
            "title": str(alert_info.get("title", sku_key)) if alert_info else sku_key,
            "category": str(alert_info.get("category", "Unknown")) if alert_info else "Unknown",
            "brand": str(alert_info.get("brand", "Unknown")) if alert_info else "Unknown",
            "current_stock_units": int(alert_info["current_stock_qty"]) if alert_info else 0,
            "forecast_30d_p10_units": p10_sum,
            "forecast_30d_p50_units": p50_sum,
            "forecast_30d_p90_units": p90_sum,
            "safety_stock_units": round(float(alert_info["safety_stock_units"]), 2) if alert_info else 0.0,
            "reorder_point_units": round(float(alert_info["reorder_point_units"]), 2) if alert_info else 0.0,
            "days_of_inventory": round(float(alert_info["days_of_inventory_p50"]), 2) if alert_info else 0.0,
            "alert_status": str(alert_info["alert_status"]) if alert_info else "HEALTHY_STOCK",
            "recommended_order_qty": int(alert_info["recommended_order_qty"]) if alert_info else 0,
            "recommended_action": str(alert_info["recommended_action"]) if alert_info else "Monitor",
            "horizon_days": len(daily_forecasts),
            "daily_forecasts": daily_forecasts,
        }

    serving_container.cache.set(cache_key, payload, ttl_seconds=300)
    return {**payload, "cache_hit": False}


INVENTORY_ALERT_STATUSES = (
    "CRITICAL_STOCKOUT_RISK",
    "FESTIVAL_SURGE_WATCH",
    "OVERSTOCK_DEAD_CAPITAL",
    "HEALTHY_STOCK",
)


@app.get("/inventory/alerts")
def get_inventory_alerts_endpoint(
    status: str | None = Query(
        default=None,
        description=f"Filter by alert status: {', '.join(INVENTORY_ALERT_STATUSES)}",
    ),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """Stock-out risk, festival surge and overstock alerts, most urgent (fewest days of inventory) first."""
    serving_container.ensure_initialized()
    if status is not None and status.upper() not in INVENTORY_ALERT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown status '{status}'. Use one of: {', '.join(INVENTORY_ALERT_STATUSES)}",
        )
    alerts = list(serving_container.inventory_alert_map.values())
    counts: dict[str, int] = {}
    for a in alerts:
        counts[str(a["alert_status"])] = counts.get(str(a["alert_status"]), 0) + 1
    if status is not None:
        alerts = [a for a in alerts if str(a["alert_status"]) == status.upper()]
    alerts.sort(key=lambda a: float(a.get("days_of_inventory_p50", 0.0)))

    keep = (
        "product_id", "title", "category", "brand", "current_stock_qty", "lead_time_days",
        "forecast_14d_p50", "forecast_30d_p50", "forecast_30d_p90", "safety_stock_units",
        "reorder_point_units", "days_of_inventory_p50", "recommended_order_qty",
        "alert_status", "recommended_action",
    )
    rows = [
        {k: (v.item() if isinstance(v, np.generic) else v) for k, v in a.items() if k in keep}
        for a in alerts[:limit]
    ]
    return {
        "status_filter": status.upper() if status else None,
        "counts_by_status": counts,
        "total_tracked_skus": len(serving_container.inventory_alert_map),
        "count": len(rows),
        "alerts": rows,
    }


@app.post("/assistant/chat")
@app.post("/chat", include_in_schema=False)
def chat_assistant_endpoint(req: ChatRequest) -> dict[str, Any]:
    """Multi-turn UrduLish Shopping Assistant with 6 grounded tools & zero-hallucination verification."""
    serving_container.ensure_initialized()
    assert serving_container.assistant is not None

    uid_str = str(req.user_id) if req.user_id is not None else "PERSONA_LUXURY_VIP"
    turn_out = serving_container.assistant.chat(
        session_id=req.session_id,
        user_message=req.message,
        user_id=uid_str,
    )
    session_state = serving_container.assistant.get_or_create_session(
        session_id=req.session_id, user_id=uid_str
    )

    return {
        "session_id": req.session_id,
        "user_id": req.user_id,
        "user_message": req.message,
        "engine": turn_out.engine,
        "fallback_reason": turn_out.fallback_reason,
        "detected_intent": turn_out.detected_intent,
        "assistant_response": turn_out.assistant_reply_urdulish,
        "tool_calls": turn_out.invoked_tools,
        "tool_outputs": turn_out.tool_outputs,
        "cart": {
            "item_count": turn_out.cart_item_count,
            "total_pkr": turn_out.cart_total_pkr,
            "items": session_state.cart,
        },
        "hallucination_audit": asdict(turn_out.hallucination_audit),
    }


@app.get("/reviews/summary/{product_id}")
@app.get("/reviews/{product_id}", include_in_schema=False)
def get_product_reviews_endpoint(product_id: str) -> dict[str, Any]:
    """Return Multilingual Review Intelligence, 6-Aspect ABSA net scores, and courier diagnostics."""
    serving_container.ensure_initialized()
    sku_key = _normalize_sku(product_id)
    cache_key = f"reviews:{sku_key}"
    cached = serving_container.cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    rev_sum = serving_container.review_summary_map.get(sku_key)
    if rev_sum is None:
        cat_item = serving_container.catalogue_by_sku.get(sku_key)
        if cat_item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_id}' (normalized '{sku_key}') not found.",
            )
        payload = {
            "product_id": sku_key,
            "title": cat_item["title"],
            "brand": cat_item["brand"],
            "category": cat_item["category"],
            "genuine_review_count": 0,
            "spam_filtered_count": 0,
            "avg_rating": None,
            "status": "no_detailed_reviews_yet",
            "aspect_scores": {
                "quality": 0.0,
                "price": 0.0,
                "delivery": 0.0,
                "size_fit": 0.0,
                "packaging": 0.0,
                "seller": 0.0,
            },
            "is_unfairly_penalized_by_courier": False,
            "recommended_action": "Collect Initial Customer Reviews",
            "what_customers_say": "Abhi tak is product ke reviews nahi aaye.",
            "recent_reviews": [],
        }
    else:
        payload = {
            "product_id": sku_key,
            "title": str(rev_sum.get("title", sku_key)),
            "brand": str(rev_sum.get("brand", "Unknown")),
            "category": str(rev_sum.get("category", "Unknown")),
            "genuine_review_count": int(rev_sum["genuine_review_count"]),
            "spam_filtered_count": int(rev_sum["spam_filtered_count"]),
            "avg_rating": float(rev_sum["avg_rating"]),
            "positive_sentiment_pct": float(rev_sum["positive_sentiment_pct"]),
            "negative_sentiment_pct": float(rev_sum["negative_sentiment_pct"]),
            "avg_delivery_delay_days": float(rev_sum["avg_delivery_delay_days"]),
            "aspect_scores": {
                "quality": float(rev_sum["quality_net_score"]),
                "price": float(rev_sum["price_net_score"]),
                "delivery": float(rev_sum["delivery_net_score"]),
                "size_fit": float(rev_sum["size_fit_net_score"]),
                "packaging": float(rev_sum["packaging_net_score"]),
                "seller": float(rev_sum["seller_net_score"]),
            },
            "quality_positive_pct": float(rev_sum["quality_pos_pct"]),
            "delivery_negative_pct": float(rev_sum["delivery_neg_pct"]),
            "is_unfairly_penalized_by_courier": bool(rev_sum["is_unfairly_penalized_by_courier"]),
            "recommended_action": str(rev_sum["recommended_action"]),
            "what_customers_say": str(rev_sum.get("what_customers_say") or ""),
            "recent_reviews": serving_container.recent_reviews_map.get(sku_key, []),
        }

    serving_container.cache.set(cache_key, payload, ttl_seconds=300)
    return {**payload, "cache_hit": False}
