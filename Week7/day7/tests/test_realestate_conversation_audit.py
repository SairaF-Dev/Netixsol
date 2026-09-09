import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from sara_agent.models import UserUnderstanding
from sara_agent.understanding import UserUnderstandingService
from test_phase9_chat import setup, chat
from test_web_api import CUSTOMER_ID, Customers, Properties

def create_audit_properties():
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
    props.list_available_areas = lambda **k: ["DHA Phase 6", "DHA Phase 8", "Gulshan-e-Iqbal"]
    props.list_available_cities = lambda: ["Karachi", "Lahore", "Islamabad"]
    props.get_property = lambda pid: next((dict(r) for r in props.rows if r["property_id"] == pid), None)
    return props

@pytest.fixture
def audit_env(monkeypatch):
    monkeypatch.setattr(UserUnderstandingService, "_call_llm", Mock(side_effect=RuntimeError("offline test")))
    web, svc, _ = setup()
    svc.chat.sara.understanding = UserUnderstandingService(deterministic_first=True)
    svc.properties = create_audit_properties()
    svc.chat.services.properties = svc.properties

    prefs = svc.customers.preferences
    prefs.city = "Karachi"
    prefs.area = "DHA Phase 6"
    prefs.budget_max = 65_000_000
    prefs.property_type = "House"
    prefs.purpose = "purchase"
    prefs.bedrooms = 4
    return web, svc

def test_1_same_requirements_retrieval_and_profile_intact(audit_env):
    """Test 1: 'wahi requirements hai meri' retrieves saved requirement without mutating profile."""
    web, svc = audit_env
    # Greeting turn
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    assert "Karachi" in resp1["message"]
    
    # User confirms same requirements
    before_budget = svc.customers.preferences.budget_max
    resp2 = chat(web, cid, "wahi requirements hai meri").json()
    assert "DHA Family Residence" in resp2["message"]
    assert resp2.get("properties") and resp2["properties"][0]["property_id"] == "KHI-DHA-HSE-001"
    assert svc.customers.preferences.budget_max == before_budget == 65_000_000

def test_2_budget_objection_does_not_mutate_budget(audit_env):
    """Test 2: 'ye property bht mehngi hai' is an objection, not a budget overwrite."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")
    
    before_budget = svc.customers.preferences.budget_max
    resp3 = chat(web, cid, "ye property bht mehngi hai").json()
    assert "budget" in resp3["message"].lower()
    # Stored profile budget must remain completely unchanged
    assert svc.customers.preferences.budget_max == before_budget == 65_000_000

def test_3_minimum_budget_query_grounded_in_verified_houses(audit_env):
    """Test 3: 'minimum budget kitna hona chahey' returns 6.5 Crore for Karachi houses, NOT 1.2 Crore."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")
    
    before_budget = svc.customers.preferences.budget_max
    resp_min = chat(web, cid, "minimum budget kitna hona chahey").json()
    msg = resp_min["message"]
    
    # Must report 6.5 Crore (the lowest verified house in Karachi), never hallucinate 1.2 Crore
    assert "6.5 Crore" in msg
    assert "1.2 Crore" not in msg
    assert "DHA Family Residence" in msg
    assert svc.customers.preferences.budget_max == before_budget

def test_4_property_type_by_budget_under_1_2_crore_neither_available(audit_env):
    """Test 4: '1.2 crore mein apartment aye ga ya house' states neither is available and preserves profile budget."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")
    
    before_budget = svc.customers.preferences.budget_max
    resp = chat(web, cid, "1.2 crore mein apartment aye ga ya house").json()
    msg = resp["message"]
    
    # Ground truth: in Karachi purchase, lowest apt is 2.1 Cr, lowest house is 6.5 Cr
    # Under 1.2 Cr, neither is available
    assert "na hi apartment" in msg or "apartment available nahi" in msg
    assert "2.1 Crore" in msg  # apartment starting price
    assert "6.5 Crore" in msg  # house starting price
    # CRITICAL: customer profile budget must NOT be overwritten to 1.2 crore (12M)
    assert svc.customers.preferences.budget_max == before_budget == 65_000_000

def test_5_property_type_by_budget_under_3_crore_only_apartment(audit_env):
    """Test 5: '3 crore mein apartment aye ga ya house' states only apartment is available."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")
    
    before_budget = svc.customers.preferences.budget_max
    resp = chat(web, cid, "3 crore mein apartment aye ga ya house").json()
    msg = resp["message"]
    
    assert "apartment to mil sakta hai" in msg or "apartment available hai" in msg
    assert "house nahi mil sakta" in msg or "house available nahi" in msg
    assert svc.customers.preferences.budget_max == before_budget == 65_000_000

def test_6_property_type_by_budget_under_7_crore_both_available(audit_env):
    """Test 6: '7 crore mein apartment aye ga ya house' states both are available."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")
    
    before_budget = svc.customers.preferences.budget_max
    resp = chat(web, cid, "7 crore mein apartment aye ga ya house").json()
    msg = resp["message"]
    
    assert "apartment aur house dono" in msg or ("apartment" in msg and "house" in msg and "dono" in msg)
    assert svc.customers.preferences.budget_max == before_budget == 65_000_000

def test_7_cheapest_property_query(audit_env):
    """Test 7: 'sab se sasta house konsa hai' returns DHA Family Residence (6.5 Crore PKR)."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    
    resp = chat(web, cid, "sab se sasta house konsa hai").json()
    msg = resp["message"]
    assert "DHA Family Residence" in msg
    assert "6.5 Crore" in msg or "65,000,000" in msg

def test_8_budget_feasibility_query(audit_env):
    """Test 8: 'kya 1.2 crore mein house mil sakta hai?' explains 1.2 Crore is not enough for houses."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    
    resp = chat(web, cid, "kya 1.2 crore mein house mil sakta hai?").json()
    msg = resp["message"]
    assert "1.2 Crore" in msg or "12,000,000" in msg or "apartment" in msg
    assert "na hi" in msg or "nahi mil sakta" in msg or "houses kam az kam" in msg

def test_9_area_relaxation_breaks_repetition_loop(audit_env):
    """Test 9: 'g dusrey areas dikha dein' does not enter preference edit trap and loops."""
    web, svc = audit_env
    # Customer has 20M (2 Crore) budget in DHA Phase 6 (where houses start at 65M) -> 0 results
    svc.customers.preferences.budget_max = 20_000_000
    
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    
    # Confirming requirements leads to zero results prompt
    resp2 = chat(web, cid, "requiremenys wahi hai").json()
    assert "options nahi" in resp2["message"] or "verified options nahi mile" in resp2["message"]
    
    # User asks for other areas
    resp3 = chat(web, cid, "g dusrey areas dikha dein").json()
    msg3 = resp3["message"]
    # Must NOT ask "Aapka naya area kya hoga?" or "Aapki pichli property preference..."
    assert "Aapka naya area kya hoga" not in msg3
    assert "pichli property preference" not in msg3
    assert "pichli saved area requirement" not in msg3
    
    # User follows up
    resp4 = chat(web, cid, "mujey mazwwd areas dikhao").json()
    msg4 = resp4["message"]
    assert "Aapka naya area kya hoga" not in msg4
    assert "pichli property preference" not in msg4
    
    # User follows up again
    resp5 = chat(web, cid, "mazeed areas dikha dein").json()
    msg5 = resp5["message"]
    assert "Aapka naya area kya hoga" not in msg5
    assert "pichli property preference" not in msg5

def test_10_dha_phase8_selection_and_feasibility_flow(audit_env):
    """Test 10: Full conversation reproduction:
    - 10 Crore Karachi House Purchase
    - User selects DHA Phase 8: Sara retrieves DHA Luxury Residence (KHI-DHA-HSE-002, 95M)
    - User asks about DHA Phase 6 feasibility: Sara confirms options available under 10 Crore, no '0.08 Lakh PKR'.
    """
    web, svc = audit_env
    svc.customers.preferences.budget_max = 100_000_000
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "purchase"
    svc.customers.preferences.area = None

    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    assert "Karachi" in resp1["message"]

    resp2 = chat(web, cid, "wahi requirements hai").json()
    assert "DHA Phase 8" in resp2["message"] or "DHA Phase 6" in resp2["message"]

    # Turn 3: User specifies DHA Phase 8
    resp3 = chat(web, cid, "mujhey DHA Phase 8 mrein dekhna hai").json()
    msg3 = resp3["message"]
    assert "DHA Luxury Residence" in msg3 or "95,000,000" in msg3
    assert "options nahi" not in msg3.lower()

    # Turn 4: User asks if options are available in DHA Phase 6 according to budget
    resp4 = chat(web, cid, "kiya dha phase 6 mein meray budget k according options available hai").json()
    msg4 = resp4["message"]
    assert "Ji bilkul" in msg4
    assert "0.08 Lakh" not in msg4
    assert "0.08" not in msg4
    assert "8,000" not in msg4
    assert "10 Crore" in msg4 or "Karachi" in msg4

def test_11_k_options_does_not_corrupt_budget_to_8000(audit_env):
    """Test 11: 'ap phir dha phase 8 k options dikha rahey hai' must not parse '8 k' as 8,000 PKR budget."""
    web, svc = audit_env
    svc.customers.preferences.budget_max = 100_000_000
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    
    chat(web, cid, "lakin ap ne to kaha k dha phase 8 mein options nahi hai aor dha phase 6 mein options available hai jb mein g dekhna chahu gi to ap phir dha phase 8 k options dikha rahey hai")
    
    assert svc.customers.preferences.budget_max == 100_000_000

def test_12_pending_suggested_area_transition(audit_env):
    """Test 12: When Sara suggests alternative areas, user agreement ('g dekhna chahu gi')
    switches to the suggested area and displays verified listings."""
    web, svc = audit_env
    svc.customers.preferences.budget_max = 70_000_000
    svc.customers.preferences.area = "DHA Phase 8"
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "purchase"
    
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    
    resp2 = chat(web, cid, "wahi requirements hai").json()
    msg2 = resp2["message"]
    assert "DHA Phase 6" in msg2
    
    resp3 = chat(web, cid, "g dekhna chahu gi").json()
    msg3 = resp3["message"]
    assert "DHA Family Residence" in msg3
    assert "DHA Phase 6" in msg3
    assert "DHA Phase 8" not in msg3

def test_13_budget_query_not_mistaken_for_area(audit_env):
    """Test 13: '60 crore mein kn kn si properties hai' must NOT treat '60 crore' as an area name."""
    web, svc = audit_env
    resp1 = chat(web, message="Aoa mujey property chahey mera budget 10 crore hai").json()
    cid = resp1["conversation_id"]
    
    resp2 = chat(web, cid, "karachi mein knsey areas hai").json()
    msg2 = resp2["message"]
    assert "DHA Family Residence" in msg2 or "DHA Phase 6" in msg2
    
    resp3 = chat(web, cid, "60 crore mein kn kn si properties hai").json()
    msg3 = resp3["message"]
    
    assert "60 crore mein to is criteria par verified options nahi mile" not in msg3
    assert "60 crore mein to" not in msg3
    assert "DHA Family Residence" in msg3
    assert "DHA Luxury Residence" in msg3


def test_14_cheaper_property_flow_from_dha_phase_8(audit_env):
    """Test 14: When viewing DHA Phase 8 (95M), 'is se sasti dikhaye' retrieves
    DHA Family Residence (65M, DHA Phase 6) with property card and no 500 error."""
    web, svc = audit_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = None
    svc.customers.preferences.budget_max = 600_000_000
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "purchase"
    svc.customers.preferences.bedrooms = None

    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]

    # Turn 2: wahi requirements
    resp2 = chat(web, cid, "wahi requirements hai").json()
    assert "DHA Phase 8" in resp2["message"] or "DHA Phase 6" in resp2["message"]

    # Turn 3: User picks DHA Phase 8
    resp3 = chat(web, cid, "Dha phase 8 mein dikha dein").json()
    assert resp3.get("properties") and resp3["properties"][0]["property_id"] == "KHI-DHA-HSE-002"

    # Turn 4: User requests cheaper option
    resp4_raw = chat(web, cid, "ye mehngi hai property, is se sasti dikhaye")
    assert resp4_raw.status_code == 200
    resp4 = resp4_raw.json()
    msg4 = resp4["message"]

    assert "DHA Family Residence" in msg4
    assert "DHA Phase 6" in msg4
    assert "65,000,000" in msg4 or "6.5 Crore" in msg4
    assert resp4.get("properties") and resp4["properties"][0]["property_id"] == "KHI-DHA-HSE-001"
    assert "plots" not in msg4.lower()


def test_15_cheapest_house_alternative_suggests_apartments_not_plots(audit_env):
    """Test 15: When viewing lowest house (6.5 Crore), requesting cheaper property
    suggests Apartments (starting at 2.1 Crore), NEVER bare plots."""
    web, svc = audit_env
    svc.customers.preferences.city = "Karachi"
    svc.customers.preferences.area = "DHA Phase 6"
    svc.customers.preferences.budget_max = 65_000_000
    svc.customers.preferences.property_type = "House"
    svc.customers.preferences.purpose = "purchase"
    svc.customers.preferences.bedrooms = 4

    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]
    chat(web, cid, "wahi requirements hai meri")

    # User views DHA Family Residence (65M), then asks for cheaper
    resp_cheap = chat(web, cid, "ye bhi bht mehngi hai, is se sasta kya hai").json()
    msg = resp_cheap["message"]

    assert "apartment" in msg.lower()
    assert "2.1 Crore" in msg or "21,000,000" in msg
    assert "plot" not in msg.lower()


def test_16_strict_preference_update_rules(audit_env):
    """Test 16: Strict adherence to user's 5 PREFERENCE UPDATE RULES:
    1. Only update or save preference when user explicitly states it in their message.
    2. NEVER save a value as user preference just because assistant suggested/searched it.
    3. Treat 'yeh area/property mujhe dikhao' as a ONE-TIME query, not saved preference.
    4. Only report explicitly stated preferences on 'meri preferences kya hain?'.
    """
    web, svc = audit_env
    # Initial customer state: Karachi, 10 Crore, House, Purchase, Area=None
    prefs = svc.customers.preferences
    prefs.city = "Karachi"
    prefs.area = None
    prefs.budget_max = 100_000_000
    prefs.property_type = "House"
    prefs.purpose = "purchase"
    prefs.bedrooms = None

    # Turn 1: Greeting
    resp1 = chat(web, message="Aoa").json()
    cid = resp1["conversation_id"]

    # Turn 2: User confirms requirements
    resp2 = chat(web, cid, "wahi requirements hai").json()
    msg2 = resp2["message"]
    assert "Karachi" in msg2 or "10 crore" in msg2
    assert svc.customers.preferences.area is None

    # Turn 3: User asks one-time search query "Dha phase 8 mein dikha dein"
    resp3 = chat(web, cid, "Dha phase 8 mein dikha dein").json()
    msg3 = resp3["message"]
    assert "DHA Luxury Residence" in msg3
    # Rule 3: Must NOT save DHA Phase 8 into persistent user preferences!
    assert svc.customers.preferences.area is None

    # Turn 4: User requests cheaper option "ye mehngi hai property, is se sasti dikhaye"
    resp4 = chat(web, cid, "ye mehngi hai property, is se sasti dikhaye").json()
    msg4 = resp4["message"]
    assert "DHA Family Residence" in msg4
    # Rule 2: Assistant suggestion must NOT overwrite budget_max or save DHA Phase 6 area
    assert svc.customers.preferences.budget_max == 100_000_000
    assert svc.customers.preferences.area is None

    # Turn 5: User asks "meri preferences kya hain?"
    resp5 = chat(web, cid, "meri preferences kya hain?").json()
    msg5 = resp5["message"]
    # Rule 5: Only report explicitly confirmed fields; NEVER include assistant-suggested values
    assert "Karachi" in msg5
    assert "10 Crore" in msg5
    assert "House" in msg5
    assert "DHA Phase 8" not in msg5
    assert "DHA Phase 6" not in msg5
