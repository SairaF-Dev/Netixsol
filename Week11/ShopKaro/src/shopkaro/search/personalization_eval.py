"""
Does personalised search rank higher the products a shopper actually goes on to engage with?

RetailRocket has no search logs, so queries are built from future behaviour (a standard protocol for evaluating
personalised product search offline):
- users: those with a search profile (built only from `train_interactions`) and activity in the later test window;
- one query per (user, product type) the user engaged with in the test window, text = the product type
  (sub-category, e.g. "Embroidered Lawn Suit");
- relevant items: the products of that type the user engaged with in the test window, graded
  purchase 3 / add-to-cart 2 / view 1 (gain 2^g - 1);
- systems: plain hybrid search vs personalised re-ranking of the hybrid candidates, top 10.

Users are split 50/50 into dev and held-out halves by a hash of the user id, so any tuning can be checked on users it
never saw. Reported: NDCG@10, hit rate@10, the share of queries whose relevant items are even in the re-ranker's
candidate pool (re-ranking cannot help otherwise), and a paired bootstrap CI + sign test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from shopkaro.assistant.shopping_agent import PersonalizedSearchReRanker
from shopkaro.config.settings import settings
from shopkaro.search.benchmark import paired_comparison
from shopkaro.search.hybrid_search import HybridSearchEngine

GRADE = {"transaction": 3, "addtocart": 2, "view": 1}
K = 10


def _half(user_id: str) -> str:
    return "dev" if int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 2 == 0 else "holdout"


def build_queries(con: duckdb.DuckDBPyConnection, profiled_users: set[str]) -> pd.DataFrame:
    """One row per (user, sub_category) with the graded relevant products from the test window."""
    df = con.execute(
        """
        SELECT t.user_id, p.sub_category, t.product_id, t.event_type
        FROM test_interactions t
        JOIN product_catalogue p USING (product_id)
        WHERE p.in_stock
        """
    ).df()
    df = df[df["user_id"].astype(str).isin(profiled_users)]
    df["grade"] = df["event_type"].map(GRADE).fillna(1).astype(int)
    rel = df.groupby(["user_id", "sub_category", "product_id"], as_index=False)["grade"].max()
    queries = (
        rel.groupby(["user_id", "sub_category"])
        .apply(lambda g: dict(zip(g["product_id"], g["grade"])), include_groups=False)
        .rename("relevant")
        .reset_index()
    )
    queries["user_id"] = queries["user_id"].astype(str)
    queries["half"] = queries["user_id"].map(_half)
    return queries


def _ndcg(ranked: list[str], relevant: dict[str, int], k: int = K) -> float:
    gains = [2 ** relevant.get(pid, 0) - 1 for pid in ranked[:k]]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted((2 ** g - 1 for g in relevant.values()), reverse=True)[:k]
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def evaluate(
    personalizer: PersonalizedSearchReRanker,
    queries: pd.DataFrame,
    candidate_pool: int = 40,
) -> pd.DataFrame:
    """Per-query NDCG@10 / hit@10 for plain hybrid and personalised search."""
    engine = personalizer.search_engine
    rows = []
    for q in queries.itertuples(index=False):
        pool, _ = engine.search_hybrid(q.sub_category, k=candidate_pool, only_in_stock=True, cross_encode=False)
        pool_ids = [r["product_id"] for r in pool]
        pers, _ = personalizer.search_personalized(q.sub_category, user_id=q.user_id, k=K, candidate_pool=candidate_pool)
        in_pool = any(pid in q.relevant for pid in pool_ids)
        for system, ranked in (("hybrid", pool_ids[:K]), ("personalised", [r["product_id"] for r in pers])):
            rows.append(
                {
                    "query": f"{q.user_id}|{q.sub_category}",
                    "user_id": q.user_id,
                    "half": q.half,
                    "system": system,
                    "ndcg_at_10": _ndcg(ranked, q.relevant),
                    "hit_at_10": float(any(pid in q.relevant for pid in ranked[:K])),
                    "relevant_in_pool": float(in_pool),
                    "n_relevant": len(q.relevant),
                }
            )
    return pd.DataFrame(rows)


def train_eval_item_cf(con: duckdb.DuckDBPyConnection):
    """Item-CF trained on train_interactions only (the production artifact includes the test window)."""
    from shopkaro.recommendations.serving import train_serving_model

    return train_serving_model(con, table="train_interactions").model


def evaluate_cf_rerank(
    engine: HybridSearchEngine,
    cf,
    queries: pd.DataFrame,
    pools: tuple[int, ...] = (40, 100, 200),
    lams: tuple[float, ...] = (0.3, 0.5, 0.7, 0.9),
) -> pd.DataFrame:
    """
    Candidate re-ranking with collaborative evidence: hybrid top-P, then
    final = (1 - lam) * minmax(search score) + lam * minmax(item-CF score for this user).
    Returns per-query rows for every (P, lam) plus the hybrid baseline.
    """
    user_scores: dict[str, np.ndarray] = {}
    rows = []
    max_pool = max(pools)
    for q in queries.itertuples(index=False):
        if q.user_id not in user_scores:
            user_scores[q.user_id] = cf._score_user_vector(user_id=q.user_id, exclude_seen=False, only_in_stock=True)
        scores_u = user_scores[q.user_id]
        full, _ = engine.search_hybrid(q.sub_category, k=max_pool, only_in_stock=True, cross_encode=False)
        ids = [r["product_id"] for r in full]
        s_search = np.array([float(r["score"]) for r in full], dtype=float)
        s_cf = np.array([float(scores_u[cf.item_to_col[p]]) if p in cf.item_to_col else 0.0 for p in ids])
        base = {"query": f"{q.user_id}|{q.sub_category}", "user_id": q.user_id, "half": q.half}
        rows.append({**base, "system": "hybrid", "ndcg_at_10": _ndcg(ids[:K], q.relevant),
                     "hit_at_10": float(any(p in q.relevant for p in ids[:K]))})
        for pool in pools:
            ss, sc = s_search[:pool], s_cf[:pool]
            ns = (ss - ss.min()) / max(ss.max() - ss.min(), 1e-9)
            nc = (sc - sc.min()) / max(sc.max() - sc.min(), 1e-9)
            for lam in lams:
                order = np.argsort(-((1 - lam) * ns + lam * nc), kind="stable")[:K]
                ranked = [ids[i] for i in order]
                rows.append({**base, "system": f"cf_rerank_P{pool}_lam{lam}", "ndcg_at_10": _ndcg(ranked, q.relevant),
                             "hit_at_10": float(any(p in q.relevant for p in ranked))})
    return pd.DataFrame(rows)


def summarise(per_query: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for half, part in per_query.groupby("half"):
        sys_means = part.groupby("system")[["ndcg_at_10", "hit_at_10"]].mean().round(4).to_dict("index")
        out[half] = {
            "queries": int(part["query"].nunique()),
            "users": int(part["user_id"].nunique()),
            "relevant_item_in_candidate_pool_pct": round(
                100 * float(part[part["system"] == "hybrid"]["relevant_in_pool"].mean()), 2
            ),
            "by_system": sys_means,
            "personalised_vs_hybrid": paired_comparison(part, "hybrid", "personalised"),
        }
    return out


# Chosen on the DEV half only (grid P in {40, 100, 200} x lambda in {0.3, 0.5, 0.7, 0.9}); held-out users never used.
CF_POOL = 200
CF_LAMBDA = 0.9


def _discovery_only(queries: pd.DataFrame, cf) -> pd.DataFrame:
    """Keep only relevant products the user had NOT interacted with in training (no revisits)."""
    out = []
    for q in queries.itertuples(index=False):
        row = cf.user_to_row.get(q.user_id)
        seen = set() if row is None else {cf.col_to_item[int(c)] for c in cf.R_log_csr[row].indices}
        new = {p: g for p, g in q.relevant.items() if p not in seen}
        if new:
            out.append({"user_id": q.user_id, "sub_category": q.sub_category, "relevant": new, "half": q.half})
    return pd.DataFrame(out)


def run_personalization_eval(db_path: Path | None = None, max_users: int = 3000) -> dict[str, Any]:
    con = duckdb.connect(str(db_path or settings.duckdb_path), read_only=True)
    engine = HybridSearchEngine(rrf_k=60).fit_from_duckdb(con)
    personalizer = PersonalizedSearchReRanker(engine).fit_user_profiles_from_duckdb(con, max_users=max_users)
    profiled = {u for u in personalizer.user_profiles if not u.startswith("PERSONA_")}
    queries = build_queries(con, profiled)
    cf = train_eval_item_cf(con)
    con.close()

    # 1. Current production re-ranker (brand / category / price profile) vs plain hybrid
    per_query = evaluate(personalizer, queries)
    results: dict[str, Any] = {
        "profiled_users": len(profiled),
        "max_users": max_users,
        "profile_reranker": summarise(per_query),
    }

    # 2. Collaborative re-ranking with the dev-chosen config, all relevant items and discovery-only
    chosen = f"cf_rerank_P{CF_POOL}_lam{CF_LAMBDA}"
    cf_frames = []
    for label, qs in (("all", queries), ("discovery_only", _discovery_only(queries, cf))):
        pq = evaluate_cf_rerank(engine, cf, qs, pools=(CF_POOL,), lams=(CF_LAMBDA,))
        pq = pq[pq["system"].isin(["hybrid", chosen])].assign(relevance=label)
        pq["system"] = pq["system"].replace({chosen: "personalised"})
        pq["relevant_in_pool"] = np.nan
        cf_frames.append(pq)
        results[f"cf_rerank_{label}"] = {
            half: {
                "queries": int(part["query"].nunique()),
                "users": int(part["user_id"].nunique()),
                "by_system": part.groupby("system")[["ndcg_at_10", "hit_at_10"]].mean().round(4).to_dict("index"),
                "personalised_vs_hybrid": paired_comparison(part, "hybrid", "personalised"),
            }
            for half, part in pq.groupby("half")
        }
    results["cf_rerank_config"] = {"candidate_pool": CF_POOL, "lambda": CF_LAMBDA, "chosen_on": "dev half"}
    per_query = pd.concat([per_query.assign(relevance="all", method="profile_reranker")]
                          + [f.assign(method="cf_rerank") for f in cf_frames], ignore_index=True)

    out = settings.reports_dir
    per_query.to_csv(out / "day4_personalized_search_per_query.csv", index=False)
    (out / "day4_personalized_search_eval.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    print(json.dumps(run_personalization_eval(), indent=2))
