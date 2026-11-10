"""
Runner script for Day 5 — Tasks 1, 2 & 3:
1. Real-Time FastAPI Serving (<100ms SLA benchmark across all 6 endpoint families + TTL cache)
2. Statistical A/B Testing Framework (Power Analysis, Two-Proportion Z-Test, Welch's t-Test,
   Segment Subgroup Analysis, Guardrails & 1-Page Ship/No-Ship Decision Report)
3. 3-View Interactive Streamlit Dashboard Data Snapshot Verification
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from shopkaro.ab_testing.experiment import run_replay_ab_test
from shopkaro.api.main import app, serving_container
from shopkaro.dashboard.app import load_dashboard_snapshot


def _ascii_safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def main() -> None:
    print("=" * 84)
    print("SHOPKARO DAY 5: REAL-TIME FASTAPI SERVING, A/B TESTING & 3-VIEW DASHBOARD")
    print("=" * 84)

    # Warm up serving container once before measuring endpoint response latencies
    t_init0 = time.perf_counter()
    serving_container.ensure_initialized()
    init_sec = time.perf_counter() - t_init0
    print(f"\n[Startup] Serving container initialized in {init_sec:.2f}s")

    client = TestClient(app)

    # 1. Benchmark all FastAPI endpoints (Cold vs Warm Cached)
    endpoints_to_test = [
        ("GET", "/health", None, "/health"),
        ("GET", "/recommend/15442?top_k=5&occasion=Eid", None, "/recommend/{user_id}"),
        ("GET", "/search?q=shaadi+ke+liye+red+lehenga+20+hazaar+tak&top_k=5&user_id=15442", None, "/search"),
        ("GET", "/forecast/SK-00001", None, "/forecast/{product_id}"),
        ("POST", "/chat", {"message": "Ammi ke liye Eid gift chahiye, 3000 tak", "session_id": "bench-1", "user_id": 15442}, "/chat"),
        ("GET", "/reviews/SK-00045", None, "/reviews/{product_id}"),
    ]

    endpoint_latencies = []
    print("\n[Task 1] FastAPI Endpoint Latency & Cache Benchmark (<100 ms SLA):")
    for method, url, body, label in endpoints_to_test:
        t0 = time.perf_counter()
        if method == "GET":
            r_cold = client.get(url)
        else:
            r_cold = client.post(url, json=body)
        cold_ms = (time.perf_counter() - t0) * 1000.0
        assert r_cold.status_code == 200, f"Endpoint {url} failed with {r_cold.status_code}"

        t1 = time.perf_counter()
        if method == "GET":
            r_warm = client.get(url)
        else:
            r_warm = client.post(url, json=body)
        warm_ms = (time.perf_counter() - t1) * 1000.0
        assert r_warm.status_code == 200

        endpoint_latencies.append(
            {
                "endpoint": label,
                "cold_ms": round(cold_ms, 2),
                "cached_ms": round(warm_ms, 2),
            }
        )
        print(
            f"  - {label:<24} | Status={r_cold.status_code} | "
            f"Cold={cold_ms:6.2f} ms | Warm/Cached={warm_ms:6.2f} ms"
        )

    metrics_resp = client.get("/metrics").json()
    overall_lat = metrics_resp["latency"]["overall"]
    print(
        f"  Overall Telemetry: Mean={overall_lat['mean_ms']:.2f} ms | "
        f"p50={overall_lat['p50_ms']:.2f} ms | "
        f"p95={overall_lat['p95_ms']:.2f} ms | "
        f"SLA(<100ms)={overall_lat['sla_p95_under_100ms_met']} | "
        f"Cache Hit Rate={metrics_resp['cache']['hit_rate_pct']}%"
    )

    # 2. Task 2: A/B test of the recommender, replayed on real test-window behaviour
    print()
    print("[Task 2] A/B test (replay of real test-window behaviour):")
    ab = run_replay_ab_test(seed=42)
    res = ab["results"]
    summ = res["experiment_summary"]
    print(f"  Visitors: {summ['visitors']:,} ({summ['control_users']:,} control / {summ['treatment_users']:,} treatment)")
    for m in res["metrics"]:
        print(
            f"  * {m['metric']:<40}: control={m['control_mean']:.4g} {m['unit']} -> treatment={m['treatment_mean']:.4g} {m['unit']} "
            f"| lift {m['relative_lift_pct']:+.1f}% [{m['rel_ci_95_low_pct']:+.1f}%, {m['rel_ci_95_high_pct']:+.1f}%] "
            f"| p={m['p_value']:.3g} (Holm {m['p_value_holm']:.3g}) | {m['test_type']}"
        )
    print(f"  Guardrails all passed: {res['guardrails']['all_passed']}")
    print(f"  A/A check CTR p={ab['aa_results']['metrics'][1]['p_value']:.3f}")
    print(f"  Peeking false-positive rate: {ab['peeking']['false_positive_rate_fixed_horizon_pct']}% fixed vs "
          f"{ab['peeking']['false_positive_rate_daily_peeking_pct']}% daily peeking")
    print(f"  Decision: >>> {summ['decision']} <<<  ({summ['decision_reason']})")

    # 3. Task 3: 3-View Streamlit Dashboard Data Snapshot Verification
    print("\n[Task 3] 3-View Interactive Streamlit Dashboard Verification:")
    snap = load_dashboard_snapshot()
    print(
        f"  - Customer Segments Loaded: {len(snap['segments_summary'])} segments\n"
        f"  - Inventory Alerts Loaded : {len(snap['inventory_alerts'])} SKUs\n"
        f"  - Festivals Loaded        : {len(snap['festivals'])} events\n"
        f"  - Seller Scorecards Loaded: {len(snap['seller_scorecards'])} sellers\n"
        f"  - Unfairly Penalized Gems : {len(snap['unfairly_penalized_gems'])} SKUs\n"
        f"  - A/B Test Rows Loaded    : {len(snap['ab_test_results'])} metrics"
    )

    print("\nSaved Day 5 Artifacts:")
    print("  - reports/day5_ab_test_results.csv")
    print("  - reports/day5_ab_test_segment_subgroups.csv")
    print("  - reports/day5_ab_test_summary.json")
    print("  - reports/day5_ab_test_ship_decision_report.md")
    print("  - reports/figures/14_ab_testing_and_api_latency.png")
    print("=" * 84)


if __name__ == "__main__":
    main()

