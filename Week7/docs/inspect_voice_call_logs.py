import json
import sys
import httpx
from dotenv import dotenv_values

env = dotenv_values('day7/vapi_integration/.env')
with httpx.Client(timeout=45) as client:
    call = client.get('https://api.vapi.ai/call/'+sys.argv[1], headers={'Authorization':'Bearer '+env['VAPI_API_KEY']}).json()
    artifact = call.get('artifact') or {}
    if isinstance(artifact,str): artifact=json.loads(artifact)
    print('artifact_keys',list(artifact))
    for key in ('presignedLogUrl',):
        if artifact.get(key):
            log = client.get(artifact[key])
            print('log_http_status',log.status_code)
            print('log_format',log.headers.get('content-type'),len(log.content),log.content[:8].hex())
            if log.content.startswith(b'\x1f\x8b'):
                import gzip
                log = httpx.Response(200,content=gzip.decompress(log.content))
            try:
                parsed = log.json()
                print('log_shape',type(parsed).__name__, list(parsed)[:10] if isinstance(parsed,dict) else len(parsed))
                lines = [json.dumps(e) for e in parsed] if isinstance(parsed,list) else log.text.splitlines()
            except ValueError:
                lines = log.text.splitlines()
            for line in lines:
                try: event=json.loads(line)
                except ValueError: continue
                if any(term in line for term in ('call_AvYHPDv8rSgRjjvRl8oEMw3c','tool-calls','LockNotAvailable')):
                    print('event_keys',list(event))
                    print('event_summary',json.dumps({k:v for k,v in event.items() if k in ('level','time','timestamp','body','type')},ensure_ascii=True)[:1200])
                    data=event.get('attributes',{})
                    if isinstance(data,dict):
                        print('data_keys', list(data))
                        print('safe_data', json.dumps({k:v for k,v in data.items() if k in ('statusCode','duration','responseBody','response','error.message','http.response.status_code')},ensure_ascii=True)[:1200])
