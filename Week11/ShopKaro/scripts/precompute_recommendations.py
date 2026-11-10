"""
Daily batch job: retrain the production item-CF recommender on all interactions and save it for
the API (models/item_cf_serving.joblib). The API picks up the new file on its next restart.

Usage:
    python scripts/precompute_recommendations.py

Schedule (cron example, 02:00 daily):
    0 2 * * *  cd /app && python scripts/precompute_recommendations.py && docker compose restart shopkaro-api
"""

from __future__ import annotations

import json

import duckdb

from shopkaro.config.settings import settings
from shopkaro.recommendations.serving import ARTIFACT_PATH, save_artifact, train_serving_model


def main() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        artifact = train_serving_model(con, table="interactions_clean")
    finally:
        con.close()
    path = save_artifact(artifact, ARTIFACT_PATH)
    print(json.dumps({**artifact.info(), "saved_to": str(path), "size_mb": round(path.stat().st_size / 1e6, 1)}, indent=2))


if __name__ == "__main__":
    main()
