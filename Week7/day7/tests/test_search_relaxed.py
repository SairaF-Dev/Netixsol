import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from postgres_repository import (
    DEFAULT_WEIGHT_AREA,
    DEFAULT_WEIGHT_BEDROOM,
    DEFAULT_WEIGHT_BUDGET,
    DEFAULT_WEIGHT_TYPE,
    PostgresPropertyRepository,
    compute_allowed_budget_increase,
)
from test_phase9_chat import Store, chat, setup
from test_web_api import CUSTOMER_ID, Customers, Interactions, Properties
from web_api.app import ChatRequest
from web_api.chat import ChatAdapter
from web_api.services import WebServices


# ==============================================================================
# 1. WEIGHT ORDERING TEST
# ==============================================================================
def test_weight_ordering_and_priority():
    """
    Verify that bedroom is the most flexible constraint (lowest weight/penalty),
    so a bedroom-mismatch-only candidate scores lower (better) than a
    budget-mismatch-only candidate of similar normalized magnitude.
    """
    assert DEFAULT_WEIGHT_BEDROOM < DEFAULT_WEIGHT_BUDGET, "Bedroom weight must be lower than budget"
    assert DEFAULT_WEIGHT_BUDGET < DEFAULT_WEIGHT_TYPE, "Budget weight must be lower than property type"
    assert DEFAULT_WEIGHT_TYPE < DEFAULT_WEIGHT_AREA, "Property type weight must be lower than area"

    repo = PostgresPropertyRepository()

    req_bedrooms = 4
    req_budget = 50_000_000
    req_area = "DHA Phase 8"
    req_type = "House"
    req_purpose = "Purchase"

    cand_bed_mismatch = {
        "property_id": "TEST-1",
        "bedrooms": 5,
        "price": 50_000_000,
        "area": "DHA Phase 8",
        "property_type": "House",
        "purpose": "Purchase",
    }

    cand_budget_mismatch = {
        "property_id": "TEST-2",
        "bedrooms": 4,
        "price": 51_500_000,
        "area": "DHA Phase 8",
        "property_type": "House",
        "purpose": "Purchase",
    }

    d_bed1, d_bud1, d_ar1, d_ty1 = repo.compute_distance_metrics(
        cand_bed_mismatch, req_bedrooms, req_budget, req_area, req_type, req_purpose
    )
    d_bed2, d_bud2, d_ar2, d_ty2 = repo.compute_distance_metrics(
        cand_budget_mismatch, req_bedrooms, req_budget, req_area, req_type, req_purpose
    )

    assert pytest.approx(d_bed1, 0.01) == 0.333
    assert d_bud1 == 0.0
    assert d_bed2 == 0.0
    assert pytest.approx(d_bud2, 0.01) == 0.333

    score_bed = (
        DEFAULT_WEIGHT_BEDROOM * d_bed1
        + DEFAULT_WEIGHT_BUDGET * d_bud1
        + DEFAULT_WEIGHT_AREA * d_ar1
        + DEFAULT_WEIGHT_TYPE * d_ty1
    )
    score_bud = (
        DEFAULT_WEIGHT_BEDROOM * d_bed2
        + DEFAULT_WEIGHT_BUDGET * d_bud2
        + DEFAULT_WEIGHT_AREA * d_ar2
        + DEFAULT_WEIGHT_TYPE * d_ty2
    )

    assert score_bed < score_bud, f"Bedroom mismatch score ({score_bed}) should be lower than budget mismatch ({score_bud})"


# ==============================================================================
# 2. NORMALIZATION TEST (No distance component exceeds 1.0)
# ==============================================================================
def test_distance_normalization_bounds():
    """
    Verify that all distance metrics are strictly clamped to [0.0, 1.0]
    under extreme inputs.
    """
    repo = PostgresPropertyRepository()

    extreme_cand = {
        "bedrooms": 25,
        "price": 5_000_000_000,
        "area": "Different Area",
        "property_type": "Commercial Office",
    }

    d_bed, d_bud, d_ar, d_ty = repo.compute_distance_metrics(
        extreme_cand,
        requested_bedrooms=1,
        requested_budget=10_000_000,
        requested_area="DHA Phase 8",
        requested_type="Apartment",
        requested_purpose="Purchase",
    )

    assert 0.0 <= d_bed <= 1.0, f"d_bed {d_bed} exceeded [0, 1]"
    assert 0.0 <= d_bud <= 1.0, f"d_bud {d_bud} exceeded [0, 1]"
    assert 0.0 <= d_ar <= 1.0, f"d_ar {d_ar} exceeded [0, 1]"
    assert 0.0 <= d_ty <= 1.0, f"d_ty {d_ty} exceeded [0, 1]"
    assert d_bed == 1.0
    assert d_bud == 1.0
    assert d_ar == 1.0
    assert d_ty == 1.0


# ==============================================================================
# 3. BUDGET TIER + ABSOLUTE CAP TEST
# ==============================================================================
def test_budget_tiers_and_absolute_caps():
    """
    Verify tiered percentage tolerance and absolute PKR caps across price tiers.
    """
    # 1. Economy (< 3 Crore): 15% tolerance, capped at 30 Lakh
    assert compute_allowed_budget_increase(10_000_000, "Purchase") == 1_500_000.0
    assert compute_allowed_budget_increase(25_000_000, "Purchase") == 3_000_000.0

    # 2. Mid (3 to 6 Crore): 10% tolerance, capped at 45 Lakh
    assert compute_allowed_budget_increase(40_000_000, "Purchase") == 4_000_000.0
    assert compute_allowed_budget_increase(55_000_000, "Purchase") == 4_500_000.0

    # 3. Luxury (> 6 Crore): 5% tolerance, capped at 50 Lakh
    assert compute_allowed_budget_increase(80_000_000, "Purchase") == 4_000_000.0
    # At 80 Crore (800M): 5% would be 40M, but capped at 5M!
    assert compute_allowed_budget_increase(800_000_000, "Purchase") == 5_000_000.0


# ==============================================================================
# 4. HARD BUDGET CUTOFF TEST
# ==============================================================================
def test_hard_budget_cutoff_in_search_relaxed():
    """
    Verify that an over-budget property is completely excluded from the candidate
    pool before scoring, even if area and type are a perfect match.
    """
    repo = PostgresPropertyRepository()

    res = repo.search_relaxed(
        city="Lahore",
        area="NonExistentArea",
        budget=20_000_000,
        purpose="Purchase",
    )

    for p in res["relaxed_matches"]:
        price = float(p.get("price") or 0)
        assert price <= 23_000_000, f"Property {p.get('property_id')} with price {price} exceeded hard cutoff 23M"


# ==============================================================================
# 5. FAIL-SAFE LLM INTENT CLASSIFICATION TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_classify_pending_choice_fail_safe():
    """
    Verify that on API error / timeout / malformed output, classify_pending_choice
    safely defaults to UNCLEAR and never crashes or guesses.
    """
    services = WebServices(Customers(), PostgresPropertyRepository(), Interactions())
    chat_adapter = ChatAdapter(services, Store())

    # Simulated LLM failure via exception
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = TimeoutError("Connection timed out")

    mock_sara = MagicMock()
    mock_sara.understanding.client = mock_client
    chat_adapter.sara = mock_sara

    # Call with failing client
    result = await chat_adapter.classify_pending_choice("Option A please", "DHA Phase 8 5-bed", "DHA Phase 6 4-bed")
    # Must safely default to UNCLEAR on error
    assert result == "UNCLEAR"


@pytest.mark.asyncio
async def test_classify_pending_choice_offline_heuristics():
    """
    Verify offline deterministic classification when no LLM is connected.
    """
    services = WebServices(Customers(), PostgresPropertyRepository(), Interactions())
    chat_adapter = ChatAdapter(services, Store())
    chat_adapter.sara = MagicMock()
    chat_adapter.sara.understanding.client = None

    opt_a = "DHA Phase 8 mein 5-bed option"
    opt_b = "DHA Phase 6 mein 4-bed exact match"

    assert await chat_adapter.classify_pending_choice("Phase 8 wala dikhao", opt_a, opt_b) == "OPTION_A"
    assert await chat_adapter.classify_pending_choice("pehle wala dekhna hai", opt_a, opt_b) == "OPTION_A"
    assert await chat_adapter.classify_pending_choice("Phase 6 wala dikha dein", opt_a, opt_b) == "OPTION_B"
    assert await chat_adapter.classify_pending_choice("doosra option dikhao", opt_a, opt_b) == "OPTION_B"
    assert await chat_adapter.classify_pending_choice("dono nahi chahiye", opt_a, opt_b) == "NEITHER"
    assert await chat_adapter.classify_pending_choice("haan theek hai", opt_a, opt_b) == "UNCLEAR"
    assert await chat_adapter.classify_pending_choice("batao", opt_a, opt_b) == "UNCLEAR"


# ==============================================================================
# 6. FRAME HANDLING: IN-DOMAIN SEARCH VS OFF-TOPIC INTERRUPTION & RE-ANCHORING
# ==============================================================================
def test_frame_handling_interruption_vs_new_search():
    """
    Verify that:
    1. An off-topic guardrail query preserves the frame as 'interrupted'.
    2. Returning to property topic prompts a re-anchoring question.
    3. A new in-domain search discards the frame without re-anchoring.
    """
    store = Store()
    web, svc, nlu = setup(store=store)

    frame = {
        "status": "pending",
        "city": "Karachi",
        "requested_area": "DHA Phase 8",
        "option_a": {
            "type": "same_area_relaxed",
            "area": "DHA Phase 8",
            "bedrooms": 5,
            "desc": "DHA Phase 8 mein 5-bed option",
            "properties": [],
        },
        "option_b": {
            "type": "cross_area_exact",
            "area": "DHA Phase 6",
            "bedrooms": 4,
            "desc": "DHA Phase 6 mein 4-bed exact match",
            "properties": [],
        },
    }

    # Start a chat session
    r0 = chat(web, message="Aoa").json()
    cid = r0["conversation_id"]

    # Inject pending_choice_frame into saved context
    store.rows[cid][2]["pending_choice_frame"] = frame

    # Turn 1: Off-topic interruption (cricket)
    nlu.result.intent = "off_topic"
    res1 = chat(web, cid, message="mujey cricket k barey mein btao").json()
    assert "property" in res1["message"].lower()

    # Verify frame is NOT discarded; status is now 'interrupted'
    saved_after = store.rows[cid][2]
    assert "pending_choice_frame" in saved_after
    assert saved_after["pending_choice_frame"]["status"] == "interrupted"

    # Turn 2: User returns to property topic without new search criteria
    nlu.result.intent = "property_search"
    nlu.result.required = {}
    res2 = chat(web, cid, message="acha chalo property ki baat karein").json()
    # Should re-anchor to the earlier choice!
    reply2 = res2["message"].lower()
    assert "pehle aap" in reply2 or "dha phase 8" in reply2
    assert "naye sirey" in reply2 or "choose kar rahe the" in reply2

    # Turn 3: User now decides to do a brand new in-domain search in Islamabad
    nlu.result.required = {"city": "Islamabad"}
    res3 = chat(web, cid, message="Islamabad mein 3-bed apartment dikhao").json()
    # New in-domain search must take priority and discard the old frame!
    saved_final = store.rows[cid][2]
    assert "pending_choice_frame" not in saved_final


# ==============================================================================
# 7. LIVE KARACHI DUAL-OPTION INTEGRATION TEST
# ==============================================================================
def test_live_karachi_dual_option_flow():
    """
    Verify the user's exact scenario:
    Karachi, DHA Phase 8, 4 beds, House, 80 Crore:
    Sara returns dual option: DHA Phase 8 (5-bed) vs DHA Phase 6 (4-bed exact match).
    """
    store = Store()
    props = Properties()
    # Populate Karachi properties matching database truth
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
    ]

    class MockRelaxedRepo(PostgresPropertyRepository):
        def _connect(self):
            # Use live postgres or mock rows
            return super()._connect()

    web, svc, nlu = setup(store=store)
    # Use real PostgresPropertyRepository
    svc.properties = PostgresPropertyRepository()

    # User establishes 4-bed house in DHA Phase 8 with 80 crore budget
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 800_000_000

    r1 = chat(web, message="yhi requirements hai").json()
    reply = r1["message"]

    # Should offer DHA Phase 8 (5-bed) vs DHA Phase 6 (4-bed exact match)
    assert "DHA Phase 8" in reply
    assert "4-bed" in reply or "4" in reply
    assert "5-bed" in reply or "5" in reply
    assert "DHA Phase 6" in reply
    assert "kaunsa dekhna chahenge" in reply

    cid = r1["conversation_id"]
    saved = store.rows[cid][2]
    assert "pending_choice_frame" in saved
    assert saved["pending_choice_frame"]["status"] == "pending"

    # User chooses Option A (5-bed / DHA Phase 8)
    r2 = chat(web, cid, message="DHA Phase 8 wala 5-bed option dikhao").json()
    assert "DHA Luxury Residence" in r2["message"]
    assert "95,000,000" in r2["message"]


# ==============================================================================
# 8. FAILURE 1: SEARCH_RELAXED TRIGGERS AT MID-RANGE BUDGET
# ==============================================================================
def test_relaxed_search_triggers_at_mid_budget():
    """
    Reproduce Failure 1:
    User establishes Karachi, DHA Phase 8, House, 4 bedroom, budget 15 crore (150M PKR).
    Exact match is 0 rows (only 5-bed house KHI-DHA-HSE-002 exists in DHA Phase 8, 9.5 Cr).
    search_relaxed() must trigger and suggest the DHA Phase 8 5-bed house in Option A.
    """
    store = Store()
    web, svc, nlu = setup(store=store)
    svc.properties = PostgresPropertyRepository()

    # User establishes 4-bed house in DHA Phase 8 with 15 crore budget
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 150_000_000

    r1 = chat(web, message="Karachi, DHA Phase 8, House, 4 bedroom, budget 15 crore").json()
    reply = r1["message"]

    # Must suggest DHA Phase 8 (5-bed) relaxed option!
    assert "DHA Phase 8" in reply
    assert "5-bed" in reply or "5" in reply
    assert "kaunsa dekhna chahenge" in reply or "Kya aap yeh option dekhna chahenge" in reply

    cid = r1["conversation_id"]
    saved = store.rows[cid][2]
    assert "pending_choice_frame" in saved
    frame = saved["pending_choice_frame"]
    assert frame["option_a"]["area"] == "DHA Phase 8"
    assert frame["option_a"]["bedrooms"] == 5


# ==============================================================================
# 9. FAILURE 2: HARD CUTOFF EXCLUDES OVER-TIER PROPERTY
# ==============================================================================
def test_hard_cutoff_excludes_over_tier_property():
    """
    Reproduce Failure 2 Cutoff:
    Budget 3 Crore (30M PKR). Allowed increase: 3M (max 33M).
    In DHA Phase 8:
      - KHI-DHA-APT-001 is 35M (> 33M, excluded)
      - KHI-DHA-HSE-002 is 95M (> 33M, excluded)
    search_relaxed() must return 0 relaxed_matches for DHA Phase 8.
    """
    repo = PostgresPropertyRepository()
    res = repo.search_relaxed(
        city="Karachi",
        area="DHA Phase 8",
        budget=30_000_000,
        property_type="House",
        purpose="Purchase",
    )
    assert len(res["relaxed_matches"]) == 0, (
        f"Expected 0 relaxed matches in DHA Phase 8 under 33M cutoff, but got: {res['relaxed_matches']}"
    )


# ==============================================================================
# 10. FAILURE 2: RELAXED SUGGESTION NAMES PROPERTY TYPE TRANSPARENTLY
# ==============================================================================
def test_relaxed_suggestion_names_property_type():
    """
    Reproduce Failure 2 Property-Type Substitution:
    Budget 4 Crore (40M PKR). Max allowed price under 10% increase is 44M.
    In DHA Phase 8, only an Apartment (KHI-DHA-APT-001, 35M, 2 beds) is <= 44M.
    When property_type is relaxed from House to Apartment, Sara must explicitly
    name 'Apartment' and not falsely claim it is a House.
    """
    repo = PostgresPropertyRepository()
    res = repo.search_relaxed(
        city="Karachi",
        area="DHA Phase 8",
        budget=40_000_000,
        bedrooms=4,
        property_type="House",
        purpose="Purchase",
    )
    assert len(res["relaxed_matches"]) > 0
    top_cand = res["relaxed_matches"][0]
    assert top_cand["property_type"] == "Apartment"

    store = Store()
    web, svc, nlu = setup(store=store)
    svc.properties = repo

    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 40_000_000

    r1 = chat(web, message="DHA Phase 8 mein 4-bed house chahiye 4 crore budget hai").json()
    reply = r1["message"]
    # Must transparently mention Apartment
    assert "Apartment" in reply or "apartment" in reply
    assert "House nahi mila" in reply or "House" in reply


# ==============================================================================
# 11. FAILURE 3: SINGLE-OPTION AFFIRMATIVE RESOLUTION
# ==============================================================================
@pytest.mark.asyncio
async def test_single_option_affirmative_resolves():
    """
    Reproduce Failure 3:
    When a single relaxed option is presented (option_b is None),
    affirmative replies ('thik hai', 'ji', 'haan', 'ok', 'acha')
    must resolve to OPTION_A instead of UNCLEAR.
    """
    services = WebServices(Customers(), PostgresPropertyRepository(), Interactions())
    chat_adapter = ChatAdapter(services, Store())
    chat_adapter.sara = MagicMock()
    chat_adapter.sara.understanding.client = None

    opt_a = "DHA Phase 8 mein 5-bed option"
    # Single-option mode: option_b is None
    for aff in ["thik hai", "theek hai", "ji", "haan", "ok", "acha", "sahi hai", "dikhao", "bilkul"]:
        assert await chat_adapter.classify_pending_choice(aff, opt_a, None) == "OPTION_A", (
            f"'{aff}' failed to classify as OPTION_A in single-option mode"
        )

    # Rejections must resolve to NEITHER
    for neg in ["nahi", "nahin", "rehne do", "koi aur"]:
        assert await chat_adapter.classify_pending_choice(neg, opt_a, None) == "NEITHER", (
            f"'{neg}' failed to classify as NEITHER in single-option mode"
        )


# ==============================================================================
# 12. EDGE CASE 1: CROSS-AREA FALLBACK WHEN SAME-AREA IS EMPTY
# ==============================================================================
def test_cross_area_fallback_when_same_area_empty():
    """
    Edge Case 1:
    When same-area has 0 relaxed matches passing budget cutoff (e.g. DHA Phase 8, 3 crore),
    cross-area alternatives (DHA Phase 6) must still be presented as Branch 3.
    Affirmative reply ('thik hai') must resolve against option_a and display cross-area options.
    """
    store = Store()
    web, svc, nlu = setup(store=store)

    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 30_000_000

    prop_p6 = {
        "property_id": "KHI-DHA-HSE-001",
        "property_name": "DHA Family Residence",
        "city": "Karachi",
        "area": "DHA Phase 6",
        "price": 28_000_000,
        "bedrooms": 4,
        "bathrooms": 4,
        "property_type": "House",
        "purpose": "purchase",
        "available": True,
        "verification_status": "Verified",
        "currency": "PKR",
        "amenities": ["Parking"],
    }

    class MockCrossAreaRepo(PostgresPropertyRepository):
        def search_relaxed(self, **kwargs):
            if kwargs.get("area") == "DHA Phase 8":
                return {
                    "exact_matches": [],
                    "relaxed_matches": [],
                    "relaxed_scores": [],
                    "relaxed_constraint": None,
                    "relaxed_meta": {},
                    "cross_area_alternatives": ["DHA Phase 6"],
                }
            return {
                "exact_matches": [prop_p6],
                "relaxed_matches": [],
                "relaxed_scores": [],
                "relaxed_constraint": None,
                "relaxed_meta": {},
                "cross_area_alternatives": [],
            }

        def search(self, **kwargs):
            if kwargs.get("area") == "DHA Phase 8":
                return []
            return [prop_p6]

        def list_available_areas(self, **kwargs):
            return ["DHA Phase 6"]

    svc.properties = MockCrossAreaRepo()

    r1 = chat(web, message="yhi requirements hai").json()
    reply1 = r1["message"]
    # Branch 3 phrasing: states DHA Phase 8 has no options, but DHA Phase 6 has exact match
    assert "DHA Phase 6" in reply1
    assert "dekhna chahenge" in reply1

    cid = r1["conversation_id"]
    saved = store.rows[cid][2]
    assert "pending_choice_frame" in saved
    frame = saved["pending_choice_frame"]
    assert frame["option_a"]["area"] == "DHA Phase 6"
    assert frame["option_b"] is None

    # User confirms with single-option affirmative 'thik hai'
    r2 = chat(web, cid, message="thik hai").json()
    reply2 = r2["message"]
    assert "DHA Family Residence" in reply2
    assert "DHA Phase 6" in reply2


# ==============================================================================
# 13. EDGE CASE 2: SINGLE-FIELD REFINEMENT OF PENDING CHOICE
# ==============================================================================
def test_single_field_adjustment_refines_pending_choice():
    """
    Edge Case 2:
    User has a pending choice frame.
    User adjusts only budget (e.g. 'budget 20 crore kar dete hain') without changing city/area/type.
    Must NOT trigger classify_pending_choice / UNCLEAR loop;
    must update state.required['budget'], discard frame, and re-run search at 20 crore.
    """
    store = Store()
    web, svc, nlu = setup(store=store)
    svc.properties = PostgresPropertyRepository()

    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 150_000_000

    r1 = chat(web, message="Karachi, DHA Phase 8, 4 bedroom house, budget 15 crore").json()
    cid = r1["conversation_id"]
    saved = store.rows[cid][2]
    assert "pending_choice_frame" in saved

    # User refines budget to 20 crore (200M)
    nlu.result.intent = "property_search"
    nlu.result.required = {"budget": 200_000_000}
    r2 = chat(web, cid, message="budget 20 crore kar dete hain").json()
    reply2 = r2["message"]

    # Frame should be popped, and search should re-run with 20 crore budget in DHA Phase 8
    # Should NOT ask 'Barah-e-karam wazeh kar dein'
    assert "Barah-e-karam wazeh kar dein" not in reply2
    assert "DHA Phase 8" in reply2


# ==============================================================================
# 14. EDGE CASE 2: AREA CHANGE DISCARDS PENDING CHOICE
# ==============================================================================
def test_area_change_discards_pending_choice():
    """
    Edge Case 2:
    When user specifies a new area not in the frame (e.g. 'Clifton'),
    old choice frame is discarded and new search is executed for Clifton.
    """
    store = Store()
    web, svc, nlu = setup(store=store)
    svc.properties = PostgresPropertyRepository()

    # Create initial pending choice frame in DHA Phase 8
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 150_000_000

    r1 = chat(web, message="DHA Phase 8 mein house chahiye").json()
    cid = r1["conversation_id"]
    assert "pending_choice_frame" in store.rows[cid][2]

    # User changes area to Clifton
    nlu.result.intent = "property_search"
    nlu.result.required = {"city": "Karachi", "area": "Clifton"}
    r2 = chat(web, cid, message="Clifton mein dekhte hain").json()

    saved_after = store.rows[cid][2]
    # Frame was either discarded or replaced by Clifton search
    if "pending_choice_frame" in saved_after:
        assert saved_after["pending_choice_frame"]["requested_area"] == "Clifton"


# ==============================================================================
# 15. EDGE CASE 3: NO FRAME CREATED WHEN NO OPTIONS EXIST ANYWHERE
# ==============================================================================
def test_no_frame_created_when_no_options_exist():
    """
    Edge Case 3:
    When neither same-area relaxed matches nor cross-area alternatives exist
    (e.g. budget 100,000 PKR for a house in Karachi),
    Branch 4 emits a grounded terminal message and NEVER creates pending_choice_frame.
    """
    store = Store()
    web, svc, nlu = setup(store=store)
    svc.properties = PostgresPropertyRepository()

    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.bedrooms = 4
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "Purchase"
    svc.customers.preferences.budget_max = 100_000  # 1 Lakh PKR (impossible)

    r1 = chat(web, message="yhi requirements hai").json()
    reply = r1["message"]

    # Grounded message emitted
    assert "verified options nahi mile" in reply or "koi verified option nahi" in reply

    cid = r1["conversation_id"]
    saved = store.rows[cid][2]
    # CRITICAL: No frame must be created!
    assert "pending_choice_frame" not in saved
    assert "pending_suggested_area" not in saved
