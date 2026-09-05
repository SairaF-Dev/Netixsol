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
    assert len(calls)==2 and calls[0]['messages']==calls[1]['messages']
    outputs=iter(['bad','bad']); calls.clear()
    with pytest.raises(UnderstandingError): service.understand('hello',context={})
    assert len(calls)==2
