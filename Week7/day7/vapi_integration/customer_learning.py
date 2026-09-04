"""Customer preference learning and explainable property ranking."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

import psycopg

CITIES = ("Lahore", "Karachi", "Islamabad", "Rawalpindi")
AMENITIES = (
    "parking", "gym", "swimming pool", "pool", "security", "park",
    "elevator", "lift", "rooftop", "backup", "school", "mosque",
)
AREAS = (
    "DHA Phase 1", "DHA Phase 2", "DHA Phase 5", "DHA Phase 6",
    "DHA", "Bahria Town", "Gulberg", "Johar Town", "Clifton",
    "Gulshan", "F-7", "F-8", "Bahria Enclave",
)


def customer_key_for_phone(phone: str, salt: str | None = None) -> str:
    """Return a stable, non-reversible customer key for a phone number."""
    normalized = re.sub(r"\D", "", phone or "")
    if not normalized or normalized == "0":
        return ""
    secret = salt or os.getenv("SARA_CUSTOMER_HASH_SALT", "")
    if not secret:
        raise ValueError("SARA_CUSTOMER_HASH_SALT is required for customer profiles")
    return hashlib.sha256(f"{secret}:{normalized}".encode("utf-8")).hexdigest()


def _text(record: dict[str, Any]) -> str:
    messages = record.get("messages") or []
    return " ".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))


def _first_number(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else None


def _budget(text: str) -> int | None:
    match = re.search(r"(?:up to|max(?:imum)?|budget|under|tak|crore|cr|lakh)\D{0,12}(\d+(?:\.\d+)?)\s*(crore|cr|lakh)?", text, re.I)
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in ("crore", "cr"):
        amount *= 10_000_000
    elif unit == "lakh":
        amount *= 100_000
    return int(amount)


def extract_features(record: dict[str, Any]) -> dict[str, Any]:
    """Extract review-supplied features and conservative text features."""
    supplied = record.get("features") if isinstance(record.get("features"), dict) else {}
    text = _text(record)
    features: dict[str, Any] = {
        "city": supplied.get("city"),
        "area": supplied.get("area"),
        "budget": supplied.get("budget"),
        "bedrooms": supplied.get("bedrooms"),
        "property_type": supplied.get("property_type"),
        "purpose": supplied.get("purpose"),
        "amenities": list(supplied.get("amenities") or []),
        "viewed_property_ids": list(supplied.get("viewed_property_ids") or []),
        "rejected_property_ids": list(supplied.get("rejected_property_ids") or []),
        "booked_property_ids": list(supplied.get("booked_property_ids") or []),
    }
    if not features["city"]:
        features["city"] = next((city for city in CITIES if re.search(rf"\b{re.escape(city)}\b", text, re.I)), None)
    if not features["area"]:
        features["area"] = next((area for area in AREAS if re.search(rf"\b{re.escape(area)}\b", text, re.I)), None)
    if features["budget"] is None:
        features["budget"] = _budget(text)
    if features["bedrooms"] is None:
        features["bedrooms"] = _first_number(text, r"(\d+)\s*(?:bed(?:room)?s?|br)\b")
    if not features["property_type"]:
        features["property_type"] = next((value for value in ("apartment", "house", "villa", "plot", "commercial") if re.search(rf"\b{value}\b", text, re.I)), None)
    if not features["purpose"]:
        features["purpose"] = next((value for value, pattern in (("rent", r"rent|kiraya|lease"), ("invest", r"invest"), ("buy", r"buy|purchase|lena")) if re.search(pattern, text, re.I)), None)
    features["amenities"] = sorted(set(features["amenities"]) | {value for value in AMENITIES if re.search(rf"\b{re.escape(value)}\b", text, re.I)})
    return features


def approved_learning_dataset(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a dataset using only explicitly approved reviewed records."""
    dataset = []
    for record in records:
        if record.get("review_status") != "approved":
            continue
        features = extract_features(record)
        dataset.append({
            "customer_key": record.get("customer_key", ""),
            "source_call_id": record.get("call_id", ""),
            "features": features,
            "label": record.get("label"),
            "ideal_response": record.get("ideal_response", ""),
        })
    return dataset


@dataclass
class PreferenceProfile:
    customer_key: str
    city: str | None = None
    area: str | None = None
    budget: int | None = None
    bedrooms: int | None = None
    property_type: str | None = None
    purpose: str | None = None
    amenities: list[str] = field(default_factory=list)
    viewed_property_ids: list[str] = field(default_factory=list)
    rejected_property_ids: list[str] = field(default_factory=list)
    booked_property_ids: list[str] = field(default_factory=list)
    sample_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_profile(dataset: Iterable[dict[str, Any]], customer_key: str) -> PreferenceProfile | None:
    """Aggregate approved examples for one customer into a profile."""
    rows = [row for row in dataset if row.get("customer_key") == customer_key]
    if not rows:
        return None
    profile = PreferenceProfile(customer_key=customer_key, sample_count=len(rows))
    for row in rows:
        features = row.get("features") or {}
        for field_name in ("city", "area", "budget", "bedrooms", "property_type", "purpose"):
            if features.get(field_name) is not None:
                setattr(profile, field_name, features[field_name])
        for field_name in ("amenities", "viewed_property_ids", "rejected_property_ids", "booked_property_ids"):
            values = getattr(profile, field_name)
            values.extend(str(value) for value in features.get(field_name) or [])
            setattr(profile, field_name, sorted(set(values)))
    return profile


class CustomerPreferenceRepository:
    """PostgreSQL persistence for learned profiles, separate from property facts."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")

    def upsert(self, profile: PreferenceProfile) -> None:
        query = """
            INSERT INTO customer_preference_profiles
                (customer_key, profile_json, sample_count, updated_at)
            VALUES (%s, %s::jsonb, %s, NOW())
            ON CONFLICT (customer_key) DO UPDATE SET
                profile_json = EXCLUDED.profile_json,
                sample_count = EXCLUDED.sample_count,
                updated_at = NOW()
        """
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (profile.customer_key, json.dumps(profile.to_dict()), profile.sample_count))
            connection.commit()

    def get(self, customer_key: str) -> PreferenceProfile | None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT profile_json FROM customer_preference_profiles WHERE customer_key = %s", (customer_key,))
                row = cursor.fetchone()
        if not row:
            return None
        return PreferenceProfile(**row[0])


class ExplainablePreferenceRanker:
    """Small deterministic model; it cannot add or modify property facts."""

    def rank(self, candidates: list[dict[str, Any]], profile: PreferenceProfile | None) -> list[dict[str, Any]]:
        if not profile or not candidates:
            return candidates
        ranked = []
        for candidate in candidates:
            property_id = str(candidate.get("property_id", ""))
            score = 0.0
            reasons: list[str] = []
            if property_id in profile.rejected_property_ids:
                score -= 100.0
                reasons.append("previously rejected")
            if property_id in profile.booked_property_ids:
                score += 20.0
                reasons.append("previously booked")
            if str(candidate.get("city", "")).lower() == str(profile.city or "").lower():
                score += 3.0
                reasons.append("city match")
            if profile.area and str(profile.area).lower() in str(candidate.get("area", "")).lower():
                score += 3.0
                reasons.append("area match")
            if profile.property_type and str(candidate.get("property_type", "")).lower() == profile.property_type.lower():
                score += 2.0
                reasons.append("property type match")
            if profile.purpose and str(candidate.get("purpose", "")).lower() == profile.purpose.lower():
                score += 2.0
                reasons.append("purpose match")
            if profile.bedrooms is not None and candidate.get("bedrooms") == profile.bedrooms:
                score += 2.0
                reasons.append("bedroom match")
            candidate_amenities = {
                str(value).lower() for value in candidate.get("amenities", [])
            }
            matching_amenities = {
                value.lower() for value in profile.amenities
            } & candidate_amenities
            if matching_amenities:
                score += min(float(len(matching_amenities)), 3.0)
                reasons.append(f"amenity match: {', '.join(sorted(matching_amenities))}")
            if profile.budget is not None and candidate.get("price") is not None:
                price = float(candidate["price"])
                if price <= profile.budget:
                    score += 2.0
                    reasons.append("within learned budget")
                else:
                    score -= min((price - profile.budget) / profile.budget, 1.0)
            candidate_copy = dict(candidate)
            candidate_copy["_ml_score"] = round(score, 4)
            candidate_copy["_ml_reasons"] = reasons
            ranked.append(candidate_copy)
        return sorted(ranked, key=lambda item: (-item["_ml_score"], str(item.get("property_id", ""))))


def evaluate_ranker(
    ranker: ExplainablePreferenceRanker,
    cases: Iterable[dict[str, Any]],
) -> dict[str, float]:
    """Evaluate ranking against reviewed expected property IDs."""
    total = hits = reciprocal_rank = rejected_top = 0
    for case in cases:
        ranked = ranker.rank(case.get("candidates", []), case.get("profile"))
        expected = {str(value) for value in case.get("expected_property_ids", [])}
        if not ranked:
            continue
        total += 1
        ranked_ids = [str(item.get("property_id", "")) for item in ranked]
        if ranked_ids[0] in expected:
            hits += 1
        for index, property_id in enumerate(ranked_ids, 1):
            if property_id in expected:
                reciprocal_rank += 1.0 / index
                break
        rejected = {str(value) for value in getattr(case.get("profile"), "rejected_property_ids", [])}
        if ranked_ids[0] not in rejected:
            rejected_top += 1
    if not total:
        return {"cases": 0.0, "top1_hit_rate": 0.0, "mean_reciprocal_rank": 0.0, "rejected_top_rate": 0.0}
    return {
        "cases": float(total),
        "top1_hit_rate": hits / total,
        "mean_reciprocal_rank": reciprocal_rank / total,
        "rejected_top_rate": rejected_top / total,
    }
