"""
Day 3, Task 5: route each question to vector search, graph search, or both (hybrid).

* vector  - the answer is in the words of one provision or judgment: "What is the punishment for
            qatl-e-amd?", "Agar consideration unlawful ho to kya contract void hai?"
* graph   - the answer is a set of connected things or a count over them: "Which judges sat on the
            cases that refer to Section 324 PPC?", "Which precedent is cited the most?"
* hybrid  - both: find the connected judgments, then read what they say: "Which judgments refer to
            Section 324 PPC, and what did they hold about sentencing?"

The router is rules only (no LLM call, no cost, explainable): it scores graph signals (asking for
judges / courts / precedents / lists of judgments, counting, "both", benches) and content signals
(what a law says, punishment, meaning, holding, reasons).

Run:  python -m src.rag.router "Which judges sat on cases citing 2009 SCMR 230?"
"""

import re
import sys
from typing import Dict, List, Tuple

_GRAPH_SIGNALS: List[Tuple[str, str]] = [
    (r"\b(?:which|kin|kaun\s+se|who\s+were\s+the)\s+(?:[a-z\-.]+\s+){0,2}(?:judges?|courts?|precedents?|benches?)\b", "asks for judges / courts / precedents"),
    (r"\bwhich\s+(?:[a-z\-.]+\s+){0,3}(?:judgments?|cases?|decisions?)\b.{0,80}\b(?:cite|cited|citing|rel(?:y|ied)|refer|referred|apply|applied|involving|decided by|heard by)\b",
     "asks for the judgments linked to something"),
    (r"\b(?:which|kaun\s+se)\s+(?:[a-z\-.]+\s+){0,3}(?:provisions?|sections?|articles?)\b.{0,80}\b(?:cases?|judgments?|muqadmat)\b",
     "asks which provisions came up in cases"),
    (r"\bmost\b|\blargest number\b|\bsab se zyada\b|\bhow many (?:cases|judgments)\b", "counts over the graph"),
    (r"\bboth\b.{0,60}\b(?:cite|rely|judgments?)\b|\bcite both\b", "connects two judgments or precedents"),
    (r"\bsat\s+(?:on|with|together)\b|\bsit\s+on\s+a\s+bench\b|\bsamaat\b|\bon the bench\b", "asks about benches"),
    (r"\bjustice\s+[a-z\-]+(?:\s+[a-z\-]+){0,4}\s+(?:ke|ne)\b.{0,40}\bmuqadmat\b", "a judge's cases (Roman Urdu)"),
    (r"\b(?:cited by|citing|cite[sd]?)\s+(?:PLD|PLJ|SCMR|\d{4}\s+(?:SCMR|CLC|PLC|YLR|MLD))", "starts from a precedent citation"),
]
_CONTENT_SIGNALS: List[Tuple[str, str]] = [
    (r"\bwhat\s+(?:is|are|does|did|do|was|were)\b|\bwhat\s+(?:punishment|remedy)\b|\bhow\s+(?:does|did|is|can)\b|\bwhy\b", "asks what something says / why"),
    (r"\bpunish\w*|\bsentence\b|\bsaza\b|\bdefin\w+|\bmeaning\b|\bexplain\b|\bprinciple\b|\btest\b|\bconditions?\b", "asks about legal content"),
    (r"\b(?:held|hold|holding|ruled|decided that|observed|reasoning|ratio)\b", "asks what a court held"),   # not "Rule 10"
    (r"\bkya\b|\bkiya\b|\bkab\b|\bkaise\b|\bhai\?|\bhain\?|\bho ga\b|\bsakta\b|\bsakti\b|\bchahiye\b", "Roman Urdu content question"),
    (r"\b(?:can|may|must|is it|are)\b.{0,60}\?$", "yes/no legal question"),
]


def route(question: str) -> Dict:
    q = re.sub(r"\s+", " ", question).strip()
    graph = [why for pattern, why in _GRAPH_SIGNALS if re.search(pattern, q, re.I)]
    content = [why for pattern, why in _CONTENT_SIGNALS if re.search(pattern, q, re.I)]
    # "what did they hold", "and why" next to a graph request: both are needed
    asks_content_too = bool(re.search(r"\band\s+(?:what|why|how)\b|\bwhat\s+did\s+(?:they|it|the courts?)\s+(?:hold|say|decide)\b|"
                                      r"\b(?:holding|held)\b|\bkya\s+(?:faisla|kaha)\b|\bfaisla\s+kiya\b", q, re.I))
    if graph and (asks_content_too or (content and "asks what a court held" in content)):
        mode = "hybrid"
    elif graph:
        mode = "graph"
    else:
        mode = "vector"
    return {"mode": mode, "graph_signals": graph, "content_signals": content}


if __name__ == "__main__":
    print(route(" ".join(sys.argv[1:])))
