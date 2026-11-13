"""
Day 5 — Task 3: ShopKaro Production E-Commerce Storefront & Enterprise Console.

Built to look like an authentic, modern Pakistani e-commerce marketplace
(e.g., Daraz.pk, Khaadi, Sapphire, Shopify Plus):
- Announcement top bar, branded header, quick category navigation, hero festive banner
- High-resolution curated product photography for Pakistani apparel, electronics, and cosmetics
- E-commerce product cards with discount ribbons, PKR currency formatting, star ratings, and Add to Bag
- Hybrid search and recommendations integrated natively without exposing internal ML jargon to shoppers
- Integrated UrduLish Shopping Concierge (Roman Urdu & English conversational shopping)
- Role switcher to access Supply Chain & Inventory Control Tower and Executive A/B Analytics

FIX (sidebar drawer): the old JS click listener used
    e.target.closest('div:has(.shopkaro-ham-anchor) button')
which also matched Ask AI / Wishlist / Cart buttons (they live inside the same header row),
so every click first opened the navigation drawer. The sidebar is now opened/closed by
`_sync_sidebar_with_state()`, which follows Python's `st.session_state["sidebar_state"]`
after each rerun instead of listening to clicks.
"""

from __future__ import annotations

from pathlib import Path
import sys
import base64
import json
import html
import threading
from functools import lru_cache
from typing import Any

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_DEMO_USER = "USR-928443"  # real customer with Eid / lawn history
DEMO_CHECKOUT_NOTICE = (
    "Demo only. No order or payment is submitted, and your bag remains unchanged."
)


STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=64)
def get_local_asset_data_uri(filename: str) -> str:
    """
    URL for a studio photograph.

    Preferred: the resized copy in ./static served by Streamlit (`enableStaticServing` in .streamlit/config.toml),
    which the browser downloads once and caches. Embedding the 0.8 MB originals as base64 in every card made one
    storefront render ~30 MB. Fallback (static serving off): the small resized copy as a data URI.
    Build the resized copies with `python scripts/build_dashboard_images.py`.
    """
    static_path = STATIC_DIR / filename
    if static_path.exists():
        if _static_serving_enabled():
            return f"app/static/{filename}"
        return "data:image/jpeg;base64," + base64.b64encode(static_path.read_bytes()).decode("utf-8")
    img_path = ASSETS_DIR / filename
    if img_path.exists():
        return "data:image/jpeg;base64," + base64.b64encode(img_path.read_bytes()).decode("utf-8")
    return ""


def _static_serving_enabled() -> bool:
    try:
        from streamlit import config as st_config

        return bool(st_config.get_option("server.enableStaticServing"))
    except Exception:
        return False


from shopkaro.api.main import (
    ChatRequest,
    chat_assistant_endpoint,
    get_forecast_endpoint,
    get_product_reviews_endpoint,
    get_recommendations_endpoint,
    health_check,
    metrics_endpoint,
    search_products_endpoint,
    serving_container,
)
from shopkaro.config.settings import settings
from shopkaro.data.bootstrap import data_ready, ensure_data
from shopkaro.reviews import lexicon_analyzer as review_lexicon
from shopkaro.reviews.intelligence import ASPECT_NAMES


# Curated high-resolution e-commerce product photography mapped by SKU and Category
HERO_SKU_IMAGES: dict[str, str] = {
    "SK-00004": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",  # Navy School Backpack
    "SK-00005": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=600&auto=format&fit=crop&q=80",  # Red Heavy Backpack
    "SK-00008": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",  # Lenovo ThinkBook Laptop
    "SK-00009": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",  # HP ProBook Laptop
    "SK-00011": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&auto=format&fit=crop&q=80",  # Oud & Rose Perfume Set
    "SK-00012": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600&auto=format&fit=crop&q=80",  # Herbal Skincare Luxury Basket
    "SK-00013": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80",  # Samsung Galaxy A55 5G
    "SK-00014": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80",  # 45W Fast Charger Adapter
    "SK-00015": "https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=600&auto=format&fit=crop&q=80",  # Shockproof Silicone Back Cover
}

CATEGORY_FALLBACK_IMAGES: dict[str, str] = {
    "Women's Lawn & Unstitched": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop&q=80",
    "Bridal & Formal Wear": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop&q=80",
    "Men's Kurta & Ethnic": "https://images.unsplash.com/photo-1597983073493-88cd35cf93b0?w=600&auto=format&fit=crop&q=80",
    "Footwear & Khussa": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&auto=format&fit=crop&q=80",
    "Smartphones & Accessories": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80",
    "Laptops & Computing": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
    "Kids & School Supplies": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
    "Beauty & Fragrances": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&auto=format&fit=crop&q=80",
    "Home & Kitchen Appliances": "https://images.unsplash.com/photo-1588854337221-4cf9fa96059c?w=600&auto=format&fit=crop&q=80",
    "Groceries & Staples": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&auto=format&fit=crop&q=80",
    "Winter Wear & Jackets": "https://images.unsplash.com/photo-1544441893-675973e31985?w=600&auto=format&fit=crop&q=80",
}


def get_product_image_url(product_id: str, category: str) -> str:
    """
    Return high-resolution photo URL or base64 Data URI for product card.
    Strictly honors Islamic values of modesty (Haya) and authentic Pakistani Muslim culture:
    - Modest Pakistani Women's 3-Piece Designer Lawn Suit (Bareeze / Sapphire / Khaadi style - full coverage)
    - Modest Pakistani Muslim Bridal Attire (Maria B / Asim Jofa Nikah collection - long kurti, no bare waist, modest head drape)
    - Modest Sunnah-Inspired Pakistani Men's Kurta Shalwar (Junaid Jamshed / Almirah style with ban collar)
    - Luxury Pakistani Islamic Eid Gift Set (J. Arabian Oud flacon, pure pashmina shawl & olive-wood tasbeeh)
    - Handcrafted Maroon Velvet Pakistani Khussa (Chapter 13 traditional Punjabi tilla embroidery)
    """
    pid = str(product_id).upper()
    cat_lower = str(category or "").lower()

    # 1. Modest Pakistani Women's 3-Piece Lawn & Unstitched Suits (Full coverage, matching dupatta)
    if pid == "SK-00001":
        uri = get_local_asset_data_uri("pakistani_modest_lawn.jpg")
        if uri:
            return uri
    elif pid in {"SK-00002", "SK-00003"}:
        uri = get_local_asset_data_uri("pakistani_lawn_emerald.jpg")
        if uri:
            return uri
    elif "lawn" in cat_lower or "unstitched" in cat_lower:
        chosen_lawn = "pakistani_lawn_emerald.jpg" if (sum(ord(c) for c in pid) % 2 == 1) else "pakistani_modest_lawn.jpg"
        uri = get_local_asset_data_uri(chosen_lawn) or get_local_asset_data_uri("pakistani_modest_lawn.jpg") or get_local_asset_data_uri("pakistani_lawn_emerald.jpg")
        if uri:
            return uri

    # 2. Modest Pakistani Muslim Bridal & Nikah Formal Wear (Long kurti, zero midriff exposure, head dupatta)
    if pid == "SK-00006":
        uri = get_local_asset_data_uri("pakistani_modest_bridal_lehenga.jpg")
        if uri:
            return uri
    elif pid == "SK-00007":
        uri = get_local_asset_data_uri("pakistani_bridal_lehenga_crimson.jpg")
        if uri:
            return uri
    elif "bridal" in cat_lower or "lehenga" in cat_lower or "formal wear" in cat_lower:
        chosen_bridal = "pakistani_bridal_lehenga_crimson.jpg" if (sum(ord(c) for c in pid) % 2 == 1) else "pakistani_modest_bridal_lehenga.jpg"
        uri = get_local_asset_data_uri(chosen_bridal) or get_local_asset_data_uri("pakistani_modest_bridal_lehenga.jpg") or get_local_asset_data_uri("pakistani_bridal_lehenga_crimson.jpg")
        if uri:
            return uri

    # 3. Dignified Modest Pakistani Men's Kurta Shalwar (Junaid Jamshed / Almirah ban collar)
    if pid == "SK-00020":
        uri = get_local_asset_data_uri("pakistani_modest_mens_kurta.jpg")
        if uri:
            return uri
    elif "kurta" in cat_lower or "men's kurta" in cat_lower or "ethnic" in cat_lower or "shalwar" in cat_lower:
        chosen_kurta = "pakistani_mens_kurta_cream.jpg" if (sum(ord(c) for c in pid) % 2 == 1) else "pakistani_modest_mens_kurta.jpg"
        uri = get_local_asset_data_uri(chosen_kurta) or get_local_asset_data_uri("pakistani_modest_mens_kurta.jpg") or get_local_asset_data_uri("pakistani_mens_kurta_cream.jpg")
        if uri:
            return uri

    # 4. Islamic Eid Gift Hamper & Fragrances (J. Arabian Oud, Embroidered Shawl, Tasbeeh)
    if pid in {"SK-00010", "SK-00011", "SK-00012"} or "fragrance" in cat_lower or "beauty" in cat_lower or "oud" in cat_lower or "shawl" in cat_lower:
        uri = get_local_asset_data_uri("pakistani_islamic_eid_gift_oud_shawl.jpg")
        if uri:
            return uri

    # 5. Handcrafted Authentic Pakistani Velvet Khussa
    if pid in {"SK-00018", "SK-00019"} or "khussa" in cat_lower or "footwear" in cat_lower:
        uri = get_local_asset_data_uri("pakistani_khussa_maroon.jpg")
        if uri:
            return uri

    # 6. Tech, Gadgets, and School supplies
    if pid in HERO_SKU_IMAGES:
        return HERO_SKU_IMAGES[pid]

    if "bridal" in cat_lower or "formal" in cat_lower:
        return get_local_asset_data_uri("pakistani_bridal_lehenga_crimson.jpg") or get_local_asset_data_uri("pakistani_modest_bridal_lehenga.jpg")
    if "lawn" in cat_lower or "unstitched" in cat_lower:
        return get_local_asset_data_uri("pakistani_modest_lawn.jpg") or get_local_asset_data_uri("pakistani_lawn_emerald.jpg")
    if "kurta" in cat_lower or "men" in cat_lower:
        return get_local_asset_data_uri("pakistani_modest_mens_kurta.jpg") or get_local_asset_data_uri("pakistani_mens_kurta_cream.jpg")
    if "khussa" in cat_lower or "footwear" in cat_lower:
        return get_local_asset_data_uri("pakistani_khussa_maroon.jpg")

    return CATEGORY_FALLBACK_IMAGES.get(
        category,
        get_local_asset_data_uri("pakistani_lawn_emerald.jpg") or "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop&q=80",
    )


def _start_model_warmup(st: Any) -> None:
    """Start loading all serving models in a daemon thread, once per server process."""

    @st.cache_resource(show_spinner=False)
    def _warmup_thread() -> threading.Thread:
        t = threading.Thread(target=serving_container.ensure_initialized, name="shopkaro-warmup", daemon=True)
        t.start()
        return t

    _warmup_thread()


def _wait_for_models(st: Any) -> None:
    """Block (with a visible spinner) until the background model load has finished."""
    if not serving_container._initialized:
        with st.spinner("Loading ShopKaro's models (first start of the server takes about 30 seconds)..."):
            serving_container.ensure_initialized()


def _render_models_loading_placeholder(st: Any, what: str) -> None:
    """Loading note that re-checks every 2 s and reruns the page once the models are ready."""

    @st.fragment(run_every=2.0)
    def _poll() -> None:
        if serving_container._initialized:
            st.rerun()
        st.info(f"⏳ {what} are loading (first start of the server takes about 30 seconds)...")

    _poll()


def load_dashboard_snapshot() -> dict[str, Any]:
    """
    Load summary tables for the dashboard views from DuckDB and report CSVs.
    Also used directly by automated pytest verification. Reads DuckDB / CSV only, so it does not wait for models.
    """
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)

    segments_summary = con.execute(
        """
        SELECT
            segment_name,
            COUNT(*) AS customer_count,
            ROUND(AVG(recency_days), 1) AS avg_recency_days,
            ROUND(AVG(frequency_sessions), 2) AS avg_frequency,
            ROUND(AVG(monetary_intent_pkr), 0) AS avg_monetary_pkr
        FROM customer_segments
        GROUP BY segment_name
        ORDER BY avg_monetary_pkr DESC
        """
    ).df()

    alerts_df = con.execute(
        """
        SELECT
            product_id, title, category, brand,
            current_stock_qty AS current_stock_units,
            ROUND(forecast_14d_p50, 1) AS p50_14d,
            ROUND(forecast_30d_p50, 1) AS p50_30d,
            ROUND(forecast_30d_p90, 1) AS p90_30d,
            ROUND(safety_stock_units, 1) AS safety_stock,
            ROUND(reorder_point_units, 1) AS reorder_point,
            ROUND(days_of_inventory_p50, 1) AS doi_days,
            alert_status, recommended_order_qty, recommended_action
        FROM inventory_alerts
        ORDER BY
            CASE alert_status
                WHEN 'CRITICAL_STOCKOUT_RISK' THEN 1
                WHEN 'FESTIVAL_SURGE_WATCH' THEN 2
                WHEN 'OVERSTOCK_DEAD_CAPITAL' THEN 3
                ELSE 4
            END,
            p50_30d DESC
        """
    ).df()

    festivals_df = con.execute(
        """
        SELECT
            festival_name, festival_type, start_date, end_date,
            demand_multiplier, boost_categories
        FROM festival_calendar
        ORDER BY start_date
        """
    ).df()

    seller_df = con.execute(
        "SELECT * FROM seller_scorecards ORDER BY total_genuine_reviews DESC LIMIT 100"
    ).df()

    review_gems_df = con.execute(
        """
        SELECT
            product_id, title, brand, category, genuine_review_count,
            avg_rating, quality_pos_pct, delivery_neg_pct,
            avg_delivery_delay_days, recommended_action
        FROM review_intelligence_summary
        WHERE is_unfairly_penalized_by_courier = TRUE
        ORDER BY quality_pos_pct DESC
        """
    ).df()

    sales_overview = con.execute(
        """
        SELECT
            category,
            COUNT(*) AS total_sales_records,
            ROUND(SUM(units_sold), 0) AS total_units_sold,
            ROUND(SUM(revenue_pkr), 0) AS total_gmv_pkr,
            ROUND(AVG(unit_price_pkr), 0) AS avg_price_pkr
        FROM daily_sales
        GROUP BY category
        ORDER BY total_gmv_pkr DESC
        """
    ).df()

    monthly_sales = con.execute(
        """
        SELECT
            strftime(sale_date, '%Y-%m') AS sale_month,
            ROUND(SUM(revenue_pkr) / 1e6, 2) AS gmv_millions_pkr,
            ROUND(SUM(units_sold), 0) AS total_units
        FROM daily_sales
        GROUP BY 1
        ORDER BY 1
        """
    ).df()

    con.close()

    ab_path = settings.reports_dir / "day5_ab_test_results.csv"
    ab_df = pd.read_csv(ab_path) if ab_path.exists() else pd.DataFrame()

    sub_path = settings.reports_dir / "day5_ab_test_segment_subgroups.csv"
    ab_sub_df = pd.read_csv(sub_path) if sub_path.exists() else pd.DataFrame()

    ab_summary_path = settings.reports_dir / "day5_ab_test_summary.json"
    ab_summary = json.loads(ab_summary_path.read_text(encoding="utf-8")) if ab_summary_path.exists() else {}

    rec_bench_path = settings.reports_dir / "day2_model_comparison.csv"
    rec_bench_df = pd.read_csv(rec_bench_path) if rec_bench_path.exists() else pd.DataFrame()

    search_bench_path = settings.reports_dir / "day4_search_comparison.csv"
    search_bench_df = pd.read_csv(search_bench_path) if search_bench_path.exists() else pd.DataFrame()

    return {
        "segments_summary": segments_summary,
        "inventory_alerts": alerts_df,
        "festivals": festivals_df,
        "seller_scorecards": seller_df,
        "unfairly_penalized_gems": review_gems_df,
        "ab_test_results": ab_df,
        "ab_segment_subgroups": ab_sub_df,
        "ab_summary": ab_summary,
        "sales_overview": sales_overview,
        "monthly_sales": monthly_sales,
        "rec_benchmarks": rec_bench_df,
        "search_benchmarks": search_bench_df,
    }


def analyze_live_review_text(review_text: str, rating: int = 4) -> dict[str, Any]:
    """
    Live sentiment, clause, aspect and spam analysis for the Review Intelligence console. Uses the same rule
    analyzer as the batch pipeline and the API (`shopkaro.reviews.lexicon_analyzer`); `rating` is shown but does
    not change the text analysis.
    """
    sent = review_lexicon.analyze_sentiment(review_text)
    spam = review_lexicon.classify_spam(review_text)
    overall = "Mixed / Contrastive (Neutral)" if sent["is_mixed_sentiment"] else sent["sentiment"]
    return {
        "overall_sentiment": overall,
        "is_contrastive_mixed": sent["is_mixed_sentiment"],
        "clauses": sent["clauses"],
        "aspects": review_lexicon.analyze_aspects(review_text),
        "is_fake_spam": spam["is_fake_spam"],
        "spam_reason": spam["spam_reason"],
    }


def _sales_overview_totals(
    sales_df: pd.DataFrame,
) -> tuple[float, float, int] | None:
    if sales_df.empty:
        return None
    return (
        float(sales_df["total_gmv_pkr"].sum()),
        float(sales_df["total_units_sold"].sum()),
        int(sales_df["total_sales_records"].sum()),
    )


def _inject_real_ecommerce_css(st: Any) -> None:
    """Inject real-world commercial e-commerce CSS styling (Daraz / Noon / Shopify vibe)."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #111827;
            background-color: #FFFFFF;
        }

        /* 1. Top Announcement Bar - Full-Width Rectangular Banner Anchored Flush to Absolute Top */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        .block-container {
            max-width: 1420px !important;
            padding-top: 3.2rem !important;
            padding-bottom: 3.5rem !important;
            container-type: inline-size;
        }
        .laam-top-ticker {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            max-width: 100vw !important;
            height: 38px !important;
            background: #0B1E19 !important; /* luxury deep emerald black */
            color: #FFFFFF !important;
            text-align: center !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            padding: 0 1rem !important;
            border-radius: 0 !important;
            margin: 0 !important;
            border-bottom: 1px solid rgba(212, 175, 55, 0.35) !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            z-index: 999999 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.6rem !important;
            line-height: 38px !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15) !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        /* ------------------------------------------------------------- */
        /* SHOPKARO RESPONSIVE LUXURY NAVIGATION BAR                     */
        /* Desktop: 1 Single Row | Tablet & Mobile: Search on 2nd Row    */
        /* ------------------------------------------------------------- */

        /* Header Row Container - Base Styling */
        div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) {
            align-items: center !important;
            margin-bottom: 0.85rem !important;
            padding-bottom: 0.5rem !important;
            width: 100% !important;
        }

        /* Official ShopKaro Marketplace Brand Logo */
        .shopkaro-brand-logo {
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.45rem !important;
            text-decoration: none !important;
            white-space: nowrap !important;
            line-height: 1 !important;
            flex-shrink: 0 !important;
            min-width: max-content !important;
        }
        .shopkaro-brand-logo:hover, .shopkaro-brand-logo:visited, .shopkaro-brand-logo:active {
            text-decoration: none !important;
        }
        .shopkaro-logo-text {
            display: inline-flex !important;
            align-items: baseline !important;
            gap: 0.15rem !important;
            white-space: nowrap !important;
        }
        .shopkaro-logo-main {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
            font-size: 1.45rem !important;
            font-weight: 800 !important;
            color: #111827 !important;
            letter-spacing: -0.03em !important;
            white-space: nowrap !important;
        }
        .shopkaro-logo-badge {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
            color: #0F766E !important;
            font-size: 0.95rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em !important;
            margin-left: 1px !important;
            white-space: nowrap !important;
        }

        /* Clean Hamburger Button */
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 1.65rem !important;
            color: #111827 !important;
            padding: 0 !important;
            height: 44px !important;
            min-height: 44px !important;
            width: 44px !important;
            min-width: 44px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            border-radius: 8px !important;
            transition: all 0.15s ease !important;
            line-height: 1 !important;
            flex-shrink: 0 !important;
        }
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button:hover,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button:hover {
            background: #F1F5F9 !important;
            color: #0F766E !important;
        }
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button p,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button p {
            font-size: 1.65rem !important;
            font-weight: 400 !important;
            line-height: 1 !important;
            margin: 0 !important;
            color: #111827 !important;
        }

        /* Allow Streamlit to handle column widths on desktop, just ensure vertical alignment */
        div[data-testid="stHorizontalBlock"]:has(.shopkaro-ham-anchor) {
            align-items: center !important;
        }
        
        /* Ensure the right-side icons never squish on smaller desktop screens */
        div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-wish-box),
        div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-bag-box) {
            min-width: 55px !important; 
        }

        /* Center Search Bar (Height 44px, Full Pill) */
        div[data-testid="element-container"]:has(.shopkaro-search-box) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box),
        div[data-testid="column"]:has(.shopkaro-search-box) {
            display: flex !important;
            align-items: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) div[data-testid="stTextInput"],
        div[data-testid="column"]:has(.shopkaro-search-box) div[data-testid="stTextInput"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) div[data-baseweb="input"],
        div[data-testid="stColumn"]:has(.shopkaro-search-box) div[data-baseweb="base-input"],
        div[data-testid="column"]:has(.shopkaro-search-box) div[data-baseweb="input"],
        div[data-testid="column"]:has(.shopkaro-search-box) div[data-baseweb="base-input"] {
            background-color: #F8FAFC !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 999px !important;
            padding: 0 1.25rem !important;
            height: 44px !important;
            min-height: 44px !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
            position: relative !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) div[data-baseweb="input"]:focus-within,
        div[data-testid="column"]:has(.shopkaro-search-box) div[data-baseweb="input"]:focus-within {
            background-color: #FFFFFF !important;
            border-color: #0F766E !important;
            box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12) !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) div[data-baseweb="input"]::after,
        div[data-testid="column"]:has(.shopkaro-search-box) div[data-baseweb="input"]::after {
            content: "🔍" !important;
            position: absolute !important;
            right: 18px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            font-size: 1.05rem !important;
            color: #0F766E !important;
            pointer-events: none !important;
            line-height: 1 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) input,
        div[data-testid="column"]:has(.shopkaro-search-box) input {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            font-size: 0.90rem !important;
            color: #1E293B !important;
            padding-right: 2.4rem !important;
            height: 44px !important;
            font-family: inherit !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-search-box) input::placeholder,
        div[data-testid="column"]:has(.shopkaro-search-box) input::placeholder {
            color: #94A3B8 !important;
            font-size: 0.90rem !important;
        }

        /* Restored '✨ Ask AI' Button Container & Clear Styling */
        div[data-testid="element-container"]:has(.shopkaro-ai-box) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-ai-box),
        div[data-testid="column"]:has(.shopkaro-ai-box) {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-ai-box) div[data-testid="stButton"],
        div[data-testid="column"]:has(.shopkaro-ai-box) div[data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-ai-box) button,
        div[data-testid="column"]:has(.shopkaro-ai-box) button {
            background: #FFFBEB !important; /* warm champagne/cream background */
            border: 1.5px solid #FDE68A !important; /* visible warm golden border */
            border-radius: 999px !important; /* pill container */
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 1.15rem !important;
            box-shadow: 0 1px 3px rgba(180, 83, 9, 0.08) !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.45rem !important;
            width: 100% !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-ai-box) button:hover,
        div[data-testid="column"]:has(.shopkaro-ai-box) button:hover {
            background: #FEF3C7 !important;
            border-color: #F59E0B !important;
            box-shadow: 0 4px 12px rgba(180, 83, 9, 0.16) !important;
            transform: translateY(-1px) !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-ai-box) button p,
        div[data-testid="column"]:has(.shopkaro-ai-box) button p,
        div[data-testid="stColumn"]:has(.shopkaro-ai-box) button span,
        div[data-testid="column"]:has(.shopkaro-ai-box) button span {
            color: #B45309 !important; /* visible bronze text */
            font-size: 0.90rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.01em !important;
            margin: 0 !important;
            white-space: nowrap !important;
            display: inline !important;
            visibility: visible !important;
            opacity: 1 !important;
            line-height: 1 !important;
        }

        /* Action Icons (Wishlist & Cart) - Standard, Clickable Circular UI Elements */
        div[data-testid="stColumn"]:has(.shopkaro-wish-box),
        div[data-testid="column"]:has(.shopkaro-wish-box),
        div[data-testid="stColumn"]:has(.shopkaro-bag-box),
        div[data-testid="column"]:has(.shopkaro-bag-box) {
            position: relative !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-wish-box) div[data-testid="stButton"],
        div[data-testid="column"]:has(.shopkaro-wish-box) div[data-testid="stButton"],
        div[data-testid="stColumn"]:has(.shopkaro-bag-box) div[data-testid="stButton"],
        div[data-testid="column"]:has(.shopkaro-bag-box) div[data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 44px !important;
            display: flex !important;
            justify-content: center !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-wish-box) button,
        div[data-testid="column"]:has(.shopkaro-wish-box) button,
        div[data-testid="stColumn"]:has(.shopkaro-bag-box) button,
        div[data-testid="column"]:has(.shopkaro-bag-box) button {
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 50% !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
            width: 44px !important;
            height: 44px !important;
            min-width: 44px !important;
            min-height: 44px !important;
            padding: 0 !important;
            margin: 0 auto !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            transition: all 0.18s ease !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-wish-box) button:hover,
        div[data-testid="column"]:has(.shopkaro-wish-box) button:hover,
        div[data-testid="stColumn"]:has(.shopkaro-bag-box) button:hover,
        div[data-testid="column"]:has(.shopkaro-bag-box) button:hover {
            background: #F8FAFC !important;
            border-color: #0F766E !important;
            box-shadow: 0 3px 8px rgba(15, 118, 110, 0.15) !important;
            transform: translateY(-1px) !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-wish-box) button p,
        div[data-testid="column"]:has(.shopkaro-wish-box) button p {
            font-size: 1.45rem !important;
            color: #1E293B !important;
            line-height: 1 !important;
            margin: 0 !important;
        }
        div[data-testid="stColumn"]:has(.shopkaro-bag-box) button p,
        div[data-testid="column"]:has(.shopkaro-bag-box) button p {
            font-size: 1.35rem !important;
            color: #1E293B !important;
            line-height: 1 !important;
            margin: 0 !important;
        }

        /* Anchored Notification Badges (Always Locked to Top-Right Corner of 44px Icon) */
        .header-action-container {
            position: relative !important;
            width: 44px !important;
            height: 0 !important;
            margin: 0 auto !important;
            display: block !important;
        }
        .header-badge-bubble {
            position: absolute !important;
            top: -6px !important;
            right: -4px !important;
            min-width: 19px !important;
            height: 19px !important;
            border-radius: 999px !important;
            color: #FFFFFF !important;
            font-size: 0.68rem !important;
            font-weight: 800 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 4px !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25) !important;
            border: 2px solid #FFFFFF !important;
            z-index: 999 !important;
            pointer-events: none !important;
            line-height: 1 !important;
            box-sizing: border-box !important;
        }
        .badge-red {
            background: #EF4444 !important;
        }
        .badge-emerald {
            background: #0F766E !important;
        }

        /* ------------------------------------------------------------- */
        /* RESPONSIVE ENGINE: TABLET & MOBILE VIEW BREAKPOINTS           */
        /* On Tablet / Mobile / Drawer-Open, Search Bar drops to Row 2!  */
        /* ------------------------------------------------------------- */

        @media (max-width: 1024px) {
            /* Transform Header Container into 2 Rows */
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;
                align-items: center !important;
                justify-content: space-between !important;
                row-gap: 0.75rem !important;
                column-gap: 0.4rem !important;
            }

            /* Row 1 Left: Brand & Hamburger */
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-ham-anchor),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-ham-anchor) {
                order: 1 !important;
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: 0 !important;
            }

            /* Row 1 Right: Ask AI, Wishlist, Cart */
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-ai-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-ai-box) {
                order: 2 !important;
                flex: 0 0 auto !important;
                width: auto !important;
                margin-left: auto !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-wish-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-wish-box) {
                order: 3 !important;
                flex: 0 0 44px !important;
                width: 44px !important;
                min-width: 44px !important;
                margin-left: 0.45rem !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-bag-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-bag-box) {
                order: 4 !important;
                flex: 0 0 44px !important;
                width: 44px !important;
                min-width: 44px !important;
                margin-left: 0.35rem !important;
            }

            /* Row 2: Search Bar - Spanning 100% Full Width Below Row 1! */
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-search-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-search-box) {
                order: 5 !important;
                flex: 0 0 100% !important;
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                margin: 0.25rem 0 0 0 !important;
            }

            /* Off-Canvas Overlay Drawer on Tablet/Mobile - Never Squishes Main Page */
            section[data-testid="stSidebar"] {
                position: fixed !important;
                top: 38px !important;
                bottom: 0 !important;
                left: 0 !important;
                width: 360px !important;
                max-width: 88vw !important;
                z-index: 99999 !important;
                background: #FFFFFF !important;
                box-shadow: 6px 0 24px rgba(0, 0, 0, 0.2) !important;
                border-right: 1.5px solid #E5E7EB !important;
            }

            /* Horizontal Scrollable Strip for Popular Search Badges */
            div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-pchip_"]) {
                display: flex !important;
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                padding-bottom: 0.5rem !important;
                gap: 0.45rem !important;
                -webkit-overflow-scrolling: touch !important;
            }
            div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-pchip_"]) > div[data-testid="stColumn"]:has(div[class*="st-key-pchip_"]) {
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: max-content !important;
            }
        }

        /* Container Query for Drawer-Open / Narrow Viewport */
        @container (max-width: 950px) {
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;
                align-items: center !important;
                justify-content: space-between !important;
                row-gap: 0.75rem !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-ham-anchor),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-ham-anchor) {
                order: 1 !important;
                flex: 0 0 auto !important;
                width: auto !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-ai-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-ai-box) {
                order: 2 !important;
                flex: 0 0 auto !important;
                width: auto !important;
                margin-left: auto !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-wish-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-wish-box) {
                order: 3 !important;
                flex: 0 0 44px !important;
                width: 44px !important;
                margin-left: 0.45rem !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-bag-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-bag-box) {
                order: 4 !important;
                flex: 0 0 44px !important;
                width: 44px !important;
                margin-left: 0.35rem !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="stColumn"]:has(.shopkaro-search-box),
            div[data-testid="stHorizontalBlock"]:has(.shopkaro-search-box) > div[data-testid="column"]:has(.shopkaro-search-box) {
                order: 5 !important;
                flex: 0 0 100% !important;
                width: 100% !important;
                min-width: 100% !important;
                margin: 0.25rem 0 0 0 !important;
            }
        }

        /* Mobile Phones (< 550px) */
        @media (max-width: 550px) {
            .shopkaro-logo-main {
                font-size: 1.20rem !important;
            }
            .shopkaro-logo-badge {
                font-size: 0.78rem !important;
            }
            div[data-testid="stColumn"]:has(.shopkaro-ai-box) button {
                padding: 0 0.85rem !important;
                font-size: 0.82rem !important;
            }
        }

        /* Popular Search Chips (Under Search Bar) */
        div[data-testid="stElementContainer"][class*="st-key-pchip_"] button {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 999px !important;
            padding: 0.35rem 0.65rem !important;
            height: 34px !important;
            min-height: 34px !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            color: #334155 !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
        }
        div[data-testid="stElementContainer"][class*="st-key-pchip_"] button:hover {
            background: #F8FAFC !important;
            border-color: #0F766E !important;
            color: #0F766E !important;
            transform: translateY(-1px) !important;
        }

        .shopkaro-bag-pill, .laam-bag-pill {
            background: #FFFFFF !important;
            border: 2px solid #0F766E !important;
            border-radius: 999px !important;
            height: 38px !important;
            padding: 0 0.25rem 0 0.65rem !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.45rem !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            box-sizing: border-box !important;
            text-decoration: none !important;
            flex-shrink: 0 !important;
        }
        .shopkaro-bag-pill:hover, .laam-bag-pill:hover {
            background: #F0FDF4 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 6px rgba(15, 118, 110, 0.15) !important;
        }
        .shopkaro-bag-text {
            font-size: 0.86rem !important;
            font-weight: 700 !important;
            color: #1E293B !important;
            line-height: 1 !important;
            white-space: nowrap !important;
        }
        .shopkaro-free-shipping-badge {
            background: #0F766E !important;
            color: #FFFFFF !important;
            font-size: 0.65rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            padding: 0.22rem 0.5rem !important;
            border-radius: 999px !important;
            text-transform: uppercase !important;
            line-height: 1 !important;
            display: inline-block !important;
            white-space: nowrap !important;
        }
        @media (max-width: 1050px) {
            .shopkaro-currency-item {
                display: none !important;
            }
        }

        /* Luxury Streamlit Tabs - Harmonious with LAAM Maroon */
        div[data-testid="stTabs"] {
            margin-top: 0.4rem !important;
            margin-bottom: 1rem !important;
        }
        div[data-testid="stTabs"] > div:first-child {
            border-bottom: 2px solid #F3F4F6 !important;
            background: #FFFFFF !important;
            padding: 0 0.5rem !important;
            border-radius: 8px 8px 0 0 !important;
            gap: 1.5rem !important;
        }
        button[data-baseweb="tab"] {
            background: transparent !important;
            border: none !important;
            color: #4B5563 !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            padding: 0.65rem 1rem !important;
            border-bottom: 3px solid transparent !important;
            transition: all 0.2s ease !important;
        }
        button[data-baseweb="tab"]:hover {
            color: #0F766E !important;
            background: #F0FDF4 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #0F766E !important;
            font-weight: 800 !important;
            border-bottom: 3px solid #0F766E !important;
            background: transparent !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #0F766E !important;
            height: 3px !important;
        }

        /* Sidebar Styling - Generous Breathing Room & Clean Layout */
        .laam-app-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .laam-app-card-title {
            font-size: 0.92rem;
            font-weight: 800;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .laam-rating-pill {
            background: #FEF3C7;
            color: #B45309;
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
        }
        .laam-app-bullets {
            font-size: 0.74rem;
            color: #4B5563;
            margin: 0.65rem 0 0.85rem 0;
            line-height: 1.6;
        }
        .laam-qr-wrap {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding-top: 0.65rem;
            border-top: 1px solid #F3F4F6;
        }
        .laam-badges-wrap {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            flex: 1;
        }
        .laam-store-badge {
            background: #111827 !important;
            color: #FFFFFF !important;
            padding: 0.4rem 0.65rem !important;
            border-radius: 6px !important;
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            text-align: center !important;
            letter-spacing: 0.02em !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        }
        section[data-testid="stSidebar"] .laam-store-badge,
        section[data-testid="stSidebar"] .laam-store-badge * {
            color: #FFFFFF !important;
        }
        .laam-sidebar-section-title {
            font-size: 0.75rem;
            font-weight: 800;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: 1.1rem 0 0.5rem 0.2rem;
            padding-bottom: 0.3rem;
            border-bottom: 1px solid #F3F4F6;
        }

        /* 3. Shop by Category (Circular Avatars & Centered Text Labels) */
        .laam-cat-heading {
            color: #111827;
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin: 1.6rem 0 1.1rem 0;
            font-family: 'Playfair Display', Georgia, 'Plus Jakarta Sans', serif;
        }
        .laam-category-heading-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin: 1.6rem 0 1.1rem 0;
        }
        .laam-category-heading {
            color: #111827;
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.15;
            margin: 0;
            font-family: 'Playfair Display', Georgia, 'Plus Jakarta Sans', serif;
        }
        .laam-category-link {
            display: inline-flex;
            align-items: center;
            min-height: 44px;
            padding: 0.25rem 0;
            color: #0F766E;
            font-size: 0.9rem;
            font-weight: 700;
            text-decoration: underline;
            text-underline-offset: 4px;
            white-space: nowrap;
        }
        .laam-circle-avatar {
            width: 96px;
            height: 96px;
            border-radius: 50%;
            overflow: hidden;
            background: #F3F4F6;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
            border: 2.5px solid #FFFFFF;
            margin: 0 auto;
            position: relative;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
        }
        .laam-circle-avatar:hover {
            transform: scale(1.06);
            border-color: #0F766E;
            box-shadow: 0 8px 20px rgba(15, 118, 110, 0.2);
        }
        .laam-circle-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 0.35s ease;
        }
        .laam-circle-avatar:hover img {
            transform: scale(1.08);
        }

        /* Luxury Centered Category Button Labels directly beneath avatar */
        div[data-testid="column"]:has(div[class*="st-key-cat_label_"]),
        div[data-testid="stColumn"]:has(div[class*="st-key-cat_label_"]) {
            text-align: center !important;
            padding: 0 0.15rem !important;
        }
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 6px !important;
            box-shadow: none !important;
            padding: 0.35rem 0.2rem !important;
            margin: 0.35rem auto 0.75rem auto !important;
            width: 100% !important;
            height: auto !important;
            min-height: unset !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button:hover {
            background: #F0FDF4 !important;
            border-color: #E2E8F0 !important;
            transform: translateY(-2px) !important;
        }
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button p,
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button span {
            font-size: 0.86rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
            letter-spacing: -0.01em !important;
            text-align: center !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            transition: color 0.15s ease !important;
        }
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button:hover p,
        div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button:hover span {
            color: #0F766E !important;
        }

        
        

        /* Clean Hamburger Button in Top Header Navbar */
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 1.55rem !important;
            color: #111827 !important;
            padding: 0 !important;
            height: 38px !important;
            min-height: 38px !important;
            width: 38px !important;
            min-width: 38px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            border-radius: 6px !important;
            transition: background 0.15s ease !important;
            line-height: 1 !important;
        }
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button:hover,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button:hover {
            background: #F1F5F9 !important;
            color: #0F766E !important;
        }
        div[data-testid="column"]:has(.shopkaro-ham-anchor) button p,
        div[data-testid="stColumn"]:has(.shopkaro-ham-anchor) button p {
            font-size: 1.55rem !important;
            font-weight: 400 !important;
            line-height: 1 !important;
            margin: 0 !important;
        }

        /* Drawer Close Button in Sidebar Header */
        div[data-testid="column"]:has(.drawer-close-anchor) button,
        div[data-testid="stColumn"]:has(.drawer-close-anchor) button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 1.35rem !important;
            font-weight: 300 !important;
            color: #111827 !important;
            padding: 0 !important;
            height: 34px !important;
            min-height: 34px !important;
            width: 34px !important;
            min-width: 34px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
            line-height: 1 !important;
        }
        div[data-testid="column"]:has(.drawer-close-anchor) button:hover,
        div[data-testid="stColumn"]:has(.drawer-close-anchor) button:hover {
            background: #FEE2E2 !important;
            color: #DC2626 !important;
        }
        div[data-testid="column"]:has(.drawer-close-anchor) button p,
        div[data-testid="stColumn"]:has(.drawer-close-anchor) button p {
            font-size: 1.35rem !important;
            font-weight: 300 !important;
            line-height: 1 !important;
            margin: 0 !important;
        }

        /* Streamlit Native Expand Button (Hidden visually, triggered by the sidebar sync script) */
        button[data-testid="stExpandSidebarButton"],
        button[aria-label*="Expand"] {
            position: absolute !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
        }

        /* Drawer Menu Header Bar with Hamburger & Close */
        .drawer-header-bar {
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 0.2rem 0 0.75rem 0 !important;
            margin-bottom: 0.85rem !important;
            border-bottom: 1.5px solid #F1F5F9 !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        .drawer-hamburger-toggle {
            background: transparent !important;
            border: none !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            padding: 0.2rem 0.35rem !important;
            border-radius: 6px !important;
            transition: background 0.15s ease !important;
        }
        .drawer-hamburger-toggle:hover {
            background: #F3F4F6 !important;
        }
        .drawer-header-title {
            font-size: 0.88rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.08em !important;
            color: #111827 !important;
            text-transform: uppercase !important;
            line-height: 1 !important;
        }
        .drawer-close-btn {
            background: transparent !important;
            border: none !important;
            cursor: pointer !important;
            font-size: 1.25rem !important;
            font-weight: 300 !important;
            color: #111827 !important;
            padding: 0.2rem 0.45rem !important;
            border-radius: 6px !important;
            line-height: 1 !important;
            transition: all 0.15s ease !important;
        }
        .drawer-close-btn:hover {
            background: #F3F4F6 !important;
            color: #DC2626 !important;
        }

        /* Keep Native Sidebar Collapse Button Functional But Hidden Visually */
        div[data-testid="stSidebarHeader"] {
            position: absolute !important;
            top: 0 !important;
            right: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
            height: 1px !important;
            width: 1px !important;
            overflow: hidden !important;
        }
        div[data-testid="stSidebarCollapseButton"] button,
        button[aria-label*="Collapse"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #111827 !important;
            padding: 0.25rem 0.5rem !important;
            cursor: pointer !important;
        }
        div[data-testid="stSidebarCollapseButton"] button svg,
        button[aria-label*="Collapse"] svg {
            display: none !important;
        }
        div[data-testid="stSidebarCollapseButton"] button::after,
        button[aria-label*="Collapse"]::after {
            content: "✕" !important;
            font-size: 1.35rem !important;
            font-weight: 300 !important;
            color: #111827 !important;
            line-height: 1 !important;
        }

        /* ------------------------------------------------------------- */
        /* LUXURY SLIDE-OUT DRAWER MENU (J. / SAPPHIRE / ZARA AESTHETIC) */
        /* ------------------------------------------------------------- */

        /* 1. Top 3 Luxury Action Cards (LOGIN, CONTACT US, STORES) */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) {
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 0.45rem !important;
            width: 100% !important;
            margin-bottom: 1.15rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) > div[data-testid="stColumn"],
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: 1 1 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-card-anchor) div[data-testid="element-container"]:first-child {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) div.stButton,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) div[data-testid="stButton"] {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button {
            border: 1.2px solid #111827 !important;
            border-radius: 10px !important;
            background: #FFFFFF !important;
            height: 72px !important;
            min-height: 72px !important;
            padding: 0.35rem 0.1rem 0.3rem 0.1rem !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.2rem !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
            width: 100% !important;
            cursor: pointer !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button:hover {
            background: #111827 !important;
            border-color: #111827 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button p,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button span {
            color: #111827 !important;
            font-size: 0.60rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.03em !important;
            text-transform: uppercase !important;
            line-height: 1.1 !important;
            white-space: nowrap !important;
            text-align: center !important;
            margin: 0 !important;
            padding: 0 !important;
            display: block !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button:hover p,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-card-anchor) button:hover span {
            color: #FFFFFF !important;
        }

        /* SVG Line-Art Icons for Top 3 Cards via Mask on stColumn */
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-card-login) button::before {
            content: "" !important;
            display: block !important;
            width: 22px !important;
            height: 22px !important;
            margin-bottom: 2px !important;
            background-color: #111827 !important;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3C/svg%3E") no-repeat center / contain !important;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3C/svg%3E") no-repeat center / contain !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-card-contact) button::before {
            content: "" !important;
            display: block !important;
            width: 22px !important;
            height: 22px !important;
            margin-bottom: 2px !important;
            background-color: #111827 !important;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z'/%3E%3C/svg%3E") no-repeat center / contain !important;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z'/%3E%3C/svg%3E") no-repeat center / contain !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-card-stores) button::before {
            content: "" !important;
            display: block !important;
            width: 22px !important;
            height: 22px !important;
            margin-bottom: 2px !important;
            background-color: #111827 !important;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/%3E%3Cpolyline points='9 22 9 12 15 12 15 22'/%3E%3C/svg%3E") no-repeat center / contain !important;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/%3E%3Cpolyline points='9 22 9 12 15 12 15 22'/%3E%3C/svg%3E") no-repeat center / contain !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-card-anchor) button:hover::before {
            background-color: #FFFFFF !important;
        }

        /* 2. Horizontal Department Navigation Tabs Strip */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) {
            display: flex !important;
            flex-direction: row !important;
            align-items: flex-end !important;
            justify-content: space-between !important;
            gap: 0.25rem !important;
            width: 100% !important;
            border-bottom: 1.5px solid #E5E7EB !important;
            padding-bottom: 0 !important;
            margin-bottom: 0.75rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) > div[data-testid="stColumn"],
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) > div[data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 auto !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stColumn"]:has(.drawer-dept-anchor) div[data-testid="element-container"]:first-child {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) button {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0.4rem 0.1rem 0.55rem 0.1rem !important;
            margin: 0 !important;
            width: 100% !important;
            min-height: unset !important;
            height: auto !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-bottom: 2.5px solid transparent !important;
            transition: all 0.15s ease !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) button p,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) button span {
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            color: #6B7280 !important;
            white-space: nowrap !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) button:hover p,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) button:hover span {
            color: #111827 !important;
        }
        /* Active Tab with Solid Black Bottom Underline */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) div[data-testid="stColumn"]:has(.drawer-dept-active) button {
            border-bottom: 2.5px solid #111827 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) div[data-testid="stColumn"]:has(.drawer-dept-active) button p,
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.drawer-dept-anchor) div[data-testid="stColumn"]:has(.drawer-dept-active) button span {
            color: #111827 !important;
            font-weight: 800 !important;
        }

        /* 3. Luxury Category Line Items (Zero Vertical Gap, Minimalist List) */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) {
            gap: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) > div[data-testid="element-container"]:has(.drawer-item-anchor) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] > button {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: #111827 !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding: 0.45rem 0.2rem !important;
            margin: 0 !important;
            width: 100% !important;
            height: 38px !important;
            min-height: 38px !important;
            border-bottom: 1px solid #F3F4F6 !important;
            transition: all 0.15s ease !important;
            cursor: pointer !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] > button:hover {
            color: #0F766E !important;
            background: #FAFAFA !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] > button p {
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.07em !important;
            text-transform: uppercase !important;
            color: #111827 !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.65rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] > button:hover p {
            color: #0F766E !important;
        }
        /* Red promo badge styling */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="stButton"] > button span[style*="color"] {
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            color: #EF4444 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            margin-left: 0.65rem !important;
        }
        /* Right-aligned + sign via CSS ::after on drawer-item-has-plus */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="element-container"]:has(.drawer-item-has-plus) + div[data-testid="element-container"] button::after {
            content: "+" !important;
            font-size: 1.15rem !important;
            font-weight: 300 !important;
            color: #6B7280 !important;
            margin-left: auto !important;
            line-height: 1 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-categories-wrap) div[data-testid="element-container"]:has(.drawer-item-has-plus) + div[data-testid="element-container"] button:hover::after {
            color: #0F766E !important;
        }

        /* 4. Bottom Utility Link: TRACK YOUR ORDER */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-track-wrap) div[data-testid="stButton"] > button {
            background: transparent !important;
            border: none !important;
            border-top: 1.5px solid #E5E7EB !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: #111827 !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            padding: 0.9rem 0.2rem 0.6rem 0.2rem !important;
            margin-top: 0.5rem !important;
            width: 100% !important;
            height: auto !important;
            min-height: unset !important;
            cursor: pointer !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-track-wrap) div[data-testid="stButton"] > button:hover {
            color: #0F766E !important;
            background: transparent !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-track-wrap) div[data-testid="stButton"] > button p {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            color: #111827 !important;
            margin: 0 !important;
            line-height: 1 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.drawer-track-wrap) div[data-testid="stButton"] > button:hover p {
            color: #0F766E !important;
        }

        /* ------------------------------------------------------------- */
        /* RIGHT-DOCKED SLIDING CART & AI CONCIERGE DRAWERS             */
        /* ------------------------------------------------------------- */
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active),
        section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active) {
            position: fixed !important;
            top: 0 !important;
            bottom: 0 !important;
            right: 0 !important;
            left: auto !important;
            width: 440px !important;
            min-width: 380px !important;
            max-width: 95vw !important;
            z-index: 999999 !important;
            background: #FFFFFF !important;
            border-left: 1.5px solid #E5E7EB !important;
            border-right: none !important;
            box-shadow: -8px 0 32px rgba(0, 0, 0, 0.16) !important;
            transform: translateX(0) !important;
            animation: slideInRightDrawer 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
        }

        @keyframes slideInRightDrawer {
            from {
                transform: translateX(100%);
            }
            to {
                transform: translateX(0);
            }
        }

        /* Hide empty element container for drawer anchors */
        section[data-testid="stSidebar"] div[data-testid="element-container"]:has(.shopkaro-cart-drawer-active),
        section[data-testid="stSidebar"] div[data-testid="element-container"]:has(.shopkaro-ai-drawer-active) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Keep main page content spacious and prevent overlap with right-docked drawer */
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) .stMain,
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) section[data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) div[data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) .stMain,
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) section[data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) div[data-testid="stMain"] {
            margin-left: 0 !important;
            padding-left: 1.5rem !important;
            padding-right: calc(440px + 1.5rem) !important;
            transition: padding 0.25s ease !important;
        }

        @media (max-width: 900px) {
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) .stMain,
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) section[data-testid="stMain"],
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active)) div[data-testid="stMain"],
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) .stMain,
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) section[data-testid="stMain"],
            .stApp:has(section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active)) div[data-testid="stMain"] {
                padding-right: 1.5rem !important;
            }
            section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active),
            section[data-testid="stSidebar"]:has(.shopkaro-ai-drawer-active) {
                width: 100vw !important;
                max-width: 100vw !important;
            }
        }

        .cart-drawer-header {
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding-bottom: 0.65rem !important;
            border-bottom: 1.5px solid #F1F5F9 !important;
            margin-bottom: 0.85rem !important;
        }
        .cart-item-card {
            background: #FFFFFF !important;
            border: 1.2px solid #E5E7EB !important;
            border-radius: 10px !important;
            padding: 0.75rem 0.85rem !important;
            margin-bottom: 0.5rem !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
            transition: border-color 0.15s ease !important;
        }
        .cart-item-card:hover {
            border-color: #CBD5E1 !important;
        }
        .cart-item-title {
            font-size: 0.86rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
            line-height: 1.25 !important;
        }
        .cart-item-meta {
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            color: #0F766E !important;
            margin-top: 2px !important;
        }
        .cart-item-price {
            font-size: 0.90rem !important;
            font-weight: 800 !important;
            color: #111827 !important;
            white-space: nowrap !important;
        }
        /* Cart Quantity Adjuster Buttons */
        div[data-testid="stColumn"]:has(button[key*="cart_dec_"]) button,
        div[data-testid="stColumn"]:has(button[key*="cart_inc_"]) button {
            background: #F3F4F6 !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 6px !important;
            height: 28px !important;
            min-height: 28px !important;
            width: 28px !important;
            min-width: 28px !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
            color: #111827 !important;
            padding: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[data-testid="stColumn"]:has(button[key*="cart_dec_"]) button:hover,
        div[data-testid="stColumn"]:has(button[key*="cart_inc_"]) button:hover {
            background: #0F766E !important;
            border-color: #0F766E !important;
            color: #FFFFFF !important;
        }
        /* Cart Remove Button */
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key*="cart_del_"] {
            background: #FEE2E2 !important;
            border: 1px solid #FECACA !important;
            color: #DC2626 !important;
            font-size: 0.76rem !important;
            font-weight: 700 !important;
            height: 28px !important;
            min-height: 28px !important;
            padding: 0 0.45rem !important;
            border-radius: 6px !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key*="cart_del_"]:hover {
            background: #DC2626 !important;
            border-color: #DC2626 !important;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key*="cart_del_"] p {
            font-size: 0.76rem !important;
            font-weight: 700 !important;
            color: #DC2626 !important;
            margin: 0 !important;
            line-height: 1 !important;
            white-space: nowrap !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key*="cart_del_"]:hover p {
            color: #FFFFFF !important;
        }

        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_checkout_btn"] {
            background: #0F766E !important;
            border: none !important;
            border-radius: 8px !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
            font-size: 0.86rem !important;
            letter-spacing: 0.02em !important;
            padding: 0.6rem 0.5rem !important;
            height: 42px !important;
            min-height: 42px !important;
            white-space: nowrap !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_checkout_btn"]:hover {
            background: #115E59 !important;
            box-shadow: 0 4px 12px rgba(15, 118, 110, 0.25) !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_checkout_btn"] p {
            color: #FFFFFF !important;
            font-size: 0.86rem !important;
            font-weight: 800 !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_clear_btn"] {
            background: #FFFFFF !important;
            border: 1.2px solid #E5E7EB !important;
            border-radius: 8px !important;
            color: #4B5563 !important;
            font-weight: 700 !important;
            font-size: 0.84rem !important;
            padding: 0.6rem 0.5rem !important;
            height: 42px !important;
            min-height: 42px !important;
            white-space: nowrap !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_clear_btn"]:hover {
            background: #F9FAFB !important;
            border-color: #CBD5E1 !important;
            color: #111827 !important;
        }
        section[data-testid="stSidebar"]:has(.shopkaro-cart-drawer-active) button[key="cart_sidebar_clear_btn"] p {
            font-size: 0.84rem !important;
            font-weight: 700 !important;
            color: #4B5563 !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }

        /* Sidebar Expanders matching LAAM Category Menus */
        section[data-testid="stSidebar"] details {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            margin-bottom: 0.15rem !important;
        }
        section[data-testid="stSidebar"] details summary {
            font-size: 0.92rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
            padding: 0.45rem 0.65rem !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
        }
        section[data-testid="stSidebar"] details summary:hover {
            color: #0F766E !important;
            background: #F9FAFB !important;
        }
        section[data-testid="stSidebar"] details[open] summary {
            color: #0F766E !important;
            font-weight: 800 !important;
        }
        section[data-testid="stSidebar"] details div[data-testid="stVerticalBlock"] > div.stButton > button {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: #4B5563 !important;
            padding: 0.3rem 0.65rem 0.3rem 1.1rem !important;
            border-left: 2px solid #E5E7EB !important;
            border-radius: 0 4px 4px 0 !important;
        }
        section[data-testid="stSidebar"] details div[data-testid="stVerticalBlock"] > div.stButton > button:hover {
            color: #0F766E !important;
            border-left-color: #0F766E !important;
            background: #ECFDF5 !important;
            padding-left: 1.35rem !important;
        }

        
        /* Sidebar Expanders - Strict Uniform Left Alignment */
        section[data-testid="stSidebar"] div[data-testid="stExpander"] {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            margin-bottom: 0.25rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] details {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
            font-size: 0.94rem !important;
            font-weight: 700 !important;
            color: #1F2937 !important;
            padding: 0.5rem 0.65rem !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
            display: flex !important;
            align-items: center !important;
            cursor: pointer !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] summary:hover {
            color: #0F766E !important;
            background: #F9FAFB !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] details[open] summary {
            color: #0F766E !important;
            font-weight: 800 !important;
            background: #ECFDF5 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] > div.stButton > button {
            text-align: left !important;
            justify-content: flex-start !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: #4B5563 !important;
            padding: 0.35rem 0.65rem 0.35rem 1.1rem !important;
            border-left: 2px solid #E5E7EB !important;
            border-radius: 0 4px 4px 0 !important;
            margin-left: 0.5rem !important;
            width: calc(100% - 0.5rem) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] > div.stButton > button:hover {
            color: #0F766E !important;
            border-left-color: #0F766E !important;
            background: #ECFDF5 !important;
            padding-left: 1.35rem !important;
        }

        /* 4. LAAM Clean Sidebar Theme */
        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid #E5E7EB !important;
        }
        
        /* Pushes sidebar content down so the close button clears the top black bar */
        div[data-testid="stSidebarUserContent"] {
            padding-top: 45px !important; 
        }

        section[data-testid="stSidebar"] * {
            color: #1F2937 !important;
        }

        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3 {
            color: #111827 !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: #E5E7EB !important;
            margin: 1rem 0 !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: #F9FAFB !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
            padding: 0.55rem 0.85rem !important;
            margin: 0 !important;
            cursor: pointer !important;
            color: #1F2937 !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background: #F3F4F6 !important;
            border-color: #D1D5DB !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: #0F766E !important;
            border-color: #0F766E !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        /* LAAM "Try App" Box in Sidebar */
        .laam-app-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .laam-app-card-title {
            font-size: 0.88rem;
            font-weight: 800;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .laam-rating-pill {
            background: #FEF3C7;
            color: #B45309;
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
        }
        .laam-app-bullets {
            font-size: 0.74rem;
            color: #4B5563;
            margin: 0.65rem 0;
            line-height: 1.5;
        }
        .laam-qr-wrap {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.6rem;
            padding-top: 0.6rem;
            border-top: 1px solid #F3F4F6;
        }
        .laam-badges-wrap {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }
        .laam-store-badge {
            background: #000000;
            color: #FFFFFF;
            padding: 0.28rem 0.55rem;
            border-radius: 6px;
            font-size: 0.62rem;
            font-weight: 700;
            text-align: center;
            letter-spacing: 0.02em;
            line-height: 1.1;
        }

        /* Active Cart Box in Sidebar */
        .sidebar-cart-box {
            background: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            padding: 0.85rem;
            margin-bottom: 0.8rem;
        }
        .sidebar-cart-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.72rem;
            font-weight: 700;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .sidebar-cart-total {
            font-size: 1.35rem;
            font-weight: 800;
            color: #5B0E2D;
            margin: 0.3rem 0 0.4rem 0;
        }

        /* Product Cards (LAAM Multi-Brand Luxury Style) */
        .ecom-prod-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 0.8rem;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            min-height: 390px;
            height: 100%;
        }
        .ecom-prod-card:hover {
            border-color: #5B0E2D;
            box-shadow: 0 10px 25px rgba(91, 14, 45, 0.08);
            transform: translateY(-3px);
        }
        .ecom-img-wrap {
            width: 100%;
            height: 220px;
            background: #F9FAFB;
            position: relative;
            overflow: hidden;
        }
        .ecom-img-wrap img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.35s ease;
        }
        .ecom-prod-card:hover .ecom-img-wrap img {
            transform: scale(1.04);
        }
        .ecom-ribbon-sale {
            position: absolute;
            top: 10px;
            left: 10px;
            background: #5B0E2D;
            color: #FFFFFF;
            font-size: 0.65rem;
            font-weight: 800;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
            letter-spacing: 0.03em;
        }
        .ecom-ribbon-sku {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            color: #4B5563;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            font-weight: 600;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            border: 1px solid #E5E7EB;
        }
        .ecom-card-content {
            padding: 0.85rem 0.95rem 0.5rem 0.95rem;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .ecom-brand-tag {
            font-size: 0.72rem;
            font-weight: 800;
            color: #5B0E2D;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.25rem;
        }

        
        .ecom-title {
            font-size: 0.86rem;
            font-weight: 600;
            color: #111827;
            line-height: 1.35;
            margin-bottom: 0.4rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            height: 2.7em;
        }
        .ecom-rating-row {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.75rem;
            color: #6B7280;
            margin-bottom: 0.45rem;
        }
        .ecom-stars {
            color: #D97706;
            font-weight: 700;
        }
        .ecom-price-wrap {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-top: auto;
        }
        .ecom-price-curr {
            font-size: 1.15rem;
            font-weight: 800;
            color: #111827;
        }
        .ecom-price-struck {
            font-size: 0.8rem;
            color: #6B7280;
            text-decoration: line-through;
        }

        /* Filter Pills & Bar */
        .ecom-filter-bar {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            overflow-x: auto;
            padding: 0.5rem 0 1rem 0;
            white-space: nowrap;
        }
        .ecom-filter-pill {
            background: #F9FAFB;
            border: 1px solid #E5E7EB;
            color: #374151;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        /* Enterprise Portal Banner */
        .enterprise-banner {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1.3rem 1.8rem;
            color: #FFFFFF;
            margin-bottom: 1.25rem;
        }
        .enterprise-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #38BDF8;
        }
        .enterprise-sub {
            font-size: 0.82rem;
            color: #94A3B8;
            margin-top: 0.25rem;
        }
        .enterprise-mobile-table {
            display: none;
            width: 100%;
            min-width: 0;
            color: #1E293B;
        }
        .enterprise-mobile-table-head,
        .enterprise-mobile-row-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
        }
        .enterprise-mobile-table-head {
            padding: 0 0 0.45rem;
            border-bottom: 1px solid #CBD5E1;
            color: #475569;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .enterprise-mobile-row {
            padding: 0.7rem 0;
            border-bottom: 1px solid #E2E8F0;
        }
        .enterprise-mobile-row:last-child {
            border-bottom: 0;
        }
        .enterprise-mobile-row-top > :first-child {
            min-width: 0;
            overflow-wrap: anywhere;
            color: #1E293B;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .enterprise-mobile-row-top > :last-child {
            flex: 0 0 auto;
            color: #0F172A;
            font-size: 0.82rem;
            font-variant-numeric: tabular-nums;
            font-weight: 700;
            text-align: right;
            white-space: nowrap;
        }
        .enterprise-mobile-row-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem 0.75rem;
            margin-top: 0.3rem;
            color: #475569;
            font-size: 0.75rem;
            line-height: 1.4;
        }

        /* Streamlit Button & Container Tweaks */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
        }
        /* Hero Banner - Luxury Dark Emerald Tint with Aspirational Imagery */
        .shopkaro-hero-banner {
            background-size: cover !important;
            background-position: center 30% !important;
            background-repeat: no-repeat !important;
            border-radius: 16px;
            padding: 2.2rem 2.5rem;
            color: #FFFFFF;
            margin-bottom: 2rem;
            border: 1.5px solid rgba(212, 175, 55, 0.35); /* champagne gold trim */
            box-shadow: 0 16px 36px -8px rgba(6, 38, 30, 0.35);
            position: relative;
            overflow: hidden;
        }
        .shopkaro-hero-badge {
            display: inline-flex;
            align-items: center;
            background: rgba(212, 175, 55, 0.22);
            color: #FDE047;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            margin-bottom: 1rem;
            border: 1px solid rgba(212, 175, 55, 0.55);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .shopkaro-hero-title {
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 2.35rem;
            font-weight: 800;
            line-height: 1.18;
            color: #FFFFFF;
            margin: 0 0 1rem 0;
            letter-spacing: -0.015em;
            text-shadow: 0 2px 14px rgba(0, 0, 0, 0.85), 0 1px 4px rgba(0, 0, 0, 0.95);
        }
        .shopkaro-hero-sub-tiers {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-bottom: 1.6rem;
            max-width: 850px;
        }
        .hero-tier-item {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            font-size: 0.95rem;
            color: #FFFFFF;
            line-height: 1.45;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.85), 0 1px 3px rgba(0, 0, 0, 0.95);
        }
        .hero-tier-bullet {
            color: #FDE047;
            font-size: 0.90rem;
            flex-shrink: 0;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
        }
        .shopkaro-hero-pills {
            display: grid !important;
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 0.85rem !important;
            width: 100% !important;
            margin-top: 1.25rem !important;
            box-sizing: border-box !important;
        }
        @media (max-width: 992px) {
            .shopkaro-hero-pills {
                grid-template-columns: repeat(2, 1fr) !important; /* perfectly symmetrical 2x2 grid */
            }
        }
        /* Phones: Streamlit stacks every column full-width below 640px. Keep the category circles in a 3-up grid
           and the header icons on one line instead of 14 / 5 separate rows; let hero pills stack. */
        @media (max-width: 640px) {
            .shopkaro-hero-pills { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
            [data-testid="stHorizontalBlock"]:has(.laam-circle-avatar) {
                flex-direction: row !important;
                flex-wrap: wrap !important;
                gap: 0.6rem 0.5rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.laam-circle-avatar) > [data-testid="stColumn"] {
                flex: 0 0 calc(33.333% - 0.5rem) !important;
                width: calc(33.333% - 0.5rem) !important;
                min-width: 0 !important;
            }
            [data-testid="stHorizontalBlock"]:has(.shopkaro-logo-badge) {
                flex-direction: row !important;
                flex-wrap: wrap !important;
                align-items: center !important;
                gap: 0.5rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.shopkaro-logo-badge) > [data-testid="stColumn"] {
                flex: 1 1 auto !important;
                width: auto !important;
                min-width: 0 !important;
            }
        }
        .hero-pill {
            background: rgba(7, 29, 23, 0.78) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border: 1.5px solid rgba(212, 175, 55, 0.5) !important; /* crisp champagne gold border */
            color: #FFFFFF !important;
            padding: 0.65rem 0.5rem !important;
            border-radius: 999px !important;
            font-size: 0.84rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            gap: 0.45rem !important;
            width: 100% !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
            transition: all 0.2s ease !important;
            white-space: nowrap !important;
            box-sizing: border-box !important;
        }
        .hero-pill:hover {
            background: rgba(10, 42, 34, 0.94) !important;
            border-color: #FDE047 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45) !important;
        }
        @media (max-width: 640px) {
            .shopkaro-hero-banner {
                padding: 1.35rem 1rem;
                margin-bottom: 1.25rem;
            }
            .shopkaro-hero-badge {
                max-width: 100%;
                font-size: 0.66rem;
                letter-spacing: 0.05em;
                padding: 0.3rem 0.6rem;
                margin-bottom: 0.8rem;
                white-space: normal;
            }
            .shopkaro-hero-title {
                font-size: clamp(1.7rem, 7vw, 2.1rem);
                line-height: 1.12;
                margin-bottom: 0.75rem;
            }
            .shopkaro-hero-sub-tiers {
                gap: 0.4rem;
                margin-bottom: 0.9rem;
            }
            .hero-tier-item {
                gap: 0.45rem;
                font-size: 0.88rem;
                line-height: 1.35;
            }
            .shopkaro-hero-pills {
                gap: 0.55rem !important;
                margin-top: 0.75rem !important;
            }
            .hero-pill {
                min-height: 44px;
                height: auto;
                padding: 0.55rem 0.4rem !important;
                font-size: 0.72rem !important;
                line-height: 1.25;
                white-space: normal !important;
                overflow-wrap: anywhere;
            }
            .laam-category-heading-row {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.15rem;
                margin: 1.35rem 0 0.8rem;
            }
            .laam-category-heading {
                font-size: 1.4rem;
            }
            .laam-category-link {
                font-size: 0.82rem;
            }
            .enterprise-mobile-table {
                display: block;
            }
            .st-key-enterprise-category-desktop-table,
            .st-key-enterprise-rfm-desktop-table {
                display: none !important;
            }
            div[data-testid="stElementContainer"][class*="st-key-pchip_"] button {
                height: auto !important;
                min-height: 44px !important;
            }
            div[data-testid="stElementContainer"][class*="st-key-cat_label_"] button {
                min-height: 44px !important;
            }
            div[data-testid="stElementContainer"][class*="_add_"] button,
            div[data-testid="stElementContainer"][class*="_rev_"] button,
            div[data-testid="stElementContainer"][class*="_wish_"] button {
                height: auto !important;
                min-height: 44px !important;
            }
        }

        /* Flash Deals Header */
        .flash-deals-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 1.2rem 0 0.75rem 0;
        }
        .flash-deals-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .flash-deals-timer {
            background: #FEF2F2;
            border: 1px solid #FECACA;
            color: #DC2626;
            font-weight: 800;
            font-size: 0.78rem;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        /* Footer */
        .shopkaro-footer {
            background: #0F172A;
            color: #E2E8F0;
            border-radius: 12px;
            padding: 2.2rem 2rem 1.2rem 2rem;
            margin-top: 3rem;
        }
        .shopkaro-footer-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.8rem;
            margin-bottom: 2rem;
        }
        .shopkaro-footer-col h4 {
            color: #FFFFFF;
            font-size: 0.92rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
            letter-spacing: 0.02em;
        }
        .shopkaro-footer-col p, .shopkaro-footer-col li {
            color: #94A3B8;
            font-size: 0.82rem;
            line-height: 1.6;
        }
        .shopkaro-footer-col ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .shopkaro-footer-bottom {
            border-top: 1px solid #1E293B;
            padding-top: 1.2rem;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            font-size: 0.76rem;
            color: #64748B;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sync_live_cart_to_assistant_session() -> None:
    """Sync frontend live_cart directly into the backend conversational session state."""
    try:
        import streamlit as st
        from shopkaro.api.main import serving_container
        if serving_container.assistant is not None:
            sess_id = st.session_state.get("chat_session_id", "shopkaro-consumer-session")
            backend_sess = serving_container.assistant.get_or_create_session(session_id=sess_id)
            backend_sess.cart = [dict(it) for it in st.session_state.get("live_cart", {}).get("items", [])]
    except Exception:
        pass


def _add_item_to_live_cart(item: dict[str, Any], quantity: int = 1) -> None:
    """Add exactly the specified item and quantity to live_cart deterministically."""
    import streamlit as st
    cart = st.session_state.get("live_cart", {"item_count": 0, "total_pkr": 0.0, "items": []})
    items = [dict(it) for it in cart.get("items", [])]
    sku = str(item.get("product_id", "SK-00001"))
    title = str(item.get("title", sku))
    brand = str(item.get("brand", "ShopKaro"))
    price = float(item.get("price_pkr", 0.0))

    found = False
    for it in items:
        if str(it.get("product_id")) == sku:
            new_qty = int(it.get("quantity", 1)) + quantity
            it["quantity"] = new_qty
            it["line_total_pkr"] = float(new_qty) * price
            found = True
            break
    if not found:
        items.append({
            "product_id": sku,
            "title": title,
            "brand": brand,
            "unit_price_pkr": price,
            "quantity": quantity,
            "line_total_pkr": price * quantity,
        })

    new_count = sum(int(it.get("quantity", 1)) for it in items)
    new_total = sum(float(it.get("line_total_pkr", 0.0)) for it in items)
    st.session_state["live_cart"] = {
        "item_count": new_count,
        "total_pkr": new_total,
        "items": items,
    }
    _sync_live_cart_to_assistant_session()


@lru_cache(maxsize=4)
def load_deal_items(limit: int = 3) -> tuple[dict[str, Any], ...]:
    """Largest real discounts on in-stock products, one per category, reviewed products first."""
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        df = con.execute(
            """
            SELECT product_id, title, brand, category, price_pkr, on_sale, discount_pct, avg_rating, review_count
            FROM (
                SELECT p.product_id, p.title, p.brand, p.category, p.price_pkr, p.on_sale, p.discount_pct,
                       r.avg_rating, COALESCE(r.genuine_review_count, 0) AS review_count,
                       ROW_NUMBER() OVER (
                           PARTITION BY p.category
                           ORDER BY p.discount_pct DESC, r.avg_rating DESC NULLS LAST, p.product_id
                       ) AS rn
                FROM product_catalogue p
                LEFT JOIN review_intelligence_summary r USING (product_id)
                WHERE p.on_sale AND p.in_stock AND p.discount_pct > 0
            )
            WHERE rn = 1
            ORDER BY review_count > 0 DESC, discount_pct DESC, product_id
            LIMIT ?
            """,
            [limit],
        ).df()
        # NaN -> None so cards show "No reviews yet" instead of a number
        rows = df.astype(object).where(df.notna(), None).to_dict("records")
        return tuple(rows)
    finally:
        con.close()


ENTERPRISE_VIEW_SLUGS: dict[str, str] = {
    "overview": "📈 Executive Overview & Sales Analytics",
    "supply-chain": "📦 Supply Chain & Demand Forecasting",
    "recommendations": "🎯 Recommendation Engine Analytics",
    "ab-test": "📊 A/B Testing & ABSA Reviews",
    "search": "🔍 Hybrid Search Analytics",
    "system": "⚡ AI System Health & Telemetry",
}
@lru_cache(maxsize=1)
def catalogue_discount_stats() -> tuple[float, int]:
    """(largest discount %, number of in-stock products on sale), for honest banner copy."""
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        row = con.execute(
            "SELECT COALESCE(MAX(discount_pct), 0), COUNT(*) FILTER (WHERE on_sale AND in_stock) FROM product_catalogue"
        ).fetchone()
        return float(row[0]), int(row[1])
    finally:
        con.close()


def _readable_p_values(df: pd.DataFrame) -> pd.DataFrame:
    """Format p-value columns as '3.6e-07' / '0.021' so tables do not show 30-digit decimals."""
    out = df.copy()
    for col in out.columns:
        if "p_value" in col:
            out[col] = out[col].map(
                lambda v: "" if pd.isna(v) else ("< 1e-15" if v < 1e-15 else (f"{v:.1e}" if v < 0.001 else f"{v:.3f}"))
            )
    return out


GRID_PAGE_SIZE = 9


@lru_cache(maxsize=2)
def load_popular_items(limit: int = 18) -> tuple[dict[str, Any], ...]:
    """Best-reviewed in-stock products (rating weighted by review count), round-robin across categories."""
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        df = con.execute(
            """
            SELECT p.product_id, p.title, p.brand, p.category, p.price_pkr, p.on_sale, p.discount_pct,
                   r.avg_rating, r.genuine_review_count AS review_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY p.category
                       ORDER BY r.avg_rating * LN(1 + r.genuine_review_count) DESC, p.product_id
                   ) AS rank_in_category
            FROM product_catalogue p
            JOIN review_intelligence_summary r USING (product_id)
            WHERE p.in_stock
            QUALIFY rank_in_category <= 3
            ORDER BY rank_in_category, r.avg_rating DESC, p.product_id
            LIMIT ?
            """,
            [limit],
        ).df()
        return tuple(df.drop(columns="rank_in_category").to_dict("records"))
    finally:
        con.close()


def _render_real_ecom_card(
    st: Any,
    item: dict[str, Any],
    user_id: int | str,
    card_prefix: str,
) -> None:
    """Render an authentic e-commerce product card with high-resolution photo, prices & Add to Cart."""
    sku = str(item.get("product_id", "SK-00001"))
    title = str(item.get("title", sku))
    brand = str(item.get("brand", "ShopKaro"))
    category = str(item.get("category", "Women's Lawn & Unstitched"))
    price = float(item.get("price_pkr", 0.0))
    on_sale = bool(item.get("on_sale", False))
    disc = int(float(item.get("discount_pct", 0.0)))
    # Real review data only: products without reviews show "No reviews yet", never a made-up rating.
    raw_rating = item.get("avg_rating")
    try:
        rating = float(raw_rating) if raw_rating is not None else None
    except (TypeError, ValueError):
        rating = None
    if rating is not None and rating != rating:  # NaN
        rating = None
    review_cnt = int(item.get("review_count") or 0)
    img_url = get_product_image_url(sku, category)

    if on_sale and disc > 0:
        orig_price = price / max(1.0 - disc / 100.0, 0.5)
        struck_html = f'<span class="ecom-price-struck">PKR {orig_price:,.0f}</span>'
        ribbon_html = f'<span class="ecom-ribbon-sale">SAVE {disc}%</span>'
    elif rating is not None and rating >= 4.5 and review_cnt >= 5:
        struck_html = ""
        ribbon_html = '<span class="ecom-ribbon-sale" style="background:#0F766E;">TOP RATED</span>'
    else:
        struck_html = ""
        ribbon_html = ""

    if rating is not None and review_cnt > 0:
        rating_html = (
            f'<span class="ecom-stars">★ {rating:.1f}</span>'
            f'<span>({review_cnt} review{"s" if review_cnt != 1 else ""})</span>'
        )
    else:
        rating_html = '<span style="color:#6B7280;">No reviews yet</span>'

    explanation = item.get("explanation_roman_urdu") or ""
    tooltip_attr = f'title="{html.escape(str(explanation))}"' if explanation else ""
    title_attr = html.escape(title)
    title = html.escape(title)
    brand = html.escape(brand)

    card_html = (
        f'<div class="ecom-prod-card" {tooltip_attr}>'
        f'<div class="ecom-img-wrap">'
        f'<img src="{img_url}" alt="{title_attr}" loading="lazy"/>'
        f'{ribbon_html}'
        f'<span class="ecom-ribbon-sku">{sku}</span>'
        f'</div>'
        f'<div class="ecom-card-content">'
        f'<div class="ecom-brand-tag">{brand} &bull; {category}</div>'
        f'<div class="ecom-title" title="{title_attr}">{title}</div>'
        f'<div class="ecom-rating-row">{rating_html}</div>'
        f'<div class="ecom-price-wrap">'
        f'<span class="ecom-price-curr">PKR {price:,.0f}</span>'
        f'{struck_html}'
        f'</div>'
        f'<div style="font-size:0.72rem; color:#0F766E; font-weight:600; margin-top:0.35rem; display:flex; align-items:center; gap:0.25rem;">'
        f'🚚 <span>Express Delivery &bull; COD Available</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    b1, b2, b3 = st.columns([1.6, 1.4, 0.7], gap="small")
    with b1:
        if st.button("🛒 Add to Bag", key=f"{card_prefix}_add_{sku}", width="stretch"):
            _add_item_to_live_cart(item, quantity=1)
            st.toast(f"Added {item.get('title', sku)} to your bag!", icon="🛍️")
            st.session_state["sidebar_mode"] = "cart"
            st.session_state["sidebar_state"] = "expanded"
            st.rerun()
    with b2:
        if st.button("⭐ Details", key=f"{card_prefix}_rev_{sku}", width="stretch"):
            st.session_state["inspected_sku"] = sku
            rv = st.session_state.get("recently_viewed", [])
            if sku not in rv:
                rv.insert(0, sku)
                st.session_state["recently_viewed"] = rv[:12]
            st.rerun()
    with b3:
        w_list = st.session_state.get("wishlist", [])
        is_wished = any(str(w.get("product_id")) == sku for w in w_list)
        w_icon = "❤️" if is_wished else "🤍"
        if st.button(w_icon, key=f"{card_prefix}_wish_{sku}", help="Save to Wishlist"):
            if is_wished:
                st.session_state["wishlist"] = [w for w in w_list if str(w.get("product_id")) != sku]
                st.toast(f"Removed {item.get('title', sku)} from wishlist.", icon="🤍")
            else:
                w_list.append(dict(item))
                st.session_state["wishlist"] = w_list
                st.toast(f"Saved {item.get('title', sku)} to wishlist!", icon="❤️")
            st.rerun()


def _sync_sidebar_with_state(st: Any, components: Any = None) -> None:
    """
    Show or hide the sidebar drawer purely with CSS, driven by
    st.session_state["sidebar_state"] ("expanded" or "collapsed").

    No JavaScript and no clicking of Streamlit's hidden native expand/collapse buttons
    (those are hidden by our own CSS, so clicking them was unreliable and the drawer
    could neither close nor open correctly). The page is always configured with
    initial_sidebar_state="expanded"; "closed" simply means display:none.
    """
    want = st.session_state.get("sidebar_state", "collapsed")
    if want == "expanded":
        css = """
        section[data-testid="stSidebar"] {
            display: flex !important;
            visibility: visible !important;
            transform: none !important;
            margin-left: 0 !important;
        }
        """
    else:
        css = """
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"],
        button[data-testid="stExpandSidebarButton"] {
            display: none !important;
        }
        """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def run_streamlit_app() -> None:
    """Render the real-world e-commerce storefront & enterprise operations console."""
    import streamlit as st
    import streamlit.components.v1 as components

    if "sidebar_state" not in st.session_state:
        st.session_state["sidebar_state"] = "collapsed"
    if "sidebar_mode" not in st.session_state:
        st.session_state["sidebar_mode"] = "menu"

    st.set_page_config(
        page_title="ShopKaro.pk — Pakistan's AI E-Commerce Marketplace",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_real_ecommerce_css(st)

    # Fresh cloud deployment: fetch the prebuilt database + models once (see shopkaro.data.bootstrap).
    if not data_ready():
        bar = st.progress(0.0, text="First start: downloading ShopKaro data (about a minute)...")
        # Not wrapped in st.cache_resource: Streamlit forbids updating an outside element (the progress bar) from a
        # cached function. ensure_data() uses its own lock, so concurrent visitors download only once.
        try:
            ensure_data(progress=lambda f: bar.progress(min(f, 1.0), text=f"Downloading data... {f:.0%}"))
        except Exception as exc:  # show the reason instead of a raw traceback
            bar.empty()
            st.error(f"Could not load the ShopKaro data: {exc}")
            st.stop()
        bar.empty()

    # FIX: sidebar open/close now follows Python state instead of listening to clicks.
    _sync_sidebar_with_state(st, components)

    # Session State defaults
    if "chat_session_id" not in st.session_state:
        import uuid
        st.session_state["chat_session_id"] = f"shopkaro-sess-{uuid.uuid4().hex[:8]}"
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": (
                    "Assalam-o-Alaikum! Welcome to **ShopKaro AI Assistant**. "
                    "Aap mujh se Urdu, Roman Urdu, ya English mein kuch bhi pooch sakte hain — "
                    "jaise *'Ammi ke liye Eid gift under 3000'*, *'compare pehla aur doosra'*, ya *'order track karo'*."
                ),
                "tools": [],
                "verified": True,
            }
        ]
    if "live_cart" not in st.session_state:
        st.session_state["live_cart"] = {"item_count": 0, "total_pkr": 0.0, "items": []}
    if "active_search_query" not in st.session_state:
        st.session_state["active_search_query"] = ""
    if "header_search_input_widget" not in st.session_state:
        st.session_state["header_search_input_widget"] = st.session_state["active_search_query"]
    if "wishlist" not in st.session_state:
        st.session_state["wishlist"] = []
    if "recently_viewed" not in st.session_state:
        st.session_state["recently_viewed"] = []
    if "delivery_city" not in st.session_state:
        st.session_state["delivery_city"] = "Karachi"
    if "payment_method" not in st.session_state:
        st.session_state["payment_method"] = "Cash on Delivery (COD)"
    # Callback to safely update category and search query before widgets instantiate
    def _apply_filter_cb(cat: str, q: str, dept: str | None = None) -> None:
        st.session_state["customer_filter_cat"] = cat
        st.session_state["active_search_query"] = q
        if dept:
            st.session_state["drawer_dept"] = dept
        try:
            st.session_state["header_search_input_widget"] = q
        except Exception:
            pass

    @st.dialog("🛍️ Your Shopping Bag")
    def _open_shopping_bag_dialog() -> None:
        cart = st.session_state.get("live_cart", {"item_count": 0, "total_pkr": 0.0, "items": []})
        items = cart.get("items", [])
        total_pkr = cart.get("total_pkr", 0.0)

        st.markdown(
            """
            <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 0.65rem 0.9rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.1rem;">🚚</span>
                <span style="font-size: 0.85rem; font-weight: 700; color: #065F46;">Free Express Delivery Across Pakistan Applied!</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not items:
            st.markdown(
                """
                <div style="text-align: center; padding: 2rem 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 0.5rem;">🛍️</div>
                    <h4 style="color: #111827; font-weight: 700; margin-bottom: 0.35rem;">Your Shopping Bag is empty</h4>
                    <p style="color: #6B7280; font-size: 0.88rem; margin-bottom: 1.25rem;">Explore our curated Pakistani designer collections or ask our AI Concierge for recommendations!</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("✨ Browse Collections / Ask AI", width="stretch", key="dlg_bag_explore_btn", type="primary"):
                st.rerun()
            return

        st.markdown(f"**Items in Bag ({len(items)})**")
        st.markdown("<hr style='margin: 0.4rem 0 0.8rem 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)

        for idx, itm in enumerate(items):
            c_info, c_action = st.columns([4, 1], vertical_alignment="center")
            with c_info:
                brand_str = f"[{itm['brand']}]" if itm.get('brand') else ""
                st.markdown(
                    f"""
                    <div style="line-height: 1.35;">
                        <span style="font-size: 0.92rem; font-weight: 700; color: #111827;">{itm['product_id']}</span>
                        <span style="font-size: 0.78rem; font-weight: 600; color: #0F766E; margin-left: 0.35rem;">{brand_str}</span><br/>
                        <span style="font-size: 0.82rem; color: #4B5563;">Qty: <b>{itm['quantity']}</b> &bull; PKR {itm['line_total_pkr']:,.0f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_action:
                if st.button("🗑️", key=f"del_cart_item_{idx}", help="Remove from bag"):
                    new_items = [it for j, it in enumerate(items) if j != idx]
                    new_total = sum(it.get("line_total_pkr", 0.0) for it in new_items)
                    new_count = sum(it.get("quantity", 1) for it in new_items)
                    st.session_state["live_cart"] = {
                        "item_count": new_count,
                        "total_pkr": new_total,
                        "items": new_items,
                    }
                    _sync_live_cart_to_assistant_session()
                    st.rerun()
            st.markdown("<hr style='margin: 0.4rem 0 0.6rem 0; border-color: #F3F4F6;'/>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style="background: #F9FAFB; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.8rem 0 0.5rem 0; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.95rem; font-weight: 700; color: #1F2937;">Total Payable:</span>
                <span style="font-size: 1.25rem; font-weight: 800; color: #0F766E;">PKR {total_pkr:,.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(DEMO_CHECKOUT_NOTICE)
        st.markdown("**Demo payment method (not processed):**")
        pay_method = st.selectbox(
            "Payment Method:",
            [
                "Cash on Delivery (COD) — demo only",
                "JazzCash Mobile Wallet — demo only",
                "EasyPaisa — demo only",
                "Debit / Credit Card — demo only",
            ],
            key="dlg_pay_method_sel",
            label_visibility="collapsed",
        )
        st.session_state["payment_method"] = pay_method

        btn_chk, btn_clr = st.columns([2, 1])
        with btn_chk:
            if st.button("Preview Demo Checkout", width="stretch", key="dlg_checkout_btn", type="primary"):
                st.warning(DEMO_CHECKOUT_NOTICE)
        with btn_clr:
            if st.button("Clear Bag", width="stretch", key="dlg_clear_cart_btn"):
                st.session_state["live_cart"] = {"item_count": 0, "total_pkr": 0.0, "items": []}
                _sync_live_cart_to_assistant_session()
                st.rerun()

    @st.dialog("❤️ Your Saved Wishlist")
    def _open_wishlist_dialog() -> None:
        w_list = st.session_state.get("wishlist", [])
        if not w_list:
            st.markdown(
                """
                <div style="text-align: center; padding: 2rem 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 0.5rem;">🤍</div>
                    <h4 style="color: #111827; font-weight: 700; margin-bottom: 0.35rem;">Your Wishlist is empty</h4>
                    <p style="color: #6B7280; font-size: 0.88rem; margin-bottom: 1.25rem;">Browse Pakistani designer collections and click the heart icon on any product to save it here!</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        st.markdown(f"**Saved Wishlist Items ({len(w_list)})**")
        st.markdown("<hr style='margin: 0.4rem 0 0.8rem 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)
        for idx_w, w_item in enumerate(w_list):
            w_sku = str(w_item.get("product_id", f"SK-{idx_w}"))
            w_title = str(w_item.get("title", w_sku))
            w_price = float(w_item.get("price_pkr", 0.0))
            w_brand = str(w_item.get("brand", "ShopKaro"))

            wc_info, wc_act1, wc_act2 = st.columns([3.2, 1.8, 0.6], vertical_alignment="center", gap="small")
            with wc_info:
                st.markdown(
                    f"""
                    <div style="line-height: 1.35;">
                        <span style="font-size: 0.88rem; font-weight: 700; color: #111827;">{w_title}</span><br/>
                        <span style="font-size: 0.78rem; color: #6B7280;">{w_brand} &bull; <b style="color:#0F766E;">PKR {w_price:,.0f}</b></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with wc_act1:
                if st.button("🛒 Move to Bag", key=f"w_move_{w_sku}_{idx_w}", width="stretch"):
                    _add_item_to_live_cart(w_item, quantity=1)
                    st.session_state["wishlist"] = [it for it in w_list if it.get("product_id") != w_sku]
                    st.toast(f"Moved {w_title} to your bag!", icon="🛍️")
                    st.session_state["sidebar_mode"] = "cart"
                    st.session_state["sidebar_state"] = "expanded"
                    st.rerun()
            with wc_act2:
                if st.button("🗑️", key=f"w_del_{w_sku}_{idx_w}", help="Remove from wishlist"):
                    st.session_state["wishlist"] = [it for it in w_list if it.get("product_id") != w_sku]
                    st.rerun()
            st.markdown("<hr style='margin: 0.35rem 0 0.5rem 0; border-color: #F3F4F6;'/>", unsafe_allow_html=True)

        if st.button("Clear Wishlist", key="w_clear_all_btn", width="stretch"):
            st.session_state["wishlist"] = []
            st.rerun()

    @st.dialog("👤 Account & Profile Manager")
    def _open_login_dialog() -> None:
        acc_tab1, acc_tab2, acc_tab3 = st.tabs(["👤 Profile & Rewards", "📦 Order History (3)", "⚙️ Persona Simulation"])

        with acc_tab1:
            st.caption("Sample customer profile for demonstration only; not a live account.")
            st.markdown(
                """
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:0.95rem; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="font-weight:800; font-size:1.05rem; color:#065F46;">Hamza Khan</div>
                        <span style="background:#DCFCE7; color:#15803D; font-weight:800; font-size:0.75rem; padding:0.2rem 0.6rem; border-radius:999px;">VIP GOLD MEMBER</span>
                    </div>
                    <div style="font-size:0.82rem; color:#4B5563; margin-top:0.4rem;">📍 <b>Delivery Address:</b> House 42-B, Block 4, Clifton, Karachi</div>
                    <div style="font-size:0.82rem; color:#4B5563; margin-top:0.2rem;">📱 <b>Mobile:</b> +92 300 8274419 &bull; COD Verified Customer</div>
                    <div style="font-size:0.85rem; color:#0F766E; font-weight:700; margin-top:0.5rem;">🪙 <b>450 ShopKaro Rewards Coins</b> Available (Worth PKR 450)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with acc_tab2:
            st.markdown("##### 📦 Recent Consignments & Past Orders")
            st.caption("Example order history for demonstration only; not linked to this profile.")
            orders_mock = [
                ("ORD-1002", "Leopard Express", "1x Embroidered Festive Kurta", 3450, "⚡ Out for Delivery Today", "#065F46", "#ECFDF5"),
                ("ORD-1001", "TCS Express", "2x Sapphire Luxury Lawn 3-Pc", 12800, "✅ Delivered (Karachi)", "#1E40AF", "#EFF6FF"),
                ("ORD-0988", "Trax Logistics", "1x Chapter 13 Velvet Khussa", 6500, "✅ Delivered (Lahore)", "#1E40AF", "#EFF6FF"),
            ]
            for ord_id, cr, itm_desc, amt, st_lbl, col, bg in orders_mock:
                st.markdown(
                    f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:0.75rem 0.9rem; margin-bottom:0.6rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:800; font-size:0.88rem; color:#111827;">{ord_id} &bull; <span style="font-weight:600; color:#64748B;">{cr}</span></span>
                            <span style="background:{bg}; color:{col}; font-weight:700; font-size:0.74rem; padding:0.2rem 0.55rem; border-radius:6px;">{st_lbl}</span>
                        </div>
                        <div style="font-size:0.8rem; color:#4B5563; margin-top:0.3rem;">{itm_desc} &bull; <b>PKR {amt:,.0f}</b> (Cash on Delivery)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with acc_tab3:
            st.markdown("**Switch Customer Persona (For AI Testing):**")
            selected_persona_name = st.selectbox(
                "Customer Persona:",
                list(persona_map.values()),
                format_func=lambda x: f"{x[0]} — {x[1]}",
                key="dlg_persona_selector",
                label_visibility="collapsed",
            )
            new_uid = next(uid for uid, p in persona_map.items() if p == selected_persona_name)
            st.markdown("**Active Shopping Occasion:**")
            new_occasion = st.selectbox(
                "Occasion:",
                ["Eid", "Shaadi / Wedding", "Ramadan Preparation", "Casual Daily"],
                key="dlg_occasion_selector",
                label_visibility="collapsed",
            )
            if st.button("Apply Profile Settings", type="primary", width="stretch"):
                st.session_state["portal_selected_uid"] = new_uid
                st.session_state["portal_selected_occasion"] = new_occasion
                st.toast("Profile settings updated!", icon="👤")
                st.rerun()

    @st.dialog("📞 Contact ShopKaro Support")
    def _open_contact_dialog() -> None:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.25rem;">
                <div style="font-size: 2.2rem; margin-bottom: 0.25rem;">📞</div>
                <h3 style="margin: 0; font-weight: 800; color: #111827;">We're Here to Help</h3>
                <p style="color: #6B7280; font-size: 0.85rem; margin-top: 0.25rem;">Our concierges and stylists are available 24/7 across Pakistan</p>
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
                <div style="font-weight: 700; color: #111827; font-size: 0.88rem;">💬 WhatsApp Concierge (Fastest)</div>
                <div style="color: #0F766E; font-weight: 800; font-size: 1.05rem; margin-top: 0.15rem;">+92 300 7467527 (SHOPKARO)</div>
                <div style="color: #6B7280; font-size: 0.76rem; margin-top: 0.15rem;">Instant order updates, stylist advice, and size help</div>
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
                <div style="font-weight: 700; color: #111827; font-size: 0.88rem;">☎️ UAN Helpline</div>
                <div style="color: #111827; font-weight: 800; font-size: 1.05rem; margin-top: 0.15rem;">021-111-SHOP-PK (7467)</div>
                <div style="color: #6B7280; font-size: 0.76rem; margin-top: 0.15rem;">Mon - Sat, 9:00 AM - 9:00 PM PKT</div>
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem 1rem;">
                <div style="font-weight: 700; color: #111827; font-size: 0.88rem;">✉️ Customer Care Email</div>
                <div style="color: #0F766E; font-weight: 700; font-size: 0.95rem; margin-top: 0.15rem;">support@shopkaro.pk</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    @st.dialog("🏪 Retail Store Outlets")
    def _open_stores_dialog() -> None:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.25rem;">
                <div style="font-size: 2.2rem; margin-bottom: 0.25rem;">🏪</div>
                <h3 style="margin: 0; font-weight: 800; color: #111827;">Our Flagship Stores</h3>
                <p style="color: #6B7280; font-size: 0.85rem; margin-top: 0.25rem;">Visit our studios for luxury try-on & click-and-collect</p>
            </div>
            <div style="border-left: 3px solid #0F766E; background: #F8FAFC; padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 800; color: #111827; font-size: 0.92rem;">📍 Karachi — Dolmen Mall Clifton</div>
                <div style="font-size: 0.8rem; color: #4B5563; margin-top: 0.2rem;">Ground Floor, Ocean Wing &bull; Daily 11:00 AM – 11:00 PM</div>
            </div>
            <div style="border-left: 3px solid #0F766E; background: #F8FAFC; padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 800; color: #111827; font-size: 0.92rem;">📍 Lahore — MM Alam Road</div>
                <div style="font-size: 0.8rem; color: #4B5563; margin-top: 0.2rem;">Gulberg III (Near Mini Market) &bull; Daily 11:00 AM – 11:00 PM</div>
            </div>
            <div style="border-left: 3px solid #0F766E; background: #F8FAFC; padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 800; color: #111827; font-size: 0.92rem;">📍 Islamabad — Beverly Centre</div>
                <div style="font-size: 0.8rem; color: #4B5563; margin-top: 0.2rem;">Blue Area &bull; Daily 11:00 AM – 10:30 PM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    @st.dialog("🚚 Track Your Order")
    def _open_order_tracking_dialog() -> None:
        st.info("Sample tracking only. This shipment is not connected to a real order or carrier.")
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.25rem;">
                <div style="font-size: 2.2rem; margin-bottom: 0.25rem;">🚚</div>
                <h3 style="margin: 0; font-weight: 800; color: #111827;">Sample Order Tracking (Demo)</h3>
                <p style="color: #6B7280; font-size: 0.85rem; margin-top: 0.25rem;">Example consignment: <b>ORD-1002</b> &bull; Leopard Express</p>
            </div>
            <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.6rem;">
                <span style="font-size: 1.3rem;">⚡</span>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 800; color: #065F46;">Example status: Out for Delivery</div>
                    <div style="font-size: 0.75rem; color: #047857;">Live carrier updates are not connected.</div>
                </div>
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.85rem 1rem; font-size: 0.82rem; color: #374151; line-height: 1.6;">
                <div><b>Example destination:</b> Clifton Block 4, Karachi</div>
                <div><b>Example payment:</b> Cash on Delivery (COD) — PKR 3,450</div>
                <div><b>Example package:</b> 1x Embroidered Pakistani Lawn 3-Piece</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if "inspected_sku" not in st.session_state:
        st.session_state["inspected_sku"] = None

    # Models load in a background thread (started at the end of this run, once per server process) so the
    # storefront renders immediately; only the parts that need a model wait for it.
    snapshot = load_dashboard_snapshot()
    cart_state = st.session_state["live_cart"]

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # 1. LAAM Top Slim Black Announcement Bar
    st.markdown(
        """
        <div class="laam-top-ticker">
            <span>🚚 Free Express Delivery Across Pakistan &bull; Cash on Delivery Available</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # 2. ShopKaro Unified Single-Row Luxury Navigation Bar
    # Logo, Search Bar, Ask AI Button, and Action Icons all in the SAME ROW
    # -------------------------------------------------------------------------
    nav_brand, nav_search, nav_ai, nav_wish, nav_cart = st.columns(
        [2.3, 4.2, 1.4, 0.55, 0.55],
        vertical_alignment="center",
        gap="small",
    )

    with nav_brand:
        ham_c, logo_c = st.columns([0.45, 3.2], vertical_alignment="center", gap="small")
        with ham_c:
            st.markdown('<div class="shopkaro-ham-anchor"></div>', unsafe_allow_html=True)
            if st.button("☰", key="nav_hamburger_toggle_btn", help="Open Navigation Drawer"):
                st.session_state["sidebar_mode"] = "menu"
                st.session_state["sidebar_state"] = "expanded"
                st.rerun()
        with logo_c:
            st.markdown(
                """
                <a href="?" target="_self" class="shopkaro-brand-logo">
                    <svg width="30" height="30" viewBox="0 0 40 40" fill="none" style="flex-shrink:0;">
                        <rect width="40" height="40" rx="9" fill="#0F766E"/>
                        <rect x="9" y="14" width="22" height="18" rx="3" stroke="#FFFFFF" stroke-width="2.2" fill="none"/>
                        <path d="M14 14V11C14 9.34 15.34 8 17 8H23C24.66 8 26 8.34 26 11V14" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round"/>
                        <path d="M15 19C15 21.76 17.24 24 20 24C22.76 24 25 21.76 25 19" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round"/>
                    </svg>
                    <div class="shopkaro-logo-text">
                        <span class="shopkaro-logo-main">ShopKaro</span>
                        <span class="shopkaro-logo-badge">.PK</span>
                    </div>
                </a>
                """,
                unsafe_allow_html=True,
            )

    with nav_search:
        st.markdown('<div class="shopkaro-search-box"></div>', unsafe_allow_html=True)
        header_search = st.text_input(
            "Search ShopKaro",
            value=st.session_state.get("active_search_query", ""),
            placeholder="Search for 'party wear lehenga'...",
            label_visibility="collapsed",
            key="header_search_input_widget",
        )
        st.session_state["active_search_query"] = header_search

    with nav_ai:
        st.markdown('<div class="shopkaro-ai-box"></div>', unsafe_allow_html=True)
        if st.button("✨ Ask AI", key="header_ask_ai_btn", width="stretch"):
            q_to_ask = (st.session_state.get("header_search_input_widget") or st.session_state.get("active_search_query", "")).strip()
            if q_to_ask:
                st.session_state["chat_history"].append({"role": "user", "content": q_to_ask})
                _wait_for_models(st)
                c_out = chat_assistant_endpoint(
                    ChatRequest(
                        message=q_to_ask,
                        session_id=st.session_state["chat_session_id"],
                        user_id=st.session_state.get("portal_selected_uid", DEFAULT_DEMO_USER),
                    )
                )
                st.session_state["live_cart"] = c_out["cart"]
                st.session_state["chat_history"].append(
                    {
                        "role": "assistant",
                        "content": c_out["assistant_response"],
                        "intent": c_out["detected_intent"],
                        "tools": c_out["tool_calls"],
                        "tool_outputs": c_out["tool_outputs"],
                        "verified": c_out["hallucination_audit"]["passed_zero_hallucination_check"],
                    }
                )
            st.session_state["sidebar_mode"] = "ai_chat"
            st.session_state["sidebar_state"] = "expanded"
            st.rerun()

    with nav_wish:
        w_cnt = len(st.session_state.get("wishlist", []))
        st.markdown(
            f'<div class="header-action-container shopkaro-wish-box">'
            f'<span class="header-badge-bubble badge-red">{w_cnt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("♡", key="header_nav_wish_btn", help="View Saved Wishlist"):
            _open_wishlist_dialog()

    with nav_cart:
        header_cart_count = cart_state.get("item_count", 0)
        st.markdown(
            f'<div class="header-action-container shopkaro-bag-box">'
            f'<span class="header-badge-bubble badge-emerald">{header_cart_count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("🛍", key="header_nav_bag_btn", help="View Shopping Bag"):
            st.session_state["sidebar_mode"] = "cart"
            st.session_state["sidebar_state"] = "expanded"
            st.rerun()

    # -------------------------------------------------------------------------
    # Sidebar: Mode Selector & Active Account Settings
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Mode State Initialization
    # -------------------------------------------------------------------------
    if "portal_role" not in st.session_state:
        st.session_state["portal_role"] = "🛍️ Customer Storefront"
    if "customer_filter_cat" not in st.session_state:
        st.session_state["customer_filter_cat"] = "All Categories"
    if "customer_filter_budget" not in st.session_state:
        st.session_state["customer_filter_budget"] = 60000

    # Real customers from the interaction data (recommendations use their actual history).
    # Third value = curated search persona used for personalised search re-ranking.
    persona_map = {
        DEFAULT_DEMO_USER: ("🌙 Eid & Festive Lawn Shopper", "Eid & Festive Lawn Shoppers", "PERSONA_LUXURY_VIP"),
        "USR-368401": ("📱 Smartphone & Electronics Buyer", "Loyal Electronics & VIP Buyers", "PERSONA_LUXURY_VIP"),
        "USR-1398811": ("🎒 School-Supplies Parent", "Bargain Hunters & Cart Hesitators", "PERSONA_BUDGET_HUNTER"),
        "new-visitor": ("🆕 New Visitor (cold start)", "Cold-Start New Visitor", None),
    }

    # -------------------------------------------------------------------------
    # Sidebar: Role-Based Portal Switcher
    # -------------------------------------------------------------------------
    with st.sidebar:
        # Default Portal Selection; a shareable link such as ?view=supply-chain opens that console view directly.
        if "deep_link_applied" not in st.session_state:
            st.session_state["deep_link_applied"] = True
            linked = ENTERPRISE_VIEW_SLUGS.get(str(st.query_params.get("view", "")).lower())
            if linked:
                st.session_state["portal_role"] = "🏢 Merchant & Enterprise Hub"
                st.session_state["ent_view"] = linked
        if "portal_role" not in st.session_state:
            st.session_state["portal_role"] = "🛍️ Customer Storefront"
        portal_choice = st.session_state["portal_role"]
        if portal_choice != "🏢 Merchant & Enterprise Hub" and "view" in st.query_params:
            del st.query_params["view"]

        if portal_choice == "🛍️ Customer Storefront":
            selected_uid = st.session_state.get("portal_selected_uid", DEFAULT_DEMO_USER)
            selected_occasion = st.session_state.get("portal_selected_occasion", "Eid")
            sidebar_mode = st.session_state.get("sidebar_mode", "menu")

            if sidebar_mode == "cart":
                # -------------------------------------------------------------
                # Sliding Cart Sidebar Menu (Drawer) - Docked to Right Edge
                # -------------------------------------------------------------
                st.markdown('<div class="shopkaro-cart-drawer-active"></div>', unsafe_allow_html=True)
                cart = st.session_state.get("live_cart", {"item_count": 0, "total_pkr": 0.0, "items": []})
                items = list(cart.get("items", []))
                total_pkr = float(cart.get("total_pkr", 0.0))
                item_count = int(cart.get("item_count", 0))

                # Cart Header with Badge & Close Button
                col_cart_hdr, col_cart_cls = st.columns([4, 1], vertical_alignment="center")
                with col_cart_hdr:
                    st.markdown(
                        f"""
                        <div style="display:flex; align-items:center; gap:0.45rem;">
                            <span style="font-size:1.25rem;">🛍️</span>
                            <span style="font-weight:800; font-size:0.95rem; letter-spacing:0.04em; color:#111827; text-transform:uppercase;">YOUR BAG</span>
                            <span style="background:#0F766E; color:#FFFFFF; font-size:0.65rem; font-weight:800; padding:0.12rem 0.45rem; border-radius:999px;">{item_count}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_cart_cls:
                    st.markdown('<div class="drawer-close-anchor"></div>', unsafe_allow_html=True)
                    if st.button("✕", key="cart_close_drawer_btn", help="Close Cart Drawer"):
                        st.session_state["sidebar_state"] = "collapsed"
                        st.session_state["sidebar_mode"] = "menu"
                        st.rerun()

                # Free Express Delivery Banner
                st.markdown(
                    """
                    <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 0.5rem 0.75rem; margin: 0.45rem 0 0.85rem 0; display: flex; align-items: center; gap: 0.45rem;">
                        <span style="font-size: 1rem;">🚚</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #065F46;">Free Express Delivery Across Pakistan Active!</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not items:
                    st.markdown(
                        """
                        <div style="text-align: center; padding: 2.5rem 1rem;">
                            <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🛍️</div>
                            <h4 style="color: #111827; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem;">Your Bag is empty</h4>
                            <p style="color: #6B7280; font-size: 0.82rem; margin-bottom: 1.25rem;">Explore curated unstitched lawn, festive bridal & luxury perfumes from top designers.</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("✨ Browse Collections", key="cart_empty_browse_btn", width="stretch", type="primary"):
                        st.session_state["sidebar_mode"] = "menu"
                        st.rerun()
                else:
                    st.markdown(f"<div style='font-size:0.75rem; font-weight:800; color:#6B7280; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.6rem;'>Added Items ({item_count})</div>", unsafe_allow_html=True)

                    for idx, itm in enumerate(items):
                        pid = str(itm.get("product_id", f"SK-{idx}"))
                        title = str(itm.get("title", pid))
                        brand = str(itm.get("brand", "ShopKaro"))
                        qty = int(itm.get("quantity", 1))
                        line_total = float(itm.get("line_total_pkr", 0.0))
                        unit_price = float(itm.get("unit_price_pkr", line_total / max(1, qty)))

                        st.markdown(
                            f"""
                            <div class="cart-item-card">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.35rem;">
                                    <div style="padding-right:0.5rem;">
                                        <div class="cart-item-title">{title}</div>
                                        <div class="cart-item-meta">{brand} &bull; PKR {unit_price:,.0f} each</div>
                                    </div>
                                    <div class="cart-item-price">
                                        PKR {line_total:,.0f}
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Controls row: [-] [Qty: N] [+] [🗑️ Remove]
                        q1, q2, q3, q4 = st.columns([0.8, 1.2, 0.8, 1.8], gap="small", vertical_alignment="center")
                        with q1:
                            if st.button("−", key=f"cart_dec_{idx}", help="Decrease quantity"):
                                if qty > 1:
                                    items[idx]["quantity"] = qty - 1
                                    items[idx]["line_total_pkr"] = (qty - 1) * unit_price
                                else:
                                    items.pop(idx)
                                new_tot = sum(float(it.get("line_total_pkr", 0.0)) for it in items)
                                new_cnt = sum(int(it.get("quantity", 1)) for it in items)
                                st.session_state["live_cart"] = {"item_count": new_cnt, "total_pkr": new_tot, "items": items}
                                _sync_live_cart_to_assistant_session()
                                st.rerun()
                        with q2:
                            st.markdown(f"<div style='text-align:center; font-size:0.82rem; font-weight:700; color:#1F2937;'>Qty: {qty}</div>", unsafe_allow_html=True)
                        with q3:
                            if st.button("+", key=f"cart_inc_{idx}", help="Increase quantity"):
                                items[idx]["quantity"] = qty + 1
                                items[idx]["line_total_pkr"] = (qty + 1) * unit_price
                                new_tot = sum(float(it.get("line_total_pkr", 0.0)) for it in items)
                                new_cnt = sum(int(it.get("quantity", 1)) for it in items)
                                st.session_state["live_cart"] = {"item_count": new_cnt, "total_pkr": new_tot, "items": items}
                                _sync_live_cart_to_assistant_session()
                                st.rerun()
                        with q4:
                            if st.button("🗑️ Remove", key=f"cart_del_{idx}", help="Remove from bag"):
                                items.pop(idx)
                                new_tot = sum(float(it.get("line_total_pkr", 0.0)) for it in items)
                                new_cnt = sum(int(it.get("quantity", 1)) for it in items)
                                st.session_state["live_cart"] = {"item_count": new_cnt, "total_pkr": new_tot, "items": items}
                                _sync_live_cart_to_assistant_session()
                                st.toast(f"Removed {title} from your bag.", icon="🗑️")
                                st.rerun()

                        st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

                    # Dynamic Total Calculation Summary Box
                    st.markdown(
                        f"""
                        <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:10px; padding:0.85rem; margin:1rem 0 1.15rem 0;">
                            <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#4B5563; margin-bottom:0.35rem;">
                                <span>Subtotal ({item_count} items):</span>
                                <span style="font-weight:700; color:#111827;">PKR {total_pkr:,.0f}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#4B5563; margin-bottom:0.35rem;">
                                <span>Delivery Charges:</span>
                                <span style="font-weight:700; color:#0F766E;">FREE (Express)</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#4B5563; margin-bottom:0.5rem;">
                                <span>Cash on Delivery (COD) Fee:</span>
                                <span style="font-weight:600; color:#111827;">PKR 0.00</span>
                            </div>
                            <div style="border-top:1.5px dashed #D1D5DB; margin:0.45rem 0; padding-top:0.5rem; display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:0.92rem; font-weight:800; color:#111827;">TOTAL DUE:</span>
                                <span style="font-size:1.25rem; font-weight:800; color:#0F766E;">PKR {total_pkr:,.0f}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    chk_col1, chk_col2 = st.columns([2.2, 1.0], gap="small")
                    with chk_col1:
                        st.info(DEMO_CHECKOUT_NOTICE)
                        if st.button("Preview Demo Checkout", key="cart_sidebar_checkout_btn", width="stretch", type="primary"):
                            st.warning(DEMO_CHECKOUT_NOTICE)
                    with chk_col2:
                        if st.button("Clear Bag", key="cart_sidebar_clear_btn", width="stretch"):
                            st.session_state["live_cart"] = {"item_count": 0, "total_pkr": 0.0, "items": []}
                            _sync_live_cart_to_assistant_session()
                            st.toast("Bag cleared.", icon="🧹")
                            st.rerun()

            elif sidebar_mode == "ai_chat":
                # -------------------------------------------------------------
                # Sliding AI Concierge Drawer - Docked to Right Edge
                # -------------------------------------------------------------
                st.markdown('<div class="shopkaro-ai-drawer-active"></div>', unsafe_allow_html=True)

                # AI Concierge Header with Badge & Close Button
                col_ai_hdr, col_ai_cls = st.columns([4, 1], vertical_alignment="center")
                with col_ai_hdr:
                    st.markdown(
                        """
                        <div style="display:flex; align-items:center; gap:0.45rem;">
                            <span style="font-size:1.25rem;">💬</span>
                            <span style="font-weight:800; font-size:0.95rem; letter-spacing:0.04em; color:#111827; text-transform:uppercase;">AI CONCIERGE</span>
                            <span style="background:#0F766E; color:#FFFFFF; font-size:0.65rem; font-weight:800; padding:0.12rem 0.45rem; border-radius:999px;">URDULISH LIVE</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_ai_cls:
                    st.markdown('<div class="drawer-close-anchor"></div>', unsafe_allow_html=True)
                    if st.button("✕", key="ai_close_drawer_btn", help="Close AI Concierge Drawer"):
                        st.session_state["sidebar_state"] = "collapsed"
                        st.session_state["sidebar_mode"] = "menu"
                        st.rerun()

                # Welcoming sub-banner
                st.markdown(
                    """
                    <div style="background:#F0FDFA; border:1px solid #99F6E4; border-radius:8px; padding:0.55rem 0.75rem; margin:0.45rem 0 0.75rem 0; font-size:0.78rem; color:#0F766E; line-height:1.4;">
                        ✨ <b>Assalam-o-Alaikum!</b> Poochiye Roman Urdu ya English mein — gifts under budget, outfit comparisons, tracking, ya styling advice!
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Quick Suggested Prompts (Chips)
                st.markdown("<div style='font-size:0.72rem; font-weight:800; color:#6B7280; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.35rem;'>⚡ Quick Suggestions:</div>", unsafe_allow_html=True)
                chips = [
                    ("🎁 Gift under 3000", "Ammi ke liye Eid gift chahiye, 3000 tak"),
                    ("👗 Compare dresses", "Pehla aur doosra compare karo"),
                    ("⭐ Check reviews", "SK-00010 ke reviews kaise hain?"),
                    ("🚚 Track order", "Mera order ORD-1001 kahan pohancha?"),
                ]
                ch_c1, ch_c2 = st.columns(2, gap="small")
                clicked_chip_text = None
                for idx_ch, (label, query_text) in enumerate(chips):
                    target_col = ch_c1 if idx_ch % 2 == 0 else ch_c2
                    with target_col:
                        if st.button(label, key=f"ai_chip_btn_{idx_ch}", width="stretch"):
                            clicked_chip_text = query_text

                # Chat input in drawer
                drawer_chat_input = st.chat_input("Poochiye Roman Urdu ya English mein...", key="ai_drawer_chat_input")
                active_msg = clicked_chip_text or drawer_chat_input

                if active_msg:
                    st.session_state["chat_history"].append({"role": "user", "content": active_msg})
                    _wait_for_models(st)
                    c_out = chat_assistant_endpoint(
                        ChatRequest(
                            message=active_msg,
                            session_id=st.session_state["chat_session_id"],
                            user_id=selected_uid,
                        )
                    )
                    st.session_state["live_cart"] = c_out["cart"]
                    st.session_state["chat_history"].append(
                        {
                            "role": "assistant",
                            "content": c_out["assistant_response"],
                            "intent": c_out["detected_intent"],
                            "tools": c_out["tool_calls"],
                            "tool_outputs": c_out["tool_outputs"],
                            "verified": c_out["hallucination_audit"]["passed_zero_hallucination_check"],
                        }
                    )
                    st.rerun()

                st.markdown("<hr style='margin:0.5rem 0 0.75rem 0; border-color:#F1F5F9;'/>", unsafe_allow_html=True)

                # Render Conversation Messages
                msg_history = st.session_state.get("chat_history", [])
                if not msg_history:
                    st.markdown(
                        """
                        <div style="text-align:center; padding:1.5rem 0.5rem; color:#9CA3AF; font-size:0.82rem;">
                            No messages yet. Ask a question or tap one of the quick suggestions above!
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    for msg in msg_history:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
                            if msg["role"] == "assistant" and msg.get("tools"):
                                tools_str = ", ".join(f"`{t}`" for t in msg["tools"])
                                st.caption(f"Executed Tools: {tools_str} &bull; **100% Grounded Catalogue Verification**")
                                if msg.get("tool_outputs"):
                                    with st.expander("Inspect Grounded Tool JSON"):
                                        st.json(msg["tool_outputs"])

                st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("🧹 Reset Conversation", key="ai_drawer_clear_btn", width="stretch"):
                    st.session_state["chat_history"] = []
                    st.toast("Conversation cleared.", icon="🧹")
                    st.rerun()

            else:
                # -------------------------------------------------------------
                # Drawer Top Header: Clean Close Button (Top-Left Minimalist)
                # -------------------------------------------------------------
                col_close, _ = st.columns([1, 4], vertical_alignment="center")
                with col_close:
                    st.markdown('<div class="drawer-close-anchor"></div>', unsafe_allow_html=True)
                    if st.button("✕", key="drawer_close_toggle_btn", help="Close Navigation Drawer"):
                        st.session_state["sidebar_state"] = "collapsed"
                        st.rerun()

                st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

                # -------------------------------------------------------------
                # Top 3 Action Cards (Image 2 style: LOGIN, CONTACT US, STORES)
                # -------------------------------------------------------------
                card_c1, card_c2, card_c3 = st.columns(3, gap="small")
                with card_c1:
                    st.markdown('<div class="drawer-card-anchor drawer-card-login"></div>', unsafe_allow_html=True)
                    if st.button("LOGIN", key="drawer_act_login", width="stretch"):
                        _open_login_dialog()
                with card_c2:
                    st.markdown('<div class="drawer-card-anchor drawer-card-contact"></div>', unsafe_allow_html=True)
                    if st.button("CONTACT US", key="drawer_act_contact", width="stretch"):
                        _open_contact_dialog()
                with card_c3:
                    st.markdown('<div class="drawer-card-anchor drawer-card-stores"></div>', unsafe_allow_html=True)
                    if st.button("STORES", key="drawer_act_stores", width="stretch"):
                        _open_stores_dialog()

                st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

                # Quick Bag Shortcut if items present
                cart_now = st.session_state.get("live_cart", {"item_count": 0, "total_pkr": 0.0, "items": []})
                c_cnt = int(cart_now.get("item_count", 0))
                c_tot = float(cart_now.get("total_pkr", 0.0))
                if c_cnt > 0:
                    if st.button(f"🛍️ View Bag ({c_cnt} items &bull; PKR {c_tot:,.0f}) →", key="drawer_open_bag_shortcut", width="stretch"):
                        st.session_state["sidebar_mode"] = "cart"
                        st.rerun()
                    st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

                # -------------------------------------------------------------
                # Department Tabs (Image 2 style: WOMAN, KID, MAN, FRAGRANCE)
                # -------------------------------------------------------------
                if "drawer_dept" not in st.session_state:
                    st.session_state["drawer_dept"] = "WOMAN"
                active_dept = st.session_state["drawer_dept"]

                t1, t2, t3, t4 = st.columns([1.1, 0.8, 0.8, 1.4], gap="small")
                with t1:
                    cls_t1 = "drawer-dept-anchor drawer-dept-active" if active_dept == "WOMAN" else "drawer-dept-anchor"
                    st.markdown(f'<div class="{cls_t1}"></div>', unsafe_allow_html=True)
                    st.button(
                        "WOMAN",
                        key="tab_dept_woman",
                        width="stretch",
                        on_click=_apply_filter_cb,
                        args=("Women's Lawn & Unstitched", "", "WOMAN"),
                    )
                with t2:
                    cls_t2 = "drawer-dept-anchor drawer-dept-active" if active_dept == "KID" else "drawer-dept-anchor"
                    st.markdown(f'<div class="{cls_t2}"></div>', unsafe_allow_html=True)
                    st.button(
                        "KID",
                        key="tab_dept_kid",
                        width="stretch",
                        on_click=_apply_filter_cb,
                        args=("Kids & School Supplies", "kids", "KID"),
                    )
                with t3:
                    cls_t3 = "drawer-dept-anchor drawer-dept-active" if active_dept == "MAN" else "drawer-dept-anchor"
                    st.markdown(f'<div class="{cls_t3}"></div>', unsafe_allow_html=True)
                    st.button(
                        "MAN",
                        key="tab_dept_man",
                        width="stretch",
                        on_click=_apply_filter_cb,
                        args=("Men's Kurta & Ethnic", "men kurta ethnic", "MAN"),
                    )
                with t4:
                    cls_t4 = "drawer-dept-anchor drawer-dept-active" if active_dept == "FRAGRANCE" else "drawer-dept-anchor"
                    st.markdown(f'<div class="{cls_t4}"></div>', unsafe_allow_html=True)
                    st.button(
                        "FRAGRANCE",
                        key="tab_dept_frag",
                        width="stretch",
                        on_click=_apply_filter_cb,
                        args=("Beauty & Fragrances", "oud perfume beauty", "FRAGRANCE"),
                    )

                st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

                # -------------------------------------------------------------
                # Luxury Fashion Category Line Items (Image 2 style)
                # -------------------------------------------------------------
                if active_dept == "WOMAN":
                    dept_items = [
                        ("WINTER ' 26", "", "Women's Lawn & Unstitched", "winter warm shawl collection", False),
                        ("GRAND WINTER", "FLAT PRICES", "Women's Lawn & Unstitched", "sale discount lawn", True),
                        ("NEW ARRIVALS", "", "Women's Lawn & Unstitched", "new arrival 2026", True),
                        ("UNSTITCHED", "", "Women's Lawn & Unstitched", "Sapphire Khaadi lawn 3-piece", True),
                        ("READY TO WEAR", "", "Women's Lawn & Unstitched", "pret kurti luxury", True),
                        ("WEST", "", "Women's Lawn & Unstitched", "silk kaftan luxury", False),
                        ("NOOR", "", "Women's Lawn & Unstitched", "festive silk embroidered", False),
                        ("BOTTOMS", "", "Women's Lawn & Unstitched", "trouser shalwar", True),
                        ("ACCESSORIES", "", "Footwear & Khussa", "traditional velvet khussa", True),
                    ]
                elif active_dept == "MAN":
                    dept_items = [
                        ("FESTIVE '26", "", "Men's Kurta & Ethnic", "men festive 2026", False),
                        ("KURTA & SHALWAR", "", "Men's Kurta & Ethnic", "Junaid Jamshed kurta shalwar", True),
                        ("WAISTCOATS", "", "Men's Kurta & Ethnic", "waistcoat embroidered", True),
                        ("FOOTWEAR", "", "Footwear & Khussa", "men khussa leather", True),
                        ("SHAWLS", "", "Men's Kurta & Ethnic", "pashmina shawl men", False),
                    ]
                elif active_dept == "KID":
                    dept_items = [
                        ("BOYS EASTERN", "", "Kids & School Supplies", "boys kurta shalwar", True),
                        ("GIRLS FESTIVE", "", "Kids & School Supplies", "girls frock lehenga", True),
                        ("CASUAL", "", "Kids & School Supplies", "kids casual cotton", False),
                        ("ESSENTIALS", "", "Kids & School Supplies", "backpack school", True),
                    ]
                else:  # FRAGRANCE
                    dept_items = [
                        ("ARABIAN DEHN AL OUD", "", "Beauty & Fragrances", "Junaid Jamshed Arabian Oud perfume", True),
                        ("FRENCH PERFUMES", "", "Beauty & Fragrances", "french perfume luxury", True),
                        ("TRADITIONAL ATTAR", "", "Beauty & Fragrances", "attar pure oil", False),
                        ("HERBAL SKINCARE", "", "Beauty & Fragrances", "herbal skincare luxury", True),
                    ]

                st.markdown('<div class="drawer-categories-wrap"></div>', unsafe_allow_html=True)
                for idx, (disp_title, promo_badge, itm_cat, itm_q, has_plus) in enumerate(dept_items):
                    plus_cls = "drawer-item-has-plus" if has_plus else ""
                    st.markdown(f'<div class="drawer-item-anchor {plus_cls}"></div>', unsafe_allow_html=True)
                    btn_label = f"{disp_title}  :red[{promo_badge}]" if promo_badge else disp_title
                    st.button(
                        btn_label,
                        key=f"drw_itm_{active_dept}_{idx}",
                        width="stretch",
                        on_click=_apply_filter_cb,
                        args=(itm_cat, itm_q),
                    )

                # -------------------------------------------------------------
                # Bottom Utility: TRACK YOUR ORDER 🚚 (Image 2 style)
                # -------------------------------------------------------------
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="drawer-track-wrap"></div>', unsafe_allow_html=True)
                if st.button("TRACK YOUR ORDER  🚚", key="drw_btn_track_order", width="stretch"):
                    _open_order_tracking_dialog()

                # Budget Slider (Navigation Menu only)
                st.markdown("<div style='margin-top:1rem; font-size:0.75rem; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.06em;'>Budget Filter (PKR)</div>", unsafe_allow_html=True)
                filter_budget = st.slider(
                    "Filter by Budget (PKR):",
                    min_value=2000,
                    max_value=60000,
                    value=int(st.session_state.get("customer_filter_budget", 60000)),
                    step=1000,
                    key="sidebar_budget_slider",
                    label_visibility="collapsed",
                )
                st.session_state["customer_filter_budget"] = filter_budget

                # 6. Discreet Portal Switcher at the very bottom (Navigation Menu only)
                st.markdown("<div style='margin-top:2.5rem; padding-top:1rem; border-top:1px dashed #E5E7EB;'></div>", unsafe_allow_html=True)
                admin_switch = st.checkbox("🏢 Enterprise & Merchant Console", value=False)
                if admin_switch:
                    st.session_state["portal_role"] = "🏢 Merchant & Enterprise Hub"
                    st.rerun()

        else:
            # Enterprise Mode Sidebar
            if st.button("🛍️ Return to Storefront", key="ent_side_back_btn", width="stretch", type="primary"):
                st.session_state["portal_role"] = "🛍️ Customer Storefront"
                st.rerun()

            st.divider()
            st.markdown("### 🏢 Enterprise Console")
            ent_view = st.radio(
                "Console Section:",
                list(ENTERPRISE_VIEW_SLUGS.values()),
                label_visibility="collapsed",
                key="ent_view",
            )
            # Keep the URL in sync so the current view can be bookmarked or shared.
            st.query_params["view"] = {v: k for k, v in ENTERPRISE_VIEW_SLUGS.items()}[ent_view]

            st.divider()
            st.markdown("### 👤 Persona Simulation (For ML Testing)")
            selected_uid = st.selectbox(
                "Active Customer Profile:",
                options=list(persona_map.keys()),
                format_func=lambda u: f"{persona_map[u][0]} (#{u})",
            )
            selected_occasion = st.selectbox(
                "Seasonal Event Context:",
                options=["Eid", "Shaadi/Wedding", "11.11 Sale", "All-Season"],
            )

            st.divider()
            st.caption("ShopKaro Enterprise BI • DuckDB v1.0 • FastAPI Serving Engine")

    # =========================================================================
    # VIEW 1: CUSTOMER STOREFRONT (LOOKS 100% LIKE REAL E-COMMERCE)
    # =========================================================================
    if portal_choice == "🛍️ Customer Storefront":
        # Hero Promotional Campaign Banner (Aspirational Background Image with Reduced 25% Opacity Tint)
        hero_bg_uri = get_local_asset_data_uri("pakistani_royal_modest_bridal.jpg")
        max_disc, n_on_sale = catalogue_discount_stats()  # banner numbers come from the catalogue, not copywriting
        hero_html = (
            f'<div class="shopkaro-hero-banner" style="background-image: linear-gradient(135deg, rgba(6, 38, 30, 0.65) 0%, rgba(10, 58, 46, 0.58) 50%, rgba(4, 24, 18, 0.70) 100%), url(\'{hero_bg_uri}\');">'
            '<div class="shopkaro-hero-badge">🌙 EID UL FITR 2026 GRAND BAZAAR</div>'
            '<h1 class="shopkaro-hero-title">Pakistan\'s AI-Powered Luxury Marketplace</h1>'
            '<div class="shopkaro-hero-sub-tiers">'
            f'<div class="hero-tier-item"><span class="hero-tier-bullet">✦</span><span><b>Up to {max_disc:.0f}% OFF</b> on {n_on_sale:,} products: lawn, bridal & festive wear</span></div>'
            '<div class="hero-tier-item"><span class="hero-tier-bullet">✦</span><span><b>Free Express Doorstep Delivery</b> Across 250+ Cities in Pakistan (24–48h Dispatch)</span></div>'
            '<div class="hero-tier-item"><span class="hero-tier-bullet">✦</span><span><b>100% Genuine Designer Guarantee</b> with Verified Cash on Delivery (COD)</span></div>'
            '</div>'
            '<div class="shopkaro-hero-pills">'
            '<div class="hero-pill">⚡ 24–48h Dispatch</div>'
            '<div class="hero-pill">💵 Cash on Delivery</div>'
            '<div class="hero-pill">🇵🇰 100% Authentic Brand Guarantee</div>'
            '<div class="hero-pill">🔄 7-Day Hassle-Free Returns</div>'
            '</div>'
            '</div>'
        )
        st.markdown(hero_html, unsafe_allow_html=True)

        # 1. LAAM Shop by Category (Circular Avatars Grid)
        st.markdown(
            """<div class="laam-category-heading-row">
<h2 class="laam-category-heading">Shop by category</h2>
<a class="laam-category-link" href="#all-categories">Curated Designer Collections ›</a>
</div>""",
            unsafe_allow_html=True,
        )

        laam_categories_data = [
            # Row 1 - 7 Distinct Fashion Categories
            {
                "name": "Kurta Set",
                "img": get_local_asset_data_uri("pakistani_lawn_emerald.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Kurta Set emerald embroidered lawn",
            },
            {
                "name": "Lehenga",
                "img": get_local_asset_data_uri("pakistani_bridal_lehenga_crimson.jpg"),
                "cat": "Bridal & Formal Wear",
                "q": "Lehenga crimson bridal shaadi",
            },
            {
                "name": "Kaftan",
                "img": get_local_asset_data_uri("pakistani_luxury_silk_kaftan.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Kaftan luxury jewel silk draped",
            },
            {
                "name": "Pret Kurti",
                "img": get_local_asset_data_uri("pakistani_modest_lawn.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Pret kurti stitched lawn ivory",
            },
            {
                "name": "Shawl",
                "img": get_local_asset_data_uri("pakistani_islamic_eid_gift_oud_shawl.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Embroidered Pashmina Shawl luxury",
            },
            {
                "name": "Peplum",
                "img": get_local_asset_data_uri("pakistani_short_peplum_frock.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Short Frock peplum stitched kurti",
            },
            {
                "name": "Saree",
                "img": get_local_asset_data_uri("pakistani_royal_modest_bridal.jpg"),
                "cat": "Bridal & Formal Wear",
                "q": "Saree banarasi royal zari formal",
            },
            # Row 2 - 7 Distinct Fashion Categories
            {
                "name": "Unstitched",
                "img": get_local_asset_data_uri("pakistani_lawn_emerald.jpg"),
                "cat": "Women's Lawn & Unstitched",
                "q": "Unstitched 3-piece lawn suit",
            },
            {
                "name": "Gharara",
                "img": get_local_asset_data_uri("pakistani_modest_bridal_lehenga.jpg"),
                "cat": "Bridal & Formal Wear",
                "q": "Gharara traditional wedding nikah",
            },
            {
                "name": "Pishwas",
                "img": get_local_asset_data_uri("pakistani_flared_pishwas.jpg"),
                "cat": "Bridal & Formal Wear",
                "q": "Pishwas flared 30 kali formal maxi",
            },
            {
                "name": "Jewelry Set",
                "img": get_local_asset_data_uri("pakistani_kundan_jewelry_set.jpg"),
                "cat": "Beauty & Fragrances",
                "q": "Kundan bridal jewelry set gold choker",
            },
            {
                "name": "Waistcoat",
                "img": get_local_asset_data_uri("pakistani_mens_velvet_waistcoat.jpg"),
                "cat": "Men's Kurta & Ethnic",
                "q": "Men navy velvet embroidered waistcoat",
            },
            {
                "name": "Khussa",
                "img": get_local_asset_data_uri("pakistani_khussa_maroon.jpg"),
                "cat": "Footwear & Khussa",
                "q": "Handcrafted Punjabi velvet khussa maroon",
            },
            {
                "name": "Angrakha",
                "img": get_local_asset_data_uri("pakistani_angrakha_kalidar.jpg"),
                "cat": "Bridal & Formal Wear",
                "q": "Angrakha gota patti kalidar crossover",
            },
        ]

        # Render 2 rows of 7 circular items
        for row_idx in range(0, 14, 7):
            row_items = laam_categories_data[row_idx:row_idx+7]
            cols = st.columns(7)
            for c_idx, c_item in enumerate(row_items):
                with cols[c_idx]:
                    st.markdown(
                        f'<div class="laam-circle-avatar">'
                        f'<img src="{c_item["img"]}" alt="{c_item["name"]}"/>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.button(
                        c_item["name"],
                        key=f"cat_label_{row_idx + c_idx}",
                        on_click=_apply_filter_cb,
                        args=(c_item["cat"], c_item["q"]),
                        width="stretch",
                    )

        st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

        # 2. Deals: real discounted, in-stock catalogue items (one per category, reviewed products first).
        st.markdown(
            """
            <div class="flash-deals-header">
                <div class="flash-deals-title">⚡ Eid Deals &bull; Biggest discounts in stock</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        flash_items = [dict(x) for x in load_deal_items()]
        if not flash_items:
            st.info("No discounted products in stock right now.")
            flash_items = []
        fd_cols = st.columns(3) if flash_items else []
        for fd_idx, fd_item in enumerate(flash_items[:3]):
            with fd_cols[fd_idx]:
                _render_real_ecom_card(st, fd_item, selected_uid, card_prefix=f"flash_{fd_idx}")

        st.markdown("<div style='height: 1.4rem;'></div>", unsafe_allow_html=True)

        # 3. Catalog Filter & Preset Chips
        search_input = st.session_state.get("active_search_query", "")

        # Quick Popular Pakistani Fashion & Electronics Query Badges
        preset_chips = [
            ("👰 Maria B Modest Nikah Lehenga <= 20k", "shaadi ke liye red lehenga 20 hazaar tak"),
            ("👗 Sapphire Modest Lawn <= 5k", "Sapphire lawn suit emerald green eid"),
            ("👔 J. Men's Kurta Shalwar <= 6k", "Khaadi man classic kurta beige"),
            ("🌸 J. Arabian Oud & Shawl <= 3k", "Junaid Jamshed oud perfume set"),
            ("🥿 Chapter 13 Velvet Khussa <= 5k", "traditional punjabi khussa golden"),
            ("💻 Coding Laptop <= 1.5 Lac", "laptop for coding under 1.5 lac"),
        ]
        q_cols = st.columns(len(preset_chips))
        for idx_p, (chip_title, chip_val) in enumerate(preset_chips):
            q_cols[idx_p].button(
                chip_title,
                key=f"pchip_{idx_p}",
                on_click=_apply_filter_cb,
                args=("All Categories", chip_val),
                width="stretch",
            )

        # Execute Search and Display Filtered Grid
        active_cat = st.session_state.get("customer_filter_cat", "All Categories")
        raw_query = str(st.session_state.get("active_search_query", "")).strip()

        # Construct targeted query based on active category and user text
        if active_cat != "All Categories":
            effective_query = f"{active_cat} {raw_query}".strip()
        elif raw_query:
            effective_query = raw_query
        else:
            effective_query = ""

        persona_info = persona_map[selected_uid]
        if effective_query:
            _wait_for_models(st)
            # Search as the real shopper (collaborative re-ranking from their history); new visitors get plain search.
            s_out = search_products_endpoint(
                q=effective_query, top_k=18, user_id=None if selected_uid == "new-visitor" else selected_uid
            )
        else:
            # No search yet: real best-reviewed in-stock products, spread across categories.
            s_out = {"results": [dict(x) for x in load_popular_items()], "parsed_constraints": {}}
        pc = s_out["parsed_constraints"]

        # Filter results strictly by active category and budget
        filtered_results = []
        for item in s_out["results"]:
            if active_cat != "All Categories" and item.get("category") != active_cat:
                continue
            if item.get("price_pkr", 0) > st.session_state.get("customer_filter_budget", 60000):
                continue
            filtered_results.append(item)

        # Many catalogue items share a title (generated from templates); show each title once.
        seen_titles: set[str] = set()
        filtered_results = [
            it for it in filtered_results
            if not (str(it.get("title", "")).lower() in seen_titles or seen_titles.add(str(it.get("title", "")).lower()))
        ]

        # If search did not yield enough items for the selected category, directly fetch authentic items from DuckDB
        if len(filtered_results) < 3 and active_cat != "All Categories":
            try:
                con = duckdb.connect(str(settings.duckdb_path), read_only=True)
                db_items = con.execute(
                    """
                    SELECT p.product_id, p.title, p.brand, p.category, p.price_pkr, p.on_sale, p.discount_pct,
                           r.avg_rating, COALESCE(r.genuine_review_count, 0) AS review_count
                    FROM product_catalogue p
                    LEFT JOIN review_intelligence_summary r USING (product_id)
                    WHERE p.category = ? AND p.price_pkr <= ? AND p.in_stock
                    ORDER BY r.avg_rating DESC NULLS LAST, review_count DESC
                    LIMIT 9
                    """,
                    [active_cat, float(st.session_state.get("customer_filter_budget", 60000))],
                ).df().to_dict("records")
                con.close()
                if db_items:
                    filtered_results = db_items
            except Exception:
                pass

        # If still empty (e.g. strict budget filter on All Categories), show top results within budget
        if not filtered_results and s_out["results"]:
            filtered_results = [it for it in s_out["results"] if it.get("price_pkr", 0) <= st.session_state.get("customer_filter_budget", 60000)]
            if not filtered_results:
                filtered_results = s_out["results"][:6]

        # Sorting & Rating Filter Controls
        f_col1, f_col2, f_col3 = st.columns([2.5, 1.4, 1.3], vertical_alignment="center", gap="small")
        with f_col1:
            cat_badge = f'<span class="ecom-filter-pill" style="background:#FDF2F4; color:#5B0E2D; font-weight:800;">🏷️ {active_cat}</span>' if active_cat != "All Categories" else ""
            pills_html = [
                f'<span class="ecom-filter-pill">Showing <b>{min(len(filtered_results), GRID_PAGE_SIZE)} of {len(filtered_results)}</b> products{"" if raw_query or active_cat != "All Categories" else " &bull; most reviewed"}</span>',
                cat_badge,
                f'<span class="ecom-filter-pill">Budget: &le; PKR {st.session_state.get("customer_filter_budget", 60000):,.0f}</span>',
            ]
            st.markdown(f'<div class="ecom-filter-bar">{"".join(pills_html)}</div>', unsafe_allow_html=True)
        with f_col2:
            sort_order = st.selectbox(
                "Sort by:",
                ["✨ Curated", "💰 Price: Low to High", "💎 Price: High to Low", "★ Customer Rating", "🔥 Biggest Savings"],
                key="catalog_sort_order",
                label_visibility="collapsed",
            )
        with f_col3:
            rating_min = st.selectbox(
                "Rating:",
                ["All Ratings", "★ 4.5 & Above", "★ 4.0 & Above"],
                key="catalog_rating_filter",
                label_visibility="collapsed",
            )

        # Apply Rating filter
        if rating_min == "★ 4.5 & Above":
            filtered_results = [it for it in filtered_results if (it.get("avg_rating") or 0.0) >= 4.5]
        elif rating_min == "★ 4.0 & Above":
            filtered_results = [it for it in filtered_results if (it.get("avg_rating") or 0.0) >= 4.0]

        # Apply Sorting
        if sort_order == "💰 Price: Low to High":
            filtered_results.sort(key=lambda x: float(x.get("price_pkr", 0.0)))
        elif sort_order == "💎 Price: High to Low":
            filtered_results.sort(key=lambda x: float(x.get("price_pkr", 0.0)), reverse=True)
        elif sort_order == "★ Customer Rating":
            filtered_results.sort(key=lambda x: (x.get("avg_rating") or 0.0, x.get("review_count") or 0), reverse=True)
        elif sort_order == "🔥 Biggest Savings":
            filtered_results.sort(key=lambda x: float(x.get("discount_pct", 0.0)), reverse=True)

        if filtered_results:
            for row_start in range(0, min(len(filtered_results), GRID_PAGE_SIZE), 3):
                grid_cols = st.columns(3)
                for col_idx in range(3):
                    item_idx = row_start + col_idx
                    if item_idx < len(filtered_results):
                        with grid_cols[col_idx]:
                            _render_real_ecom_card(
                                st, filtered_results[item_idx], selected_uid, card_prefix=f"sgrid_{item_idx}"
                            )

        # 4. Comprehensive Product Inspection & Detail Modal
        if st.session_state.get("inspected_sku"):
            insp_sku = st.session_state["inspected_sku"]
            _wait_for_models(st)
            rev_data = get_product_reviews_endpoint(insp_sku)
            matching_items = [it for it in filtered_results if str(it.get("product_id")) == insp_sku]
            # Fall back to the catalogue (never a made-up price): the cart charges current_item["price_pkr"].
            cat_item = serving_container.catalogue_by_sku.get(insp_sku, {})
            current_item = matching_items[0] if matching_items else {
                "product_id": insp_sku,
                "title": cat_item.get("title", rev_data.get("title", insp_sku)),
                "brand": cat_item.get("brand", rev_data.get("brand", "")),
                "price_pkr": float(cat_item.get("price_pkr", 0.0)),
                "category": cat_item.get("category", rev_data.get("category", "")),
                "on_sale": bool(cat_item.get("on_sale", False)),
                "discount_pct": float(cat_item.get("discount_pct", 0.0)),
            }

            with st.expander(f"⭐ Product Specifications, Sizing & Verified ABSA Reviews — {insp_sku}: {rev_data['title']}", expanded=True):
                det_col1, det_col2, det_col3 = st.columns([1.8, 2.2, 2.0], gap="medium")

                with det_col1:
                    p_img = get_product_image_url(insp_sku, current_item.get("category", "Festive"))
                    st.markdown(
                        f"""
                        <div style="border:1px solid #E2E8F0; border-radius:12px; overflow:hidden; background:#F8FAFC;">
                            <img src="{p_img}" style="width:100%; height:260px; object-fit:cover;" alt="{rev_data['title']}"/>
                            <div style="padding:0.6rem; font-size:0.75rem; color:#64748B; text-align:center;">
                                🔍 High-Resolution Texture & Stitch Inspection
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with det_col2:
                    st.markdown(f"### {rev_data['title']}")
                    st.markdown(f"**Brand:** {current_item.get('brand', 'ShopKaro')} &bull; **SKU:** `{insp_sku}`")
                    st.markdown(f"<div style='font-size:1.35rem; font-weight:800; color:#0F766E;'>PKR {float(current_item.get('price_pkr', 0.0)):,.0f}</div>", unsafe_allow_html=True)
                    # Real catalogue attributes for this SKU (previously a fixed "Pure Lawn / Banarasi Silk" text
                    # was shown for every product, phones included).
                    cat_rec = serving_container.catalogue_by_sku.get(insp_sku, {})
                    stock_qty = int(cat_rec.get("stock_qty", 0) or 0)
                    spec_lines = [
                        ("Type", cat_rec.get("sub_category")),
                        ("Category", cat_rec.get("category")),
                        ("Colour", cat_rec.get("color")),
                        ("Occasion", cat_rec.get("occasion")),
                        ("Availability", f"In stock ({stock_qty} units)" if stock_qty > 0 else "Out of stock"),
                    ]
                    spec_html = "<br/>".join(
                        f"&bull; <b>{html.escape(k)}:</b> {html.escape(str(v))}" for k, v in spec_lines if v
                    )
                    st.markdown(
                        f'<div style="font-size:0.8rem; color:#4B5563; line-height:1.5; margin:0.4rem 0;">{spec_html}</div>',
                        unsafe_allow_html=True,
                    )

                    # Size options only for clothing; other products have a single variant.
                    clothing = {"Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Bridal & Formal Wear", "Winter Wear & Jackets"}
                    if cat_rec.get("category") in clothing:
                        sel_variant = st.radio(
                            "Select size:",
                            ["Unstitched", "XS", "S", "M", "L", "XL"],
                            horizontal=True,
                            key=f"det_size_sel_{insp_sku}",
                        )
                    else:
                        sel_variant = "Standard"

                    det_b1, det_b2 = st.columns([1.5, 1])
                    with det_b1:
                        if st.button("🛒 Add to Bag", key=f"det_add_{insp_sku}", width="stretch", type="primary"):
                            _add_item_to_live_cart(current_item, quantity=1)
                            st.toast(f"Added {rev_data['title']} ({sel_variant}) to your bag!", icon="🛍️")
                            st.session_state["sidebar_mode"] = "cart"
                            st.session_state["sidebar_state"] = "expanded"
                            st.rerun()
                    with det_b2:
                        w_list = st.session_state.get("wishlist", [])
                        is_w = any(str(w.get("product_id")) == insp_sku for w in w_list)
                        w_lbl = "❤️ In Wishlist" if is_w else "🤍 Save to Wish"
                        if st.button(w_lbl, key=f"det_wish_{insp_sku}", width="stretch"):
                            if is_w:
                                st.session_state["wishlist"] = [w for w in w_list if str(w.get("product_id")) != insp_sku]
                            else:
                                w_list.append(dict(current_item))
                                st.session_state["wishlist"] = w_list
                            st.rerun()

                with det_col3:
                    st.markdown("##### 📊 What reviewers say, by aspect")
                    n_reviews = int(rev_data.get("genuine_review_count", 0) or 0)
                    if n_reviews == 0 or rev_data.get("avg_rating") is None:
                        st.info("No reviews yet for this product.")
                    else:
                        r1, r2 = st.columns(2)
                        r1.metric("Average rating", f"★ {float(rev_data['avg_rating']):.2f}")
                        r2.metric("Genuine reviews", f"{n_reviews}")
                        if rev_data.get("what_customers_say"):
                            st.markdown(f"**What customers say:** {rev_data['what_customers_say']}")
                        st.caption(
                            "Net score per aspect: average over reviews of +1 (praised), 0 (not mentioned) and "
                            "-1 (criticised). Bar centre = neutral."
                        )
                        aspect_labels = {
                            "quality": "🧵 Quality",
                            "price": "💰 Value for money",
                            "delivery": "🚚 Delivery",
                            "size_fit": "📐 Size & fit",
                            "packaging": "📦 Packaging",
                            "seller": "🤝 Seller",
                        }
                        scores = rev_data.get("aspect_scores", {})
                        for asp_key, asp_title in aspect_labels.items():
                            if asp_key not in scores:
                                continue
                            net = max(-1.0, min(1.0, float(scores[asp_key])))
                            st.caption(f"{asp_title}: **{net:+.2f}**")
                            st.progress((net + 1.0) / 2.0)
                        if rev_data.get("is_unfairly_penalized_by_courier"):
                            st.info(
                                "ℹ️ Reviewers praise this product's quality but often complain about delivery, so its "
                                "rating is likely pulled down by the courier rather than the product."
                            )

                if st.button("Close Product Specifications", key="close_insp", width="stretch"):
                    st.session_state["inspected_sku"] = None
                    st.rerun()

        st.divider()

        # 5. Personalized Recommendations Strip (Amazon/Noon style); placeholder until the models are loaded.
        if serving_container._initialized:
            rec_out = get_recommendations_endpoint(user_id=selected_uid, top_k=6, occasion=selected_occasion)
        else:
            _render_models_loading_placeholder(st, "Personalised picks")
            rec_out = {"segment_name": "", "recommendations": []}
        if rec_out["recommendations"]:
            st.markdown(
                f"### ✨ Recommended for You &bull; {selected_occasion} Picks\n"
                f"*Curated for your profile ({rec_out['segment_name']}) with free express delivery*"
            )
        rec_items = rec_out["recommendations"][:6]
        for row_start in range(0, len(rec_items), 3):
            rec_cols = st.columns(3)
            for col_idx in range(3):
                item_idx = row_start + col_idx
                if item_idx < len(rec_items):
                    with rec_cols[col_idx]:
                        _render_real_ecom_card(
                            st, rec_items[item_idx], selected_uid, card_prefix=f"rgrid_{item_idx}"
                        )

        # 6. Comprehensive ShopKaro E-Commerce Marketplace Footer
        st.markdown(
            """
            <div class="shopkaro-footer">
                <div class="shopkaro-footer-grid">
                    <div class="shopkaro-footer-col">
                        <h4>🛍️ ShopKaro.PK</h4>
                        <p>Pakistan's premier AI-powered commerce marketplace connecting discerning shoppers with authentic designer fashion, modest festive wear, luxury fragrances, and genuine electronics.</p>
                        <p style="margin-top:0.6rem; color:#14B8A6; font-weight:700;">✓ 100% Original Brand Guarantee</p>
                    </div>
                    <div class="shopkaro-footer-col">
                        <h4>📞 Customer Care & Support</h4>
                        <ul>
                            <li><b>UAN Helpline:</b> +92 (21) 111-746-752</li>
                            <li><b>WhatsApp AI Concierge:</b> 24/7 Available</li>
                            <li><b>Email:</b> support@shopkaro.pk</li>
                            <li><b>Operating Hours:</b> Mon–Sun (9 AM – 11 PM PKT)</li>
                            <li><b>Hassle-Free Returns:</b> 7 Days Doorstep Pickup</li>
                        </ul>
                    </div>
                    <div class="shopkaro-footer-col">
                        <h4>💳 Secure Payment Options</h4>
                        <p>We accept all major verified Pakistani payment methods:</p>
                        <div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.5rem;">
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">💵 Cash on Delivery (COD)</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">📱 JazzCash Wallet</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">🟢 EasyPaisa</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">💳 Visa / Mastercard</span>
                        </div>
                    </div>
                    <div class="shopkaro-footer-col">
                        <h4>🚚 Express Courier Partners</h4>
                        <p>Nationwide fast doorstep delivery in 24 to 48 hours across 250+ cities:</p>
                        <div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.5rem;">
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">🐆 Leopards Courier</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">🔴 TCS Express</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">⚡ Trax Logistics</span>
                            <span style="background:#1E293B; border:1px solid #334155; padding:0.25rem 0.55rem; border-radius:4px; font-size:0.75rem; color:#F8FAFC;">📦 CallCourier</span>
                        </div>
                    </div>
                </div>
                <div class="shopkaro-footer-bottom">
                    <span>© 2026 ShopKaro Technologies Pakistan (Pvt) Ltd. All Rights Reserved.</span>
                    <span>Karachi &bull; Lahore &bull; Islamabad &bull; Faisalabad &bull; Multan &bull; Peshawar &bull; Quetta</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =========================================================================
    # VIEW 2: MERCHANT & ENTERPRISE BACK-OFFICE HUB
    # =========================================================================
    else:
        _wait_for_models(st)  # forecasts, health and metrics come from the serving container
        top_ret, top_bnr = st.columns([1.5, 4.5], vertical_alignment="center")
        with top_ret:
            if st.button("🛍️ Return to Storefront", key="ent_top_back_btn", width="stretch", type="primary"):
                st.session_state["portal_role"] = "🛍️ Customer Storefront"
                st.rerun()
        with top_bnr:
            st.markdown(
                """
                <div class="enterprise-banner" style="margin:0;">
                    <div>
                        <div class="enterprise-title">🏢 ShopKaro Enterprise Back-Office & Merchant Intelligence Hub</div>
                        <div class="enterprise-sub">Sales Intelligence &bull; Demand Forecasting &bull; Recommendation Engine &bull; A/B Testing &bull; 6-Aspect ABSA &bull; AI Telemetry</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

        # 1. Executive Overview & Sales Analytics
        if ent_view == "📈 Executive Overview & Sales Analytics":
            st.markdown(
                "## 📈 Executive Overview & Commercial Sales Analytics\n"
                "*High-Level Gross Merchandise Value (GMV), Order Volumes, Velocity Tiers, and Category Revenue Dynamics.*"
            )

            sales_df = snapshot.get("sales_overview", pd.DataFrame())
            sales_totals = _sales_overview_totals(sales_df)

            # Year-on-year growth computed from the monthly series (2025 vs 2024), not typed in.
            m_all = snapshot.get("monthly_sales", pd.DataFrame())
            yoy_note = "Year-over-year comparison unavailable"
            if not m_all.empty:
                by_year = m_all.assign(year=m_all["sale_month"].astype(str).str[:4]).groupby("year")["gmv_millions_pkr"].sum()
                if {"2024", "2025"} <= set(by_year.index) and by_year["2024"] > 0:
                    yoy_note = f"{(by_year['2025'] / by_year['2024'] - 1) * 100:+.1f}% in 2025 vs 2024"
            if sales_totals is None:
                st.info("Sales metrics are unavailable because no daily sales records were found.")
                metric_values = (
                    ("Total GMV", "—", yoy_note),
                    ("Units sold", "—", "No sales data"),
                    ("Daily sales records", "—", "No sales data"),
                    ("Average price per unit", "—", "No sales data"),
                )
            else:
                tot_gmv, tot_units, tot_records = sales_totals
                aov = tot_gmv / tot_units if tot_units > 0 else None
                metric_values = (
                    ("Total GMV", f"PKR {tot_gmv/1e9:.2f} bn", yoy_note),
                    ("Units sold", f"{tot_units/1e6:.2f} M", "synthetic daily sales"),
                    ("Daily sales records", f"{tot_records:,}", "SKU x day"),
                    ("Average price per unit", f"PKR {aov:,.0f}" if aov is not None else "—", "GMV / units"),
                )
            k1, k2, k3, k4 = st.columns(4)
            for col, (label, value, note) in zip((k1, k2, k3, k4), metric_values):
                col.metric(label, value)
                col.caption(note)

            st.divider()

            c_chart1, c_chart2 = st.columns([3, 2])
            with c_chart1:
                st.markdown("### 📊 Monthly Revenue Growth Trajectory (PKR Millions)")
                m_sales = snapshot.get("monthly_sales", pd.DataFrame())
                if not m_sales.empty:
                    fig, ax = plt.subplots(figsize=(8.5, 3.8), facecolor="#FFFFFF")
                    ax.set_facecolor("#FFFFFF")
                    ax.plot(m_sales["sale_month"], m_sales["gmv_millions_pkr"], marker="o", color="#0F766E", linewidth=2.5, markersize=4.5)
                    ax.fill_between(m_sales["sale_month"], m_sales["gmv_millions_pkr"], color="#14B8A6", alpha=0.15)
                    for s in ["top", "right", "left"]:
                        ax.spines[s].set_visible(False)
                    ax.grid(axis="y", linestyle="--", color="#E2E8F0")
                    ax.set_ylabel("Revenue (PKR Millions)")
                    plt.xticks(rotation=45, ha="right", fontsize=8)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.caption("Monthly sales data is unavailable.")

            with c_chart2:
                st.markdown("### 🏆 Top Category GMV Contribution")
                if not sales_df.empty:
                    with st.container(key="enterprise-category-desktop-table"):
                        st.dataframe(
                            sales_df[["category", "total_gmv_pkr", "total_units_sold", "avg_price_pkr"]],
                            width="stretch",
                            height=280,
                            hide_index=True,
                        )
                    category_rows = []
                    for row in sales_df.to_dict("records"):
                        category = html.escape(str(row["category"]))
                        gmv = float(row["total_gmv_pkr"])
                        units = float(row["total_units_sold"])
                        avg_price = float(row["avg_price_pkr"])
                        category_rows.append(
                            f'<div class="enterprise-mobile-row" role="listitem">'
                            f'<div class="enterprise-mobile-row-top">'
                            f'<span>{category}</span>'
                            f'<strong>PKR {gmv:,.0f}</strong>'
                            f'</div>'
                            f'<div class="enterprise-mobile-row-meta">'
                            f'<span>{units:,.0f} units sold</span>'
                            f'<span>Average price PKR {avg_price:,.0f}</span>'
                            f'</div>'
                            f'</div>'
                        )
                    st.markdown(
                        '<div class="enterprise-mobile-table" role="list" '
                        'aria-label="Top category GMV contribution">'
                        '<div class="enterprise-mobile-table-head" aria-hidden="true">'
                        '<span>Category</span><span>GMV</span>'
                        '</div>'
                        f'{"".join(category_rows)}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Category sales data is unavailable.")

            st.divider()
            st.markdown("### 👥 Customer RFM Segment Distribution")
            segments_df = snapshot["segments_summary"]
            if not segments_df.empty:
                with st.container(key="enterprise-rfm-desktop-table"):
                    st.dataframe(segments_df, width="stretch", hide_index=True)
                segment_rows = []
                for row in segments_df.to_dict("records"):
                    segment = html.escape(str(row["segment_name"]))
                    customers = float(row["customer_count"])
                    recency = float(row["avg_recency_days"])
                    frequency = float(row["avg_frequency"])
                    monetary = float(row["avg_monetary_pkr"])
                    segment_rows.append(
                        f'<div class="enterprise-mobile-row" role="listitem">'
                        f'<div class="enterprise-mobile-row-top">'
                        f'<span>{segment}</span>'
                        f'<strong>{customers:,.0f} customers</strong>'
                        f'</div>'
                        f'<div class="enterprise-mobile-row-meta">'
                        f'<span>Average recency {recency:,.1f} days</span>'
                        f'<span>Average frequency {frequency:,.2f}</span>'
                        f'<span>Average monetary intent PKR {monetary:,.0f}</span>'
                        f'</div>'
                        f'</div>'
                    )
                st.markdown(
                    '<div class="enterprise-mobile-table" role="list" '
                    'aria-label="Customer RFM segment distribution">'
                    '<div class="enterprise-mobile-table-head" aria-hidden="true">'
                    '<span>Segment</span><span>Customers</span>'
                    '</div>'
                    f'{"".join(segment_rows)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("Customer segment data is unavailable.")

        # 2. Supply Chain & Demand Forecasting
        elif ent_view == "📦 Supply Chain & Demand Forecasting":
            st.markdown(
                "## 📦 Supply Chain & Inventory Control Tower\n"
                "*Probabilistic Demand Forecasting (`P10 / P50 / P90`), Dynamic Safety Stock, and Stock-out Alarms.*"
            )

            alerts_df = snapshot["inventory_alerts"]
            crit_cnt = int((alerts_df["alert_status"] == "CRITICAL_STOCKOUT_RISK").sum())
            fest_cnt = int((alerts_df["alert_status"] == "FESTIVAL_SURGE_WATCH").sum())
            over_cnt = int((alerts_df["alert_status"] == "OVERSTOCK_DEAD_CAPITAL").sum())
            ok_cnt = int((alerts_df["alert_status"] == "HEALTHY_STOCK").sum())
            tot_po = int(alerts_df["recommended_order_qty"].sum())

            k1, k2, k3, k4, k5 = st.columns(5)
            # Plain captions, not st.metric deltas: deltas draw up/down trend arrows, and these are not trends.
            for col, label, value, note in (
                (k1, "Tracked SKUs", f"{len(alerts_df)}", f"{ok_cnt} healthy"),
                (k2, "Critical stock-out risk", f"{crit_cnt}", "stock ≤ reorder point or ≤ 14 days left"),
                (k3, "Festival surge watch", f"{fest_cnt}", "≤ 18 days of cover at P90 demand"),
                (k4, "Overstock", f"{over_cnt}", "more than 90 days of cover"),
                (k5, "Recommended order", f"{tot_po:,} units", "across all alerts"),
            ):
                col.metric(label, value)
                col.caption(note)

            backtest_path = settings.reports_dir / "day3_inventory_backtest.json"
            if backtest_path.exists():
                try:
                    bt = json.loads(backtest_path.read_text(encoding="utf-8"))
                    vs_ma = bt["forecast_vs_moving_average_pct_change"]
                    vs_sn = bt["forecast_vs_seasonal_naive_pct_change"]
                    st.info(
                        f"**2025 replay (weekly re-ordering, {bt['skus']} SKUs):** forecast-driven ordering lost "
                        f"{-vs_ma['lost_units']:.0f}% fewer units than a 28-day moving average and "
                        f"{-vs_sn['lost_units']:.0f}% fewer than same-days-last-year, while holding "
                        f"{-vs_ma['avg_stock_value_pkr']:.0f}% / {-vs_sn['avg_stock_value_pkr']:.0f}% less stock. "
                        "Demand is synthetic (built from the same festival calendar the forecaster uses), so real "
                        "gains would be smaller."
                    )
                except (KeyError, ValueError):
                    pass

            st.divider()

            op1, op2 = st.columns([3, 2])
            with op1:
                st.markdown("### 📈 30-Day Probabilistic Demand Fan Chart (`P10 / P50 / P90`)")
                sku_options = alerts_df["product_id"].head(80).tolist()
                sku_titles = dict(zip(alerts_df["product_id"], alerts_df["title"]))
                sel_sku = st.selectbox(
                    "Select SKU to Inspect Demand Trajectory:",
                    options=sku_options,
                    format_func=lambda s: f"{s} — {sku_titles.get(s, s)[:55]}",
                )
                fc_data = get_forecast_endpoint(sel_sku)
                fc_daily = pd.DataFrame(fc_data["daily_forecasts"])

                if not fc_daily.empty:
                    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor="#FFFFFF")
                    ax.set_facecolor("#FFFFFF")
                    dx = pd.to_datetime(fc_daily["forecast_date"])
                    ax.plot(dx, fc_daily["p50_units"], color="#0F766E", linewidth=2.2, label="P50 Expected Demand")
                    ax.fill_between(dx, fc_daily["p10_units"], fc_daily["p90_units"], color="#14B8A6", alpha=0.18, label="80% Prediction Band [P10 - P90]")
                    ax.plot(dx, fc_daily["p90_units"], color="#D97706", linestyle="--", linewidth=1.2, label="P90 Surge Bound")
                    for s in ["top", "right", "left"]:
                        ax.spines[s].set_visible(False)
                    ax.grid(axis="y", linestyle="--", color="#E2E8F0")
                    ax.set_ylabel("Units / Day")
                    ax.legend(frameon=False, loc="upper right")
                    fig.autofmt_xdate()
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)

            with op2:
                st.markdown("### 🛡️ SKU Replenishment Policy Card")
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:1.1rem;">
                        <div style="font-size:0.75rem;font-weight:700;color:#0F766E;">{fc_data['product_id']} &bull; {fc_data['brand']}</div>
                        <div style="font-size:1.05rem;font-weight:700;margin:0.25rem 0;">{fc_data['title']}</div>
                        <table style="width:100%;font-size:0.84rem;margin-top:0.75rem;">
                            <tr><td style="color:#64748B;">Current Warehouse Stock</td><td style="text-align:right;font-weight:700;">{fc_data['current_stock_units']} units</td></tr>
                            <tr><td style="color:#64748B;">Reorder Point (ROP)</td><td style="text-align:right;font-weight:700;">{fc_data['reorder_point_units']:.0f} units</td></tr>
                            <tr><td style="color:#64748B;">Safety Stock Buffer</td><td style="text-align:right;font-weight:700;">{fc_data['safety_stock_units']:.0f} units</td></tr>
                            <tr><td style="color:#64748B;">Days of Inventory (DOI)</td><td style="text-align:right;font-weight:700;">{fc_data['days_of_inventory']:.1f} days</td></tr>
                            <tr style="border-top:1px solid #E2E8F0;"><td style="font-weight:700;padding-top:0.4rem;">Recommended PO</td><td style="text-align:right;font-weight:800;color:#0F766E;padding-top:0.4rem;">{fc_data['recommended_order_qty']} units</td></tr>
                        </table>
                        <div style="margin-top:0.8rem;padding:0.6rem;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;font-size:0.78rem;">
                            <b>Automated ERP Action:</b> {fc_data['recommended_action']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.divider()
            st.markdown("### 📋 Filterable Warehouse Alert Queue")
            st.dataframe(alerts_df, width="stretch", height=320, hide_index=True)

        # 3. Recommendation Engine Analytics
        elif ent_view == "🎯 Recommendation Engine Analytics":
            st.markdown(
                "## 🎯 Recommendation Engine Intelligence & Offline Benchmarks\n"
                "*All 8 Day 2 models (incl. the PyTorch neural two-tower) compared on 5,000 held-out users (Day 2 benchmark; numbers read from reports/day2_model_comparison.csv).*"
            )

            rec_df = snapshot.get("rec_benchmarks", pd.DataFrame())
            if not rec_df.empty:
                # All tiles come from the benchmark file; the best model is the one with the highest NDCG@10.
                best = rec_df.sort_values("ndcg_at_10", ascending=False).iloc[0]
                pop = rec_df[rec_df["model_family"] == "Baseline"].sort_values("ndcg_at_10", ascending=False).iloc[0]
                rk1, rk2, rk3, r4 = st.columns(4)
                for col, label, value, note in (
                    (rk1, "Best model (NDCG@10)", str(best["model_name"]).split(". ", 1)[-1].replace("Collaborative Filtering", "CF").split(" (")[0], f"NDCG@10 {best['ndcg_at_10']:.4f}"),
                    (rk2, "NDCG@10 vs best baseline", f"{best['ndcg_at_10'] / max(pop['ndcg_at_10'], 1e-9):.1f}x",
                     f"baseline: {str(pop['model_name']).split('. ', 1)[-1]}"),
                    (rk3, "Hit rate @10", f"{best['hit_rate_at_10'] * 100:.1f}%", "users with >= 1 relevant item in top 10"),
                    (r4, "Catalogue coverage", f"{best['catalogue_coverage_pct']:.1f}%", "share of products ever recommended"),
                ):
                    col.metric(label, value)
                    col.caption(note)

            st.divider()
            st.markdown("### 📋 Comprehensive 7-Model Evaluation Matrix")
            if not rec_df.empty:
                st.dataframe(rec_df, width="stretch", hide_index=True)

            st.divider()
            st.markdown("### 💡 What is served in production")
            st.markdown(
                """
                - **Model:** item-to-item collaborative filtering (shrunk cosine similarity between products, from
                  views / carts / purchases), scored on the shopper's history plus clicks in the current session.
                - **Cold start:** new visitors get popular products, narrowed to categories picked at onboarding.
                - **Business re-ranking:** out-of-stock items removed, a cap per brand, festival boost.
                - **Caveat:** the A/B replay showed most of the conversion gain comes from showing shoppers products
                  they had already browsed; discovery of new products was not significantly better.
                """
            )

        # 4. A/B Testing & ABSA Reviews
        elif ent_view == "📊 A/B Testing & ABSA Reviews":
            st.markdown(
                "## 📊 Executive Analytics & A/B Experimentation Console\n"
                "*Statistical Rollout Decision, 6-Aspect ABSA Review Intelligence, Customer RFM Personas, and API Telemetry.*"
            )

            ab_df = snapshot["ab_test_results"]
            ab_sum = snapshot.get("ab_summary", {}).get("experiment_summary", {})
            if ab_sum:
                decision_box = {"SHIP": st.success, "DO NOT SHIP": st.error}.get(ab_sum["decision"], st.warning)
                decision_box(
                    f"### Rollout decision: {ab_sum['decision']} (`{ab_sum['experiment_id']}`)\n"
                    f"{ab_sum['decision_reason']}\n\n"
                    f"Replay of real test-window behaviour: **{ab_sum['visitors']:,} visitors** "
                    f"({ab_sum['control_users']:,} control / {ab_sum['treatment_users']:,} treatment). "
                    "Full write-up: `reports/day5_ab_test_ship_decision_report.md`."
                )
            else:
                st.info("No A/B test results yet. Run `python scripts/run_day5.py`.")

            if not ab_df.empty:
                # Show control -> treatment values, not just relative lift: a +500% lift on a 0.009% base is
                # 7 vs 42 buyers, and the reader should see that directly.
                rows = list(ab_df.iterrows())
                for start in range(0, len(rows), 3):  # 3 per row so values are not truncated
                    m_cols = st.columns(3)
                    for col, (_, m_row) in zip(m_cols, rows[start : start + 3]):
                        p_val = float(m_row.get("p_value_holm", m_row["p_value"]))
                        unit = str(m_row.get("unit", ""))
                        fmt = (lambda v: f"PKR {v:,.2f}") if unit == "PKR" else (lambda v: f"{v:.3g}%")
                        with col:
                            st.metric(
                                label=f"{m_row['metric']}: treatment",
                                value=fmt(float(m_row["treatment_mean"])),
                            )
                            counts = ""
                            if unit == "%" and pd.notna(m_row.get("control_successes")):
                                counts = f" ({int(m_row['control_successes']):,} → {int(m_row['treatment_successes']):,} visitors)"
                            verdict = "significant" if p_val < 0.05 else "not significant"
                            st.caption(
                                f"control {fmt(float(m_row['control_mean']))}{counts}  \n"
                                f"{m_row['relative_lift_pct']:+.0f}% relative · "
                                f"{'p < 1e-15' if p_val < 1e-15 else f'p = {p_val:.2g}'} ({verdict})"
                            )
                st.dataframe(
                    _readable_p_values(ab_df), width="stretch", hide_index=True
                )

            sub_df = snapshot.get("ab_segment_subgroups", pd.DataFrame())
            if not sub_df.empty:
                st.markdown("##### 👥 Results by customer segment (exploratory, not used for the decision)")
                st.dataframe(_readable_p_values(sub_df), width="stretch", hide_index=True)

            st.divider()
            st.markdown("### 🧪 Live Multilingual Review & 6-Aspect ABSA Sandbox")
            sample_rev_presets = [
                ("Mixed Roman Urdu (Quality vs Delivery)", "Product bohot acha hai lekin delivery 10 din late aayi", 3),
                ("Sizing & Packaging Complaint", "Kapra aur finishing zabardast hai magar size thora chhota hai aur packing phata hua tha", 3),
                ("Urdu Script Verified Praise", "سفائر کی یہ پراڈکٹ بہت شاندار ہے۔ کوالٹی اور پیکنگ دونوں لاجواب ہیں، قیمت بھی مناسب ہے۔", 5),
                ("Promotional Link / Spam", "Visit www.cheap-deals-pk.biz or WhatsApp 0300-0000000 for 90% off replicas!!", 5),
            ]
            sr_cols = st.columns(len(sample_rev_presets))
            if "sandbox_rev_text" not in st.session_state:
                st.session_state["sandbox_rev_text"] = sample_rev_presets[0][1]
                st.session_state["sandbox_rev_rating"] = sample_rev_presets[0][2]

            for idx_sr, (s_lbl, s_txt, s_rt) in enumerate(sample_rev_presets):
                if sr_cols[idx_sr].button(s_lbl, key=f"s_btn_{idx_sr}", width="stretch"):
                    st.session_state["sandbox_rev_text"] = s_txt
                    st.session_state["sandbox_rev_rating"] = s_rt

            r_in1, r_in2 = st.columns([4, 1])
            with r_in1:
                rev_txt = st.text_input("Review Text:", value=st.session_state["sandbox_rev_text"])
            with r_in2:
                rev_rt = st.slider("Rating", min_value=1, max_value=5, value=int(st.session_state["sandbox_rev_rating"]))

            if rev_txt:
                live_res = analyze_live_review_text(rev_txt, rating=rev_rt)
                la1, la2, la3 = st.columns(3)
                la1.metric("Predicted Sentiment", live_res["overall_sentiment"])
                la2.metric("Contrastive Clauses", len(live_res["clauses"]))
                la3.metric("Spam Classification", f"🚨 SPAM ({live_res['spam_reason']})" if live_res["is_fake_spam"] else "✅ Genuine")

                asp_cols = st.columns(6)
                for idx_a, a_name in enumerate(ASPECT_NAMES):
                    v_sc = live_res["aspects"][a_name]
                    asp_cols[idx_a].metric(a_name, f"{v_sc:+d}")

            st.divider()
            gems_df = snapshot["unfairly_penalized_gems"]
            n_gems = len(gems_df)
            st.markdown(
                f"### 💎 {n_gems} product{'s' if n_gems != 1 else ''} unfairly penalised by courier delays"
            )
            st.caption(
                "Rule: at least 65% of reviews praise quality, at least 35% complain about delivery, and the average "
                "rating is below 4.15. Aspects come from the review analyzer's predictions."
            )
            if n_gems:
                st.dataframe(gems_df, width="stretch", hide_index=True)
            else:
                st.info("No product currently meets the rule.")

        # 5. Hybrid Search Analytics
        elif ent_view == "🔍 Hybrid Search Analytics":
            st.markdown(
                "## 🔍 Hybrid Multilingual Search Benchmarks & Query Intelligence\n"
                "*Keyword (BM25) vs semantic (TF-IDF + SVD) vs hybrid search on 50 dev + 20 held-out labelled queries.*"
            )

            s_bench = snapshot.get("search_benchmarks", pd.DataFrame())
            if not s_bench.empty and "query_set" in s_bench.columns:
                # Headline = the 20 held-out queries (never used for tuning); dev numbers are in the table below.
                hold = s_bench[s_bench["query_set"] == "holdout_20"]
                hyb = hold[hold["architecture_name"].str.contains("Hybrid")].iloc[0]
                kw = hold[hold["architecture_name"].str.contains("BM25") & ~hold["architecture_name"].str.contains("Hybrid")].iloc[0]
                sk1, sk2, sk3, sk4 = st.columns(4)
                for col, label, value, note in (
                    (sk1, "Hybrid NDCG@10 (held-out)", f"{hyb['ndcg_at_10']:.3f}", f"keyword only: {kw['ndcg_at_10']:.3f}"),
                    (sk2, "Precision@5 (held-out)", f"{hyb['precision_at_5'] * 100:.0f}%", f"keyword only: {kw['precision_at_5'] * 100:.0f}%"),
                    (sk3, "Budget respected", f"{hyb['budget_compliance_pct']:.0f}%", f"keyword only: {kw['budget_compliance_pct']:.0f}%"),
                    (sk4, "Avg latency (benchmark)", f"{hyb['avg_latency_ms']:.1f} ms", f"{int(hyb['queries_evaluated'])} held-out queries"),
                ):
                    col.metric(label, value)
                    col.caption(note)

            st.divider()
            st.markdown("### 📋 Search Architecture Benchmark Results")
            if not s_bench.empty:
                st.dataframe(s_bench, width="stretch", hide_index=True)

            st.divider()
            st.markdown("### 🔎 Production Query Pipeline")
            st.markdown(
                """
                1. **Query understanding:** Roman Urdu / Urdu to English translation, budget parsing (*"20 hazaar tak"*,
                   *"3000 se kam"*, *"1.5 lac"*), product type, colour, occasion and brand detection.
                2. **Two retrievers:** Okapi BM25 keyword search and a TF-IDF + SVD semantic index (not a neural model).
                3. **Reciprocal Rank Fusion (RRF, k=60):** merges the two ranked lists.
                4. **Feature re-ranker:** boosts matching product type / colour / occasion / brand; out-of-stock and
                   over-budget items are removed.
                """
            )

        # 6. AI System Health & Telemetry
        elif ent_view == "⚡ AI System Health & Telemetry":
            st.markdown(
                "## ⚡ AI System Health, Latency SLAs & Service Telemetry\n"
                "*Real-Time Telemetry Monitored via `/health` and `/metrics` Serving Engine.*"
            )

            h_status = health_check()
            m_status = metrics_endpoint()

            # Latency: live API numbers when there is traffic; otherwise the last measured benchmark, labelled as such.
            # (The dashboard calls the models in-process, so its own clicks never reach the API latency tracker.)
            overall = m_status.get("latency", {}).get("overall", {})
            if overall.get("recommendation_p95_ms") is not None:
                lat_value = f"{overall['recommendation_p95_ms']:.1f} ms"
                lat_note = "live recommendation requests; target < 100 ms"
            else:
                measured = snapshot.get("ab_summary", {}).get("guardrails", {}).get("recommendation_latency_p95_ms")
                lat_value = f"{measured:.1f} ms" if measured is not None else "not measured"
                lat_note = "last benchmark run (no live API traffic yet); target < 100 ms"
            cache = h_status.get("cache", {})
            tk1, tk2, tk3, tk4 = st.columns(4)
            for col, label, value, note in (
                (tk1, "Service status", str(h_status.get("status", "unknown")).upper(), f"assistant: {h_status.get('assistant_engine', 'n/a')}"),
                (tk2, "DuckDB tables", f"{h_status.get('tables_count', 0)}", "read-only connection"),
                (tk3, "Cache hit rate", f"{cache.get('hit_rate_pct', 0.0):.1f}%", f"{cache.get('hits', 0)} hits / {cache.get('misses', 0)} misses"),
                (tk4, "Recommendation p95 latency", lat_value, lat_note),
            ):
                col.metric(label, value)
                col.caption(note)

            st.divider()
            st.markdown("### 📊 Operational Telemetry Payload")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("##### Health Check Status (`/health`)")
                st.json(h_status)
            with t_col2:
                st.markdown("##### Telemetry & Latencies (`/metrics`)")
                st.json(m_status)

    # Start loading models only after the first page has been rendered: the loader is CPU-bound Python and would
    # otherwise compete with the first render for the GIL. (No-op once started or loaded.)
    _start_model_warmup(st)


if __name__ == "__main__":
    run_streamlit_app()