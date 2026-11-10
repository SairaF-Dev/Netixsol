"""
Day 4 Task 1: 50-query search benchmark with graded relevance and catalogue-wide NDCG@10.

How relevance is defined (independently of any search system)
-------------------------------------------------------------
Each query has a hand-written spec describing what the shopper MEANS, in terms of product attributes:
  - `types`: acceptable product sub-categories (hard: anything else is irrelevant)
  - `max_price` / `min_price`: budget (hard)
  - `colors`, `occasions`, `brands`: preferences (soft), matched as lowercase substrings
Grades: 0 = wrong type, over budget or out of stock; 1 = right type within budget but misses a stated
preference; 2 = matches everything stated. Specs were written from the query text, never from a parser's
output, so a system only scores well if it understands the query.

How NDCG is computed
--------------------
Gains 2^grade - 1, discount 1/log2(rank+1). The ideal ranking is the best 10 products in the WHOLE in-stock
catalogue (every product can be graded because relevance is a function of its attributes). The previous
evaluation normalised by the relevant items each system happened to return, which let a system with one
relevant result at rank 1 score a perfect 1.0.

Limitation: grades are attribute rules, not human judgements of each result. They are exact for this
catalogue because titles are generated from the same attributes, but they cannot judge e.g. style or quality.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

import numpy as np
import pandas as pd

LAWN = ["3-Piece Lawn Suit", "2-Piece Printed Lawn", "Embroidered Eid Lawn"]
KURTA = ["Cotton Embroidered Kurta", "Boski Silk Kurta"]
SCHOOL_BAGS = ["Waterproof Ergonomic School Bag", "Kids Cartoon Backpack"]
CODING_LAPTOPS = ["Core i5 Coding Laptop 16GB RAM", "Ryzen 7 Programming Laptop"]

# lang: roman_urdu | english | urdu | mixed. tag: what the query tests.
QUERIES: list[dict[str, Any]] = [
    # --- Women's lawn & unstitched ---
    {"q": "eid ke liye lawn suit under 5000", "types": LAWN, "max_price": 5000, "occasions": ["eid"], "lang": "roman_urdu", "tag": "brief_example"},
    {"q": "sapfire emerald green unstitched lawn suit", "types": LAWN, "brands": ["sapphire"], "colors": ["emerald"], "lang": "english", "tag": "brand_typo"},
    {"q": "black chiffon dupatta suit", "types": ["Chiffon Dupatta Suit"], "colors": ["black"], "lang": "english", "tag": "color"},
    {"q": "khaadi embroidered shawl", "types": ["Embroidered Shawl"], "brands": ["khaadi"], "lang": "english", "tag": "brand"},
    {"q": "pastel pink 2 piece printed lawn 3000 se kam", "types": ["2-Piece Printed Lawn"], "colors": ["pink"], "max_price": 3000, "lang": "roman_urdu", "tag": "price_format"},
    {"q": "garmiyon ke liye halka lawn kapra", "types": LAWN, "occasions": ["summer"], "lang": "roman_urdu", "tag": "roman_urdu_vocab"},
    {"q": "عید کے لیے لان کا سوٹ", "types": LAWN, "occasions": ["eid"], "lang": "urdu", "tag": "urdu_script"},
    {"q": "gul ahmed 3 piece lawn maroon", "types": ["3-Piece Lawn Suit"], "brands": ["gul ahmed"], "colors": ["maroon"], "lang": "english", "tag": "brand_color"},
    # --- Men's kurta & ethnic ---
    {"q": "mardana white kurta eid ke liye under 4000", "types": KURTA, "colors": ["white"], "max_price": 4000, "occasions": ["eid"], "lang": "roman_urdu", "tag": "multi_constraint"},
    {"q": "wash and wear shalwar kameez", "types": ["Wash & Wear Shalwar Kameez"], "lang": "english", "tag": "product_type"},
    {"q": "shaadi ke liye waistcoat", "types": ["Festive Waistcoat"], "occasions": ["shaadi"], "lang": "roman_urdu", "tag": "occasion"},
    {"q": "jummah ke liye boski kurta", "types": ["Boski Silk Kurta"], "occasions": ["jummah"], "lang": "roman_urdu", "tag": "occasion"},
    {"q": "junaid jamshed navy blue kurta", "types": KURTA, "brands": ["junaid jamshed"], "colors": ["navy"], "lang": "english", "tag": "brand_color"},
    # --- Bridal & formal ---
    {"q": "shaadi ke liye red lehenga 20 hazaar tak", "types": ["Bridal Embroidered Lehenga"], "colors": ["red"], "max_price": 20000, "lang": "roman_urdu", "tag": "brief_example"},
    {"q": "barat ke liye bridal lehnga", "types": ["Bridal Embroidered Lehenga"], "occasions": ["barat"], "lang": "roman_urdu", "tag": "spelling_variant"},
    {"q": "walima maxi dress champagne", "types": ["Shaadi Maxi Dress"], "colors": ["champagne"], "occasions": ["walima"], "lang": "english", "tag": "occasion_color"},
    {"q": "maria b gharara suit", "types": ["Zari Gharara Suit"], "brands": ["maria b"], "lang": "english", "tag": "brand"},
    {"q": "formal velvet shawl for wedding", "types": ["Velvet Formal Shawl"], "occasions": ["shaadi", "wedding"], "lang": "english", "tag": "product_type"},
    {"q": "دلہن کا لہنگا", "types": ["Bridal Embroidered Lehenga"], "lang": "urdu", "tag": "urdu_script"},
    # --- Footwear ---
    {"q": "traditional golden khussa joota shaadi ke liye", "types": ["Traditional Punjabi Khussa"], "colors": ["golden"], "occasions": ["shaadi"], "lang": "roman_urdu", "tag": "multi_constraint"},
    {"q": "school ke liye black juta", "types": ["School Uniform Shoes"], "colors": ["black"], "lang": "roman_urdu", "tag": "spelling_variant"},
    {"q": "running shoes for men under 5000", "types": ["Running Sneakers"], "max_price": 5000, "lang": "english", "tag": "synonym"},
    {"q": "peshawari chappal tan brown", "types": ["Peshawari Chappal"], "colors": ["tan"], "lang": "english", "tag": "color"},
    {"q": "eid par pehnne wali heels", "types": ["Festive Block Heels"], "occasions": ["eid"], "lang": "roman_urdu", "tag": "roman_urdu_vocab"},
    # --- Smartphones & accessories ---
    {"q": "samsung 5g mobile phone pta approved", "types": ["5G Smartphone"], "brands": ["samsung"], "lang": "english", "tag": "brand"},
    {"q": "sasta 5g phone 50000 se kam", "types": ["5G Smartphone"], "max_price": 50000, "lang": "roman_urdu", "tag": "price_format"},
    {"q": "fast charger 45w", "types": ["Fast Charger 45W"], "lang": "english", "tag": "product_type"},
    {"q": "wireless earbuds under 5k", "types": ["Wireless Earbuds"], "max_price": 5000, "lang": "english", "tag": "price_format"},
    {"q": "power bank 20000mah anker", "types": ["Power Bank 20000mAh"], "brands": ["anker"], "lang": "english", "tag": "brand"},
    {"q": "mobile cover silicone", "types": ["Silicone Back Cover"], "lang": "english", "tag": "synonym"},
    # --- Laptops & computing ---
    {"q": "laptop for coding under 1.5 lac", "types": CODING_LAPTOPS, "max_price": 150000, "lang": "english", "tag": "brief_example"},
    {"q": "student laptop ssd", "types": ["Student Notebook SSD"], "lang": "english", "tag": "product_type"},
    {"q": "gaming keyboard mechanical", "types": ["Mechanical Gaming Keyboard"], "lang": "english", "tag": "product_type"},
    {"q": "wireless mouse logitech", "types": ["Wireless Mouse"], "brands": ["logitech"], "lang": "english", "tag": "brand"},
    # --- Kids & school ---
    {"q": "bachon ke liye school bag", "types": SCHOOL_BAGS, "lang": "roman_urdu", "tag": "brief_example"},
    {"q": "بچوں کے لیے اسکول بیگ", "types": SCHOOL_BAGS, "lang": "urdu", "tag": "urdu_script"},
    {"q": "lunch box aur water bottle", "types": ["Lunch Box & Water Bottle Set"], "lang": "mixed", "tag": "product_type"},
    {"q": "geometry box stationery set", "types": ["Complete Geometry & Stationery Kit"], "lang": "english", "tag": "synonym"},
    # --- Beauty & fragrances / gifts ---
    {"q": "Ammi ke liye Eid gift chahiye 3000 tak", "types": ["Embroidered Shawl", "Oud & Attar Perfume Gift Set", "Luxury Eau De Parfum", "Herbal Skincare Facial Kit"], "max_price": 3000, "occasions": ["eid", "gift"], "lang": "roman_urdu", "tag": "gift_intent"},
    {"q": "oud attar perfume", "types": ["Oud & Attar Perfume Gift Set", "Luxury Eau De Parfum"], "lang": "english", "tag": "product_type"},
    {"q": "halal lipstick set", "types": ["Halal Matte Lipstick Set"], "lang": "english", "tag": "product_type"},
    # --- Home & kitchen ---
    {"q": "air fryer 5 litre", "types": ["Air Fryer 5L"], "lang": "english", "tag": "unit_variant"},
    {"q": "juicer blender for kitchen", "types": ["Food Processor & Juicer Blender"], "lang": "english", "tag": "product_type"},
    {"q": "electric kettle under 8000", "types": ["Electric Kettle"], "max_price": 8000, "lang": "english", "tag": "budget"},
    # --- Groceries ---
    {"q": "ramzan iftar ke liye rooh afza aur basmati chawal", "types": ["Ramadan Iftar Rooh Afza & Dates Pack", "Super Kernel Basmati Rice 5kg"], "lang": "roman_urdu", "tag": "roman_urdu_vocab"},
    {"q": "biryani masala shan", "types": ["Biryani & Qorma Masala Value Pack"], "brands": ["shan"], "lang": "english", "tag": "brand"},
    {"q": "cooking oil 5 litre dalda", "types": ["Pure Cooking Oil 5L"], "brands": ["dalda"], "lang": "english", "tag": "brand"},
    # --- Winter wear ---
    {"q": "sardi ke liye black puffer winter jacket under 8000", "types": ["Puffer Winter Jacket"], "colors": ["black"], "max_price": 8000, "lang": "roman_urdu", "tag": "multi_constraint"},
    {"q": "leather jacket mardana", "types": ["Men's Leather Jacket"], "lang": "mixed", "tag": "roman_urdu_vocab"},
    {"q": "kashmiri shawl", "types": ["Woolen Kashmiri Shawl"], "lang": "english", "tag": "product_type"},
]


def grade_catalogue(spec: dict[str, Any], catalogue: pd.DataFrame) -> np.ndarray:
    """Relevance grade (0/1/2) of every catalogue product for one query spec."""
    ok = catalogue["sub_category"].isin(spec["types"]).to_numpy().copy()
    ok &= (catalogue["stock_qty"] > 0).to_numpy()
    if spec.get("max_price") is not None:
        ok &= (catalogue["price_pkr"] <= spec["max_price"]).to_numpy()
    if spec.get("min_price") is not None:
        ok &= (catalogue["price_pkr"] >= spec["min_price"]).to_numpy()
    full = ok.copy()
    for field, col in (("colors", "color"), ("occasions", "occasion"), ("brands", "brand")):
        wanted = [w.lower() for w in spec.get(field, [])]
        if wanted:
            vals = catalogue[col].astype(str).str.lower()
            full &= vals.apply(lambda v: any(w in v for w in wanted)).to_numpy()
    return np.where(full, 2, np.where(ok, 1, 0)).astype(int)


def _dcg(grades: np.ndarray, k: int) -> float:
    g = np.asarray(grades[:k], dtype=float)
    return float(np.sum((2.0**g - 1.0) / np.log2(np.arange(2, len(g) + 2))))


@dataclass
class QueryResult:
    system: str
    query: str
    lang: str
    tag: str
    ndcg_at_10: float
    mrr_at_10: float
    precision_at_5: float
    perfect_matches_top10: int
    budget_ok_top5_pct: float | None
    latency_ms: float


def evaluate_systems(
    systems: dict[str, Callable[[str], list[dict[str, Any]]]],
    catalogue: pd.DataFrame,
    queries: list[dict[str, Any]] | None = None,
    k: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (summary per system, per-query results)."""
    queries = queries or QUERIES
    catalogue = catalogue.reset_index(drop=True)
    index_of = {pid: i for i, pid in enumerate(catalogue["product_id"].astype(str))}
    rows: list[QueryResult] = []
    for spec in queries:
        grades = grade_catalogue(spec, catalogue)
        ideal = _dcg(np.sort(grades)[::-1], k)
        for name, search in systems.items():
            t0 = time.perf_counter()
            results = search(spec["q"])[:k]
            latency = (time.perf_counter() - t0) * 1000.0
            got = np.array([grades[index_of[str(r["product_id"])]] for r in results], dtype=int)
            hits = np.where(got > 0)[0]
            budget = None
            if spec.get("max_price") is not None and results:
                budget = 100.0 * float(np.mean([float(r["price_pkr"]) <= spec["max_price"] for r in results[:5]]))
            rows.append(
                QueryResult(
                    system=name,
                    query=spec["q"],
                    lang=spec["lang"],
                    tag=spec["tag"],
                    ndcg_at_10=round(_dcg(got, k) / ideal, 4) if ideal > 0 else 0.0,
                    mrr_at_10=round(1.0 / (hits[0] + 1), 4) if len(hits) else 0.0,
                    precision_at_5=round(float(np.mean(got[:5] > 0)) if len(got) else 0.0, 4),
                    perfect_matches_top10=int(np.sum(got == 2)),
                    budget_ok_top5_pct=budget,
                    latency_ms=round(latency, 2),
                )
            )
    per_query = pd.DataFrame([r.__dict__ for r in rows])
    summary = (
        per_query.groupby("system", sort=False)
        .agg(
            queries_evaluated=("query", "count"),
            ndcg_at_10=("ndcg_at_10", "mean"),
            mrr_at_10=("mrr_at_10", "mean"),
            precision_at_5=("precision_at_5", "mean"),
            budget_compliance_pct=("budget_ok_top5_pct", "mean"),
            zero_relevant_queries=("mrr_at_10", lambda s: int((s == 0).sum())),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .round(4)
        .reset_index()
        .rename(columns={"system": "architecture_name"})
    )
    return summary, per_query


def paired_comparison(per_query: pd.DataFrame, a: str, b: str, n_boot: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Paired bootstrap CI and sign test for NDCG@10 of system b minus system a over the same queries."""
    from scipy import stats

    pa = per_query[per_query["system"] == a].set_index("query")["ndcg_at_10"]
    pb = per_query[per_query["system"] == b].set_index("query")["ndcg_at_10"].reindex(pa.index)
    diff = (pb - pa).to_numpy()
    rng = np.random.default_rng(seed)
    boots = rng.choice(diff, size=(n_boot, len(diff)), replace=True).mean(axis=1)
    wins, losses = int((diff > 0).sum()), int((diff < 0).sum())
    sign_p = float(stats.binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0
    return {
        "baseline": a,
        "system": b,
        "mean_ndcg_diff": round(float(diff.mean()), 4),
        "ci_95": [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
        "queries_better": wins,
        "queries_worse": losses,
        "queries_tied": int(len(diff) - wins - losses),
        "sign_test_p": sign_p,
    }


# Held-out queries: written BEFORE any search fixes and never used to tune the system. Results on this set
# show whether improvements generalise or only fit the 50 development queries above.
HOLDOUT_QUERIES: list[dict[str, Any]] = [
    {"q": "nishat linen sky blue lawn", "types": LAWN, "brands": ["nishat"], "colors": ["sky blue"], "lang": "english", "tag": "brand_color"},
    {"q": "chiffon suit for eid 7000 tak", "types": ["Chiffon Dupatta Suit"], "max_price": 7000, "occasions": ["eid"], "lang": "roman_urdu", "tag": "multi_constraint"},
    {"q": "olive green kurta for men", "types": KURTA, "colors": ["olive"], "lang": "english", "tag": "color"},
    {"q": "ghararah for walima", "types": ["Zari Gharara Suit"], "occasions": ["walima"], "lang": "english", "tag": "spelling_variant"},
    {"q": "dusty rose maxi for nikkah under 30000", "types": ["Shaadi Maxi Dress"], "colors": ["dusty rose"], "max_price": 30000, "lang": "english", "tag": "multi_constraint"},
    {"q": "office ke liye joote", "types": ["School Uniform Shoes"], "occasions": ["office"], "lang": "roman_urdu", "tag": "roman_urdu_vocab"},
    {"q": "white sneakers", "types": ["Running Sneakers"], "colors": ["white"], "lang": "english", "tag": "color"},
    {"q": "redmi earbuds", "types": ["Wireless Earbuds"], "brands": ["redmi"], "lang": "english", "tag": "brand"},
    {"q": "phone ka charger fast charging", "types": ["Fast Charger 45W"], "lang": "roman_urdu", "tag": "synonym"},
    {"q": "dell laptop 2 lac tak", "types": CODING_LAPTOPS + ["Student Notebook SSD"], "brands": ["dell"], "max_price": 200000, "lang": "roman_urdu", "tag": "price_format"},
    {"q": "pelikan school bag navy blue", "types": SCHOOL_BAGS, "brands": ["pelikan"], "colors": ["navy"], "lang": "english", "tag": "brand_color"},
    {"q": "water bottle aur tiffin bachon ke liye", "types": ["Lunch Box & Water Bottle Set"], "lang": "roman_urdu", "tag": "synonym"},
    {"q": "skincare kit for women", "types": ["Herbal Skincare Facial Kit"], "lang": "english", "tag": "product_type"},
    {"q": "perfume under 2000", "types": ["Oud & Attar Perfume Gift Set", "Luxury Eau De Parfum"], "max_price": 2000, "lang": "english", "tag": "budget"},
    {"q": "microwave oven dawlance", "types": ["Microwave Oven"], "brands": ["dawlance"], "lang": "english", "tag": "brand"},
    {"q": "istri kapre press karne wali", "types": ["Steam Iron"], "lang": "roman_urdu", "tag": "roman_urdu_vocab"},
    {"q": "tapal chai", "types": ["Danedar Family Mixture Tea 900g"], "brands": ["tapal"], "lang": "roman_urdu", "tag": "brand"},
    {"q": "fleece hoodie navy", "types": ["Fleece Hoodie"], "colors": ["navy"], "lang": "english", "tag": "color"},
    {"q": "سردیوں کی جیکٹ", "types": ["Puffer Winter Jacket", "Men's Leather Jacket"], "lang": "urdu", "tag": "urdu_script"},
    {"q": "موبائل فون", "types": ["5G Smartphone"], "lang": "urdu", "tag": "urdu_script"},
]
