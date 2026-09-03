from __future__ import annotations
import re
from enum import Enum
class QueryRoute(str,Enum): STRUCTURED='structured'; RAG='rag'; MIXED='mixed'
POLICY_PATTERNS=(r'\bcan sara\b',r'\bhow does sara\b',r'\bwhat happens if\b',r'\bwhat if\b',r'\bcompany policy\b',r'\bpolicy\b',r'\bfaq\b')
STRUCTURED_FACT_PATTERNS=(r'\bprice\b',r'\bcost\b',r'\bhow much\b',r'\bqeemat\b',r'\bkeemat\b',r'\bdaam\b',r'\bavailable\b',r'\bavailability\b',r'\bstatus\b',r'\bready\b',r'\bbedroom',r'\bbathroom',r'\bplot\s*size\b',r'\bcovered\s*area\b',r'\bdeveloper\b',r'\bdeveloped by\b',r'\bamenit',r'\bgym\b',r'\bpool\b',r'\bparking\b',r'\bsecurity\b',r'\belevator\b',r'\binstallment\s+(?:amount|value)\b',r'\bdown\s*payment\s+(?:amount|value)\b',r'\bbooking\s*amount\b',r'\bschool\b',r'\bhospital\b',r'\bnearby\b',r'\bdistance\b',r'\bagent\b',r'\bproperty\s*id\b')
SEARCH_PATTERNS=(r'\bshow me\b',r'\bfind me\b',r'\bfind\b',r'\boptions?\b',r'\blooking for\b',r'\bchahiye\b',r'\bchahye\b',r'\bbuy\b',r'\bpurchase\b',r'\brent\b',r'\brental\b',r'\bbudget\b',r'\bunder\b',r'\bup to\b',r'\btak\b')
SEMANTIC_PATTERNS=(r'\btell me about\b',r'\boverview\b',r'\bdescription\b',r'\babout the project\b',r'\babout this project\b',r'\bproject ke bare\b',r'\bcompany information\b',r'\bcompany info\b',r'\bpayment\s*plan\b',r'\binvestment return',r'\broi\b',r'\bguarantee\b',r'\bbook.*visit\b',r'\bvisit.*book\b',r'\bproperty visit\b')
def normalize_question(q):
    if not isinstance(q,str): raise TypeError('question must be a string')
    q=re.sub(r'\s+',' ',q.strip().lower())
    if not q: raise ValueError('question cannot be empty')
    return q
def _matches(q,patterns): return any(re.search(p,q,re.I) for p in patterns)
def route_query(question):
    q=normalize_question(question); policy=_matches(q,POLICY_PATTERNS); structured=_matches(q,STRUCTURED_FACT_PATTERNS) or _matches(q,SEARCH_PATTERNS); semantic=_matches(q,SEMANTIC_PATTERNS) or policy
    if policy:
        compound=re.search(r'\b(and|aur)\b',q) is not None
        if structured and compound: return QueryRoute.MIXED
        return QueryRoute.RAG
    if structured and semantic: return QueryRoute.MIXED
    if structured: return QueryRoute.STRUCTURED
    if semantic: return QueryRoute.RAG
    return QueryRoute.RAG
def is_structured_query(q): return route_query(q)==QueryRoute.STRUCTURED
def is_rag_query(q): return route_query(q)==QueryRoute.RAG
def is_mixed_query(q): return route_query(q)==QueryRoute.MIXED
