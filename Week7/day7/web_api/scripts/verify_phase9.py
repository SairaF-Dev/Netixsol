"""Run the Phase 9 two-process scenario in an isolated PostgreSQL schema.

Uses the configured LLM and real repository/services. Test listings are disposable
fixtures; no production customer or property rows are changed. Requires ports
8010 and 8011 to be free. Workers and schema are removed in finally.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT/'day7', ROOT/'day3/src', ROOT/'day2/03_structured_retrieval'):
    sys.path.insert(0,str(p))


def main():
    load_dotenv(ROOT/'day7/vapi_integration/.env')
    load_dotenv(ROOT/'day3/.env')
    original = os.environ['DATABASE_URL']
    schema = 'phase9_' + uuid4().hex
    processes=[]; logs=[]; report={}
    for port in (8010,8011):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port)) == 0:
                raise RuntimeError(f'Port {port} is occupied; no existing process was stopped')
    try:
        with psycopg.connect(original) as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
            for table in ('locations','developers','properties','prices','amenities'):
                connection.execute(sql.SQL('CREATE TABLE {}.{} (LIKE public.{} INCLUDING ALL)').format(sql.Identifier(schema),sql.Identifier(table),sql.Identifier(table)))
                connection.execute(sql.SQL('INSERT INTO {}.{} SELECT * FROM public.{}').format(sql.Identifier(schema),sql.Identifier(table),sql.Identifier(table)))
        dsn=make_conninfo(original,options=f'-c search_path={schema}')
        with psycopg.connect(dsn) as connection:
            connection.execute((ROOT/'day7/vapi_integration/customer_schema.sql').read_text(encoding='utf-8'))
            connection.execute((ROOT/'day7/vapi_integration/interaction_schema.sql').read_text(encoding='utf-8'))
            location=connection.execute("SELECT location_id FROM locations WHERE city='Lahore' AND area ILIKE '%DHA%' LIMIT 1").fetchone()[0]
            for i,price in enumerate((20000000,25000000,35000000),1):
                pid=f'PHASE9-FIXTURE-{i}'
                connection.execute("""INSERT INTO properties(property_id,name,location_id,property_type,bedrooms,bathrooms,available,status,purpose)
                    VALUES (%s,%s,%s,'Apartment',3,2,TRUE,'Ready','purchase')""",(pid,f'Disposable Phase 9 apartment {i}',location))
                connection.execute("""INSERT INTO prices(property_id,price,currency,transaction_type,price_period,verified_on,verification_status)
                    VALUES (%s,%s,'PKR','Purchase','One-time',CURRENT_DATE,'Verified')""",(pid,price))
        env=dict(os.environ,DATABASE_URL=dsn,PYTHONPATH=os.pathsep.join(str(p) for p in (ROOT/'day7',ROOT/'day3/src',ROOT/'day2/03_structured_retrieval')),
                 SARA_ML_RANKING_MODE='off',SARA_AUTH_SECURE_COOKIE='0',SARA_ENV='development')
        for port in (8010,8011):
            log=(ROOT/f'docs/phase9-worker-{port}.log').open('w',encoding='utf-8'); logs.append(log)
            process=subprocess.Popen([sys.executable,'-m','uvicorn','web_api.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append(process)
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                try:
                    if httpx.get(f'http://127.0.0.1:{port}/api/auth/me').status_code==401: break
                except httpx.HTTPError: pass
                if process.poll() is not None: raise RuntimeError('Worker startup failed; inspect local worker log')
                time.sleep(.25)
            else: raise RuntimeError('Worker startup timeout')
        a='http://127.0.0.1:8010'; b='http://127.0.0.1:8011'
        with httpx.Client(timeout=90) as client:
            registration=client.post(a+'/api/auth/register',json={'full_name':'Phase Nine Test','email':'phase9@example.test','phone':'03009990001','password':'DisposablePhase9Pass1'})
            assert registration.status_code==201, registration.text
            customer=registration.json()['customer_id']
            client.headers['X-CSRF-Token']=client.get(a+'/api/auth/csrf').json()['csrf_token']
            def turn(base,message,cid=None):
                result=client.post(base+'/api/me/chat',json={'message':message,**({'conversation_id':cid} if cid else {})})
                assert result.status_code==200, f'Chat status {result.status_code}: {result.text}'
                return result.json()
            first=turn(a,'Mujhe Lahore DHA mein 3 bedroom apartment chahiye. Budget 3 crore hai.')
            cid=first['conversation_id']
            prefs=client.get(b+'/api/me/preferences').json()
            assert prefs['city']=='Lahore' and prefs['area']=='DHA' and prefs['bedrooms']==3 and prefs['budget_max']==30000000,prefs
            # Purpose was genuinely omitted by the supplied scenario; answer Sara's one question.
            if first['requires_clarification']:
                turn(b,'Purchase ke liye.',cid)
            options=turn(b,'Options dikha dein.',cid)
            assert len(options.get('properties',[]))>=2, options
            second=options['properties'][1]['property_id']; rid=options['recommendation_session_id']
            feedback=turn(a,'Mujhe second wali pasand hai.',cid)
            with psycopg.connect(dsn) as connection:
                event=connection.execute("SELECT property_id,preference_snapshot FROM customer_interactions WHERE customer_id=%s AND action='liked' ORDER BY created_at DESC LIMIT 1",(customer,)).fetchone()
                assert event and event[0]==second and event[1]['budget_max']==30000000,feedback
                shown=connection.execute("SELECT property_id FROM customer_interactions WHERE conversation_id=%s AND action='shown'",(rid,)).fetchall()
                assert {r[0] for r in shown}=={r['property_id'] for r in options['properties']}
            turn(b,'Budget 4 crore kar dein.',cid)
            assert client.get(a+'/api/me/preferences').json()['budget_max']==40000000
            new=turn(a,'Ab new options dikha dein.',cid)
            assert new['recommendation_session_id']!=rid
            with psycopg.connect(dsn) as connection:
                snapshots=connection.execute('SELECT recommendation_session_id,preference_snapshot FROM recommendation_session_properties WHERE recommendation_session_id IN (%s,%s)',(rid,new['recommendation_session_id'])).fetchall()
                assert all(s[1]['budget_max']==(30000000 if str(s[0])==rid else 40000000) for s in snapshots)
                state=connection.execute('SELECT state FROM chat_sessions WHERE conversation_id=%s',(cid,)).fetchone()[0]
                assert state['recent_turns'] and len(state['recent_turns'])<=6
                assert state['recommendation_session_id']==new['recommendation_session_id']
            with httpx.Client(timeout=30) as other:
                assert other.post(b+'/api/auth/register',json={'full_name':'Other Test','email':'other@example.test','phone':'03009990002','password':'DisposablePhase9Pass2'}).status_code==201
                csrf=other.get(b+'/api/auth/csrf').json()['csrf_token']
                denied=other.post(b+'/api/me/chat',headers={'X-CSRF-Token':csrf},json={'conversation_id':cid,'message':'Options dikha dein.'})
                assert denied.status_code==404,denied.text
            report={'two_workers':[8010,8011], 'real_postgres':True,'real_shared_nlu':True,'isolated_fixture_listings':True,
                    'preference_hydration':True,'preferences_3_to_4_crore':True,'second_property_exact_feedback':True,
                    'shown_membership':True,'historical_snapshots_preserved':True,'new_session_new_budget':True,
                    'cross_user_denial':404,'bounded_context_across_workers':True,
                    'purpose_clarification_added':first['requires_clarification'],'result':'passed'}
            print(json.dumps(report,indent=2))
    finally:
        for process in processes:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        for log in logs: log.close()
        # Delete only this invocation's UUID-named isolated schema, never public.
        assert schema.startswith('phase9_') and len(schema)==39
        with psycopg.connect(original) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
        if report:
            report['workers_stopped_and_schema_removed']=True
            (ROOT/'docs/phase9-live-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
