import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from test_phase9_chat import setup
from web_api.auth import AuthIdentity
from web_api.voice_sessions import VoiceSessionStore, digest


def voice_setup(monkeypatch):
    web, services, nlu = setup()
    current = services.auth.identities['token-a']
    cid = str(uuid4())
    services.chat.store.rows[cid] = (current.customer_id, current.user_id, {})
    services.voice = SimpleNamespace(
        issue=lambda *args: {'voice_session': 'x' * 43, 'assistant_id': 'existing'},
        resolve=lambda *args: (current, cid), close=lambda *args: None)
    monkeypatch.setenv('VAPI_WEBHOOK_SECRET', 'test-secret')
    monkeypatch.setenv('VAPI_ASSISTANT_ID', 'existing')
    return web, services, nlu


def tool(web, name, arguments, tid=None):
    return web.post('/api/internal/voice/webhook', headers={'x-vapi-secret': 'test-secret'}, json={
        'message': {'type': 'tool-calls', 'call': {'type': 'webCall', 'id': 'call'},
                    'toolCallList': [{'id': tid or str(uuid4()), 'name': name, 'parameters': arguments}]}})


def test_bootstrap_auth_csrf_and_strict_identity(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    assert web.post('/api/me/voice-sessions', json={}).status_code == 201
    assert web.post('/api/me/voice-sessions', json={}).headers['cache-control'] == 'no-store'
    assert web.post('/api/me/voice-sessions', json={'customer_id': 'forged'}).status_code == 422
    assert web.post('/api/me/voice-sessions', json={}, headers={'x-csrf-token': 'wrong'}).status_code == 403
    web.cookies.clear()
    assert web.post('/api/me/voice-sessions', json={}).status_code == 401


def test_internal_webhook_fails_closed(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    assert web.post('/api/internal/voice/webhook', json={}).status_code == 403
    def denied(*args): raise PermissionError()
    svc.voice.resolve = denied
    assert tool(web, 'search_properties', {}).status_code == 403
    assert not svc.interactions.events


def test_voice_search_reuses_preferences_recommendations_and_deduplicates(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    response = tool(web, 'search_properties', {'location': 'DHA Lahore', 'max_price': 40_000_000, 'customer_id': 'forged'}, 'same-id')
    assert response.status_code == 200
    data = json.loads(response.json()['results'][0]['result'])
    assert data['properties']
    assert 'ml_mode' not in data
    count = len(svc.interactions.events)
    assert count == len(data['properties'])
    assert tool(web, 'search_properties', {}, 'same-id').json() == response.json()
    assert len(svc.interactions.events) == count
    assert svc.customers.resolve_for_customer_id(svc.auth.identities['token-a'].customer_id).preferences.budget_max == 40_000_000


def test_voice_cannot_mutate_foreign_or_unpresented_appointments(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    svc.appointments.request = AsyncMock()
    for name, args in [('cancel_appointment', {'appointment_id': str(uuid4())}),
                       ('reschedule_appointment', {'appointment_id': str(uuid4()), 'starts_at': '2030-01-01T10:00:00+05:00'}),
                       ('book_appointment', {'property_id': 'unpresented', 'starts_at': '2030-01-01T10:00:00+05:00'})]:
        response = tool(web, name, args)
        assert 'could not be confirmed' in response.text
    svc.appointments.request.assert_not_called()


def test_voice_booking_uses_authenticated_contact_and_records_ownership(monkeypatch):
    web, svc, _ = voice_setup(monkeypatch)
    tool(web, 'search_properties', {})
    aid = str(uuid4())
    svc.appointments.request = AsyncMock(return_value=(201, {'appointment': {'appointment_id': aid, 'status': 'confirmed'}}))
    svc.auth.repository.own_appointment = Mock()
    response = tool(web, 'book_appointment', {'property_id': 'P-1', 'starts_at': '2030-01-01T10:00:00+05:00',
        'client_name': 'Imposter', 'client_phone': '+923009999999', 'client_email': 'other@example.com'}, 'booking-id')
    assert aid in response.text
    sent = svc.appointments.request.call_args.args[2]
    assert sent['client_name'] == svc.customers.customer.full_name
    assert sent['client_phone'] == svc.customers.customer.phone_normalized
    svc.auth.repository.own_appointment.assert_called_once_with('ua', aid)
    tool(web, 'book_appointment', {}, 'booking-id')
    svc.appointments.request.assert_awaited_once()


def test_voice_final_feedback_reuses_chat_without_duplicate_search(monkeypatch):
    from sara_agent.models import UserUnderstanding
    web, svc, nlu = voice_setup(monkeypatch)
    data = json.loads(tool(web, 'search_properties', {}).json()['results'][0]['result'])
    count = len(svc.interactions.events)
    nlu.result = UserUnderstanding(interaction_action='liked', selected_index=1)
    payload = {'message': {'type': 'transcript', 'role': 'user', 'transcriptType': 'final',
                          'transcript': 'second wali pasand', 'call': {'type': 'webCall', 'id': 'call'}}}
    for _ in range(2):
        assert web.post('/api/internal/voice/webhook', json=payload, headers={'x-vapi-secret': 'test-secret'}).status_code == 200
    assert len(svc.interactions.events) == count + 1
    assert svc.interactions.events[-1]['property_id'] == data['properties'][1]['property_id']


def test_web_calls_never_enter_phone_session_manager(monkeypatch):
    from fastapi.testclient import TestClient
    from vapi_integration import webhook_server
    monkeypatch.setenv('VAPI_WEBHOOK_SECRET', 'test-secret')
    manager = SimpleNamespace(create_session=AsyncMock())
    monkeypatch.setattr(webhook_server, 'session_manager', manager)
    with patch.object(webhook_server.httpx.AsyncClient, 'post', AsyncMock(side_effect=RuntimeError())):
        response = TestClient(webhook_server.app).post('/vapi/webhook', headers={'x-vapi-secret': 'test-secret'},
            json={'message': {'type': 'call-start', 'call': {'id': 'call', 'type': 'webCall', 'customer': {'number': '+923001111111'}}}})
    assert response.status_code == 503
    manager.create_session.assert_not_called()


@pytest.fixture
def database():
    url = os.getenv('SARA_VOICE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set SARA_VOICE_TEST_DATABASE_URL to run isolated PostgreSQL verification')
    schema = 'voice_test_' + uuid4().hex
    with psycopg.connect(url, autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    isolated = make_conninfo(url, options=f'-c search_path={schema}')
    try:
        with psycopg.connect(isolated) as db:
            db.execute('CREATE TABLE customers(customer_id uuid PRIMARY KEY,full_name text,email text,phone_normalized text)')
            db.execute('CREATE TABLE auth_users(user_id uuid PRIMARY KEY,customer_id uuid REFERENCES customers(customer_id),email text)')
            db.execute('CREATE TABLE auth_sessions(session_id uuid PRIMARY KEY,user_id uuid REFERENCES auth_users(user_id),token_digest text,expires_at timestamptz)')
            db.execute((Path(__file__).parents[1] / 'web_api/chat_schema.sql').read_text())
        yield isolated
    finally:
        with psycopg.connect(url, autocommit=True) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_postgres_single_call_expiry_logout_and_cross_worker(database):
    identity = AuthIdentity(str(uuid4()), str(uuid4()), 'Test', 'test@example.com', None)
    sid = str(uuid4())
    with psycopg.connect(database) as db:
        db.execute('INSERT INTO customers(customer_id) VALUES (%s)', (identity.customer_id,))
        db.execute('INSERT INTO auth_users VALUES (%s,%s,%s)', (identity.user_id, identity.customer_id, identity.email))
        db.execute('INSERT INTO auth_sessions VALUES (%s,%s,%s,%s)',
                   (sid, identity.user_id, digest('auth-token'), datetime.now(timezone.utc) + timedelta(hours=1)))
    first, second = VoiceSessionStore(database), VoiceSessionStore(database)
    first.initialize()
    token = first.issue(identity, 'auth-token', 'existing')['voice_session']
    call = {'type': 'webCall', 'id': 'one', 'assistantId': 'existing'}
    current, cid = second.resolve(token, call)
    assert current.customer_id == identity.customer_id
    assert first.resolve(token, call)[1] == cid
    for wrong in [{**call, 'id': 'two'}, {**call, 'assistantId': 'other'}, {**call, 'type': 'inboundPhoneCall'}]:
        with pytest.raises(PermissionError): second.resolve(token, wrong)
    second.close(token, str(uuid4()))
    first.resolve(token, call)  # Another account cannot revoke it.
    second.close(token, identity.user_id)
    with pytest.raises(PermissionError): first.resolve(token, call)
    token = first.issue(identity, 'auth-token', 'existing')['voice_session']
    with psycopg.connect(database) as db:
        db.execute("UPDATE voice_sessions SET created_at=NOW()-INTERVAL '3 minutes' WHERE token_digest=%s", (digest(token),))
    with pytest.raises(PermissionError): second.resolve(token, call)
    token = first.issue(identity, 'auth-token', 'existing')['voice_session']
    with psycopg.connect(database) as db:
        db.execute('UPDATE voice_sessions SET expires_at=NOW() WHERE token_digest=%s', (digest(token),))
    with pytest.raises(PermissionError): second.resolve(token, call)
    token = first.issue(identity, 'auth-token', 'existing')['voice_session']
    with psycopg.connect(database) as db:
        db.execute('DELETE FROM auth_sessions WHERE session_id=%s', (sid,))
    with pytest.raises(PermissionError): second.resolve(token, call)
