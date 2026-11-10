"""
Day 4 — Task 4 / Task 5 additions: "What customers say" summaries, falling sentiment, top complaints, and the
weekly management insight report (LLM-written prose, every number computed here).

All inputs are the analyzer's PREDICTIONS per review (see ReviewIntelligencePipeline.predict_review_labels), not
the synthetic generator's labels.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from shopkaro.config.settings import settings

ASPECT_COLS = {
    "quality": "aspect_quality",
    "price": "aspect_price",
    "delivery": "aspect_delivery",
    "size_fit": "aspect_size_fit",
    "packaging": "aspect_packaging",
    "seller": "aspect_seller",
}
PRAISE_UR = {
    "quality": "cheez ki quality",
    "price": "qeemat",
    "delivery": "delivery ki speed",
    "size_fit": "size aur fitting",
    "packaging": "packing",
    "seller": "seller ka rawaiya",
}
COMPLAINT_UR = {
    "quality": "quality achi nahi thi",
    "price": "qeemat zyada hai",
    "delivery": "delivery late thi",
    "size_fit": "size theek nahi tha",
    "packaging": "packing kharab thi",
    "seller": "seller ne theek jawab nahi diya",
}
MIN_COMPLAINT_SHARE = 15.0


def _aspect_shares(df: pd.DataFrame) -> pd.DataFrame:
    """Per product: % of genuine reviews praising (+1) / criticising (-1) each aspect."""
    g = df.groupby("product_id")
    out = pd.DataFrame({"n_reviews": g.size()})
    for asp, col in ASPECT_COLS.items():
        out[f"{asp}_pos_pct"] = g[col].apply(lambda s: float((s == 1).mean() * 100))
        out[f"{asp}_neg_pct"] = g[col].apply(lambda s: float((s == -1).mean() * 100))
    return out


def customer_summaries(predicted_df: pd.DataFrame) -> pd.Series:
    """
    One Roman Urdu sentence per product, e.g.
    "Zyada tar customers (82%) ko cheez ki quality pasand aayi, lekin 31% ne kaha size theek nahi tha."
    Numbers are shares of the product's genuine reviews.
    """
    genuine = predicted_df[~predicted_df["is_fake_spam"]]
    shares = _aspect_shares(genuine)
    texts = {}
    for pid, r in shares.iterrows():
        best = max(ASPECT_COLS, key=lambda a: r[f"{a}_pos_pct"])
        worst = max(ASPECT_COLS, key=lambda a: r[f"{a}_neg_pct"])
        pos, neg = round(r[f"{best}_pos_pct"]), round(r[f"{worst}_neg_pct"])
        lead = "Zyada tar customers" if pos >= 50 else "Kuch customers"
        text = f"{lead} ({pos}%) ko {PRAISE_UR[best]} pasand aayi" if pos > 0 else "Abhi tak koi khaas tareef nahi mili"
        if neg >= MIN_COMPLAINT_SHARE:
            text += f", lekin {neg}% ne kaha {COMPLAINT_UR[worst]}"
        texts[pid] = text + f". ({int(r['n_reviews'])} reviews)"
    return pd.Series(texts, name="what_customers_say")


def falling_sentiment(predicted_df: pd.DataFrame, months: int = 6, min_reviews: int = 4) -> pd.DataFrame:
    """Products whose positive-review share dropped: last `months` vs the `months` before (both with >= min_reviews)."""
    df = predicted_df[~predicted_df["is_fake_spam"]].copy()
    df["review_date"] = pd.to_datetime(df["review_date"])
    end = df["review_date"].max()
    recent_start = end - pd.DateOffset(months=months)
    prior_start = recent_start - pd.DateOffset(months=months)
    df["is_pos"] = (df["sentiment_label"] == "Positive").astype(float)
    recent = df[df["review_date"] > recent_start].groupby("product_id")["is_pos"].agg(["mean", "size"])
    prior = df[(df["review_date"] > prior_start) & (df["review_date"] <= recent_start)].groupby("product_id")["is_pos"].agg(["mean", "size"])
    j = recent.join(prior, lsuffix="_recent", rsuffix="_prior", how="inner")
    j = j[(j["size_recent"] >= min_reviews) & (j["size_prior"] >= min_reviews)]
    j["change_pct_points"] = (j["mean_recent"] - j["mean_prior"]) * 100

    # With ~5-15 reviews per period a 20-point drop often happens by chance; keep only drops that are
    # statistically significant (one-sided Fisher exact test, p < 0.05).
    from scipy.stats import fisher_exact

    def p_drop(r: pd.Series) -> float:
        pos_p, pos_r = round(r["mean_prior"] * r["size_prior"]), round(r["mean_recent"] * r["size_recent"])
        table = [[pos_p, r["size_prior"] - pos_p], [pos_r, r["size_recent"] - pos_r]]
        return float(fisher_exact(table, alternative="greater").pvalue)

    j = j[j["change_pct_points"] <= -20]
    j["p_value"] = j.apply(p_drop, axis=1) if len(j) else []
    j = j[j["p_value"] < 0.05].sort_values("change_pct_points")
    meta = predicted_df.drop_duplicates("product_id").set_index("product_id")[["brand", "category"]]
    return (
        j.join(meta)
        .assign(
            positive_pct_prior=lambda d: (d["mean_prior"] * 100).round(1),
            positive_pct_recent=lambda d: (d["mean_recent"] * 100).round(1),
            change_pct_points=lambda d: d["change_pct_points"].round(1),
        )
        .reset_index()[["product_id", "brand", "category", "size_prior", "positive_pct_prior", "size_recent",
                        "positive_pct_recent", "change_pct_points", "p_value"]]
        .rename(columns={"size_prior": "reviews_prior", "size_recent": "reviews_recent"})
    )


def top_complaints(predicted_df: pd.DataFrame, by: str, min_reviews: int = 30) -> pd.DataFrame:
    """Per category / seller: the aspect most often criticised and its share of genuine reviews."""
    df = predicted_df[~predicted_df["is_fake_spam"]]
    rows = []
    for key, g in df.groupby(by):
        if len(g) < min_reviews:
            continue
        neg = {asp: float((g[col] == -1).mean() * 100) for asp, col in ASPECT_COLS.items()}
        worst = max(neg, key=neg.get)
        rows.append({by: key, "genuine_reviews": len(g), "top_complaint": worst,
                     "complaint_share_pct": round(neg[worst], 1),
                     "negative_review_pct": round(float((g["sentiment_label"] == "Negative").mean() * 100), 1)})
    return pd.DataFrame(rows).sort_values("complaint_share_pct", ascending=False).reset_index(drop=True)


def save_insight_tables(predicted_df: pd.DataFrame, out_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    out = out_dir or settings.reports_dir
    tables = {
        "falling_sentiment": falling_sentiment(predicted_df),
        "complaints_by_category": top_complaints(predicted_df, "category"),
        "complaints_by_seller": top_complaints(predicted_df, "seller_id", min_reviews=15),
    }
    for name, df in tables.items():
        df.to_csv(out / f"day4_{name}.csv", index=False)
    return tables


# ----------------------------------------------------------------------------------------------- weekly report
def weekly_facts(con: Any, predicted_df: pd.DataFrame) -> dict[str, Any]:
    """All numbers for the weekly report: latest full week in the data vs the week before (SQL + pandas)."""
    week = con.execute(
        "SELECT date_trunc('week', MAX(review_date)) FROM reviews"
    ).fetchone()[0]
    df = predicted_df.copy()
    df["review_date"] = pd.to_datetime(df["review_date"])
    this_w = df[(df["review_date"] >= week) & (df["review_date"] < week + pd.Timedelta(days=7))]
    prev_w = df[(df["review_date"] >= week - pd.Timedelta(days=7)) & (df["review_date"] < week)]

    def stats(w: pd.DataFrame) -> dict[str, Any]:
        g = w[~w["is_fake_spam"]]
        return {
            "reviews": int(len(w)),
            "spam_filtered": int(w["is_fake_spam"].sum()),
            "positive_pct": round(float((g["sentiment_label"] == "Positive").mean() * 100), 1) if len(g) else 0.0,
            "negative_pct": round(float((g["sentiment_label"] == "Negative").mean() * 100), 1) if len(g) else 0.0,
            "delivery_complaint_pct": round(float((g["aspect_delivery"] == -1).mean() * 100), 1) if len(g) else 0.0,
        }

    cats = top_complaints(this_w, "category", min_reviews=5).head(3)
    falling = falling_sentiment(predicted_df).head(3)
    alerts = con.execute(
        "SELECT alert_status, COUNT(*) FROM inventory_alerts GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall() if "inventory_alerts" in {r[0] for r in con.execute("SHOW TABLES").fetchall()} else []
    sellers = con.execute(
        "SELECT COUNT(*) FROM seller_scorecards WHERE seller_tier = 'Courier_Bottlenecked_Seller'"
    ).fetchone()[0]
    return {
        "week_starting": pd.Timestamp(week).date().isoformat(),
        "this_week": stats(this_w),
        "previous_week": stats(prev_w),
        "top_complaints_by_category_this_week": cats.to_dict("records"),
        "products_with_falling_sentiment": falling[["product_id", "brand", "positive_pct_prior",
                                                    "positive_pct_recent"]].to_dict("records"),
        "sellers_with_delivery_problems": int(sellers),
        "inventory_alerts": {str(k): int(v) for k, v in alerts},
    }


_NUM = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}


def unsupported_numbers(report: str, facts: dict[str, Any]) -> set[str]:
    """Numbers in the report that do not appear in the facts (dates and IDs in the facts count as supported)."""
    allowed = _numbers(json.dumps(facts))
    allowed |= {str(int(float(a))) for a in allowed if re.fullmatch(r"\d+\.0", a)}
    return {n for n in _numbers(report) if n not in allowed and not n.startswith("0")}


def template_report(f: dict[str, Any]) -> str:
    t, p = f["this_week"], f["previous_week"]
    lines = [
        f"# Weekly customer & operations insights — week of {f['week_starting']}",
        "",
        f"- **Reviews:** {t['reviews']} this week (previous week {p['reviews']}); {t['spam_filtered']} filtered as spam.",
        f"- **Sentiment:** {t['positive_pct']}% positive, {t['negative_pct']}% negative "
        f"(previous week {p['positive_pct']}% / {p['negative_pct']}%).",
        f"- **Delivery complaints:** {t['delivery_complaint_pct']}% of reviews (previous week {p['delivery_complaint_pct']}%); "
        f"{f['sellers_with_delivery_problems']} sellers are flagged as courier-bottlenecked.",
    ]
    for c in f["top_complaints_by_category_this_week"]:
        lines.append(f"- **{c['category']}:** top complaint {c['top_complaint']} ({c['complaint_share_pct']}% of reviews).")
    for x in f["products_with_falling_sentiment"]:
        lines.append(f"- **Falling sentiment:** {x['product_id']} ({x['brand']}) {x['positive_pct_prior']}% -> "
                     f"{x['positive_pct_recent']}% positive.")
    if f["inventory_alerts"]:
        lines.append("- **Inventory:** " + ", ".join(f"{v} {k}" for k, v in f["inventory_alerts"].items()) + ".")
    return "\n".join(lines) + "\n"


def write_weekly_report(facts: dict[str, Any], use_llm: bool = True) -> tuple[str, str]:
    """
    Gemini writes the prose from the facts; if it cites any number not in the facts (or no key / call fails),
    the deterministic template is used. Returns (markdown, engine).
    """
    if use_llm and settings.llm_api_key:
        try:
            from google import genai

            client = genai.Client(api_key=settings.llm_api_key)
            prompt = (
                "You write a short weekly insight report for ShopKaro's management (markdown, max 250 words: a title, "
                "3-6 bullet findings, 2-3 recommended actions). Use ONLY the numbers in the JSON below, exactly as "
                "written; do not compute new numbers, do not round, do not invent anything.\n\n"
                + json.dumps(facts, indent=2)
            )
            text = client.models.generate_content(model=settings.llm_model, contents=prompt).text or ""
            bad = unsupported_numbers(text, facts)
            if text.strip() and not bad:
                return text.strip() + "\n", f"llm ({settings.llm_model})"
        except Exception:
            pass
    return template_report(facts), "template"
