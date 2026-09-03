from __future__ import annotations
import re
POLICY_MARKERS=(r'\bcan sara\b',r'\bhow does sara\b',r'\bwhat happens if\b',r'\bwhat if\b',r'\bcompany policy\b',r'\bpolicy\b',r'\bfaq\b')
SEMANTIC_MARKERS=(r'\btell me about\b',r'\boverview\b',r'\bdescription\b',r'\babout the project\b',r'\babout this project\b',r'\bproject ke bare\b')
STRUCTURED_FACT_PATTERNS=(r'\bprice\b',r'\bcost\b',r'\bhow much\b',r'\bqeemat\b',r'\bkeemat\b',r'\bavailable\b',r'\bavailability\b',r'\bstatus\b',r'\bbedroom',r'\bbathroom',r'\bplot\s*size\b',r'\bcovered\s*area\b',r'\bamenit',r'\bgym\b',r'\bpool\b',r'\bparking\b',r'\bsecurity\b',r'\bdeveloper\b',r'\bdeveloped by\b',r'\bpayment\s*plan\b',r'\binstallment',r'\bdown\s*payment\b',r'\bschool\b',r'\bhospital\b',r'\bnearby\b',r'\bdistance\b',r'\bagent\b',r'\bproperty\s*id\b')
def _text(q): return ' '.join(q.casefold().split())
def is_policy_question(question):
    if not isinstance(question,str) or not question.strip(): return False
    t=_text(question); return any(re.search(p,t) for p in POLICY_MARKERS)
def requires_structured_source(question):
    if not isinstance(question,str) or not question.strip(): return False
    if is_policy_question(question): return False
    t=_text(question)
    if any(re.search(p,t) for p in SEMANTIC_MARKERS): return False
    return any(re.search(p,t) for p in STRUCTURED_FACT_PATTERNS)
