"""
Tests for mapping RetailRocket's category tree onto Pakistani categories (Day 1 data foundation).

Unit tests use a tiny hand-made tree. The data test checks the built catalogue: categories follow the
RetailRocket tree, so items browsed together mostly share a category (random labels would give ~12%).
"""

from __future__ import annotations

from collections import Counter

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.data.category_mapping import assign_groups_to_categories, level1_groups
from shopkaro.data.synthesizer import CATEGORY_TEMPLATES, CATEGORY_WEIGHTS, CURATED_HERO_PRODUCTS

#        1 (root)           2 (root)
#       /      \               |
#     10        11            20
#    /  \        |             |
#  100  101     110           200
TREE = pd.DataFrame(
    {
        "category_id": [1, 2, 10, 11, 20, 100, 101, 110, 200],
        "parent_id": [None, None, 1, 1, 2, 10, 10, 11, 20],
    }
)


def test_level1_groups_roll_leaves_up_to_child_of_root() -> None:
    group, root = level1_groups(TREE)
    assert group[100] == group[101] == group[10] == 10
    assert group[110] == 11
    assert group[200] == 20
    assert group[1] == 1  # a root is its own group
    assert root[101] == 1 and root[200] == 2


def test_assignment_matches_target_mix_and_is_deterministic() -> None:
    sizes = {g: n for g, n in enumerate([400, 300, 200, 50, 30, 20], start=1)}
    roots = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3}
    cats, weights = ["A", "B", "C"], np.array([0.5, 0.3, 0.2])
    a1 = assign_groups_to_categories(sizes, roots, cats, weights)
    a2 = assign_groups_to_categories(sizes, roots, cats, weights)
    assert a1 == a2
    got = Counter()
    for g, c in a1.items():
        got[c] += sizes[g]
    total = sum(sizes.values())
    for c, w in zip(cats, weights):
        assert abs(got[c] / total - w) <= 0.15


def test_built_catalogue_follows_retailrocket_tree() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    cat = con.execute(
        "SELECT product_id, raw_itemid, category, category_source, rr_categoryid, is_curated_hero FROM product_catalogue"
    ).df()
    mapping = con.execute("SELECT * FROM category_mapping").df()
    pairs = con.execute(
        """
        WITH s AS (SELECT DISTINCT session_id, product_id FROM interactions_clean),
        p AS (
            SELECT a.product_id AS x, b.product_id AS y
            FROM s a JOIN s b ON a.session_id = b.session_id AND a.product_id < b.product_id
            USING SAMPLE 200000 ROWS
        )
        SELECT AVG(CASE WHEN c1.category = c2.category THEN 1.0 ELSE 0.0 END)
        FROM p JOIN product_catalogue c1 ON c1.product_id = p.x JOIN product_catalogue c2 ON c2.product_id = p.y
        """
    ).fetchone()[0]
    con.close()

    # No random categories; >= 90% come straight from the RetailRocket tree
    assert "random_legacy" not in set(cat["category_source"])
    assert (cat["category_source"] == "retailrocket_tree").mean() >= 0.90

    # Category mix stays close to the target marketplace mix
    share = cat["category"].value_counts(normalize=True)
    for name, w in zip(CATEGORY_TEMPLATES, CATEGORY_WEIGHTS / CATEGORY_WEIGHTS.sum()):
        assert abs(share.get(name, 0.0) - w) <= 0.03, name

    # Every RetailRocket group maps to exactly one Pakistani category
    assert mapping.groupby("rr_group_id")["category"].nunique().max() == 1

    # Heroes keep SK-00001.. codes and their curated categories
    heroes = cat[cat["is_curated_hero"]].sort_values("product_id")
    assert list(heroes["product_id"]) == [f"SK-{i:05d}" for i in range(1, len(CURATED_HERO_PRODUCTS) + 1)]
    assert list(heroes["category"]) == [h["category"] for h in CURATED_HERO_PRODUCTS]

    # Co-browsed products share a category far more often than random labels would (~12%)
    assert pairs >= 0.45, f"same-category share of co-browsed pairs: {pairs:.1%}"
