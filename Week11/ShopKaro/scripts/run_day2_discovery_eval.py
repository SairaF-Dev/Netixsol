"""
Day 2 Task 4 addendum: separate "re-showing what the user already browsed" from real discovery.

The main Day 2 protocol counts ANY test-period interaction as a hit, including re-views of items the
user already interacted with in training. This script adds:
  1. A no-model "repeat own history" baseline on that protocol.
  2. A discovery protocol: ground truth = only items the user never interacted with in training,
     and models must not recommend seen items.

Writes reports/day2_discovery_evaluation.csv. Usage:  python scripts/run_day2_discovery_eval.py
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import (
    BaseRecommender,
    PopularOverallRecommender,
    evaluate_recommender_at_k,
    load_test_ground_truth,
)
from shopkaro.recommendations.collaborative import (
    ImplicitALSRecommender,
    ItemToItemCFRecommender,
    _load_sparse_interaction_data,
    load_val_ground_truth,
)
from shopkaro.recommendations.two_tower import TwoTowerRecommender


class RepeatOwnHistoryRecommender(BaseRecommender):
    """No model: the user's own most-interacted training items."""

    name = "Repeat own history (no model)"

    def __init__(self, R, user_to_row: dict[str, int], item_ids: list[str]) -> None:  # noqa: ANN001
        super().__init__()
        self.R, self.user_to_row, self.item_ids = R, user_to_row, item_ids
        self.total_catalogue_size = len(item_ids)

    def recommend_ids(self, user_id, k=10, exclude_seen=False, only_in_stock=True):  # noqa: ANN001, ANN201
        row = self.R[self.user_to_row[user_id]]
        order = np.argsort(-row.data)[:k]
        return [(self.item_ids[row.indices[j]], float(row.data[j])) for j in order]


def main() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    catalogue, user_to_row, _uids, item_to_col, item_ids, R, bought = _load_sparse_interaction_data(con)
    ground_truth = load_test_ground_truth(con, require_warm_user=True, max_eval_users=5000)
    popular = PopularOverallRecommender().fit_from_duckdb(con)
    val_gt = load_val_ground_truth(con, max_eval_users=2000)
    con.close()
    item_cf = ItemToItemCFRecommender().fit_from_sparse(catalogue, user_to_row, item_to_col, item_ids, R, bought)
    repeat = RepeatOwnHistoryRecommender(R, user_to_row, item_ids)
    als = ImplicitALSRecommender(factors=96, regularization=0.10, alpha=30.0, iterations=10, revisit_boost=0.25)
    als.fit_from_sparse(catalogue, user_to_row, item_to_col, item_ids, R, bought)
    neural = TwoTowerRecommender(verbose=False).fit_from_sparse(
        catalogue, user_to_row, item_to_col, item_ids, R, bought,
        np.load(settings.models_dir / "item_text_embeddings.npy"), val_ground_truth=val_gt,
    )

    def seen(uid: str) -> set[str]:
        return {item_ids[c] for c in R[user_to_row[uid]].indices}

    new_items_gt = {u: items - seen(u) for u, items in ground_truth.items()}
    new_items_gt = {u: items for u, items in new_items_gt.items() if items}
    n_all = sum(len(v) for v in ground_truth.values())
    n_new = sum(len(v) for v in new_items_gt.values())

    runs = [
        ("all_test_items", ground_truth, popular, False),
        ("all_test_items", ground_truth, repeat, False),
        ("all_test_items", ground_truth, item_cf, False),
        ("all_test_items", ground_truth, als, False),
        ("all_test_items", ground_truth, neural, False),
        ("new_items_only", new_items_gt, popular, True),
        ("new_items_only", new_items_gt, item_cf, True),
        ("new_items_only", new_items_gt, als, True),
        ("new_items_only", new_items_gt, neural, True),
    ]
    rows = []
    for protocol, gt, model, exclude_seen in runs:
        m = evaluate_recommender_at_k(model, gt, k=10, exclude_seen=exclude_seen)
        rows.append(
            {
                "protocol": protocol,
                "model_name": model.name,
                "exclude_seen": exclude_seen,
                "evaluated_users": m.evaluated_users,
                "ndcg_at_10": m.ndcg_at_k,
                "hit_rate_at_10": m.hit_rate_at_k,
                "recall_at_10": m.recall_at_k,
                "catalogue_coverage_pct": m.catalogue_coverage_pct,
            }
        )
    df = pd.DataFrame(rows)
    out = settings.reports_dir / "day2_discovery_evaluation.csv"
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print(f"\nTest items already seen in training: {1 - n_new / n_all:.1%} of ground-truth items")
    pop = df.query("protocol == 'new_items_only' and model_name.str.contains('Popular')")["ndcg_at_10"].iloc[0]
    cf = df.query("protocol == 'new_items_only' and model_name.str.contains('Item-to-Item')")["ndcg_at_10"].iloc[0]
    print(f"Discovery NDCG@10: item-CF {cf:.4f} vs popularity {pop:.4f} -> {cf / pop:.1f}x (target: >= 1.2x)")
    tt = df.query("protocol == 'new_items_only' and model_name.str.contains('Two-Tower')")["ndcg_at_10"].iloc[0]
    print(f"Discovery NDCG@10: neural two-tower {tt:.4f} ({tt / pop:.1f}x popularity, {tt / cf - 1:+.1%} vs item-CF)")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
