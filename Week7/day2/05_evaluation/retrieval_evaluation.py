from __future__ import annotations
import csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; RAG=ROOT/'02_rag'; INTEG=ROOT/'07_integration'; sys.path[:0]=[str(RAG),str(INTEG)]
from retriever import Retriever
from query_router import route_query
CASES=Path(__file__).with_name('evaluation_questions.csv')
def evaluate():
    retriever=Retriever(documents_dir=str(RAG/'documents')); rows=list(csv.DictReader(CASES.open(newline='',encoding='utf-8'))); passed=0
    for c in rows:
        route=route_query(c['question']).value; route_ok=route==c['expected_route']; retrieval_ok=True
        if route=='rag':
            results=retriever.retrieve(c['question'],top_k=4); expected=c['expected_source'].strip()
            if expected and expected!='NONE': retrieval_ok=any(Path(r['source']).name==expected for r in results)
            elif c['expected_answer_type']=='REFUSAL': retrieval_ok=not results
        ok=route_ok and retrieval_ok; passed+=int(ok)
        detail=[]
        if not route_ok: detail.append(f"expected_route={c['expected_route']}")
        if not retrieval_ok: detail.append(f"expected_source={c['expected_source']}")
        print(f"{'PASS' if ok else 'FAIL'} {c['question_id']} route={route}" + (f" ({', '.join(detail)})" if detail else ''))
    total=len(rows); print(f'Retrieval/routing pass rate: {passed}/{total} ({passed/total:.2%})'); return passed==total
if __name__=='__main__': raise SystemExit(0 if evaluate() else 1)
