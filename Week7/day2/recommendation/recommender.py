"""
Property Recommendation Engine — Task 4

Two-stage approach:
  1. HARD FILTER (structured SQL): budget, city, bedrooms, purpose —
     non-negotiable constraints, so filtering wrong here is worse than
     filtering loosely.
  2. SOFT SCORING: area preference, amenities match, investment goals —
     ranks the filtered candidates rather than excluding on them.

Run: python recommendation/recommender.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "retrieval"))

from structured_retrieval import search_properties, _connect


AMENITY_WEIGHTS = {
    "gym": 1, "swimming_pool": 1, "park_nearby": 1, "mosque_nearby": 0.5,
    "generator_backup": 1.5, "solar_panels": 1, "servant_quarter": 1, "lift": 0.5,
    "gated_community": 2, "parking": 1,
}


def _get_amenities(property_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM amenities WHERE property_id = ?", (property_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def score_property(prop, preferred_amenities=None, investment_goal=False):
    score = 0.0
    amenities = _get_amenities(prop["property_id"])
    preferred_amenities = preferred_amenities or []

    for amenity in preferred_amenities:
        if amenities.get(amenity) == "Yes":
            score += AMENITY_WEIGHTS.get(amenity, 1)

    if investment_goal:
        # Under-construction + negotiable + lower price tends to favor ROI-seeking investors
        if prop.get("possession_status") == "Under Construction":
            score += 3
        if prop.get("type") in ("Plot", "Commercial"):
            score += 2

    return score


def recommend(budget=None, city=None, purpose=None, bedrooms=None,
              preferred_amenities=None, investment_goal=False, top_k=5):
    """
    budget: (min, max) tuple in PKR, or None
    """
    min_price, max_price = (budget if budget else (None, None))
    candidates = search_properties(
        city=city, purpose=purpose, min_price=min_price, max_price=max_price,
        bedrooms=bedrooms, status="Available",
    )

    scored = [
        (score_property(c, preferred_amenities, investment_goal), c)
        for c in candidates
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


if __name__ == "__main__":
    results = recommend(
        budget=(20000000, 50000000),
        city="Lahore",
        purpose="Buy",
        preferred_amenities=["gated_community", "generator_backup", "gym"],
    )
    for r in results:
        print(f"{r['title']} — PKR {r['price_pkr']:,.0f} — {r['area']}")

    print("\nInvestment-focused recommendation:")
    investors = recommend(budget=(10000000, 200000000), investment_goal=True, top_k=3)
    for r in investors:
        print(f"{r['title']} — {r['type']} — {r['possession_status']}")
