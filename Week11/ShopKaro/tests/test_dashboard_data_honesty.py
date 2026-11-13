"""Storefront data helpers must show catalogue truth: real SKUs, real discounts, real ratings, clean titles."""

from __future__ import annotations

import re

import duckdb

from shopkaro.config.settings import settings
from shopkaro.dashboard import app


def _catalogue() -> dict[str, tuple]:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    rows = con.execute("SELECT product_id, title, price_pkr, discount_pct, in_stock FROM product_catalogue").fetchall()
    con.close()
    return {r[0]: r[1:] for r in rows}


def test_deals_are_real_in_stock_discounted_products() -> None:
    cat = _catalogue()
    deals = app.load_deal_items()
    assert len(deals) == 3 and len({d["category"] for d in deals}) == 3
    for d in deals:
        title, price, disc, in_stock = cat[d["product_id"]]
        assert (d["title"], d["price_pkr"], d["discount_pct"]) == (title, price, disc)
        assert in_stock and disc > 0


def test_default_grid_items_have_real_reviews_and_variety() -> None:
    items = app.load_popular_items()
    assert len({i["category"] for i in items}) >= 6
    assert all(i["review_count"] > 0 and i["avg_rating"] is not None for i in items)


def test_banner_discount_matches_catalogue() -> None:
    max_disc, n_on_sale = app.catalogue_discount_stats()
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    assert max_disc == con.execute("SELECT MAX(discount_pct) FROM product_catalogue").fetchone()[0]
    con.close()
    assert n_on_sale > 0


def test_no_title_repeats_a_word() -> None:
    pat = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
    assert not [t for t, *_ in _catalogue().values() if pat.search(t)]


def test_p_values_are_readable() -> None:
    import pandas as pd

    out = app._readable_p_values(pd.DataFrame({"ctr_p_value": [0.0, 3.6e-7, 0.58]}))
    assert out["ctr_p_value"].tolist() == ["< 1e-15", "3.6e-07", "0.580"]


def test_sales_overview_totals_reports_empty_data_and_sums_records() -> None:
    import pandas as pd

    assert app._sales_overview_totals(pd.DataFrame()) is None
    sales = pd.DataFrame(
        {
            "total_gmv_pkr": [1200.0, 800.0],
            "total_units_sold": [3, 2],
            "total_sales_records": [2, 1],
        }
    )
    assert app._sales_overview_totals(sales) == (2000.0, 5.0, 3)


def test_demo_checkout_keeps_items_in_the_bag() -> None:
    from streamlit.testing.v1 import AppTest

    bag = {
        "item_count": 1,
        "total_pkr": 3450.0,
        "items": [
            {
                "product_id": "SK-00001",
                "title": "Sample Kurta",
                "brand": "ShopKaro",
                "quantity": 1,
                "line_total_pkr": 3450.0,
                "unit_price_pkr": 3450.0,
            }
        ],
    }
    at = AppTest.from_file(app.__file__, default_timeout=300)
    at.session_state["sidebar_mode"] = "cart"
    at.session_state["live_cart"] = bag
    at.run()
    assert not at.exception

    at.button(key="cart_sidebar_checkout_btn").click().run()
    assert not at.exception
    assert at.session_state["live_cart"] == bag


def test_product_details_panel_renders_with_and_without_reviews() -> None:
    """Regression: the panel formatted avg_rating as a float and crashed for unreviewed products."""
    from streamlit.testing.v1 import AppTest

    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    reviewed = con.execute("SELECT product_id FROM review_intelligence_summary ORDER BY product_id LIMIT 1").fetchone()[0]
    unreviewed, price = con.execute(
        "SELECT product_id, price_pkr FROM product_catalogue WHERE product_id NOT IN "
        "(SELECT product_id FROM review_intelligence_summary) AND category = 'Laptops & Computing' LIMIT 1"
    ).fetchone()
    con.close()
    app.serving_container.ensure_initialized()
    for sku in (reviewed, unreviewed):
        at = AppTest.from_file(app.__file__, default_timeout=300)
        at.session_state["inspected_sku"] = sku
        at.run()
        assert not at.exception, (sku, [e.value for e in at.exception])
        text = " ".join(m.value for m in at.markdown)
        assert "Banarasi Silk" not in text  # no fixed fabric copy for every product
    # Unreviewed laptop: no rating, no clothing sizes, real price
    assert any("No reviews yet for this product." in i.value for i in at.info)
    assert not any(r.label == "Select size:" for r in at.radio)
    assert f"PKR {price:,.0f}" in text
