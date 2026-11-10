"""
Map RetailRocket's (anonymised) category tree onto ShopKaro's Pakistani categories.

Why: RetailRocket item IDs only become "Pakistani products" through this project's synthetic catalogue.
If each item gets a random category, items that real shoppers browse together end up with unrelated
labels (earbuds -> dupatta), so co-occurrence models, "bought together" and every category feature
become meaningless to a human. Mapping whole RetailRocket subtrees to one Pakistani category keeps
real co-browsing structure consistent with the labels.

Method:
1. Item -> its latest RetailRocket `categoryid` (item_properties; categories can change over time).
2. categoryid -> its level-1 ancestor in category_tree (child of a root; a root maps to itself).
3. Level-1 groups are assigned to Pakistani categories greedily, largest first, so category sizes match
   the target marketplace mix. Groups under the same root stay in the same Pakistani category while
   that category still has room, so sibling branches stay together.
4. Items with no RetailRocket category take the majority category of items browsed in the same
   sessions; if they have none, the category furthest below its target.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings


def load_latest_item_categories(con: duckdb.DuckDBPyConnection, raw_dir: Path | None = None) -> pd.DataFrame:
    """raw_itemid -> latest RetailRocket categoryid, from both item_properties CSV parts."""
    raw = raw_dir or settings.raw_retailrocket_dir
    files = [str(raw / f"item_properties_part{i}.csv").replace("\\", "/") for i in (1, 2)]
    return con.execute(
        f"""
        SELECT itemid AS raw_itemid, CAST(arg_max(value, "timestamp") AS INTEGER) AS rr_categoryid
        FROM read_csv({files}, header = true,
                      columns = {{'timestamp': 'BIGINT', 'itemid': 'BIGINT', 'property': 'VARCHAR', 'value': 'VARCHAR'}})
        WHERE property = 'categoryid'
        GROUP BY itemid
        """
    ).df()


def level1_groups(tree_df: pd.DataFrame) -> tuple[dict[int, int], dict[int, int]]:
    """For each category: its level-1 ancestor (group) and its root."""
    parent = {
        int(c): (int(p) if pd.notna(p) else None)
        for c, p in zip(tree_df["category_id"], tree_df["parent_id"])
    }
    group: dict[int, int] = {}
    root: dict[int, int] = {}
    for cat in parent:
        path = [cat]
        seen = {cat}
        while parent.get(path[-1]) is not None and parent[path[-1]] not in seen:
            seen.add(parent[path[-1]])
            path.append(parent[path[-1]])
        root[cat] = path[-1]
        group[cat] = path[-2] if len(path) >= 2 else path[-1]
    return group, root


def assign_groups_to_categories(
    group_sizes: dict[int, int],
    group_root: dict[int, int],
    categories: list[str],
    weights: np.ndarray,
) -> dict[int, str]:
    """Greedy, deterministic bin assignment of RetailRocket groups to Pakistani categories."""
    total = sum(group_sizes.values())
    remaining = {c: float(w) * total for c, w in zip(categories, weights)}
    root_sizes: Counter[int] = Counter()
    for g, n in group_sizes.items():
        root_sizes[group_root[g]] += n

    assignment: dict[int, str] = {}
    root_choice: dict[int, str] = {}
    # Roots largest first; within a root, groups largest first (ties broken by id for determinism)
    for r in sorted(root_sizes, key=lambda x: (-root_sizes[x], x)):
        groups = sorted((g for g in group_sizes if group_root[g] == r), key=lambda g: (-group_sizes[g], g))
        for g in groups:
            n = group_sizes[g]
            preferred = root_choice.get(r)
            if preferred is not None and remaining[preferred] >= n * 0.5:
                choice = preferred
            else:
                choice = max(categories, key=lambda c: (remaining[c], -categories.index(c)))
            assignment[g] = choice
            remaining[choice] -= n
            root_choice.setdefault(r, choice)
    return assignment


def map_items_to_categories(
    con: duckdb.DuckDBPyConnection,
    active_item_ids: list[int],
    categories: list[str],
    weights: np.ndarray,
    session_table: str = "sessionized_events",
) -> pd.DataFrame:
    """
    Returns one row per active item: raw_itemid, rr_categoryid, rr_group_id, category, category_source
    (`retailrocket_tree` or `session_neighbours` or `fallback_deficit`).
    """
    weights = np.asarray(weights, dtype=float) / np.sum(weights)
    item_cat = load_latest_item_categories(con)
    tree = con.execute("SELECT category_id, parent_id FROM raw_category_tree").df()
    group_of, root_of = level1_groups(tree)

    items = pd.DataFrame({"raw_itemid": [int(i) for i in active_item_ids]})
    items = items.merge(item_cat, on="raw_itemid", how="left")
    items["rr_group_id"] = items["rr_categoryid"].map(
        lambda c: group_of.get(int(c), int(c)) if pd.notna(c) else None
    )

    known = items.dropna(subset=["rr_group_id"])
    group_sizes = Counter(int(g) for g in known["rr_group_id"])
    group_root = {g: root_of.get(g, g) for g in group_sizes}
    assignment = assign_groups_to_categories(group_sizes, group_root, categories, weights)

    items["category"] = items["rr_group_id"].map(lambda g: assignment.get(int(g)) if pd.notna(g) else None)
    items["category_source"] = np.where(items["category"].notna(), "retailrocket_tree", None)

    # Uncategorised items: majority category of items browsed in the same sessions
    missing = items.loc[items["category"].isna(), "raw_itemid"].astype(int).tolist()
    if missing:
        con.register("_missing_items", pd.DataFrame({"raw_itemid": missing}))
        con.register("_known_items", items.loc[items["category"].notna(), ["raw_itemid", "category"]])
        neigh = con.execute(
            f"""
            WITH s AS (SELECT DISTINCT session_id, raw_itemid FROM {session_table})
            SELECT m.raw_itemid, k.category, COUNT(*) AS n
            FROM _missing_items m
            JOIN s s1 ON s1.raw_itemid = m.raw_itemid
            JOIN s s2 ON s2.session_id = s1.session_id AND s2.raw_itemid <> m.raw_itemid
            JOIN _known_items k ON k.raw_itemid = s2.raw_itemid
            GROUP BY 1, 2
            """
        ).df()
        con.unregister("_missing_items")
        con.unregister("_known_items")
        best = (
            neigh.sort_values(["raw_itemid", "n", "category"], ascending=[True, False, True])
            .drop_duplicates("raw_itemid")
            .set_index("raw_itemid")["category"]
            .to_dict()
        )
        counts = Counter(items["category"].dropna())
        target = {c: w * len(items) for c, w in zip(categories, weights)}
        for idx in items.index[items["category"].isna()]:
            rid = int(items.at[idx, "raw_itemid"])
            if rid in best:
                cat, source = best[rid], "session_neighbours"
            else:
                cat = max(categories, key=lambda c: (target[c] - counts[c], -categories.index(c)))
                source = "fallback_deficit"
            items.at[idx, "category"] = cat
            items.at[idx, "category_source"] = source
            counts[cat] += 1

    items["rr_categoryid"] = items["rr_categoryid"].astype("Int64")
    items["rr_group_id"] = items["rr_group_id"].astype("Int64")
    return items


def mapping_summary(items: pd.DataFrame) -> pd.DataFrame:
    """RetailRocket group -> Pakistani category table, for documentation (data model / report)."""
    return (
        items.dropna(subset=["rr_group_id"])
        .groupby(["rr_group_id", "category"], as_index=False)
        .agg(items=("raw_itemid", "count"), rr_leaf_categories=("rr_categoryid", "nunique"))
        .sort_values(["category", "items"], ascending=[True, False])
    )
