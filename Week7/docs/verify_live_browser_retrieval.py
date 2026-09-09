"""Exercise real authenticated browser transport and inventory; no audio emulation."""
import json
import secrets
import sys
from uuid import uuid4
from dotenv import dotenv_values
import httpx

env = dotenv_values('day7/vapi_integration/.env')
base = 'http://127.0.0.1:8010'
public = env['VAPI_SERVER_URL'].rstrip('/') + '/vapi/webhook'
with httpx.Client(timeout=60) as web:
    response = web.post(base + '/api/auth/register', json={
        'full_name':'Voice Retrieval Diagnostic', 'email': 'voice-probe-'+uuid4().hex+'@example.invalid',
        'phone': '+92300'+''.join(str(secrets.randbelow(10)) for _ in range(7)),
        'password':secrets.token_urlsafe(30)+'A1'})
    print('diagnostic_registration', response.status_code)
    response.raise_for_status()
    customer_id = response.json()['customer_id']
    print('diagnostic_customer_id', customer_id)
    csrf = web.get(base + '/api/auth/csrf')
    csrf.raise_for_status()
    web.headers['x-csrf-token'] = csrf.json()['csrf_token']
    voice = web.post(base + '/api/me/voice-sessions', json={})
    print('voice_bootstrap', voice.status_code)
    voice.raise_for_status()
    session = voice.json()
    call = {'type':'webCall','id':'diagnostic-'+str(uuid4()),'assistantId':session['assistant_id'],
            'assistantOverrides':{'variableValues':{'sara_voice_session':session['voice_session']}}}
    try:
        with httpx.Client(timeout=60) as hook:
            for name, args in [('search_properties', {'location':'DHA Phase 6 Lahore','max_price':40000000,'property_type':'Plot','purpose':'buy'}), ('list_available_locations', {})]:
                response = hook.post(public, headers={'x-vapi-secret':env['VAPI_WEBHOOK_SECRET']}, json={'message':{'type':'tool-calls','call':call,'toolCallList':[{'id':str(uuid4()),'function':{'name':name,'arguments':json.dumps(args)}}]}})
                print('public_browser_tool', name, response.status_code, response.text)
                response.raise_for_status()
    finally:
        print('voice_close', web.post(base+'/api/me/voice-sessions/close',json={'voice_session':session['voice_session']}).status_code)
        print('logout', web.post(base+'/api/auth/logout').status_code)
