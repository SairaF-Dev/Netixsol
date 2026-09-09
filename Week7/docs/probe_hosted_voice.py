"""Inspect hosted VAPI retrieval events without credentials or caller identity."""
import os
import sys
import json
import psutil
import httpx
from dotenv import dotenv_values
from urllib.parse import urlsplit

env = {**dotenv_values('day7/vapi_integration/.env'), **psutil.Process(int(sys.argv[1])).environ()}
headers = {'Authorization': 'Bearer ' + env.get('VAPI_API_KEY', '')}
with httpx.Client(timeout=45) as client:
    response = client.get('https://api.vapi.ai/assistant/' + env['VAPI_ASSISTANT_ID'], headers=headers)
    print('assistant_status', response.status_code)
    if response.is_success:
        a = response.json()
        print('server', {k:v for k,v in a.get('server', {}).items() if k in ('url','timeoutSeconds')})
        print('tools', [{'name':t.get('function',{}).get('name'), 'server_url':t.get('server',{}).get('url'), 'messages':t.get('messages')} for t in a.get('model',{}).get('tools',[])])
        print('toolIds', a.get('model',{}).get('toolIds', []))
    response = client.get('https://api.vapi.ai/call', headers=headers, params={'limit':5})
    print('calls_status', response.status_code)
    if response.is_success:
        for index, call in enumerate(response.json()):
            if index < 2 or call.get('id') == '01a0718f-20dd-7000-8144-603e822692ab':
                detail = client.get('https://api.vapi.ai/call/' + call['id'], headers=headers)
                detail.raise_for_status()
                call = detail.json()
            print('call', call.get('id'), call.get('createdAt'), call.get('type'), call.get('endedReason'))
            artifact = call.get('artifact') or {}
            if isinstance(artifact, str):
                try: artifact = json.loads(artifact)
                except ValueError: artifact = {}
            for message in call.get('messages') or artifact.get('messages', []):
                if message.get('role') in ('tool','tool_call_result') or message.get('toolCalls'):
                    print('tool_event', json.dumps({k:v for k,v in message.items() if k in ('role','message','result','toolCalls','name')}, ensure_ascii=True))
                elif message.get('role') in ('user', 'human'):
                    text = message.get('message', message.get('content', ''))
                    if any(word in text.lower() for word in ('dha','phase','budget','crore','cities','options')) or call.get('id') == '01a0718f-20dd-7000-8144-603e822692ab':
                        print('relevant_transcript', json.dumps(text, ensure_ascii=True))
