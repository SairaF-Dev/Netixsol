"""Build approved customer profiles and persist them to PostgreSQL.

This is preference aggregation, not LLM fine-tuning.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from customer_learning import (  # noqa: E402
    CustomerPreferenceRepository,
    approved_learning_dataset,
    build_profile,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Sara customer preference profiles")
    parser.add_argument("records", type=Path, help="Reviewed conversation JSONL file")
    args = parser.parse_args()

    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()]
    dataset = approved_learning_dataset(records)
    customer_keys = sorted({row["customer_key"] for row in dataset if row.get("customer_key")})
    repository = CustomerPreferenceRepository()
    stored = 0
    for customer_key in customer_keys:
        profile = build_profile(dataset, customer_key)
        if profile:
            repository.upsert(profile)
            stored += 1
    print(f"Approved examples: {len(dataset)}; profiles stored: {stored}")


if __name__ == "__main__":
    main()
