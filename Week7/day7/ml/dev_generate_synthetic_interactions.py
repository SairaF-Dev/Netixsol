"""Generate a development-only fixture from verified PostgreSQL facts.

This writes a local JSON file only; it never inserts synthetic events into PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg


def generate(output: str | Path, database_url: str | None = None) -> int:
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not configured")
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.property_id, p.property_type, p.bedrooms, p.purpose,
                   pr.price::double precision, l.city, l.area
            FROM properties p
            JOIN prices pr ON pr.property_id = p.property_id
            JOIN locations l ON l.location_id = p.location_id
            WHERE p.available=TRUE AND pr.verification_status='Verified'
            ORDER BY p.property_id LIMIT 8
        """)
        names = ("property_id", "property_type", "bedrooms", "purpose", "price", "city", "area")
        properties = [dict(zip(names, row)) for row in cursor.fetchall()]
    if len(properties) < 4:
        raise ValueError("need at least four verified properties for the development fixture")
    rows = []
    for index in range(20):
        customer_id = f"synthetic-customer-{index + 1}"
        preferred = properties[index % len(properties)]
        rejected = properties[(index + 1) % len(properties)]
        preference_snapshot = {
            "city": preferred["city"], "area": preferred["area"],
            "budget_min": None, "budget_max": preferred["price"],
            "bedrooms": preferred["bedrooms"],
            "property_type": preferred["property_type"],
            "purpose": preferred["purpose"], "amenities": [],
        }
        base = {
            "customer_id": customer_id,
            "preferred_city": preferred["city"],
            "preferred_area": preferred["area"],
            "budget_max": preferred["price"],
            "preferred_bedrooms": preferred["bedrooms"],
            "preferred_property_type": preferred["property_type"],
            "preferred_purpose": preferred["purpose"],
            "preferred_amenities": [],
            "synthetic": True,
        }
        rows.append({**base, **preferred, "action": "liked", "preference_snapshot": preference_snapshot,
                     "property_snapshot": preferred, "snapshot_source": "historical"})
        rows.append({**base, **rejected, "action": "rejected", "preference_snapshot": preference_snapshot,
                     "property_snapshot": rejected, "snapshot_source": "historical"})
        rows.append({**base, **properties[(index + 2) % len(properties)], "action": "shortlisted",
                     "preference_snapshot": preference_snapshot,
                     "property_snapshot": properties[(index + 2) % len(properties)], "snapshot_source": "historical"})
        rows.append({**base, **properties[(index + 3) % len(properties)], "action": "rejected",
                     "preference_snapshot": preference_snapshot,
                     "property_snapshot": properties[(index + 3) % len(properties)], "snapshot_source": "historical"})
        rows.append({**base, **properties[(index + 4) % len(properties)], "action": "liked",
                     "preference_snapshot": preference_snapshot,
                     "property_snapshot": properties[(index + 4) % len(properties)], "snapshot_source": "historical"})
        rows.append({**base, **properties[(index + 5) % len(properties)], "action": "rejected",
                     "preference_snapshot": preference_snapshot,
                     "property_snapshot": properties[(index + 5) % len(properties)], "snapshot_source": "historical"})
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    print(f"SYNTHETIC FIXTURE SAVED: {destination} rows={len(rows)}")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="ml/dev_data/synthetic_interactions.json")
    arguments = parser.parse_args()
    raise SystemExit(generate(arguments.output))