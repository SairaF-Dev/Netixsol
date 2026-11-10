"""
How much does the neural two-tower move between random seeds, and does its lead survive that spread?

Trains the two-tower with seeds 42, 43 and 44 (each: epochs + serving knobs chosen on validation, new-user settings
chosen on validation new users) and scores every seed on three test protocols:
  * main       - 5,000 warm test users, any test interaction counts (the Day 2 table protocol)
  * discovery  - same users, only items never seen in training, seen items not recommended
  * new users  - 2,000 users absent from training, simulated onboarding = category of their first event
Item-CF and the hybrid blend are deterministic and scored once for reference.

Writes reports/day2_two_tower_seeds.csv. Usage:  python scripts/run_two_tower_seeds.py   (~20 min on CPU)
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import evaluate_recommender_at_k, load_test_ground_truth
from shopkaro.recommendations.collaborative import (
    ImplicitALSRecommender,
    ItemToItemCFRecommender,
    _load_sparse_interaction_data,
    load_val_ground_truth,
)
from shopkaro.recommendations.hybrid import ContentBasedRecommender, HybridTwoTowerRecommender
from shopkaro.recommendations.two_tower import TwoTowerRecommender, load_val_cold_users

SEEDS = (42, 43, 44)


def main() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    catalogue, u2r, _uids, i2c, c2i, R, bought = _load_sparse_interaction_data(con)
    warm_gt = load_test_ground_truth(con, require_warm_user=True, max_eval_users=5000)
    val_gt = load_val_ground_truth(con, max_eval_users=2000)
    val_cold_gt, val_cold_cat = load_val_cold_users(con, max_users=2000)
    cold_df = con.execute(
        """
        WITH c AS (
            SELECT user_id, ARG_MIN(category, event_timestamp) AS cat, COUNT(DISTINCT product_id) AS n
            FROM cold_start_test WHERE is_cold_user = TRUE
            GROUP BY user_id ORDER BY n DESC, user_id LIMIT 2000
        )
        SELECT t.user_id, t.product_id, c.cat FROM cold_start_test t JOIN c USING (user_id) WHERE t.is_cold_user = TRUE;
        """
    ).df()
    con.close()
    cold_gt = cold_df.groupby("user_id")["product_id"].apply(set).to_dict()
    onboarding = cold_df.drop_duplicates("user_id").set_index("user_id")["cat"].astype(str).to_dict()
    emb = np.load(settings.models_dir / "item_text_embeddings.npy")

    def seen(uid: str) -> set[str]:
        return {c2i[c] for c in R[u2r[uid]].indices}

    disc_gt = {u: items - seen(u) for u, items in warm_gt.items()}
    disc_gt = {u: v for u, v in disc_gt.items() if v}

    def score(model, label: str, seed: int | None) -> dict:  # noqa: ANN001
        return {
            "model": label,
            "seed": seed,
            "main_ndcg_at_10": evaluate_recommender_at_k(model, warm_gt, k=10).ndcg_at_k,
            "discovery_ndcg_at_10": evaluate_recommender_at_k(model, disc_gt, k=10, exclude_seen=True).ndcg_at_k,
            "new_user_ndcg_at_10": evaluate_recommender_at_k(model, cold_gt, k=10).ndcg_at_k,
        }

    rows = []
    item_cf = ItemToItemCFRecommender(k_neighbors=80, shrinkage=5.0, revisit_boost=0.35)
    item_cf.fit_from_sparse(catalogue, u2r, i2c, c2i, R, bought)
    als = ImplicitALSRecommender(factors=96, regularization=0.10, alpha=30.0, iterations=10, revisit_boost=0.25)
    als.fit_from_sparse(catalogue, u2r, i2c, c2i, R, bought)
    content = ContentBasedRecommender(category_bonus=0.15, price_affinity_bonus=0.05, revisit_boost=0.25)
    content.fit_from_sparse_and_embeddings(catalogue, u2r, i2c, c2i, R, bought, emb)
    blend = HybridTwoTowerRecommender(
        item_cf=item_cf, als_model=als, content_model=content, w_item_cf=0.65, w_als=0.23, w_content=0.07, w_features=0.05
    )
    blend.set_cold_user_context(onboarding)
    rows.append(score(item_cf, "item_to_item_cf", None))
    rows.append(score(blend, "hybrid_blend", None))
    print(rows[-2], rows[-1], sep="\n", flush=True)

    for seed in SEEDS:
        tt = TwoTowerRecommender(seed=seed, verbose=False)
        tt.fit_from_sparse(catalogue, u2r, i2c, c2i, R, bought, emb, val_ground_truth=val_gt)
        tt.tune_cold_start(val_cold_gt, val_cold_cat)
        tt.set_cold_user_context(onboarding)
        row = score(tt, "neural_two_tower", seed)
        row.update(best_epoch=tt.training_log.best_epoch, cold_setting=str(tt.training_log.cold_start_selected))
        rows.append(row)
        print(row, flush=True)

    df = pd.DataFrame(rows)
    out = settings.reports_dir / "day2_two_tower_seeds.csv"
    df.to_csv(out, index=False)
    tt_df = df[df["model"] == "neural_two_tower"]
    print("\nTwo-tower across seeds (mean +- sd, min..max):")
    for col in ("main_ndcg_at_10", "discovery_ndcg_at_10", "new_user_ndcg_at_10"):
        v = tt_df[col]
        ref = df.set_index("model")[col]
        print(
            f"  {col:22s} {v.mean():.5f} +- {v.std(ddof=1):.5f}  ({v.min():.5f}..{v.max():.5f})"
            f"   | hybrid blend {ref['hybrid_blend']:.5f}, item-CF {ref['item_to_item_cf']:.5f}"
        )
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
