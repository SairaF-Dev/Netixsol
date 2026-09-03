from __future__ import annotations
import csv, re
from pathlib import Path

RAG_DIR=Path(__file__).resolve().parent
KB_DIR=RAG_DIR.parent/'01_knowledge_base'

def _norm(value: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',str(value).casefold()).strip()

def _property_index():
    path=KB_DIR/'properties.csv'
    index={}
    if not path.exists(): return index
    with path.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            name=(row.get('name') or '').strip(); pid=(row.get('property_id') or '').strip()
            if not name or not pid: continue
            item=index.setdefault(_norm(name), {'property_name':name,'property_ids':[]})
            item['property_ids'].append(pid)
    return index

def _document_type(source: str) -> str:
    parts={p.casefold() for p in Path(source).parts}
    if 'faqs' in parts: return 'faq'
    if 'property_brochures' in parts: return 'brochure'
    if 'project_descriptions' in parts: return 'description'
    return 'knowledge'

def get_metadata(source: str) -> dict:
    path=Path(source)
    doc_type=_document_type(source)
    if doc_type=='faq':
        return {'property_name':'','property_id':'','property_ids':'','document_type':'faq'}
    candidate=_norm(path.stem.replace('_',' '))
    match=_property_index().get(candidate)
    if not match:
        return {'property_name':'','property_id':'','property_ids':'','document_type':doc_type}
    ids=sorted(set(match['property_ids']))
    return {
        'property_name': match['property_name'],
        'property_id': ids[0] if len(ids)==1 else '',
        'property_ids': '|'.join(ids),
        'document_type': doc_type,
    }
