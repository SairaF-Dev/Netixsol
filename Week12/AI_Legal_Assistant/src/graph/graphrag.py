"""
Day 3, Task 4: GraphRAG over the legal knowledge graph in Neo4j.

A question is answered from the graph in three ways, tried in this order:

1. Local search (no LLM). Entities in the question are linked to graph nodes: provisions
   ("Section 324 PPC" -> Section node), law-report citations ("2009 SCMR 230"), judges
   ("Justice Jawad Hassan"), case numbers ("C.A. 1410/2019") and a court ("Lahore High Court
   judgments"). A Cypher query is then built from them: the linked nodes fix the set of
   judgments (all must match: "cite both X and Y"), and the question's "which ..." word
   decides what to return (judges, courts, judgments, provisions of a law, precedents).
2. Global search (no LLM). Questions with "most" / "largest number" run the same query
   with counting and return the top result (all of them on a tie). Without a linked entity,
   the count runs over the whole graph ("Which judge sat on the most cases?").
3. Text-to-Cypher (LLM). If no query can be built, Gemini writes Cypher from the schema and
   examples; it is checked to be read-only, run in a read transaction, and repaired once
   if Neo4j reports an error.

Every judgment in a local-search answer carries the sentence the link was extracted from, so
the answer can be cited like a Day 2 answer.

Run:  python -m src.graph.graphrag "Which judges sat on the cases that refer to Section 324 PPC?"
"""

import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from src.graph.entities import acts_named_in, canonical_act
from src.graph.neo4j_client import database, get_driver
from src.graph.regex_extract import case_key, citations_in, norm_citation, norm_name, provision_refs

PRECEDENT = "CITES|FOLLOWS|DISTINGUISHES|OVERRULES"
PROVISION = "REFERS_TO|INTERPRETS"
MAX_ROWS = 50

# "which <word>" -> what to return
_TARGET_WORDS = [
    ("judge", r"judges?|bench"), ("court", r"courts?"), ("precedent", r"precedents?|law-report|citations?"),
    ("provision", r"provisions?|sections?|articles?|rules?"), ("case", r"judgments?|cases?|decisions?|muqadmat"),
]
_CASE_NUMBER = re.compile(
    r"\b(?:Civil\s+Appeal|Civil\s+Petition|Criminal\s+(?:Appeal|Petition)|Jail\s+Petition|Writ\s+Petition|Civil\s+Revision|"
    r"C\.?\s?R\.?\s?P|C\.?\s?A|C\.?\s?P|W\.?\s?P|Crl\.?\s?[AP]|J\.?\s?P|C\.?\s?R)\.?\s*(?:No\.?\s*)?\d+(?:\s*-\s*[A-Z])?"
    r"\s*(?:/|of)\s*\d{4}", re.I)


@dataclass
class Linked:
    """What the question is about, as graph keys, and what it asks for."""
    provisions: List[List[str]] = field(default_factory=list)   # per reference: alternative keys (English / Urdu law)
    citations: List[str] = field(default_factory=list)
    judges: List[str] = field(default_factory=list)
    cases: List[str] = field(default_factory=list)
    court: Optional[str] = None
    targets: List[str] = field(default_factory=list)   # first = main ("which judges ..., and in which cases")
    target_acts: List[str] = field(default_factory=list)
    aggregate: bool = False
    min_count: int = 1

    @property
    def starts(self) -> int:
        return len(self.provisions) + len(self.citations) + len(self.judges) + len(self.cases)


class CypherQuery(BaseModel):
    cypher: str


SCHEMA = f"""Neo4j graph of Pakistani court judgments and laws.
Nodes:
  (:Case {{key, name, case_number, court, year, document_id, citation, in_corpus, pagerank, cited_by}})
     in_corpus = true for the 225 judgments in the firm's corpus; false for precedents known only by
     their citation (key 'CIT:<citation>', e.g. 'CIT:2009 SCMR 230').
     court: 'Supreme Court of Pakistan' or 'Lahore High Court'.
  (:Section {{key, label, title, act}})   key '<act key>::<label>', label e.g. 'Section 302', 'Article 199', 'Order VII Rule 10'
  (:Act {{key, name}})                    e.g. key 'PKLAW_010' name 'Pakistan Penal Code, 1860'
  (:Judge {{key, name}})  (:Court {{key}})
Relationships:
  (:Case)-[:CITES|FOLLOWS|DISTINGUISHES|OVERRULES {{sentence, paragraph, page}}]->(:Case)
  (:Case)-[:REFERS_TO|INTERPRETS {{sentence, paragraph, page}}]->(:Section)-[:PART_OF]->(:Act)
  (:Judge)-[:SAT_ON]->(:Case)   (:Case)-[:DECIDED_BY]->(:Court)
Examples:
  Which judges sat on cases referring to Section 324 PPC?
    MATCH (j:Judge)-[:SAT_ON]->(c:Case)-[:{PROVISION}]->(s:Section {{label:'Section 324'}})-[:PART_OF]->(a:Act)
    WHERE a.name STARTS WITH 'Pakistan Penal Code' RETURN DISTINCT j.name AS item
  Which precedent is cited by the most judgments?
    MATCH (c:Case {{in_corpus:true}})-[:{PRECEDENT}]->(p:Case) RETURN p.citation AS item, count(DISTINCT c) AS n ORDER BY n DESC LIMIT 5
Rules: read-only (MATCH / OPTIONAL MATCH / WITH / WHERE / RETURN / ORDER BY / LIMIT only); return the answer as
column `item` (plus `n` when counting); at most {MAX_ROWS} rows."""

_WRITE = re.compile(r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH)\b|\bCALL\b|apoc\.|dbms\.", re.I)


# Client contracts (Contract, Clause nodes) are confidential to their matter; the public law graph is not.
# A query written by the LLM must name a public label on every node it matches (allowlist, not blocklist:
# "MATCH (n) RETURN n" would otherwise return contracts). Rejecting a harmless query is the safe failure.
PUBLIC_LABELS = {"Case", "Section", "Act", "Judge", "Court", "Party"}
_NODE = re.compile(r"(?<![\w.`])\(([^()]*)\)")
_NODE_BODY = re.compile(r"^\s*(\w*)\s*((?::\s*`?\w+`?\s*(?:\|\s*:?`?\w+`?\s*)*)*)\s*(\{.*\})?\s*$", re.S)


def private_access(cypher: str) -> Optional[str]:
    """Why the query could read client data, or None if every matched node is public."""
    # quoted values are data, not labels: s.act CONTAINS 'Contract Act' is a public statute search (red team F2)
    unquoted = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "''", cypher)
    if re.search(r"\b(?:Contract|Clause)\b", unquoted):
        return "client contracts are not searchable from the graph"
    bound: set = set()
    for body in _NODE.findall(cypher):
        m = _NODE_BODY.match(body)
        if not m:
            continue   # an expression in brackets, not a node pattern
        var, labels = m.group(1), set(re.findall(r"\w+", m.group(2) or ""))
        if labels:
            if not labels <= PUBLIC_LABELS:
                return f"label(s) {sorted(labels - PUBLIC_LABELS)} are not public"
            if var:
                bound.add(var)
        elif not var or var not in bound:
            return "every node must have a public label (Case, Section, Act, Judge, Court, Party)"
    return None


class GraphRAG:
    def __init__(self, llm=None):
        self.llm = llm
        self.driver = get_driver()
        self.db = database()
        rows = lambda q: self._run(q, {})
        self.act_keys: Dict[str, List[str]] = {}
        for r in rows("MATCH (a:Act) RETURN a.key AS key, a.name AS name"):
            self.act_keys.setdefault(canonical_act(r["key"], r["name"] or ""), []).append(r["key"])
        self.section_keys = {r["key"] for r in rows("MATCH (s:Section) RETURN s.key AS key")}
        self.citation_key = {}
        for r in rows("MATCH (c:Case {in_corpus:false}) RETURN c.key AS key, c.citation AS citation, c.aliases AS aliases"):
            for cit in [r["citation"] or ""] + (r["aliases"] or "").split("; "):
                if cit:
                    self.citation_key[norm_citation(cit)] = r["key"]
        self.corpus_case_keys = {r["key"] for r in rows("MATCH (c:Case {in_corpus:true}) RETURN c.key AS key")}
        self.judges = [(r["key"], [norm_name(n) for n in [r["name"]] + (r["aliases"] or "").split("; ") if n])
                       for r in rows("MATCH (j:Judge) RETURN j.key AS key, j.name AS name, j.aliases AS aliases")]

    def close(self):
        self.driver.close()

    def _run(self, cypher: str, params: Dict) -> List[Dict]:
        with self.driver.session(database=self.db) as session:
            return session.execute_read(lambda tx: [r.data() for r in tx.run(cypher, **params)])

    # ------------------------------------------------------------------ entity linking
    def link(self, question: str) -> Linked:
        q = re.sub(r"\s+", " ", question)
        low = q.lower()
        linked = Linked()
        start_acts = []
        for labels, act_text, _ in provision_refs(q):
            acts = acts_named_in(act_text) if act_text else []
            acts = acts or acts_named_in(q)          # "Qanun-e-Shahadat ke Article 129": the law comes first
            for act in acts[:1]:
                start_acts.append(act)
                for label in labels:
                    keys = [f"{k}::{label}" for k in self.act_keys.get(act, []) if f"{k}::{label}" in self.section_keys]
                    if keys:
                        linked.provisions.append(keys)
        for cit in citations_in(q):
            key = self.citation_key.get(norm_citation(cit))
            if key and key not in linked.citations:
                linked.citations.append(key)
        nq = f" {norm_name(q)} "
        linked.judges = [key for key, names in self.judges if any(f" {n} " in nq for n in names if n)]
        for match in _CASE_NUMBER.finditer(q):
            ck = case_key(match.group(0))
            linked.cases += [k for k in (f"SC:{ck}", f"LHC:{ck}") if ck and k in self.corpus_case_keys]
        court = re.search(r"(Lahore High Court|Supreme Court)\s+(?:judgments?|cases?|decisions?)", q, re.I)
        linked.court = None if not court else ("Lahore" if court.group(1).lower().startswith("lahore") else "Supreme")

        # what to return: the word after "which" / "kin" / "kaun se" first, then any other asked-for things
        # up to three words after "which": "which other PPC sections", "which two judges"
        # (only the first such word of each phrase: "which judges heard cases" asks for judges)
        to_target = lambda word: next((t for t, pattern in _TARGET_WORDS if re.fullmatch(pattern, word)), None)
        asked = [next((w for w in phrase.split() if to_target(w)), "")
                 for phrase in re.findall(r"\b(?:which|kin|kaun\s+se|who\s+were\s+the)\s+((?:[a-z\-.]+\s+){0,2}[a-z\-]+)", low)]
        for word in asked + re.findall(r"\b(judges?|courts?|precedents?|provisions?)\b", low):
            target = next((t for t, pattern in _TARGET_WORDS if re.fullmatch(pattern, word)), None)
            if target and target not in linked.targets:
                linked.targets.append(target)
        if re.search(r"\b(?:sat|sit)\s+(?:on|with|together)\b|\bsamaat\b", low) and "judge" not in linked.targets:
            linked.targets.append("judge")
        # laws named without a number are what the answer's provisions must belong to
        linked.target_acts = [k for act in acts_named_in(q) if act not in start_acts for k in self.act_keys.get(act, [])]
        if "provision" in linked.targets and not linked.target_acts:
            linked.target_acts = [k for act in start_acts for k in self.act_keys.get(act, [])]
        linked.aggregate = bool(re.search(r"\bmost\b|largest number|sab se zyada", low))
        if re.search(r"more than one|at least two|both", low) and not (linked.citations or linked.cases):
            linked.min_count = 2
        return linked

    # ------------------------------------------------------------------ query building
    def plan(self, linked: Linked) -> Optional[Tuple[str, Dict]]:
        if not linked.targets:
            return None
        main = "case" if "case" in linked.targets and not linked.aggregate else linked.targets[0]
        params: Dict = {"court": linked.court, "acts": linked.target_acts, "start_judges": linked.judges,
                        "start_provisions": [k for keys in linked.provisions for k in keys]}
        if main == "precedent" and len(linked.cases) == 2:    # precedents two judgments both cite
            params.update(a=linked.cases[0], b=linked.cases[1])
            return (f"MATCH (a:Case {{key:$a}})-[:{PRECEDENT}]->(p:Case)<-[:{PRECEDENT}]-(b:Case {{key:$b}}) "
                    f"RETURN DISTINCT coalesce(p.citation, p.name) AS item, 2 AS n"), params
        if linked.starts == 0 and not linked.aggregate:
            return None                                       # nothing to start from: leave it to text-to-Cypher
        lines, evidence = ["MATCH (c:Case {in_corpus:true}) WHERE $court IS NULL OR c.court STARTS WITH $court"], []
        for i, key in enumerate(linked.provisions):
            lines.append(f"MATCH (c)-[r{i}:{PROVISION}]->(s{i}:Section) WHERE s{i}.key IN $p{i}")
            params[f"p{i}"] = key
            evidence.append(f"r{i}.sentence")
        for i, key in enumerate(linked.citations):
            lines.append(f"MATCH (c)-[q{i}:{PRECEDENT}]->(:Case {{key:$q{i}}})")
            params[f"q{i}"] = key
            evidence.append(f"q{i}.sentence")
        if main != "judge":
            for i, key in enumerate(linked.judges):
                lines.append(f"MATCH (:Judge {{key:$j{i}}})-[:SAT_ON]->(c)")
                params[f"j{i}"] = key
        elif linked.judges:                                  # "with which judges did X sit": X's cases
            lines.append("MATCH (sj:Judge)-[:SAT_ON]->(c) WHERE sj.key IN $start_judges")
        ev =f"head([x IN [{', '.join(evidence)}] WHERE x IS NOT NULL])" if evidence else "null"
        lines.append(f"WITH c, collect({ev})[0] AS evidence")
        if main in ("case", "court"):
            lines.append(
                "RETURN c.document_id AS document_id, c.name AS name, c.court AS court, evidence, "
                "[(j:Judge)-[:SAT_ON]->(c) | j.name] AS judges, "
                f"[(c)-[:{PROVISION}]->(s:Section)-[:PART_OF]->(a:Act) WHERE a.key IN $acts | s.label] AS sections "
                f"ORDER BY document_id LIMIT {MAX_ROWS}")
        elif main == "judge":
            lines.append("MATCH (j:Judge)-[:SAT_ON]->(c) WHERE NOT j.key IN $start_judges "
                         "RETURN j.name AS item, count(DISTINCT c) AS n ORDER BY n DESC, item")
        elif main == "provision":
            act_filter = "a.key IN $acts AND " if linked.target_acts else ""
            lines.append(f"MATCH (c)-[:{PROVISION}]->(s:Section)-[:PART_OF]->(a:Act) WHERE {act_filter}NOT s.key IN $start_provisions "
                         "RETURN s.label AS item, count(DISTINCT c) AS n ORDER BY n DESC, item")
        elif main == "precedent":
            lines.append(f"MATCH (c)-[:{PRECEDENT}]->(p:Case) WHERE NOT p.key IN $cited "
                         "RETURN coalesce(p.citation, p.name) AS item, count(DISTINCT c) AS n ORDER BY n DESC, item")
            params["cited"] = linked.citations
        else:
            return None
        return "\n".join(lines), params

    # ------------------------------------------------------------------ text-to-Cypher
    def text_to_cypher(self, question: str) -> Tuple[Optional[str], List[Dict], Optional[str]]:
        if self.llm is None:
            return None, [], "no LLM configured"
        prompt, error = f"Question: {question}\nWrite one Cypher query that answers it.", None
        for _ in range(2):
            cypher = self.llm.generate_json(prompt, CypherQuery, system=SCHEMA, temperature=0.0).cypher.strip().rstrip(";")
            if _WRITE.search(cypher):
                return cypher, [], "rejected: not a read-only query"
            private = private_access(cypher)
            if private:
                return cypher, [], f"rejected: {private}"
            if not re.search(r"\bLIMIT\s+\d+\s*$", cypher, re.I):
                cypher += f" LIMIT {MAX_ROWS}"
            try:
                return cypher, self._run(cypher, {}), None
            except Exception as exc:   # one repair round with Neo4j's error message
                error = str(exc).splitlines()[0][:300]
                prompt = f"Question: {question}\nThis query failed:\n{cypher}\nError: {error}\nWrite a corrected query."
        return cypher, [], f"Neo4j error: {error}"

    # ------------------------------------------------------------------ answer
    def answer(self, question: str) -> Dict:
        linked = self.link(question)
        plan = self.plan(linked)
        if plan:
            cypher, params = plan
            rows, method, error = self._run(cypher, params), "global" if linked.aggregate else "local", None
        else:
            cypher, rows, error = self.text_to_cypher(question)
            params, method = {}, "text-to-cypher"
        items = self._items(rows, linked)
        return {"question": question, "method": method, "cypher": cypher, "params": params, "error": error,
                "linked": linked.__dict__, "items": items, "rows": rows}

    def _items(self, rows: List[Dict], linked: Linked) -> List[str]:
        """Rows -> answer strings in the answer-key format ('<case> (<document id>): <details>' or a name)."""
        if rows and "document_id" in rows[0]:
            out = []
            if "provision" in linked.targets and linked.target_acts:   # only judgments that refer to that law
                rows = [r for r in rows if r["sections"]]
            clean = lambda name: re.sub(r",\s*C\.?J\.?$", "", name.replace("Justice ", "")).strip()
            for r in rows:
                details = []
                if "court" in linked.targets:
                    details.append(r["court"])
                if "judge" in linked.targets:
                    details.append(", ".join(sorted(clean(j) for j in r["judges"])))
                if "provision" in linked.targets:
                    details.append(", ".join(sorted(set(r["sections"]))))
                out.append(f"{r['name']} ({r['document_id']})" + (f": {'; '.join(details)}" if details else ""))
            return out
        rows = [r for r in rows if r.get("item")]
        if "n" in (rows[0] if rows else {}):
            rows = [r for r in rows if r["n"] >= linked.min_count]
            if linked.aggregate and rows:
                best = rows[0]["n"]
                rows = [r for r in rows if r["n"] == best]
        return [str(r["item"]).replace("Justice ", "").split(",")[0].strip() for r in rows]


if __name__ == "__main__":
    rag = GraphRAG()
    result = rag.answer(" ".join(sys.argv[1:]))
    print(result["method"], "\n", result["cypher"], "\n")
    for item in result["items"]:
        print(" -", item)
    rag.close()
