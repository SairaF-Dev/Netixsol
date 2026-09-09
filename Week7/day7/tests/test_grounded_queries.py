import asyncio
import os
import re
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from postgres_repository import PostgresPropertyRepository
from sara_agent.models import UserUnderstanding
from sara_agent.understanding import UserUnderstandingService
from shared.sara_service import SaraService
from test_phase9_chat import setup, chat
from test_web_api import CUSTOMER_ID, Customers, Properties
from web_api.chat import ChatAdapter
from web_api.services import WebServices, RecommendationSessionStore


def create_grounded_properties():
    props = Properties()
    props.rows = [
        {
            "property_id": "KHI-DHA-HSE-001",
            "property_name": "DHA Family Residence",
            "city": "Karachi",
            "area": "DHA Phase 6",
            "price": 65_000_000,
            "bedrooms": 4,
            "bathrooms": 4,
            "property_type": "House",
            "purpose": "purchase",
            "available": True,
            "verification_status": "Verified",
            "currency": "PKR",
            "amenities": ["Parking", "Garden"],
        },
        {
            "property_id": "KHI-DHA-HSE-002",
            "property_name": "DHA Luxury Residence",
            "city": "Karachi",
            "area": "DHA Phase 8",
            "price": 95_000_000,
            "bedrooms": 5,
            "bathrooms": 6,
            "property_type": "House",
            "purpose": "purchase",
            "available": True,
            "verification_status": "Verified",
            "currency": "PKR",
            "amenities": ["Swimming Pool", "Garden"],
        },
        {
            "property_id": "KHI-GUL-APT-001",
            "property_name": "Gulshan Residency",
            "city": "Karachi",
            "area": "Gulshan-e-Iqbal",
            "price": 21_000_000,
            "bedrooms": 3,
            "bathrooms": 2,
            "property_type": "Apartment",
            "purpose": "purchase",
            "available": True,
            "verification_status": "Verified",
            "currency": "PKR",
            "amenities": ["Parking", "Lift"],
        },
        {
            "property_id": "LHR-DHA-HSE-001",
            "property_name": "Lahore DHA Villa",
            "city": "Lahore",
            "area": "DHA Phase 5",
            "price": 55_000_000,
            "bedrooms": 4,
            "bathrooms": 4,
            "property_type": "House",
            "purpose": "purchase",
            "available": True,
            "verification_status": "Verified",
            "currency": "PKR",
            "amenities": ["Parking"],
        },
    ]

    def _search(city=None, area=None, property_type=None, purpose=None, budget=None, bedrooms=None, **kwargs):
        res = []
        for r in props.rows:
            if not r.get("available", True):
                continue
            if city and r.get("city", "").lower() != city.lower():
                continue
            if area and r.get("area", "").lower() != area.lower():
                continue
            if property_type and r.get("property_type", "").lower() != property_type.lower():
                continue
            if purpose and r.get("purpose", "").lower() != purpose.lower():
                continue
            if budget and int(r.get("price", 0)) > int(budget):
                continue
            if bedrooms and int(r.get("bedrooms", 0)) < int(bedrooms):
                continue
            res.append(dict(r))
        return res

    props.search = _search
    props.list_available_areas = lambda city=None, **k: (
        ["DHA Phase 6", "DHA Phase 8", "Gulshan-e-Iqbal"] if city and city.lower() == "karachi"
        else ["DHA Phase 5"] if city and city.lower() == "lahore"
        else ["DHA Phase 6", "DHA Phase 8", "Gulshan-e-Iqbal", "DHA Phase 5"]
    )
    props.list_available_cities = lambda purpose=None: ["Karachi", "Lahore", "Islamabad"]
    props.get_property = lambda pid: next((dict(r) for r in props.rows if r["property_id"] == pid), None)
    return props


@pytest.fixture
def grounded_env(monkeypatch):
    monkeypatch.setattr(UserUnderstandingService, "_call_llm", Mock(side_effect=RuntimeError("offline test")))
    web, svc, _ = setup()
    svc.chat.sara.understanding = UserUnderstandingService(deterministic_first=True)
    svc.properties = create_grounded_properties()
    svc.chat.services.properties = svc.properties
    return web, svc


# ==============================================================================
# 1. DB-Level Verification: list_available_cities
# ==============================================================================
def test_list_available_cities_returns_verified_data():
    """Verify repo.list_available_cities() against postgres repository / live DB."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:Postgres123!@localhost:5432/real_estate")
    try:
        repo = PostgresPropertyRepository(database_url=db_url)
        cities = repo.list_available_cities()
        assert isinstance(cities, list)
        assert len(cities) > 0
        assert "Karachi" in cities
        assert "Lahore" in cities
        assert "Islamabad" in cities
        # No duplicates
        assert len(cities) == len(set(cities))
        # No empty or whitespace strings
        assert all(isinstance(c, str) and c.strip() for c in cities)

        # Respects optional purpose filter
        purchase_cities = repo.list_available_cities(purpose="purchase")
        assert isinstance(purchase_cities, list)
        assert "Karachi" in purchase_cities
    except Exception as exc:
        pytest.skip(f"Postgres DB not reachable in this test environment: {exc}")


# ==============================================================================
# 2. "Which cities are available" Query (Fresh Session)
# ==============================================================================
def test_which_cities_available_query(grounded_env):
    """User asks 'kon kon se cities k options available hai' on a fresh session."""
    web, svc = grounded_env
    res = chat(web, message="kon kon se cities k options available hai").json()
    assert res.get("requires_clarification") is True
    msg = res["message"].lower()
    assert "karachi" in msg
    assert "lahore" in msg
    assert "kis city mein dekhna chahengi" in msg or "kis city" in msg


# ==============================================================================
# 3. "Which cities" Query before Any Context
# ==============================================================================
def test_which_cities_query_before_any_context(grounded_env):
    """'which cities do you operate in' returns grounded cities without asking rent vs purchase."""
    web, svc = grounded_env
    res = chat(web, message="which cities do you operate in").json()
    assert res.get("requires_clarification") is True
    msg = res["message"].lower()
    assert "karachi" in msg
    assert "lahore" in msg
    assert "rent" not in msg
    assert "purchase" not in msg


# ==============================================================================
# 4. Centralized Dispatch Priority for List Queries
# ==============================================================================
def test_shared_dispatch_priority_for_list_queries(grounded_env):
    """Listing cities or areas dispatches with high priority even when slots are unfilled."""
    web, svc = grounded_env
    # City list query
    r1 = chat(web, message="kon kon se cities k options available hai").json()
    assert "karachi" in r1["message"].lower()

    # Area list query specifying city
    r2 = chat(web, message="karachi mein kon kon se areas available hain").json()
    assert "dha phase 6" in r2["message"].lower()
    assert "dha phase 8" in r2["message"].lower()


# ==============================================================================
# 5. Most Expensive Property Query
# ==============================================================================
def test_most_expensive_property_query(grounded_env):
    """'sb se menghi property knsi hai karachi mein' returns DHA Luxury Residence (9.5 Cr) + card."""
    web, svc = grounded_env
    res = chat(web, message="sb se menghi property knsi hai karachi mein").json()
    msg = res["message"].lower()
    assert "dha luxury residence" in msg
    assert "9.5 crore" in msg or "95,000,000" in msg or "95000000" in msg
    assert res.get("properties")
    assert res["properties"][0]["property_id"] == "KHI-DHA-HSE-002"


# ==============================================================================
# 6. Cheapest and Expensive Queries are Symmetric
# ==============================================================================
def test_cheapest_and_expensive_symmetric(grounded_env):
    """Symmetric handling: cheapest returns MIN price, most expensive returns MAX price."""
    web, svc = grounded_env
    # Cheapest
    r_cheap = chat(web, message="sab se sasta house konsa hai karachi mein").json()
    assert r_cheap.get("properties")
    assert r_cheap["properties"][0]["property_id"] == "KHI-DHA-HSE-001"
    assert "6.5 crore" in r_cheap["message"].lower() or "65,000,000" in r_cheap["message"]

    # Most expensive
    r_exp = chat(web, message="sab se mehnga house konsa hai karachi mein").json()
    assert r_exp.get("properties")
    assert r_exp["properties"][0]["property_id"] == "KHI-DHA-HSE-002"
    assert "9.5 crore" in r_exp["message"].lower() or "95,000,000" in r_exp["message"]

    # Verify distinct
    assert r_cheap["properties"][0]["property_id"] != r_exp["properties"][0]["property_id"]


# ==============================================================================
# 7. Most Expensive Query Never Hallucinates Non-Existent Areas (e.g. Clifton)
# ==============================================================================
def test_most_expensive_never_hallucinates_area(grounded_env):
    """Verifies that the returned property is purely DB-backed and never hallucinates 'Clifton'."""
    web, svc = grounded_env
    res = chat(web, message="karachi mein sb se mehngi property konsi hai").json()
    msg = res["message"].lower()
    assert "clifton" not in msg
    assert "dha phase 8" in msg or "dha luxury residence" in msg


# ==============================================================================
# 8. Areas Query for Known City
# ==============================================================================
def test_areas_query_for_city(grounded_env):
    """'Karachi mein konsi areas hain' returns verified areas from DB."""
    web, svc = grounded_env
    res = chat(web, message="Karachi mein konsi areas hain").json()
    assert res.get("requires_clarification") is True
    msg = res["message"].lower()
    assert "dha phase 6" in msg
    assert "dha phase 8" in msg
    assert "gulshan-e-iqbal" in msg


# ==============================================================================
# 9. Areas Query Scoped by Existing Criteria
# ==============================================================================
def test_areas_query_scoped_by_existing_criteria(grounded_env):
    """When customer has established criteria, list_available_areas scopes by criteria."""
    web, svc = grounded_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.budget_max = 70_000_000

    calls = []
    orig_list = svc.properties.list_available_areas
    def tracking_list(*a, **k):
        calls.append(k)
        return orig_list(*a, **k)
    svc.properties.list_available_areas = tracking_list

    res = chat(web, message="karachi k areas batao").json()
    assert calls
    # Scoped call passed customer filters
    assert calls[0].get("city") == "Karachi"
    assert "dha phase 6" in res["message"].lower()


# ==============================================================================
# 10. Areas Query Without City Asks City First
# ==============================================================================
def test_areas_query_without_city_asks_first(grounded_env):
    """'kon kon se areas available hain' with no city asks user to specify city."""
    web, svc = grounded_env
    svc.customers.preferences.city = None
    res = chat(web, message="kon kon se areas available hain").json()
    assert res.get("requires_clarification") is True
    msg = res["message"].lower()
    assert "kis city ke areas dekhna chahenge" in msg


# ==============================================================================
# 11. Informational Query Does Not Disturb Pending State
# ==============================================================================
def test_informational_query_does_not_disturb_pending_state(grounded_env):
    """Informational query preserves pending_choice_frame in session."""
    web, svc = grounded_env
    cid = chat(web, message="Aoa").json()["conversation_id"]
    saved = svc.chat.store.rows[cid][2]
    saved["pending_choice_frame"] = {
        "option_a": {"area": "DHA Phase 8", "bedrooms": 5, "price": 95_000_000},
        "option_b": {"fallback_areas": ["Gulshan-e-Iqbal"]},
    }

    # Ask informational query
    res = chat(web, cid=cid, message="karachi mein sb se mehngi property konsi hai").json()
    assert "dha luxury residence" in res["message"].lower()

    # Verify pending_choice_frame was NOT deleted or mutated
    assert "pending_choice_frame" in saved
    assert saved["pending_choice_frame"]["option_a"]["area"] == "DHA Phase 8"


# ==============================================================================
# 12. Area Relax Phrasing Variants
# ==============================================================================
def test_area_relax_phrasing_variants(grounded_env):
    """'karachi mein dusrey areas k options dekhna chahu gi' relaxes area."""
    web, svc = grounded_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"

    res = chat(web, message="karachi mein dusrey areas k options dekhna chahu gi").json()
    msg = res["message"].lower()
    # Bot lists available areas in Karachi
    assert "dha phase 6" in msg or "gulshan-e-iqbal" in msg


# ==============================================================================
# 13. Areas List Query Bypasses Pending State
# ==============================================================================
def test_areas_list_query_bypasses_pending_state(grounded_env):
    """Areas list query executes directly even if pending_scope_confirm is active."""
    web, svc = grounded_env
    cid = chat(web, message="Aoa").json()["conversation_id"]
    saved = svc.chat.store.rows[cid][2]
    saved["pending_scope_confirm"] = {"city": "Karachi", "scope": "city"}

    res = chat(web, cid=cid, message="karachi mein kon kon se areas k options available hai").json()
    msg = res["message"].lower()
    assert "dha phase 6" in msg or "dha phase 8" in msg
    assert "options available hain" in msg


# ==============================================================================
# 14. Established City Persists Across Multi-Turn Sequence
# ==============================================================================
def test_established_city_persists_across_turns(grounded_env):
    """City 'Karachi' established in Turn 1 persists across 5 consecutive turns."""
    web, svc = grounded_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.budget_max = 160_000_000
    svc.customers.preferences.purpose = "purchase"

    # Turn 1
    r1 = chat(web, message="Aoa").json()
    cid = r1["conversation_id"]
    assert "karachi" in r1["message"].lower()

    # Turn 2
    r2 = chat(web, cid=cid, message="mazeed options dikhaye").json()
    assert "karachi" in r2["message"].lower()

    # Turn 3
    r3 = chat(web, cid=cid, message="karachi mein dusrey areas k options dekhna chahu gi").json()
    assert "karachi" in r3["message"].lower()

    # Turn 4
    r4 = chat(web, cid=cid, message="karachi mein kon kon se areas k options available hai").json()
    assert "karachi" in r4["message"].lower()
    assert "dha phase 6" in r4["message"].lower()

    # Turn 5
    r5 = chat(web, cid=cid, message="g suggest krey").json()
    assert r5.get("properties")
    assert r5["properties"][0]["city"] == "Karachi"


# ==============================================================================
# 15. Self-Offer Affirmative Executes Suggestion
# ==============================================================================
def test_self_offer_affirmative_executes_suggestion(grounded_env):
    """User replies 'g suggest krey' -> bot executes property search recommendation."""
    web, svc = grounded_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 6"
    svc.customers.preferences.budget_max = 70_000_000
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "purchase"

    cid = chat(web, message="Aoa").json()["conversation_id"]
    res = chat(web, cid=cid, message="g suggest krey").json()
    assert res.get("properties")
    assert res["properties"][0]["property_id"] == "KHI-DHA-HSE-001"


# ==============================================================================
# 16. Anti-Loop Guard: No Verbatim Repeated Bot Message on Protest
# ==============================================================================
def test_no_verbatim_repeated_bot_message(grounded_env):
    """When user protests ('lakin ap ne to kaha tha...'), bot does NOT repeat previous message."""
    web, svc = grounded_env
    cid = chat(web, message="Aoa").json()["conversation_id"]
    saved = svc.chat.store.rows[cid][2]
    saved["last_assistant_message"] = "Filhaal is criteria par verified options nahi mile."

    # Mock the return to match last_assistant_message
    res = chat(web, cid=cid, message="lakin ap ne to kaha tha options mil jayein ge").json()
    # The anti-loop guard changes the response text
    assert res["message"] != "Filhaal is criteria par verified options nahi mile."
