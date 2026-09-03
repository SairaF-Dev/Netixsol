from __future__ import annotations
import csv,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; DOCS=ROOT/'02_rag'/'documents'; KB=ROOT/'01_knowledge_base'
STRUCTURED_PATTERNS=(r'\b\d{1,3}(?:,\d{3})+\s*PKR\b',r'\bprice\s+of\b',r'\bmarks?\s+the\s+(?:unit|property)\s+as\s+available\b')
def norm(v): return re.sub(r'[^a-z0-9]+',' ',v.casefold()).strip()
def main():
    props=list(csv.DictReader((KB/'properties.csv').open(encoding='utf-8-sig',newline=''))); names={norm(r['name']) for r in props}; errors=[]
    for p in DOCS.rglob('*.md'):
        text=p.read_text(encoding='utf-8'); parent=p.parent.name
        if parent!='faqs' and norm(p.stem.replace('_',' ')) not in names: errors.append(f'Unknown RAG project document: {p.name}')
        if parent!='faqs':
            for pat in STRUCTURED_PATTERNS:
                if re.search(pat,text,re.I): errors.append(f'Structured fact leaked into semantic document: {p.name}: {pat}')
    if errors:
        print('\n'.join('FAIL: '+e for e in errors)); return 1
    print('RAG document validation: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
