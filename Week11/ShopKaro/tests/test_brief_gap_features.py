"""Tests for the brief items added late: MAPE, pre-festival plan, review summaries / trends / weekly report, SLA scope."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from shopkaro.forecasting.inventory import build_prefestival_plan
from shopkaro.forecasting.models import compute_forecast_metrics
from shopkaro.reviews.insights_report import (
    customer_summaries,
    falling_sentiment,
    template_report,
    unsupported_numbers,
)


def test_mape_ignores_zero_sale_days_and_reports_them() -> None:
    m = compute_forecast_metrics(np.array([0, 0, 10, 10]), np.array([1, 2, 12, 8]))
    assert m["mape_pct"] == pytest.approx(20.0)  # only the two days with sales count
    assert m["zero_actual_days_pct"] == 50.0
    assert m["wape_pct"] == pytest.approx(7 / 20 * 100, abs=1e-3)  # total error / total sales, zeros included


def _plan_inputs():
    dates = pd.date_range("2025-03-16", periods=30)
    fc = pd.DataFrame(
        [{"product_id": p, "forecast_date": d.strftime("%Y-%m-%d"), "p50_units": 10.0, "p90_units": 20.0} for p in ("A", "B") for d in dates]
    )
    alerts = pd.DataFrame(
        {
            "product_id": ["A", "B"], "title": ["a", "b"], "category": ["c", "c"],
            "current_stock_qty": [10_000, 50], "safety_stock_units": [30, 30], "lead_time_days": [3, 10],
            "unit_cost_pkr": [100.0, 100.0],
        }
    )
    fest = pd.DataFrame({"festival_name": ["Eid ul Fitr"], "start_date": ["2025-03-21"], "end_date": ["2025-04-03"], "boost_categories": ["c"], "demand_multiplier": [4.0]})
    hist = pd.DataFrame({"sale_date": pd.to_datetime(["2025-03-10"] * 2), "product_id": ["A", "B"], "units_sold": [5, 9]})
    return fc, alerts, fest, hist


def test_prefestival_plan_orders_p90_need_and_flags_late_orders() -> None:
    fc, alerts, fest, hist = _plan_inputs()
    plan = build_prefestival_plan(fc, alerts, fest, pd.Timestamp("2025-03-15"), hist).set_index("product_id")
    # 19 days (Mar 16 - Apr 3) x 20 units at P90 = 380, plus safety stock 30
    assert plan.loc["A", "order_qty_units"] == 0 and plan.loc["A", "status"] == "no order needed"
    assert plan.loc["B", "order_qty_units"] == 380 + 30 - 50
    assert plan.loc["B", "status"].startswith("LATE")  # 10-day lead time: order-by Mar 11 < plan date Mar 15
    assert list(plan["rank"]) == [1, 2]  # ranked by recent sales (B sold more)


def _reviews(rows):
    base = {"is_fake_spam": False, "brand": "X", "category": "C", "seller_id": "s1"}
    cols = ["aspect_quality", "aspect_price", "aspect_delivery", "aspect_size_fit", "aspect_packaging", "aspect_seller"]
    out = []
    for pid, date, sent, aspects in rows:
        r = {**base, "product_id": pid, "review_date": pd.Timestamp(date), "sentiment_label": sent}
        r.update({c: aspects.get(c.replace("aspect_", ""), 0) for c in cols})
        out.append(r)
    return pd.DataFrame(out)


def test_customer_summary_uses_real_shares() -> None:
    df = _reviews([("P", "2018-01-01", "Positive", {"quality": 1})] * 7 + [("P", "2018-01-02", "Neutral", {"quality": 1, "size_fit": -1})] * 3)
    text = customer_summaries(df)["P"]
    assert "100%" in text and "cheez ki quality" in text
    assert "30% ne kaha size theek nahi tha" in text and "(10 reviews)" in text


def test_falling_sentiment_requires_significance() -> None:
    prior = [("BIG", "2017-09-01", "Positive", {})] * 10 + [("SMALL", "2017-09-01", "Positive", {})] * 4
    recent = [("BIG", "2018-07-01", "Negative", {})] * 10 + [("SMALL", "2018-07-01", "Positive", {})] * 3 + [("SMALL", "2018-07-01", "Negative", {})]
    out = falling_sentiment(_reviews(prior + recent))
    assert list(out["product_id"]) == ["BIG"]  # SMALL drops 25 points but 1 of 4 reviews is not significant


def test_weekly_report_number_check() -> None:
    facts = {"week_starting": "2018-08-27", "this_week": {"reviews": 121, "positive_pct": 87.0}}
    assert unsupported_numbers("121 reviews, 87.0% positive (week of 2018-08-27)", facts) == set()
    assert unsupported_numbers("125 reviews", facts) == {"125"}
    full = {
        "week_starting": "2018-08-27",
        "this_week": {"reviews": 5, "spam_filtered": 0, "positive_pct": 80.0, "negative_pct": 20.0, "delivery_complaint_pct": 0.0},
        "previous_week": {"reviews": 4, "spam_filtered": 1, "positive_pct": 75.0, "negative_pct": 25.0, "delivery_complaint_pct": 25.0},
        "top_complaints_by_category_this_week": [], "products_with_falling_sentiment": [],
        "sellers_with_delivery_problems": 2, "inventory_alerts": {"CRITICAL_STOCKOUT_RISK": 3},
    }
    assert unsupported_numbers(template_report(full), full) == set()  # the fallback never invents numbers


def test_latency_sla_is_scoped_to_recommendations() -> None:
    from shopkaro.api.main import LatencyTelemetry

    t = LatencyTelemetry()
    t.record("/search", 900.0)
    assert t.summary()["overall"]["sla_p95_under_100ms_met"] is None  # no recommendation traffic: unknown, not "met"
    for _ in range(20):
        t.record("/recommendations/{user_id}", 12.0)
    s = t.summary()["overall"]
    assert s["recommendation_p95_ms"] == 12.0 and s["sla_p95_under_100ms_met"] is True
