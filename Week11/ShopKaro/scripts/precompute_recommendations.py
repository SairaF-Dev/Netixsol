"""
Daily batch job: retrain the production recommender(s) on all interactions and save them for the API.

- Item-CF (always): models/item_cf_serving.joblib (~1 min).
- Neural two-tower (with --two-tower): models/two_tower_serving.joblib (~10 min on CPU, needs torch). Uses the
  epochs / serving knobs / new-user settings chosen on validation in the Day 2 run
  (reports/day2_two_tower_training_log.json). Served when the API runs with RECOMMENDER=two_tower.

The API picks up new files on its next restart.

Usage:
    python scripts/precompute_recommendations.py               # item-CF only
    python scripts/precompute_recommendations.py --two-tower   # item-CF + two-tower

Schedule (cron example, 02:00 daily):
    0 2 * * *  cd /app && python scripts/precompute_recommendations.py && docker compose restart shopkaro-api
"""

from __future__ import annotations

import argparse
import json

import duckdb

from shopkaro.config.settings import settings
from shopkaro.recommendations.serving import (
    ARTIFACT_PATH,
    TWO_TOWER_ARTIFACT_PATH,
    save_artifact,
    train_serving_model,
    train_two_tower_serving_model,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--two-tower", action="store_true", help="also retrain the neural two-tower (~10 min)")
    args = parser.parse_args()

    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        jobs = [(train_serving_model, ARTIFACT_PATH)]
        if args.two_tower:
            jobs.append((train_two_tower_serving_model, TWO_TOWER_ARTIFACT_PATH))
        for train, out in jobs:
            artifact = train(con, table="interactions_clean")
            path = save_artifact(artifact, out)
            info = {**artifact.info(), "saved_to": str(path), "size_mb": round(path.stat().st_size / 1e6, 1)}
            print(json.dumps(info, indent=2), flush=True)
    finally:
        con.close()


if __name__ == "__main__":
    main()
