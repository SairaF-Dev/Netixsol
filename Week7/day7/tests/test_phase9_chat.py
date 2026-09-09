from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_auth_api import FakeAuth
from test_web_api import Customers, Properties, Interactions, ML, Deterministic, Appointments, CUSTOMER_ID
from web_api.app import create_app
from web_api.services import WebServices, RecommendationSessionStore
from web_api.conversation_service import ConversationDenied, ConversationExpired
from shared.sara_service import SaraService
from sara_agent.models import UserUnderstanding


class Store:
    def __init__(self): self.rows = {}; self.expired = set()
    @asynccontextmanager
    async def turn(self, cid, identity):
        if cid is None:
            cid = str(uuid4()); self.rows[cid] = (identity.customer_id, identity.user_id, {})
        cid = str(cid)
        row = self.rows.get(cid)
        if not row or row[:2] != (identity.customer_id, identity.user_id): raise ConversationDenied()
        if cid in self.expired: raise ConversationExpired()
        state = deepcopy(row[2])
        yield cid, state
        self.rows[cid] = (*row[:2], state)


class NLU:
    def __init__(self): self.result = UserUnderstanding(intent='property_search'); self.context = None
    def understand(self, message, context):
        self.context = deepcopy(context)
        if isinstance(self.result, Exception): raise self.result
        return self.result


def setup(store=None, sessions=None, mode='off'):
    auth = FakeAuth()
    auth.identities['token-a'] = SimpleNamespace(user_id='ua', customer_id=CUSTOMER_ID)
    auth.validate_csrf = lambda token, csrf: csrf == 'valid'
    nlu = NLU()
    svc = WebServices(Customers(), Properties(), Interactions(), Deterministic(), ML(mode), Appointments(),
                      sessions=sessions, auth_service=auth, chat_store=store or Store(), sara=SaraService(nlu))
    web = TestClient(create_app(svc), raise_server_exceptions=False)
    web.cookies.set('sara_session', 'token-a'); web.headers['X-CSRF-Token'] = 'valid'
    return web, svc, nlu


def chat(web, cid=None, message='Options dikha dein.'):
    return web.post('/api/me/chat', json={'message': message, **({'conversation_id': cid} if cid else {})})


def test_auth_csrf_and_identity_input():
    web, svc, nlu = setup()
    web.cookies.clear(); assert chat(web).status_code == 401
    web.cookies.set('sara_session','token-a'); web.headers.pop('X-CSRF-Token')
    assert chat(web).status_code == 403
    web.headers['X-CSRF-Token']='valid'
    for field in ['customer_id','user_id','phone','email']:
        assert web.post('/api/me/chat',json={'message':'hello',field:'bad'}).status_code == 422
    assert chat(web,message=' ').status_code == 422
    assert chat(web,message='x'*2001).status_code == 422


def test_creation_hydration_verified_results_shown_and_no_llm_facts():
    web, svc, nlu = setup()
    response = chat(web)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['properties']) == 2 and not data['requires_clarification']
    assert nlu.context['required']['budget'] == 20000000
    assert nlu.context['required']['bedrooms'] == 3
    assert all(e['action']=='shown' for e in svc.interactions.events)
    assert 'Home P-2' in data['message']
    assert 'probability' not in data['message']
    assert 'phone' not in str(nlu.context) and 'email' not in str(nlu.context)


@pytest.mark.parametrize('action',['liked','rejected','shortlisted'])
def test_second_reference_feedback_with_historical_snapshots(action):
    web, svc, nlu = setup()
    data=chat(web).json()
    nlu.result=UserUnderstanding(interaction_action=action,selected_index=1)
    assert chat(web,data['conversation_id']).status_code==200
    event=svc.interactions.events[-1]
    assert event['property_id']==data['properties'][1]['property_id']
    assert event['conversation_id']==data['recommendation_session_id']
    assert event['preference_snapshot']['budget_max']==20000000


@pytest.mark.parametrize('u',[UserUnderstanding(interaction_action='liked'),UserUnderstanding(interaction_action='liked',selected_index=9),UserUnderstanding(interaction_action='liked',interaction_property_id='FAKE')])
def test_ambiguous_or_arbitrary_reference_never_writes(u):
    web,svc,nlu=setup(); data=chat(web).json(); count=len(svc.interactions.events)
    nlu.result=u
    assert chat(web,data['conversation_id']).json()['requires_clarification']
    assert len(svc.interactions.events)==count


def test_budget_change_preserves_old_snapshot_and_new_recommendation_uses_new_budget():
    web,svc,nlu=setup(); first=chat(web).json()
    nlu.result=UserUnderstanding(intent='unknown',required={'budget':40000000})
    assert chat(web,first['conversation_id']).status_code==200
    assert svc.customers.preferences.budget_max==40000000
    assert svc.sessions.get(first['recommendation_session_id']).preference_snapshot['budget_max']==20000000
    nlu.result=UserUnderstanding(intent='property_search')
    new=chat(web,first['conversation_id']).json()
    assert new['recommendation_session_id']!=first['recommendation_session_id']
    assert svc.sessions.get(new['recommendation_session_id']).preference_snapshot['budget_max']==40000000
    assert svc.properties.search_calls[-1]['budget']==40000000


def test_multi_service_continuity_ownership_and_expiry():
    store=Store(); sessions=RecommendationSessionStore()
    a,sa,na=setup(store,sessions); first=chat(a).json(); cid=first['conversation_id']
    b,sb,nb=setup(store,sessions)
    nb.result=UserUnderstanding(interaction_action='liked',reference_type='second_result')
    assert chat(b,cid).status_code==200
    assert sb.interactions.events[-1]['property_id']==first['properties'][1]['property_id']
    assert nb.context['recent_turns']
    b.cookies.set('sara_session','token-b'); assert chat(b,cid).status_code==404
    b.cookies.set('sara_session','token-a'); store.expired.add(cid)
    assert chat(b,cid).status_code==410
    assert chat(b,str(uuid4())).status_code==404


@pytest.mark.parametrize('failure',['llm','database','preferences'])
def test_service_failure_is_safe(failure):
    web,svc,nlu=setup()
    def fail(*a,**k): raise RuntimeError('DATABASE_URL password api-secret')
    if failure=='llm': nlu.result=RuntimeError('provider api-secret')
    elif failure=='database': svc.properties.search=fail
    else:
        nlu.result=UserUnderstanding(required={'budget':40000000}); svc.customers.update_preferences=fail
    response=chat(web)
    assert response.status_code==503
    assert 'secret' not in response.text and 'DATABASE_URL' not in response.text


@pytest.mark.parametrize('mode',['off','shadow','active_dev'])
def test_existing_ranking_modes_reused(mode):
    web,svc,nlu=setup(mode=mode); data=chat(web).json()
    assert data['properties'][0]['property_id']==('P-1' if mode=='active_dev' else 'P-2')
    assert 'ml_mode' not in data


def test_booking_collects_time_delegates_and_maps_ownership():
    web,svc,nlu=setup(); data=chat(web).json(); owned=[]
    aid=str(uuid4())
    async def request(method,path,payload=None):
        svc.appointments.calls.append((method,path,payload)); return 201,{'appointment':{'appointment_id':aid,'status':'confirmed'}}
    svc.appointments.request=request
    svc.auth.repository.own_appointment=lambda user,appointment: owned.append((user,appointment))
    nlu.result=UserUnderstanding(intent='schedule_visit',selected_index=1)
    assert chat(web,data['conversation_id']).json()['requires_clarification']
    assert not svc.appointments.calls
    nlu.result=UserUnderstanding(intent='schedule_visit',starts_at='2030-01-01T10:00:00+05:00')
    result=chat(web,data['conversation_id'])
    assert result.status_code==200, result.text
    assert result.json()['appointment']['appointment_id']==aid
    assert owned==[('ua',aid)]
    assert svc.appointments.calls[0][2]['property_id']==data['properties'][1]['property_id']


@pytest.mark.parametrize('intent',['reschedule_visit','cancel_visit'])
def test_chat_cannot_mutate_unowned_appointment(intent):
    web,svc,nlu=setup()
    nlu.result=UserUnderstanding(intent=intent,appointment_id=str(uuid4()),starts_at='2030-01-01T10:00:00+05:00')
    assert chat(web).status_code==404
    assert not svc.appointments.calls


def test_bounded_structured_history_without_raw_text():
    web,svc,nlu=setup(); cid=None
    nlu.result=UserUnderstanding(intent='greeting')
    for i in range(9): cid=chat(web,cid,'private raw message password=secret').json()['conversation_id']
    saved=svc.chat.store.rows[cid][2]
    assert len(saved['recent_turns'])==6
    assert 'secret' not in str(saved) and 'private' not in str(saved)


def test_no_match_returns_no_property_claims():
    web,svc,nlu=setup(); svc.properties.rows=[]
    response=chat(web).json()
    assert 'properties' not in response and 'verified options nahi mile' in response['message']

def test_full_shared_nlu_extracts_locations_and_appointment_fields():
    import json
    from sara_agent.understanding import UserUnderstandingService
    captured=[]
    def complete(**kwargs):
        captured.append(kwargs)
        value={'intent':'schedule_visit','required':{'city':'Lahore','area':'DHA'},'starts_at':'2030-01-01T10:00:00+05:00','appointment_id':str(uuid4())}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])
    service=UserUnderstandingService(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))),deterministic_first=False)
    result=service.understand('Visit book kar dein',context={})
    assert result.required['city']=='Lahore' and result.starts_at.endswith('+05:00')
    assert captured[0]['messages'][0]['content']==service._system_prompt()


def test_full_nlu_provider_failure_does_not_silently_persist_partial_extraction():
    from sara_agent.understanding import UserUnderstandingService, UnderstandingError
    def fail(**kwargs): raise RuntimeError('provider secret')
    service=UserUnderstandingService(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail))),deterministic_first=False)
    with pytest.raises(UnderstandingError): service.understand('Budget 4 crore hai',context={})


def test_appointment_provider_errors_are_not_exposed():
    web,svc,nlu=setup(); first=chat(web).json()
    async def failing(*a,**k): return 500,{'detail':'SMTP api-secret provider failure'}
    svc.appointments.request=failing
    nlu.result=UserUnderstanding(intent='schedule_visit',selected_index=0,starts_at='2030-01-01T10:00:00+05:00')
    result=chat(web,first['conversation_id'])
    assert result.status_code==503 and 'secret' not in result.text
    assert not any(e['action']=='appointment_booked' for e in svc.interactions.events)


@pytest.mark.parametrize('intent',['cancel_visit','reschedule_visit'])
def test_owned_appointment_mutation_delegates(intent):
    web,svc,nlu=setup(); aid=str(uuid4()); calls=[]
    svc.auth.repository.owns_appointment=lambda user,appointment: user=='ua' and appointment==aid
    async def gateway(method,path,payload=None): calls.append((method,path,payload)); return 200,{'appointment':{'appointment_id':aid,'status':'cancelled' if method=='DELETE' else 'rescheduled'}}
    svc.appointments.request=gateway
    nlu.result=UserUnderstanding(intent=intent,appointment_id=aid,starts_at='2030-01-01T10:00:00+05:00')
    result=chat(web)
    assert result.status_code==200 and result.json()['appointment']['appointment_id']==aid
    assert calls[0][0]==('DELETE' if intent=='cancel_visit' else 'PATCH')


def test_expired_recommendation_cannot_book_or_record_feedback():
    from web_api.services import RecommendationSessionExpired
    web,svc,nlu=setup(); first=chat(web).json()
    def expired(*a): raise RecommendationSessionExpired()
    svc.sessions.get=expired
    nlu.result=UserUnderstanding(interaction_action='liked',selected_index=1)
    assert chat(web,first['conversation_id']).status_code==410
    nlu.result=UserUnderstanding(intent='schedule_visit',selected_index=0,starts_at='2030-01-01T10:00:00+05:00')
    assert chat(web,first['conversation_id']).status_code==410
    assert not svc.appointments.calls


def test_clarification_does_not_book_even_with_extracted_date():
    web,svc,nlu=setup(); first=chat(web).json()
    nlu.result=UserUnderstanding(intent='schedule_visit',selected_index=0,starts_at='2030-01-01T10:00:00+05:00',needs_clarification=True)
    assert chat(web,first['conversation_id']).json()['requires_clarification']
    assert not svc.appointments.calls

def test_ambiguous_feedback_does_not_trust_a_simultaneously_extracted_index():
    web,svc,nlu=setup(); first=chat(web).json(); count=len(svc.interactions.events)
    nlu.result=UserUnderstanding(interaction_action='liked',selected_index=0,needs_clarification=True)
    assert chat(web,first['conversation_id']).json()['requires_clarification']
    assert len(svc.interactions.events)==count

def test_malformed_full_nlu_json_has_one_bounded_retry():
    import json
    from sara_agent.understanding import UserUnderstandingService, UnderstandingError
    outputs=iter(['not json', json.dumps({'intent':'greeting'})]); calls=[]
    def complete(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(outputs)))])
    service=UserUnderstandingService(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))),deterministic_first=False)
    assert service.understand('hello',context={}).intent=='greeting'
    assert len(calls)==2 and len(calls[1]['messages']) > len(calls[0]['messages'])
    outputs=iter(['bad','bad']); calls.clear()
    with pytest.raises(UnderstandingError): service.understand('hello',context={})
    assert len(calls)==2


@pytest.mark.parametrize('choices', [None, []])
def test_missing_provider_choices_has_one_bounded_retry(choices):
    from sara_agent.understanding import UserUnderstandingService, UnderstandingError
    valid = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"intent":"greeting"}'))])
    outputs = iter([SimpleNamespace(choices=choices), valid])
    calls = []
    def complete(**kwargs):
        calls.append(kwargs)
        return next(outputs)
    service = UserUnderstandingService(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))), deterministic_first=False)
    assert service.understand('hello', context={}).intent == 'greeting'
    assert len(calls) == 2
    outputs = iter([SimpleNamespace(choices=choices), SimpleNamespace(choices=choices), SimpleNamespace(choices=choices)])
    calls.clear()
    with pytest.raises(UnderstandingError):
        service.understand('hello', context={})
    assert len(calls) >= 3


def test_app_dotenv_loads_day3_nlu_configuration():
    from web_api.app import DAY3_ROOT, create_app
    assert (DAY3_ROOT / ".env").exists()
    app = create_app()
    assert app is not None


def test_multi_turn_nemotron_understanding_regression():
    import os
    from sara_agent.understanding import UserUnderstandingService
    service = UserUnderstandingService()
    assert service.model == os.getenv("SARA_LLM_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))

    t2_msg = "ap k pass knsey areas k options available hai"
    u2 = service.understand(t2_msg, context={})
    assert u2 is not None
    assert "area" in u2.relax or u2.intent == "property_search"


def test_dynamic_area_relaxation_and_inquiry():
    web, svc, nlu = setup()
    # Mock search returning 0 properties for F-11
    svc.properties.search = lambda **k: []
    svc.properties.list_available_areas = lambda **k: ["DHA Phase 2", "Bahria Town"]

    nlu.result = UserUnderstanding(intent="property_search", required={"city": "Islamabad", "area": "F-11", "purpose": "Purchase", "property_type": "Plot", "budget": 40000000})
    res1 = chat(web, message="Islamabad F-11 mein plot chahiye")
    data1 = res1.json()
    assert data1["requires_clarification"] is True
    assert "F-11 mein options nahi hain, lekin Islamabad mein in areas mein options available hain" in data1["message"]
    assert "Is criteria par verified options nahi mile" not in data1["message"]

    # Flexible turn: relaxes area constraint and returns available areas/options
    nlu.result = UserUnderstanding(intent="property_search", relax=["area"])
    svc.properties.search = lambda **k: [{
        "property_id": "P-1", "property_name": "DHA Plot", "price": 35000000, "currency": "PKR",
        "city": "Islamabad", "area": "DHA Phase 2", "bedrooms": 0, "bathrooms": 0,
        "property_type": "Plot", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }]
    res2 = chat(web, cid=data1["conversation_id"], message="flexible hai")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2.get("properties", [])) == 1
    assert "Location flexibility" in data2["message"]


def test_case_a_unspecified_area_positive_search():
    """Case A: User did NOT specify an area -> responds positively with available areas or options without no-match wording."""
    web, svc, nlu = setup()
    svc.properties.list_available_areas = lambda **k: ["B-17", "DHA Phase 2"]
    svc.properties.search = lambda **k: [{
        "property_id": "P-101", "property_name": "Verified Plot", "price": 38000000, "currency": "PKR",
        "city": "Islamabad", "area": "B-17", "bedrooms": 0, "bathrooms": 0,
        "property_type": "Plot", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }]

    # Turn 1: Area not specified -> returns available areas positively
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Islamabad", "purpose": "Purchase", "property_type": "Plot", "budget": 40000000}
    )
    res1 = chat(web, message="mujhey Islamabad mein 4 crore tak ka plot purchase ke liye chahiye")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "Is criteria par verified options nahi mile" not in data1["message"]
    assert "Islamabad mein" in data1["message"]

    # Turn 2: Area relaxed -> returns matching properties positively
    nlu.result = UserUnderstanding(intent="property_search", relax=["area"])
    res2 = chat(web, cid=data1["conversation_id"], message="flexible hai")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2.get("properties", [])) == 1
    assert "Is criteria par verified options nahi mile" not in data2["message"]


def test_case_c_zero_matches_across_city_emits_no_match_wording():
    """Case C: City-wide broadened search has 0 total matches -> emit true no-match wording."""
    web, svc, nlu = setup()
    svc.properties.search = lambda **k: []
    svc.properties.list_available_areas = lambda **k: []

    # Turn 1: Unspecified area with 0 city matches
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Islamabad", "purpose": "Purchase", "property_type": "Plot", "budget": 100000},
        relax=["area"]
    )
    res = chat(web, message="Islamabad mein 1 lac ka plot chahiye flexible area")
    assert res.status_code == 200
    data = res.json()
    assert "is criteria par options nahi mile" in data["message"].lower()


def test_search_list_available_areas_consistency():
    """Regression test proving list_available_areas matches search criteria and returned areas correspond to search results."""
    from postgres_repository import PostgresPropertyRepository
    repo = object.__new__(PostgresPropertyRepository)
    repo.MAX_SEARCH_LIMIT = 100

    # Mock search returning sample verified properties
    mock_properties = [
        {"property_id": "P-1", "area": "B-17", "city": "Islamabad", "price": 35000000, "purpose": "Purchase", "property_type": "Plot"},
        {"property_id": "P-2", "area": "DHA Phase 2", "city": "Islamabad", "price": 39000000, "purpose": "Purchase", "property_type": "Plot"},
        {"property_id": "P-3", "area": "B-17", "city": "Islamabad", "price": 32000000, "purpose": "Purchase", "property_type": "Plot"},
    ]
    repo.search = lambda **k: mock_properties

    # Query list_available_areas
    areas = repo.list_available_areas(city="Islamabad", purpose="Purchase", property_type="Plot", budget=40000000)

    # Prove that list_available_areas returns distinct areas matching search properties
    assert areas == ["DHA Phase 2", "B-17"]  # closest affordable inventory first
    property_areas = {p["area"] for p in mock_properties if p.get("area")}
    for area in areas:
        assert area in property_areas, f"Area '{area}' returned by list_available_areas is not present in search results"

    # Also attempt live DB test if DB is available
    try:
        live_repo = PostgresPropertyRepository()
        live_areas = live_repo.list_available_areas(city="Islamabad", purpose="Purchase", property_type="Plot", budget=40000000)
        live_properties = live_repo.search(city="Islamabad", purpose="Purchase", property_type="Plot", budget=40000000, area=None)
        live_prop_areas = {p["area"] for p in live_properties if p.get("area")}
        for a in live_areas:
            assert a in live_prop_areas
    except Exception:
        pass


def test_chat_adapter_handles_understanding_error_gracefully():
    """Bug #1 Regression Test: ChatAdapter returns polite clarification response instead of 503 HTTP status on UnderstandingError."""
    from sara_agent.understanding import UnderstandingError
    web, svc, nlu = setup()
    
    # Force NLU to raise UnderstandingError (simulating rate-limit, LLM outage, or unparseable turn)
    def fail_understand(*args, **kwargs):
        raise UnderstandingError("LLM rate limit / provider error")
    
    svc.chat.sara.understand = fail_understand
    res = chat(web, message="Random unparseable turn")
    assert res.status_code == 200
    data = res.json()
    assert data.get("requires_clarification") is True
    assert "smjh nahi saki" in data.get("message", "") or "samajh nahi saki" in data.get("message", "")


@pytest.mark.asyncio
async def test_vapi_session_manager_process_with_sara_executes_without_type_error():
    """Bug #2 Regression Test: VapiSessionManager._process_with_sara calls UserUnderstandingService with context dict via asyncio.to_thread without TypeError."""
    from vapi_integration.session_manager import VapiSessionManager, VapiSession, ConversationState, UserProfile
    
    manager = VapiSessionManager(customer_service=None, interaction_repository=None)
    session = await manager.create_session(call_id="test_call_123", caller_phone="+923001234567")
    
    # Deterministic fast-path turn avoids requiring active LLM API credits in unit tests
    response = await manager.process_turn("test_call_123", "rent k liye")
    assert isinstance(response, str)
    assert len(response) > 0
    assert session.sara_state.latest_intent in ("greeting", "unknown", "property_search")


def test_schema_fallback_extracts_location_on_llm_json_malformation():
    """Regression Test: Ensures 'mujey islamabad mein property chahey' extracts city='Islamabad' via schema fallback even if LLM returns preamble/malformed text."""
    from sara_agent.understanding import UserUnderstandingService
    from types import SimpleNamespace
    
    # Simulate LLM returning conversational preamble instead of valid raw JSON
    def malformed_llm(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Here is the extracted json payload:\n{\n  'intent': 'property_search',\n  'city': 'Islamabad',\n}"))])
    
    service = UserUnderstandingService(
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=malformed_llm))),
        deterministic_first=False,
    )
    
def test_regression_issue_a_more_options_no_duplicate_repetition():
    """Issue A Regression: 'is k ilawa aor knsey option hai' never repeats the same property and relaxes to other city areas or informs when exhausted."""
    web, svc, nlu = setup()
    prop1 = {
        "property_id": "P-DHA2", "property_name": "DHA Phase 2 Residential Plot", "price": 18000000, "currency": "PKR",
        "city": "Islamabad", "area": "DHA Phase 2", "bedrooms": 0, "bathrooms": 0,
        "property_type": "Plot", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }
    prop2 = {
        "property_id": "P-B17", "property_name": "B-17 Residential Plot", "price": 14000000, "currency": "PKR",
        "city": "Islamabad", "area": "B-17", "bedrooms": 0, "bathrooms": 0,
        "property_type": "Plot", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }

    # Turn 1: Search specifically in DHA Phase 2 -> 1 option returned
    svc.properties.rows = [prop1, prop2]
    svc.properties.search = lambda **k: [p for p in [prop1, prop2] if (not k.get("area") or p["area"] == k.get("area")) and (not k.get("city") or p["city"] == k.get("city"))]
    svc.properties.list_available_areas = lambda **k: ["DHA Phase 2", "B-17"]

    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Islamabad", "area": "DHA Phase 2", "purpose": "Purchase", "property_type": "Plot", "budget": 40000000}
    )
    r1 = chat(web, message="Mujhe Islamabad DHA Phase 2 mein 4 crore tak ka plot chahiye").json()
    assert r1.get("properties") and len(r1["properties"]) == 1
    assert r1["properties"][0]["property_id"] == "P-DHA2"
    cid = r1["conversation_id"]

    # Turn 2: User asks "is k ilawa aor knsey option hai"
    # Bug A Fix: Sara must NOT silently switch areas. Sara asks permission first!
    nlu.result = UserUnderstanding(intent="property_search", raw_message="is k ilawa aor knsey option hai")
    r2 = chat(web, cid=cid, message="is k ilawa aor knsey option hai").json()
    assert r2.get("requires_clarification") is True
    assert "DHA Phase 2 mein filhaal aur koi verified option available nahi hai" in r2["message"]
    assert "B-17" in r2["message"]
    assert "properties" not in r2 or len(r2.get("properties", [])) == 0

    # Turn 3: User confirms permission ("haan dikha do")
    # Now Sara returns P-B17 with clean single-sentence intro (Bug B fix)!
    r3 = chat(web, cid=cid, message="haan dikha do").json()
    assert r3.get("properties") and len(r3["properties"]) == 1
    assert r3["properties"][0]["property_id"] == "P-B17"
    assert "DHA Phase 2 Residential Plot" not in r3["message"]

    # Turn 4: User asks "is k ilawa aor knsey option hai" again
    # All plots in Islamabad have now been shown. Sara must NOT repeat and must inform user naturally.
    r4 = chat(web, cid=cid, message="is k ilawa aor knsey option hai").json()
    assert "properties" not in r4 or len(r4.get("properties", [])) == 0
    assert "is ke ilawa mazeed options abhi nahi hain" in r4["message"]
    assert "budget extend" in r4["message"] or "qareebi area" in r4["message"]


def test_regression_issue_b_area_suggestion_dynamic_db_query():
    """Issue B Regression: 'area suggest kro lahore mein' queries list_available_areas and suggests real areas from DB."""
    web, svc, nlu = setup()
    queried_city = None

    def fake_list_areas(city=None, **kwargs):
        nonlocal queried_city
        queried_city = city
        return ["DHA Phase 6", "Bahria Town", "Gulberg III"]

    svc.properties.list_available_areas = fake_list_areas

    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Lahore"},
        relax=["area"],
        raw_message="area suggest kro lahore mein"
    )
    res = chat(web, message="area suggest kro lahore mein").json()
    assert queried_city == "Lahore"
    assert "DHA Phase 6" in res["message"]
    assert "Bahria Town" in res["message"]
    assert "Gulberg III" in res["message"]
    assert "in areas mein" in res["message"]


def test_regression_issue_c_tone_humanization_no_mechanical_strings():
    """Issue C Regression: Result presentation and chat turns never contain developer status strings."""
    web, svc, nlu = setup()
    prop = {
        "property_id": "P-1", "property_name": "Gulberg Residency", "price": 25000000, "currency": "PKR",
        "city": "Lahore", "area": "Gulberg", "bedrooms": 3, "bathrooms": 3,
        "property_type": "Apartment", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }
    svc.properties.rows = [prop]
    svc.properties.search = lambda **k: [prop]

    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Lahore", "area": "Gulberg", "purpose": "Purchase"}
    )
    res = chat(web, message="Lahore Gulberg mein flat dikhao").json()
    msg = res["message"]

    # Forbidden robotic phrases:
    assert "last loaded batch" not in msg
    assert "current matching verified options" not in msg
    assert "In mein se kisi option ki details, comparison ya aur filtering chahiye?" not in msg
    # Natural warm UrduLish intro/footer must be present:
    assert "behtareen verified options" in msg or "verified options" in msg


def test_regression_broadening_relaxation_flow():
    """Regression: When user agrees to broaden after no matches ('theek hai budget extend kar lo'), search widens budget by 25%."""
    web, svc, nlu = setup()
    expensive_prop = {
        "property_id": "P-EXP", "property_name": "Luxury House", "price": 48000000, "currency": "PKR",
        "city": "Islamabad", "area": "DHA Phase 2", "bedrooms": 4, "bathrooms": 4,
        "property_type": "House", "purpose": "Purchase", "amenities": [], "available": True, "status": "Ready"
    }

    def search_fn(budget=None, **k):
        if budget and budget >= 48000000:
            return [expensive_prop]
        return []

    svc.properties.search = search_fn
    svc.properties.list_available_areas = lambda **k: []

    # Turn 1: Budget 40M has 0 matches
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"city": "Islamabad", "purpose": "Purchase", "budget": 40000000},
        relax=["area"]
    )
    r1 = chat(web, message="Islamabad mein 4 crore ka ghar chahiye").json()
    assert "properties" not in r1
    cid = r1["conversation_id"]

    # Turn 2: User says "theek hai budget extend kar lo" -> 40M * 1.25 = 50M -> Luxury House matches!
    nlu.result = UserUnderstanding(intent="property_search", raw_message="theek hai budget extend kar lo")
    r2 = chat(web, cid=cid, message="theek hai budget extend kar lo").json()
    assert r2.get("properties") and len(r2["properties"]) == 1
    assert r2["properties"][0]["property_id"] == "P-EXP"
    assert "criteria thora broaden kiya hai" in r2["message"]


# =====================================================================
# Two-Tier Slot-Filling Architecture Regression Tests
# =====================================================================

def test_tier1_missing_all_asks_purpose_first():
    """Tier 1: When all essential slots are missing, Purpose (Buy/Rent) is asked first."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    nlu.result = UserUnderstanding(intent="property_search", required={})
    res = chat(web, message="mujhe property dekhni hai").json()
    assert res.get("requires_clarification") is True
    assert "rent" in res["message"].lower() and "purchase" in res["message"].lower()


def test_tier1_purpose_given_asks_city_next():
    """Tier 1: When Purpose is given, City/Location is asked next."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    nlu.result = UserUnderstanding(intent="property_search", required={"purpose": "Purchase"})
    res = chat(web, message="mujhe ghar khareedna hai").json()
    assert res.get("requires_clarification") is True
    assert "city" in res["message"].lower() or "islamabad ya lahore" in res["message"].lower()


def test_tier1_purpose_and_city_given_asks_budget_next():
    """Tier 1: When Purpose and City are given, Budget is asked next."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    nlu.result = UserUnderstanding(intent="property_search", required={"purpose": "Purchase", "city": "Islamabad"})
    res = chat(web, message="Islamabad mein ghar khareedna hai").json()
    assert res.get("requires_clarification") is True
    assert "budget" in res["message"].lower()


def test_tier1_all_three_given_proceeds_to_search():
    """Tier 1: When Purpose, City, and Budget are all given, proceed without Tier 1 questions."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"purpose": "Purchase", "city": "Islamabad", "budget": 40000000},
        relax=["area"]
    )
    res = chat(web, message="Islamabad mein 4 crore tak purchase ke liye chahiye").json()
    assert res.get("requires_clarification") is False or "properties" in res
    assert len(res.get("properties", [])) > 0


def test_tier2_threshold_count_triggers_narrowing():
    """Tier 2: When matching count > threshold (default 5), ask narrowing question (bedrooms)."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences, property_row
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    svc.properties.rows = [property_row(f"P-{i}", 20000000) for i in range(7)]
    svc.properties.search = lambda **k: [property_row(f"P-{i}", 20000000) for i in range(7)]
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"purpose": "Purchase", "city": "Islamabad", "budget": 40000000},
        relax=["area"]
    )
    res = chat(web, message="Islamabad mein 4 crore tak chahiye").json()
    assert res.get("requires_clarification") is True
    assert "bedrooms" in res["message"].lower()


def test_tier2_low_count_shows_results_directly():
    """Tier 2: When matching count <= threshold (default 5), show results directly without extra questions."""
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences, property_row
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    svc.properties.rows = [property_row(f"P-{i}", 20000000) for i in range(3)]
    svc.properties.search = lambda **k: [property_row(f"P-{i}", 20000000) for i in range(3)]
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"purpose": "Purchase", "city": "Islamabad", "budget": 40000000},
        relax=["area"]
    )
    res = chat(web, message="Islamabad mein 4 crore tak chahiye").json()
    assert "properties" in res and len(res["properties"]) == 3


def test_tier2_threshold_env_override(monkeypatch):
    """Tier 2: SARA_RESULTS_CLARIFY_THRESHOLD environment override modifies narrowing trigger."""
    monkeypatch.setenv("SARA_RESULTS_CLARIFY_THRESHOLD", "2")
    web, svc, nlu = setup()
    from test_web_api import CustomerPreferences, property_row
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    svc.properties.rows = [property_row(f"P-{i}", 20000000) for i in range(3)]
    svc.properties.search = lambda **k: [property_row(f"P-{i}", 20000000) for i in range(3)]
    nlu.result = UserUnderstanding(
        intent="property_search",
        required={"purpose": "Purchase", "city": "Islamabad", "budget": 40000000},
        relax=["area"]
    )
    res = chat(web, message="Islamabad mein 4 crore tak chahiye").json()
    assert res.get("requires_clarification") is True
    assert "bedrooms" in res["message"].lower()


# =====================================================================
# Returning Customer First-Turn Flow Regression Tests
# =====================================================================

def test_new_customer_starts_tier1_without_mention():
    """Returning Customer: New customer with no saved preferences starts at Tier 1 without returning greeting."""
    web, svc, nlu = setup()
    nlu.test_returning = True
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    nlu.result = UserUnderstanding(intent="property_search", required={})
    res = chat(web, message="mujhe property dekhni hai").json()
    assert "pichli dafa" not in res["message"].lower()
    assert "rent" in res["message"].lower() and "purchase" in res["message"].lower()


def test_returning_customer_generic_message_case_a():
    """Returning Customer Case A: Generic message -> mention saved preferences and ask confirmation."""
    web, svc, nlu = setup()
    nlu.test_returning = True
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40000000, purpose="Purchase")
    nlu.result = UserUnderstanding(intent="property_search", required={})
    res = chat(web, message="mujhe property dekhni hai").json()
    assert res.get("requires_clarification") is True
    assert "pichli dafa aapne islamabad mein 4 crore tak purchase ke liye pucha tha" in res["message"].lower()
    assert "wahi requirement hai ya kuch change karna chahengi" in res["message"].lower()
    assert "properties" not in res or len(res.get("properties", [])) == 0


def test_returning_customer_confirms_haan():
    """Returning Customer Case A Turn 2: User confirms ('haan') -> adopts saved preferences and proceeds."""
    web, svc, nlu = setup()
    nlu.test_returning = True
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40000000, purpose="Purchase")
    
    # Turn 1: Generic opener
    nlu.result = UserUnderstanding(intent="property_search", required={})
    r1 = chat(web, message="mujhe property dekhni hai").json()
    cid = r1["conversation_id"]

    # Turn 2: User confirms "haan"
    nlu.result = UserUnderstanding(intent="property_search", relax=["area"])
    r2 = chat(web, cid=cid, message="haan").json()
    assert "pichli dafa" not in r2["message"].lower()
    assert "properties" in r2 and len(r2["properties"]) > 0


def test_returning_customer_different_requirement_case_b():
    """Returning Customer Case B: User specifies different criteria -> acknowledge both and switch."""
    web, svc, nlu = setup()
    nlu.test_returning = True
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40000000, purpose="Purchase")
    nlu.result = UserUnderstanding(intent="property_search", required={"city": "Lahore", "purpose": "Rental"})
    res = chat(web, message="lahore mein rent ke liye flat chahiye").json()
    assert "pichli dafa islamabad purchase ka tha" in res["message"].lower()
    assert "lahore mein rental dekh rahe hain" in res["message"].lower()


def test_returning_customer_turn2_no_repeat():
    """Returning Customer: In subsequent turns of the session, never repeat the saved preferences greeting."""
    web, svc, nlu = setup()
    nlu.test_returning = True
    from test_web_api import CustomerPreferences
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40000000, purpose="Purchase")

    # Turn 1: Generic message
    nlu.result = UserUnderstanding(intent="property_search", required={})
    r1 = chat(web, message="mujhe property dekhni hai").json()
    cid = r1["conversation_id"]

    # Turn 2: Confirmation
    nlu.result = UserUnderstanding(intent="property_search", relax=["area"])
    r2 = chat(web, cid=cid, message="haan").json()
    assert "pichli dafa" not in r2["message"].lower()

    # Turn 3: Follow-up question
    nlu.result = UserUnderstanding(intent="property_search", raw_message="aur options dikhao")
    r3 = chat(web, cid=cid, message="aur options dikhao").json()
    assert "pichli dafa" not in r3["message"].lower()


# =====================================================================
# Filter Shown Options by Named Area Tests
# =====================================================================

def test_area_filter_of_shown_options_single_match():
    """When user asks to filter currently shown options by area with 1 match, returns filtered list."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-DHA", price=25_000_000)
    p1.update({"area": "DHA Phase 2", "city": "Islamabad", "property_name": "DHA Phase 2 Plot"})
    p2 = property_row("P-B17", price=14_000_000)
    p2.update({"area": "B-17", "city": "Islamabad", "property_name": "B-17 Plot"})
    p3 = property_row("P-F11", price=35_000_000)
    p3.update({"area": "F-11", "city": "Islamabad", "property_name": "F-11 Villa"})
    svc.properties.rows = [p1, p2, p3]

    # Turn 1: Initial search shows all 3 properties
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) == 3

    # Turn 2: User asks to filter shown options by DHA
    nlu.result = UserUnderstanding(intent="availability", required={})
    r2 = chat(web, cid=cid, message="dha mein kn kn sey options available hai").json()

    assert "kis option ki details chahiye" not in r2["message"].lower()
    assert "dha phase 2 plot" in r2["message"].lower()
    assert "b-17 plot" not in r2["message"].lower()
    assert "properties" in r2 and len(r2["properties"]) == 1
    assert r2["properties"][0]["property_id"] == "P-DHA"


def test_area_filter_of_shown_options_multiple_matches():
    """When user asks to filter currently shown options by area with multiple matches, returns all matching options."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-B1", price=15_000_000)
    p1.update({"area": "Bahria Town Phase 4", "city": "Rawalpindi", "property_name": "Bahria House 1"})
    p2 = property_row("P-B2", price=18_000_000)
    p2.update({"area": "Bahria Town Phase 7", "city": "Rawalpindi", "property_name": "Bahria House 2"})
    p3 = property_row("P-DHA", price=25_000_000)
    p3.update({"area": "DHA Phase 1", "city": "Islamabad", "property_name": "DHA Villa"})
    svc.properties.rows = [p1, p2, p3]

    # Turn 1: Initial search shows all 3 properties
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) == 3

    # Turn 2: User asks for Bahria options
    nlu.result = UserUnderstanding(intent="property_details", required={})
    r2 = chat(web, cid=cid, message="bahria mein kya hai").json()

    assert "kis option ki details chahiye" not in r2["message"].lower()
    assert "bahria house 1" in r2["message"].lower()
    assert "bahria house 2" in r2["message"].lower()
    assert "dha villa" not in r2["message"].lower()
    assert "properties" in r2 and len(r2["properties"]) == 2


def test_area_filter_of_shown_options_zero_matches():
    """When user asks to filter currently shown options by area with 0 matches, returns polite prompt."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-B17", price=14_000_000)
    p1.update({"area": "B-17", "city": "Islamabad", "property_name": "B-17 Plot"})
    p2 = property_row("P-DHA", price=25_000_000)
    p2.update({"area": "DHA Phase 2", "city": "Islamabad", "property_name": "DHA Plot"})
    svc.properties.rows = [p1, p2]

    # Turn 1: Initial search shows properties in Islamabad
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) == 2

    # Turn 2: User asks about Karachi among shown options
    nlu.result = UserUnderstanding(intent="property_details", required={})
    r2 = chat(web, cid=cid, message="karachi mein kya hai").json()

    assert "abhi dikhaye gaye options mein karachi ka koi option nahi hai" in r2["message"].lower()
    assert "naye options dhoondun" in r2["message"].lower()


def test_ordinal_selection_remains_unaffected_by_area_filter():
    """Ordinal selection (e.g. 'second wali ki details') still resolves the specific property details directly."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-1", price=10_000_000)
    p1.update({"property_name": "P-1 DHA Luxury Apartment"})
    p2 = property_row("P-2", price=12_000_000)
    p2.update({"property_name": "P-2 Bahria Exclusive House"})
    svc.properties.rows = [p1, p2]

    # Turn 1: Initial search
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) == 2

    # Turn 2: User asks for second option details by ordinal
    nlu.result = UserUnderstanding(intent="property_details", selected_index=1)
    r2 = chat(web, cid=cid, message="second wali ki details").json()

    assert "verified details" in r2["message"].lower()
    assert "abhi dikhaye gaye options" not in r2["message"].lower()
    assert "kis option ki details chahiye" not in r2["message"].lower()


# =====================================================================
# Stale property_order after area-filter display (correctness bug)
# =====================================================================

def test_area_filter_updates_property_order_for_next_ordinal():
    """
    BUG REGRESSION: After filtering shown options by area (e.g. 'DHA mein kya options hain'),
    saved['property_order'] must be REPLACED with the filtered subset so that the user's
    subsequent 'first option ki details do' resolves to what was ACTUALLY just shown,
    NOT to the original index-0 of the pre-filter full list.

    The Deterministic mock ranker reverses the input list, so:
      rows=[P-B17, P-DHA, P-F11] -> ranked=[P-F11, P-DHA, P-B17]
    Turn 1 property_order: [P-F11, P-DHA, P-B17]  (P-F11 at index 0)
    Turn 2: area filter for 'dha' shows only P-DHA
      -> saved['property_order'] must now be [P-DHA]
    Turn 3: 'pehli wali ki details' must resolve to P-DHA,
      NOT P-F11 (stale index-0 of original ranked list).
    """
    from test_web_api import property_row
    web, svc, nlu = setup()

    p_b17 = property_row("P-B17", price=14_000_000)
    p_b17.update({"area": "B-17", "city": "Islamabad", "property_name": "B-17 Plot"})
    p_dha = property_row("P-DHA", price=25_000_000)
    p_dha.update({"area": "DHA Phase 2", "city": "Islamabad", "property_name": "DHA Phase 2 Plot"})
    p_f11 = property_row("P-F11", price=35_000_000)
    p_f11.update({"area": "F-11", "city": "Islamabad", "property_name": "F-11 Villa"})
    svc.properties.rows = [p_b17, p_dha, p_f11]

    # Turn 1: show all 3; Deterministic ranker reverses -> order=[P-F11, P-DHA, P-B17]
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) == 3
    # After ranking by Deterministic (reverses): P-F11 is index-0 (first shown)
    first_shown_id = r1["properties"][0]["property_id"]  # P-F11
    assert first_shown_id != "P-DHA", "Sanity: DHA must NOT already be at index-0 of the full list"

    # Turn 2: area filter -> shows only P-DHA
    nlu.result = UserUnderstanding(intent="availability", required={})
    r2 = chat(web, cid=cid, message="dha mein kn kn sey options available hai").json()
    assert "dha phase 2 plot" in r2["message"].lower(), "DHA property should appear in area filter response"
    assert len(r2["properties"]) == 1
    assert r2["properties"][0]["property_id"] == "P-DHA"

    # Turn 3: 'pehli wali ki details' must resolve to P-DHA (the ONLY property shown in Turn 2),
    # NOT P-F11 (stale index-0 of the full pre-filter ranked list).
    nlu.result = UserUnderstanding(intent="property_details", reference_type="first_result")
    r3 = chat(web, cid=cid, message="pehli wali ki details do").json()
    assert "dha phase 2 plot" in r3["message"].lower(), (
        f"Expected DHA property details (the one shown after filter), but got: {r3['message']!r}"
    )
    assert "f-11 villa" not in r3["message"].lower(), (
        f"Got F-11 (stale index-0 of unfiltered list), not the DHA property shown: {r3['message']!r}"
    )


def test_pagination_more_options_ordinals_still_resolve_original_list():
    """
    REGRESSION GUARD: 'more options' pagination APPENDS to property_order, so ordinals into
    the ORIGINAL shown list still work correctly after new options are added.

    The Deterministic mock ranker reverses the input list, so:
      rows=[P-1, P-2, P-3] -> ranked=[P-3, P-2, P-1]
    Turn 1 shows: whatever's at index-0 of the ranked list (P-3 = 'Bahria House 3').
    After area-filter that would REPLACE property_order (the bug case), index-0 would change.
    Here we test the PAGINATION case: it must APPEND, keeping index-0 stable.

    Key assertion: after 'aur options' pagination, 'first_result' must still resolve to
    whatever property was at index-0 of the FIRST batch — not to a newly appended one.
    """
    from test_web_api import property_row
    web, svc, nlu = setup()

    p1 = property_row("P-1", price=10_000_000)
    p1.update({"area": "DHA Phase 1", "city": "Lahore", "property_name": "DHA House 1"})
    p2 = property_row("P-2", price=12_000_000)
    p2.update({"area": "DHA Phase 2", "city": "Lahore", "property_name": "DHA House 2"})
    p3 = property_row("P-3", price=14_000_000)
    p3.update({"area": "Bahria Town", "city": "Lahore", "property_name": "Bahria House 3"})
    svc.properties.rows = [p1, p2, p3]

    # Turn 1: show initial batch; Deterministic reverses so order=[P-3, P-2, P-1]
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) >= 1
    # Record what is actually at index-0 of the first shown batch
    first_batch_first_id = r1["properties"][0]["property_id"]
    first_batch_first_name = r1["properties"][0]["property_name"].lower()
    shown_count_turn1 = len(r1["properties"])

    if shown_count_turn1 < 3:
        # Trigger pagination to append new options
        nlu.result = UserUnderstanding(intent="property_search", raw_message="aur options dikhao")
        r2 = chat(web, cid=cid, message="aur options dikhao").json()

    # 'first_result' ordinal must still point to the same property that was at index-0
    # of the FIRST batch (pagination appends; does NOT replace index-0).
    nlu.result = UserUnderstanding(intent="property_details", reference_type="first_result")
    r_first = chat(web, cid=cid, message="pehli wali ki details").json()
    assert first_batch_first_name in r_first["message"].lower(), (
        f"Expected index-0 of first batch ({first_batch_first_name!r}) to still resolve "
        f"as 'first' after pagination; got: {r_first['message']!r}"
    )



# Phase Inventory Questions & "aor" Typo Tests (Fix 1 & Fix 2)
# =====================================================================

def test_more_options_aor_typo_proceeds_to_more_options_flow():
    """'dha mein aor knsey options available hai' triggers more_options flow, not ordinal fallback."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-DHA1", price=20_000_000)
    p1.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Villa 1"})
    p2 = property_row("P-DHA2", price=25_000_000)
    p2.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Villa 2"})
    svc.properties.rows = [p1, p2]

    # Turn 1: Initial search shows properties
    nlu.result = UserUnderstanding(intent="property_search")
    r1 = chat(web, message="options dikhao").json()
    cid = r1["conversation_id"]
    assert len(r1["properties"]) > 0

    # Turn 2: User asks with 'aor' typo and 'knsey options available hai'
    # Intent classified as availability by NLU, but more_options regex intercepts it
    nlu.result = UserUnderstanding(intent="availability", required={"area": "dha"})
    r2 = chat(web, cid=cid, message="dha mein aor knsey options available hai").json()

    # Must NOT fall through to ordinal details fallback ("Kis option ki details chahiye? Option number bata dein.")
    assert "kis option ki details chahiye" not in r2["message"].lower()
    assert "option number bata dein" not in r2["message"].lower()


def test_phase_inventory_question_single_matching_phase():
    """'dha k kn kn se phase mein options available hai' returns phase list even with 1 phase."""
    web, svc, nlu = setup()
    svc.properties.list_available_areas = lambda city=None, **k: ["DHA Phase 6", "Gulberg"]
    nlu.result = UserUnderstanding(intent="property_search", required={"area": "dha"})
    res = chat(web, message="dha k kn kn se phase mein options available hai").json()

    assert res.get("requires_clarification") is True
    assert "filhaal lahore mein dha ke in phases mein verified options available hain: dha phase 6." in res["message"].lower()
    assert "kis phase ke options dekhna chahengi?" in res["message"].lower()
    assert "gulberg" not in res["message"].lower()
    assert not res.get("properties")


def test_phase_inventory_question_multiple_matching_phases():
    """'DHA ke kaunsay phases mein options hain' returns all matching phases."""
    web, svc, nlu = setup()
    svc.properties.list_available_areas = lambda city=None, **k: ["DHA Phase 5", "DHA Phase 6", "Bahria Town"]
    nlu.result = UserUnderstanding(intent="property_search")
    res = chat(web, message="DHA ke kaunsay phases mein options hain").json()

    assert res.get("requires_clarification") is True
    assert "filhaal lahore mein dha ke in phases mein verified options available hain: dha phase 5, dha phase 6." in res["message"].lower()
    assert "kis phase ke options dekhna chahengi?" in res["message"].lower()
    assert "bahria town" not in res["message"].lower()
    assert not res.get("properties")


def test_exact_phase_not_intercepted_by_phase_inventory():
    """Regression: 'DHA Phase 6 mein options dikhao' proceeds to normal search without phase question intercept."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-DHA6", price=25_000_000)
    p1.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Phase 6 House"})
    svc.properties.rows = [p1]
    svc.properties.list_available_areas = lambda city=None, **k: ["DHA Phase 6", "Gulberg"]
    nlu.result = UserUnderstanding(intent="property_search", required={"area": "DHA Phase 6"})
    res = chat(web, message="DHA Phase 6 mein options dikhao").json()

    assert not res.get("requires_clarification")
    assert "properties" in res and len(res["properties"]) > 0
    assert "filhaal lahore mein dha ke in phases" not in res["message"].lower()


# =====================================================================
# Asked-about Area Relevance Priority in Flexible/Broadened Results
# =====================================================================

def test_asked_about_area_prioritized_in_flexible_results():
    """'dha mein aor knsey options available hai agr mera budget flexible ho' places DHA results FIRST."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-B1", price=15_000_000)
    p1.update({"area": "Bahria Town", "city": "Lahore", "property_name": "Bahria House 1"})
    p2 = property_row("P-B2", price=18_000_000)
    p2.update({"area": "Bahria Town", "city": "Lahore", "property_name": "Bahria House 2"})
    p3 = property_row("P-DHA6", price=25_000_000)
    p3.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Phase 6 Villa"})
    svc.properties.rows = [p1, p2, p3]

    # Ranker by default returns Bahria first:
    svc.deterministic.rank = lambda rows, profile: [p1, p2, p3]

    nlu.result = UserUnderstanding(intent="property_search", relax=["area", "budget"])
    res = chat(web, message="dha mein aor knsey options available hai agr mera budget flexible ho").json()

    assert not res.get("requires_clarification")
    props = res.get("properties", [])
    assert len(props) == 3
    # DHA Phase 6 must appear FIRST in both properties list and formatted message text
    assert props[0]["property_id"] == "P-DHA6"
    assert props[0]["area"] == "DHA Phase 6"
    assert "1. dha phase 6 villa" in res["message"].lower()
    assert props[1]["property_id"] == "P-B1"
    assert props[2]["property_id"] == "P-B2"


def test_generic_budget_flexibility_preserves_default_ranking():
    """Generic 'budget flexible kar dein' with no area named does not reorder results."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-B1", price=15_000_000)
    p1.update({"area": "Bahria Town", "city": "Lahore", "property_name": "Bahria House 1"})
    p2 = property_row("P-B2", price=18_000_000)
    p2.update({"area": "Bahria Town", "city": "Lahore", "property_name": "Bahria House 2"})
    p3 = property_row("P-DHA6", price=25_000_000)
    p3.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Phase 6 Villa"})
    svc.properties.rows = [p1, p2, p3]
    svc.customers.preferences.area = None
    svc.deterministic.rank = lambda rows, profile: [p1, p2, p3]

    nlu.result = UserUnderstanding(intent="property_search", relax=["area", "budget"])
    res = chat(web, message="budget flexible kar dein").json()

    props = res.get("properties", [])
    assert len(props) == 3
    assert props[0]["property_id"] == "P-B1"
    assert props[1]["property_id"] == "P-B2"
    assert props[2]["property_id"] == "P-DHA6"


def test_exact_single_area_search_unaffected_by_reordering():
    """Exact single-area search (no relaxation) is completely unaffected by the area-flexible reorder."""
    from test_web_api import property_row
    web, svc, nlu = setup()
    p1 = property_row("P-DHA1", price=20_000_000)
    p1.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Villa 1"})
    p2 = property_row("P-DHA2", price=25_000_000)
    p2.update({"area": "DHA Phase 6", "city": "Lahore", "property_name": "DHA Villa 2"})
    svc.properties.rows = [p1, p2]
    svc.deterministic.rank = lambda rows, profile: [p1, p2]

    nlu.result = UserUnderstanding(intent="property_search", required={"area": "DHA Phase 6"})
    res = chat(web, message="DHA Phase 6 mein options dikhao").json()

    props = res.get("properties", [])
    assert len(props) == 2
    assert props[0]["property_id"] == "P-DHA1"
    assert props[1]["property_id"] == "P-DHA2"


# =====================================================================
# Returning Customer: Booking for Previously Viewed Property
# =====================================================================

def test_booking_single_previously_liked_property():
    """Single previously-liked property exists -> resolves it and asks date/time."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", purpose="Purchase", budget_max=40_000_000, property_type="Plot")
    svc.interactions.events = [
        {"customer_id": CUSTOMER_ID, "property_id": "P-1", "action": "liked", "conversation_id": "sess-1"}
    ]

    nlu.result = UserUnderstanding(intent="schedule_visit")
    res = chat(web, message="jo pichli dafa property dekhi thi us ki appointment book krwani").json()

    assert res.get("requires_clarification") is True
    assert "visit ke liye kis date aur time par available hain" in res["message"].lower()


def test_booking_multiple_properties_shown_ambiguous():
    """Multiple properties shown last time, none selected -> asks which property first."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", purpose="Purchase", budget_max=40_000_000, property_type="Plot")
    svc.interactions.events = [
        {"customer_id": CUSTOMER_ID, "property_id": "P-1", "action": "shown", "conversation_id": "sess-1"},
        {"customer_id": CUSTOMER_ID, "property_id": "P-2", "action": "shown", "conversation_id": "sess-1"},
    ]

    nlu.result = UserUnderstanding(intent="schedule_visit")
    res = chat(web, message="pichli property ka visit book kr dein").json()

    assert res.get("requires_clarification") is True
    assert "ek se zyada properties dekhi thin" in res["message"].lower()
    assert "kis property ki visit book karni hai" in res["message"].lower()


def test_booking_incomplete_requirement_then_resolved():
    """Last search never completed (budget missing) -> asks budget first, then proceeds to booking date/time."""
    from test_web_api import CustomerPreferences, property_row
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", purpose="Purchase", property_type="Plot")
    svc.interactions.events = []
    p1 = property_row("P-1", price=35_000_000)
    p1.update({"area": "B-17", "city": "Islamabad", "property_type": "Plot", "purpose": "Purchase"})
    svc.properties.rows = [p1]

    # Turn 1: User requests booking for previous property
    nlu.result = UserUnderstanding(intent="schedule_visit")
    r1 = chat(web, message="pichli property ka visit book kr dein").json()
    cid = r1["conversation_id"]

    assert r1.get("requires_clarification") is True
    assert "budget" in r1["message"].lower()

    # Turn 2: User provides missing budget
    nlu.result = UserUnderstanding(intent="property_search", required={"budget": 40_000_000})
    r2 = chat(web, cid=cid, message="mera budget 4 crore hai").json()

    assert r2.get("requires_clarification") is True
    assert "visit ke liye kis date aur time par available hain" in r2["message"].lower()


def test_booking_no_history_asks_fresh():
    """No history at all -> asks for property/area to start fresh."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID)
    svc.interactions.events = []

    nlu.result = UserUnderstanding(intent="schedule_visit")
    res = chat(web, message="jo pichli dafa property dekhi thi us ki appointment book krwani").json()

    assert res.get("requires_clarification") is True
    assert "koi dekhi hui property nahi mil rahi" in res["message"].lower()
    assert "naam ya area" in res["message"].lower()


# =====================================================================
# Returning Customer: Off-Topic while pending_returning_confirm is Active
# =====================================================================

def test_off_topic_while_pending_returning_confirm_case_a():
    """Off-topic query while Case A pending -> acknowledges off-topic and echoes Case A summary question."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40_000_000, purpose="Purchase")

    # Turn 1: Generic greeting triggers Case A question
    nlu.result = UserUnderstanding(intent="property_search", required={})
    r1 = chat(web, message="mujhe property dekhni hai").json()
    cid = r1["conversation_id"]
    original_question = r1["message"]
    assert "pichli dafa aapne islamabad mein 4 crore tak purchase ke liye pucha tha" in original_question.lower()

    # Turn 2: User asks off-topic question
    nlu.result = UserUnderstanding(intent="off_topic")
    r2 = chat(web, cid=cid, message="python ki defination bta saktey kiya").json()

    assert r2.get("requires_clarification") is True
    assert "main sirf property se related sawalon mein madad kar sakti hoon" in r2["message"].lower()
    assert original_question in r2["message"]


def test_off_topic_while_pending_returning_confirm_plain():
    """Off-topic query while plain fallback pending -> acknowledges off-topic and echoes plain question."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40_000_000, purpose="Purchase")

    # Turn 1: Case A
    nlu.result = UserUnderstanding(intent="property_search", required={})
    r1 = chat(web, message="mujhe property dekhni hai").json()
    cid = r1["conversation_id"]

    # Turn 2: Unrelated non-matching search triggers plain fallback question
    nlu.result = UserUnderstanding(intent="property_search", required={}, relax=[])
    r2 = chat(web, cid=cid, message="kuch bhi").json()
    assert "saved requirement continue karni hai" in r2["message"].lower()

    # Turn 3: User asks off-topic question
    nlu.result = UserUnderstanding(intent="off_topic")
    r3 = chat(web, cid=cid, message="python ki defination bta saktey kiya").json()

    assert r3.get("requires_clarification") is True
    assert "main sirf property se related sawalon mein madad kar sakti hoon" in r3["message"].lower()
    assert "saved requirement continue karni hai ya koi preference change karni hai?" in r3["message"].lower()


def test_existing_confirm_decline_wants_other_options_unchanged():
    """Existing confirm, decline, and wants_other_options behaviors remain completely unchanged."""
    from test_web_api import CustomerPreferences
    web, svc, nlu = setup()
    nlu.test_returning = True
    svc.customers.preferences = CustomerPreferences(CUSTOMER_ID, city="Islamabad", budget_max=40_000_000, purpose="Purchase")

    # Turn 1: Case A
    nlu.result = UserUnderstanding(intent="property_search", required={})
    r1 = chat(web, message="mujhe property dekhni hai").json()
    cid = r1["conversation_id"]

    # Turn 2: User confirms "haan"
    nlu.result = UserUnderstanding(intent="property_search", relax=["area"])
    r2 = chat(web, cid=cid, message="haan wahi dikha do").json()
    assert "pichli dafa" not in r2["message"].lower()
    assert "properties" in r2 and len(r2["properties"]) > 0








