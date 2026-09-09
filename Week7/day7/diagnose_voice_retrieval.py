"""Read-only live retrieval probe. Never prints environment values or credentials."""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import psutil


def main():
    pid = int(sys.argv[1])
    process = psutil.Process(pid)
    environment = process.environ()
    os.environ.clear()
    os.environ.update(environment)
    os.chdir(process.cwd())
    sys.path.insert(0, str(Path(__file__).parent))
    logging.disable(logging.CRITICAL)
    from vapi_integration.tool_handler import VapiToolHandler
    handler = VapiToolHandler()
    print('process', pid, 'DATABASE_URL_present', bool(environment.get('DATABASE_URL')))
    print('repository_initialized', handler.repository is not None)
    repo = handler.repository
    if repo:
        try:
            with repo._connect() as conn:
                print('database', conn.execute('SELECT current_database()').fetchone()[0])
            for name, query in [('buyer_search', lambda: repo.search(city='Lahore', area='DHA Phase 6', property_type='Plot', purpose='Purchase', budget=40000000)), ('available_cities', repo.list_available_cities)]:
                try:
                    rows = query()
                    print(name, 'rows', len(rows), 'cities' if name == 'available_cities' else 'property_ids', rows if name == 'available_cities' else [r['property_id'] for r in rows])
                except Exception as exc:
                    print(name, type(exc).__name__, 'sqlstate', getattr(exc, 'sqlstate', None))
                    if getattr(exc, 'diag', None):
                        print('sql_error', exc.diag.message_primary)
        except Exception as exc:
            print('connection_error', type(exc).__name__, 'sqlstate', getattr(exc, 'sqlstate', None))
    with httpx.Client(timeout=60) as client:
        for name, arguments in [('search_properties', {'location':'Lahore DHA Phase 6','property_type':'Plot','purpose':'buy','max_price':40000000}), ('list_available_locations', {})]:
            response = client.post('http://127.0.0.1:8007/vapi/webhook', headers={'x-vapi-secret':os.environ.get('VAPI_WEBHOOK_SECRET','')}, json={'message':{'type':'tool-calls','call':{'id':'diagnostic-'+str(uuid4())},'toolCallList':[{'id':str(uuid4()),'name':name,'parameters':arguments}]}})
            print('live_webhook', name, response.status_code, response.text)


if __name__ == '__main__':
    main()
