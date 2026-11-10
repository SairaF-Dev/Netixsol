"""
Tests for the search benchmark (graded relevance, catalogue-wide NDCG) and for query-understanding fixes
found with it. Grading tests use a tiny hand-made catalogue; parser tests use the real one.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from shopkaro.config.settings import settings
from shopkaro.search.benchmark import HOLDOUT_QUERIES, QUERIES, evaluate_systems, grade_catalogue
from shopkaro.search.hybrid_search import HybridSearchEngine

TOY = pd.DataFrame(
    {
        "product_id": [f"P{i}" for i in range(6)],
        "sub_category": ["Boski Silk Kurta", "Boski Silk Kurta", "Boski Silk Kurta", "Cotton Embroidered Kurta", "Festive Waistcoat", "Boski Silk Kurta"],
        "color": ["Crisp White", "Black", "Crisp White", "Crisp White", "Black", "Crisp White"],
        "occasion": ["Eid", "Eid", "Eid", "Eid", "Eid", "Eid"],
        "brand": ["MTJ", "MTJ", "MTJ", "MTJ", "MTJ", "MTJ"],
        "price_pkr": [3000, 3000, 9000, 3000, 3000, 3000],
        "stock_qty": [10, 10, 10, 10, 10, 0],
    }
)
SPEC = {"q": "white boski kurta under 5000", "types": ["Boski Silk Kurta"], "colors": ["white"], "max_price": 5000, "lang": "english", "tag": "t"}


def test_grades_follow_type_budget_stock_and_preferences() -> None:
    # P0 perfect; P1 wrong colour (1); P2 over budget (0); P3 wrong type (0); P4 wrong type (0); P5 out of stock (0)
    assert grade_catalogue(SPEC, TOY).tolist() == [2, 1, 0, 0, 0, 0]


def test_ndcg_uses_catalogue_wide_ideal() -> None:
    """Regression: one relevant result at rank 1 must not score a perfect 1.0 when better items exist."""
    only_grade1 = {"sys": lambda q: [{"product_id": "P1", "price_pkr": 3000}]}
    summary, _ = evaluate_systems(only_grade1, TOY, [SPEC])
    assert summary["ndcg_at_10"].iloc[0] < 1.0
    perfect = {"sys": lambda q: [{"product_id": "P0", "price_pkr": 3000}, {"product_id": "P1", "price_pkr": 3000}]}
    summary, _ = evaluate_systems(perfect, TOY, [SPEC])
    assert summary["ndcg_at_10"].iloc[0] == pytest.approx(1.0)


def test_every_benchmark_query_is_answerable() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    cat = con.execute("SELECT * FROM product_catalogue").df()
    con.close()
    assert len(QUERIES) == 50 and len(HOLDOUT_QUERIES) == 20
    assert not {q["q"] for q in QUERIES} & {q["q"] for q in HOLDOUT_QUERIES}
    for spec in QUERIES + HOLDOUT_QUERIES:
        assert (grade_catalogue(spec, cat) == 2).sum() >= 1, spec["q"]


@pytest.fixture(scope="module")
def engine() -> HybridSearchEngine:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    eng = HybridSearchEngine(rrf_k=60).fit_from_duckdb(con)
    con.close()
    return eng


@pytest.mark.parametrize(
    ("query", "expected_type"),
    [
        ("shaadi ke liye waistcoat", "Festive Waistcoat"),  # occasion word must not override the product
        ("kashmiri shawl", "Woolen Kashmiri Shawl"),
        ("leather jacket mardana", "Men's Leather Jacket"),
        ("mobile cover silicone", "Silicone Back Cover"),  # expansion must not turn it into a phone search
        ("jummah ke liye boski kurta", "Boski Silk Kurta"),
        ("barat ke liye bridal lehnga", "Bridal Embroidered Lehenga"),  # spelling variant
    ],
)
def test_product_type_is_understood(engine: HybridSearchEngine, query: str, expected_type: str) -> None:
    parsed = engine.parser.parse(query)
    assert parsed.type_hints and parsed.type_hints[0] == expected_type
    top3 = engine.search_hybrid(query, k=3)[0]
    assert all(r["sub_category"] == expected_type for r in top3)


def test_budget_and_occasion_parsing(engine: HybridSearchEngine) -> None:
    assert engine.parser.parse("pastel pink 2 piece printed lawn 3000 se kam").max_price_pkr == 3000
    assert engine.parser.parse("barat ke liye bridal lehnga").occasion_hint == "Bridal/Barat"
    assert engine.parser.parse("walima maxi dress").occasion_hint == "Walima"
    assert engine.parser.parse("eid ke liye lawn suit").occasion_hint == "Eid"
    results, parsed = engine.search_hybrid("pastel pink 2 piece printed lawn 3000 se kam", k=5)
    assert all(r["price_pkr"] <= 3000 for r in results)
