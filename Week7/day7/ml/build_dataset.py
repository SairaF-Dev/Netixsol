"""Build a grouped binary dataset from PostgreSQL interaction outcomes."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Iterable

import numpy as np
import psycopg

from ml import FEATURE_NAMES
from ml.feature_engineering import engineer_features
from ml.model_types import InsufficientTrainingData, TrainingDataset

POSITIVE_ACTIONS = frozenset({"liked", "shortlisted"})
NEGATIVE_ACTIONS = frozenset({"rejected"})
IGNORED_ACTIONS = frozenset({"shown", "viewed", "appointment_booked", "appointment_cancelled"})
OUTCOME_PRECEDENCE = ("rejected", "liked", "shortlisted")


def fetch_interaction_rows(database_url: str | None = None) -> list[dict[str, Any]]:
    """Fetch structured training inputs without selecting customer PII."""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not configured")
    query = """
         SELECT i.customer_id::text, i.property_id, i.action, i.created_at,
             i.preference_snapshot, i.property_snapshot,
               cp.city AS preferred_city, cp.area AS preferred_area,
               cp.budget_max, cp.bedrooms AS preferred_bedrooms,
               cp.property_type AS preferred_property_type,
               cp.purpose AS preferred_purpose,
               COALESCE(cp.amenities, '[]'::jsonb) AS preferred_amenities,
               p.property_type, p.bedrooms, p.purpose,
               pr.price::double precision AS price,
               l.city, l.area,
               COALESCE(
                   jsonb_agg(DISTINCT a.amenity) FILTER (WHERE a.amenity IS NOT NULL),
                   '[]'::jsonb
               ) AS property_amenities
        FROM customer_interactions i
        JOIN properties p ON p.property_id = i.property_id
        JOIN prices pr ON pr.property_id = p.property_id
        JOIN locations l ON l.location_id = p.location_id
        LEFT JOIN customer_preferences cp ON cp.customer_id = i.customer_id
        LEFT JOIN amenities a ON a.property_id = p.property_id
        WHERE pr.verification_status = 'Verified'
        GROUP BY i.customer_id, i.property_id, i.action, i.created_at,
                 i.preference_snapshot, i.property_snapshot,
                 cp.city, cp.area, cp.budget_max, cp.bedrooms,
                 cp.property_type, cp.purpose, cp.amenities,
                 p.property_type, p.bedrooms, p.purpose, pr.price, l.city, l.area
        ORDER BY i.customer_id, i.property_id, i.created_at, i.action
    """
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(query)
        columns = [description.name for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def resolve_outcomes(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse one customer's property history to one conservative outcome."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        action = row.get("action")
        if action in POSITIVE_ACTIONS or action in NEGATIVE_ACTIONS:
            grouped[(str(row.get("customer_id", "")), str(row.get("property_id", "")))].append(row)

    resolved = []
    for (customer_id, property_id), history in sorted(grouped.items()):
        actions = {str(row.get("action")) for row in history}
        outcome = next(action for action in OUTCOME_PRECEDENCE if action in actions)
        row = dict(sorted(history, key=lambda item: (str(item.get("created_at", "")), str(item.get("action", ""))))[-1])
        preference_snapshot = row.get("preference_snapshot") or {}
        property_snapshot = row.get("property_snapshot") or {}
        if preference_snapshot:
            row.update({
                "preferred_city": preference_snapshot.get("city"),
                "preferred_area": preference_snapshot.get("area"),
                "budget_max": preference_snapshot.get("budget_max"),
                "preferred_bedrooms": preference_snapshot.get("bedrooms"),
                "preferred_property_type": preference_snapshot.get("property_type"),
                "preferred_purpose": preference_snapshot.get("purpose"),
                "preferred_amenities": preference_snapshot.get("amenities") or [],
                "snapshot_source": "historical",
            })
        else:
            row["snapshot_source"] = "latest_profile_fallback"
        if property_snapshot:
            row.update({
                "city": property_snapshot.get("city"),
                "area": property_snapshot.get("area"),
                "price": property_snapshot.get("price"),
                "bedrooms": property_snapshot.get("bedrooms"),
                "property_type": property_snapshot.get("property_type"),
                "purpose": property_snapshot.get("purpose"),
                "property_amenities": property_snapshot.get("amenities") or [],
            })
        row["customer_id"] = customer_id
        row["property_id"] = property_id
        row["resolved_action"] = outcome
        row["target"] = 0 if outcome == "rejected" else 1
        resolved.append(row)
    return resolved


def build_dataset(rows: Iterable[dict[str, Any]], *, min_rows: int = 2) -> TrainingDataset:
    resolved = resolve_outcomes(rows)
    if len(resolved) < min_rows:
        raise InsufficientTrainingData(f"need at least {min_rows} resolved outcomes; found {len(resolved)}")
    targets = np.asarray([row["target"] for row in resolved], dtype=np.int64)
    if set(targets.tolist()) != {0, 1}:
        raise InsufficientTrainingData("resolved outcomes must contain both positive and negative classes")
    matrix = np.asarray(
        [[engineer_features(row)[name] for name in FEATURE_NAMES] for row in resolved],
        dtype=np.float64,
    )
    if not np.isfinite(matrix).all():
        raise InsufficientTrainingData("feature matrix contains NaN or infinity")
    return TrainingDataset(
        rows=resolved,
        feature_names=FEATURE_NAMES,
        features=matrix,
        targets=targets,
        groups=np.asarray([row["customer_id"] for row in resolved]),
    )