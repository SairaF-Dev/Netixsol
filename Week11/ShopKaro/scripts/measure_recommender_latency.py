"""
Latency of the two homepage recommenders as served (model compute only, then through the API with the business
re-ranker, uncached). Same users for both: 200 random warm users, the heaviest user, and new visitors.

Needs models/item_cf_serving.joblib and models/two_tower_serving.joblib
(python scripts/precompute_recommendations.py --two-tower). Writes reports/recommender_serving_latency.json.
"""

from __future__ import annotations

import dataclasses
import json
import statistics
import time

import numpy as np

import shopkaro.api.main as api
from shopkaro.config.settings import settings


def _p(xs: list[float], q: int) -> float:
    return round(float(np.percentile(xs, q)), 2)


def _summary(xs: list[float]) -> dict[str, float]:
    return {"n": len(xs), "p50_ms": _p(xs, 50), "p95_ms": _p(xs, 95), "max_ms": round(max(xs), 2),
            "mean_ms": round(statistics.mean(xs), 2)}


def main() -> None:
    results: dict[str, dict] = {}
    for name in ("item_cf", "two_tower"):
        api.settings = dataclasses.replace(settings, recommender=name)
        container = api.ShopKaroServingContainer()
        container.ensure_initialized()
        info = container.recommender_info
        assert info["serving_recommender"] == name, info
        rt = container.homepage_recommender
        users = sorted(rt.tt.user_to_row if name == "two_tower" else rt.cf.user_to_row)
        rng = np.random.default_rng(0)
        warm = [users[i] for i in rng.choice(len(users), 200, replace=False)]
        R = rt.tt.R_log_csr if name == "two_tower" else rt.cf.R_log_csr
        to_row = rt.tt.user_to_row if name == "two_tower" else rt.cf.user_to_row
        heavy = max(users[:200000], key=lambda u: R[to_row[u]].nnz)

        def timed(fn, uid: str) -> float:  # noqa: ANN001
            t0 = time.perf_counter()
            fn(uid)
            return (time.perf_counter() - t0) * 1000

        for u in warm[:10]:  # warm-up
            rt.recommend_ids(u, k=80)
        compute = [timed(lambda u: rt.recommend_ids(u, k=80, exclude_seen=False, only_in_stock=False), u) for u in warm]
        heavy_ms = [timed(lambda u: rt.recommend_ids(u, k=80), heavy) for _ in range(20)]
        new_ms = [timed(lambda u: rt.recommend_ids(u, k=80), f"new-visitor-{i}") for i in range(50)]
        full = [timed(lambda u: container.recommend_for_user(u, top_k=10), u) for u in warm]
        results[name] = {
            "model": info["model"],
            "model_compute_warm_users": _summary(compute),
            "model_compute_heaviest_user": {**_summary(heavy_ms), "history_items": int(R[to_row[heavy]].nnz)},
            "model_compute_new_visitor": _summary(new_ms),
            "full_recommendation_uncached": _summary(full),
        }
        print(name, json.dumps(results[name], indent=1), flush=True)

    out = settings.reports_dir / "recommender_serving_latency.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
