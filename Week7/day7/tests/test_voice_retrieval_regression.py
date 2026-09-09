import json
from unittest.mock import Mock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from test_browser_voice import voice_setup, tool, database
from sara_agent.transcript_normalizer import normalize_transcript
from sara_agent.understanding import UserUnderstandingService
from vapi_integration.retrieval_policy import RETRIEVAL_UNAVAILABLE, VOICE_RETRIEVAL_RULES


def test_existing_stt_and_budget_normalization():
    assert 'phase 6' in normalize_transcript('DHA phase six').lower()
    nlu = UserUnderstandingService(client=Mock())
    result = nlu.understand('mera budget 4 crore hai', context={'required': {'city': 'Lahore', 'area': 'DHA Phase 6', 'property_type': 'Plot', 'purpose': 'purchase'}})
    assert result.required['budget'] == 40_000_000


def test_browser_exact_search_zero_matches(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    svc.properties.rows = []
    response = tool(web, 'search_properties', {'location': 'Lahore DHA Phase 6', 'property_type': 'Plot', 'purpose': 'buy', 'max_price': 40_000_000})
    assert response.status_code == 200
    assert json.loads(response.json()['results'][0]['result']) == {'properties': []}
    query = svc.properties.search_calls[-1]
    assert {k: query[k] for k in ('city', 'area', 'property_type', 'purpose', 'budget')} == dict(city='Lahore', area='DHA Phase 6', property_type='Plot', purpose='purchase', budget=40_000_000)


@pytest.mark.parametrize('name', ['search_properties', 'list_available_locations'])
def test_browser_repository_error_is_safe_not_empty(monkeypatch, name):
    web, svc, _ = voice_setup(monkeypatch)
    svc.properties.search = Mock(side_effect=RuntimeError('secret-database-url'))
    svc.properties.list_available_cities = Mock(side_effect=RuntimeError('secret-database-url'))
    response = tool(web, name, {})
    result = json.loads(response.json()['results'][0]['result'])
    assert result == RETRIEVAL_UNAVAILABLE
    assert 'secret-database-url' not in response.text
    assert not any(word in result.lower() for word in ('later', 'notify', 'wait', 'dobara'))


def test_browser_cities_only_from_repository(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    svc.properties.list_available_cities = Mock(return_value=['Inventory City'])
    result = tool(web, 'list_available_locations', {}).text
    assert 'Inventory City' in result
    assert all(city not in result for city in ('Lahore', 'Islamabad', 'Karachi'))
    svc.properties.list_available_cities.assert_called_once_with()


def test_phone_accepts_actual_vapi_json_arguments(monkeypatch):
    from vapi_integration import webhook_server as server
    monkeypatch.setenv('VAPI_WEBHOOK_SECRET', 'test-secret')
    handler = Mock(execute=AsyncMock(return_value='zero matches'))
    manager = Mock(get_session=AsyncMock(return_value=None))
    monkeypatch.setattr(server, 'tool_handler', handler)
    monkeypatch.setattr(server, 'session_manager', manager)
    args = {'location':'DHA Phase 6 Lahore','max_price':40_000_000,'purpose':'buy','property_type':'Plot'}
    response = TestClient(server.app).post('/vapi/webhook', headers={'x-vapi-secret':'test-secret'}, json={'message': {'type':'tool-calls','call':{'id':'test-phone'},'toolCallList':[{'id':'t1','function':{'name':'search_properties','arguments':json.dumps(args)}}]}})
    assert response.status_code == 200
    assert handler.execute.call_args.kwargs['arguments'] == args


def test_updater_preserves_prompt_and_preflights(monkeypatch):
    from vapi_integration.scripts import update_assistant as updater
    for key, value in {'VAPI_API_KEY':'test','VAPI_ASSISTANT_ID':'test','VAPI_WEBHOOK_SECRET':'test','VAPI_SERVER_URL':'https://example.test'}.items():
        monkeypatch.setenv(key, value)
    original = 'Sara persona\nVERIFIED PROPERTY DATA RULES:\nExisting rules'
    current = {'provider':'openai','model':'test','messages':[{'role':'system','content':original}]}
    response = Mock(is_error=False)
    response.json.return_value = {'model':current}
    monkeypatch.setattr(updater.httpx, 'get', Mock(return_value=response))
    post = Mock(return_value=Mock(status_code=200, json=lambda: {'status':'ignored'}))
    patch = Mock(return_value=response)
    monkeypatch.setattr(updater.httpx, 'post', post)
    monkeypatch.setattr(updater.httpx, 'patch', patch)
    updater.main()
    content = patch.call_args.kwargs['json']['model']['messages'][0]['content']
    assert content.startswith(original)
    assert VOICE_RETRIEVAL_RULES.strip() in content
    updater.main()
    assert patch.call_args.kwargs['json']['model']['messages'][0]['content'] == content
    patch.reset_mock()
    post.return_value.status_code = 503
    with pytest.raises(SystemExit): updater.main()
    patch.assert_not_called()


def test_cities_query_against_postgres_inventory(database):
    import psycopg
    from uuid import uuid4
    from postgres_repository import PostgresPropertyRepository
    city = 'Inventory-' + uuid4().hex
    with psycopg.connect(database) as db:
        db.execute('CREATE TABLE locations(location_id int PRIMARY KEY, city text)')
        db.execute('CREATE TABLE properties(property_id int PRIMARY KEY, location_id int, available boolean)')
        db.execute('CREATE TABLE prices(property_id int, verification_status text)')
        db.execute('INSERT INTO locations VALUES (1,%s),(2,%s),(3,%s)', (city, 'Unavailable', 'Unverified'))
        db.execute('INSERT INTO properties VALUES (1,1,TRUE),(2,1,TRUE),(3,2,FALSE),(4,3,TRUE)')
        db.execute("INSERT INTO prices VALUES (1,'Verified'),(2,'Verified'),(3,'Verified'),(4,'Pending')")
    assert PostgresPropertyRepository(database_url=database).list_available_cities() == [city]
