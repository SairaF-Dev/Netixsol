"""
Day 3, Task 5 (data): 30 multi-hop questions for the Vector vs Graph vs Hybrid comparison.

A multi-hop question needs several connected facts, e.g. "Which judges sat on the cases that
applied Section 324 PPC?" = Section 324 PPC -> judgments that refer to it -> judges of those
judgments. Each question is written as such a walk (SPECS below); the answer is computed from the
graph (data/graph/*.csv) and then checked:

  * every link in the answer has its evidence sentence printed for review (--review);
  * the full text of all 225 judgments is searched for the starting provision / citation, and
    judgments the graph missed are listed, so the answer is not limited by extraction recall.

Corrections found in review are written into OVERRIDES (with the reason), so the answer key does
not inherit extraction errors. Output: evaluations/multihop_eval_set.jsonl.

Run:  python -m evaluations.build_multihop_set --review   (print evidence and text-search gaps)
      python -m evaluations.build_multihop_set            (write the set)
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Set

GRAPH = Path("data/graph")
JUDGMENTS = Path("data/structured/judgment")
OUT = Path("evaluations/multihop_eval_set.jsonl")

ACT = {"ppc": "PKLAW_010", "cpc": "PKLAW_008", "constitution": "REAL_STAT_001", "crpc": "EXT:code-of-criminal-procedure",
       "qso": "PKCODE_URDU_002", "ata": "PKLAW_011", "sales-tax": "EXT:sales-tax-act"}
# Loose text patterns for the recall check: (provision regex, law regex that must appear in the same judgment)
LAW_TEXT = {"ppc": r"P\.?\s?P\.?\s?C|Penal Code", "cpc": r"C\.?\s?P\.?\s?C|Civil Procedure",
            "constitution": r"Constitution", "crpc": r"Cr\.?\s?P\.?\s?C|Criminal Procedure",
            "qso": r"Shahadat|Q\.?S\.?O", "ata": r"Anti.?Terrorism|\bATA\b", "sales-tax": r"Sales Tax"}


def _read(name: str) -> List[Dict]:
    with (GRAPH / f"{name}.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class G:
    """The extracted graph, in memory: just the walks the questions need."""

    def __init__(self):
        self.case = {r["key"]: r for r in _read("nodes_case")}
        self.corpus = {k for k, r in self.case.items() if r.get("in_corpus") == "True"}
        self.judge_name = {r["key"]: r["name"].replace("Justice ", "").split(",")[0].strip() for r in _read("nodes_judge")}
        self.prov_cases, self.case_provs, self.evidence = defaultdict(set), defaultdict(set), defaultdict(list)
        for t in ("refers_to", "interprets"):
            for e in _read(f"edges_{t}"):
                if e["src"] in self.corpus:
                    self.prov_cases[e["dst"]].add(e["src"])
                    self.case_provs[e["src"]].add(e["dst"])
                    self.evidence[(e["src"], e["dst"])].append(e)
        self.cites, self.cited_by = defaultdict(set), defaultdict(set)
        for t in ("cites", "follows", "distinguishes", "overrules"):
            for e in _read(f"edges_{t}"):
                if e["src"] in self.corpus:
                    self.cites[e["src"]].add(e["dst"])
                    self.cited_by[e["dst"]].add(e["src"])
                    self.evidence[(e["src"], e["dst"])].append(e)
        self.judges, self.cases_of_judge = defaultdict(set), defaultdict(set)
        for e in _read("edges_sat_on"):
            self.judges[e["dst"]].add(e["src"])
            self.cases_of_judge[e["src"]].add(e["dst"])

    def label(self, case: str) -> str:
        r = self.case[case]
        return f"{r['case_number'] if r['case_number'] != 'Unknown' else r['document_id']} ({r['document_id']})"

    def doc(self, case: str) -> str:
        return self.case[case]["document_id"]

    def court(self, case: str) -> str:
        return self.case[case].get("court", "")


def P(act: str, label: str) -> str:
    return f"{ACT[act]}::{label}"


def CIT(citation: str) -> str:
    return f"CIT:{citation}"


# ----------------------------------------------------------------------------- question walks
def cases_of(g: G, prov: str, court: str = None) -> Set[str]:
    return {c for c in g.prov_cases[prov] if not court or g.court(c).startswith(court)}


def judges_of(g: G, cases: Set[str]) -> Set[str]:
    return {g.judge_name[j] for c in cases for j in g.judges[c]}


def provisions_in(g: G, cases: Set[str], act: str) -> Set[str]:
    return {p.split("::")[1] for c in cases for p in g.case_provs[c] if p.startswith(ACT[act] + "::")}


def top(counter: Counter) -> List[str]:
    if not counter:
        return []
    best = max(counter.values())
    return sorted(k for k, v in counter.items() if v == best)


def shared_precedents(g: G, doc_a: str, doc_b: str) -> Set[str]:
    a, b = (next(c for c in g.corpus if g.doc(c) == d) for d in (doc_a, doc_b))
    return {d[4:] for d in g.cites[a] & g.cites[b] if d.startswith("CIT:")}


def judge_key(g: G, name: str) -> str:
    return next(k for k, v in g.judge_name.items() if v.lower() == name.lower())


SPECS = [
    # --- provision -> judgments -> judges
    ("MH_01", "Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Penal Code?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("ppc", "Section 324"))), ("ppc", "324", "Section")),
    ("MH_02", "Kin judges ne un muqadmat ki samaat ki jin mein Qanun-e-Shahadat ke Article 129 ka hawala diya gaya?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("qso", "Article 129"))), ("qso", "129", "Article")),
    ("MH_03", "Which judges decided the judgments that discuss Section 164 of the Code of Criminal Procedure?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("crpc", "Section 164"))), ("crpc", "164", "Section")),
    ("MH_04", "Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("ata", "Section 7"))), ("ata", "7", "Section")),
    ("MH_05", "Which judges dealt with cases where a plaint was to be returned under Order VII Rule 10 CPC?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("cpc", "Order VII Rule 10"))), ("cpc", "VII Rule 10", "Order")),
    # --- provision -> judgments, filtered by court
    ("MH_06", "Which Lahore High Court judgments refer to Article 189 of the Constitution (decisions of the Supreme Court binding on other courts)?",
     "local", ["Section", "Case", "Court"], lambda g: {g.label(c) for c in cases_of(g, P("constitution", "Article 189"), "Lahore")}, ("constitution", "189", "Article")),
    ("MH_07", "Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution?",
     "local", ["Section", "Case", "Court"], lambda g: {g.label(c) for c in cases_of(g, P("constitution", "Article 212"), "Supreme")}, ("constitution", "212", "Article")),
    ("MH_08", "Which judgments refer to Section 376 PPC, and which court decided each of them?",
     "local", ["Section", "Case", "Court"], lambda g: {f"{g.label(c)}: {g.court(c)}" for c in cases_of(g, P("ppc", "Section 376"))}, ("ppc", "376", "Section")),
    ("MH_09", "Which judgments refer to Article 84 of the Qanun-e-Shahadat Order (the court comparing signatures itself), and which court decided each?",
     "local", ["Section", "Case", "Court"], lambda g: {f"{g.label(c)}: {g.court(c)}" for c in cases_of(g, P("qso", "Article 84"))}, ("qso", "84", "Article")),
    # --- judge -> judgments -> provisions of one law
    ("MH_10", "Which provisions of the Code of Civil Procedure were referred to in cases decided by Justice Syed Ahsan Raza Kazmi?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: provisions_in(g, g.cases_of_judge[judge_key(g, "Syed Ahsan Raza Kazmi")], "cpc"), None),
    ("MH_11", "Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad Ahmad Khan?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: provisions_in(g, g.cases_of_judge[judge_key(g, "Malik Shahzad Ahmad Khan")], "ppc"), None),
    ("MH_12", "Which Articles of the Constitution were referred to in cases decided by Justice Jawad Hassan?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: provisions_in(g, g.cases_of_judge[judge_key(g, "Jawad Hassan")], "constitution"), None),
    ("MH_13", "Justice Khalid Ishaq ke muqadmat mein Aain ke kaun se Articles ka zikr hua?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: provisions_in(g, g.cases_of_judge[judge_key(g, "Khalid Ishaq")], "constitution"), None),
    # --- precedent -> citing judgments -> judges
    ("MH_14", "Which judges sat on the cases that cite 2017 SCMR 1218?",
     "local", ["Case", "Case", "Judge"], lambda g: judges_of(g, g.cited_by[CIT("2017 SCMR 1218")]), ("cit", "2017 SCMR 1218", None)),
    ("MH_15", "Which judgments in the corpus rely on or cite 2009 SCMR 230, and who were the judges?",
     "local", ["Case", "Case", "Judge"], lambda g: {f"{g.label(c)}: {', '.join(sorted(judges_of(g, {c})))}" for c in g.cited_by[CIT("2009 SCMR 230")]}, ("cit", "2009 SCMR 230", None)),
    ("MH_16", "Which courts decided the judgments citing 2010 SCMR 1630?",
     "local", ["Case", "Case", "Court"], lambda g: {f"{g.label(c)}: {g.court(c)}" for c in g.cited_by[CIT("2010 SCMR 1630")]}, ("cit", "2010 SCMR 1630", None)),
    ("MH_17", "Which judges sat on the cases citing PLJ 2024 SC 114?",
     "local", ["Case", "Case", "Judge"], lambda g: judges_of(g, g.cited_by[CIT("PLJ 2024 SC 114")]), ("cit", "PLJ 2024 SC 114", None)),
    # --- co-citation and co-occurrence
    ("MH_18", "Which judgments cite both PLD 2019 SC 504 and PLD 1991 SC 197 (the cases on applications under Section 12(2) CPC)?",
     "local", ["Case", "Case", "Case"], lambda g: {g.label(c) for c in g.cited_by[CIT("PLD 2019 SC 504")] & g.cited_by[CIT("PLD 1991 SC 197")]}, None),
    ("MH_19", "In judgments that refer to Section 324 PPC (attempt to murder), which other PPC sections are also referred to in at least two of those judgments?",
     "local", ["Section", "Case", "Section"], lambda g: {s for s, n in Counter(p for c in cases_of(g, P("ppc", "Section 324")) for p in provisions_in(g, {c}, "ppc")).items() if n >= 2} - {"Section 324"}, None),
    ("MH_20", "Which precedents are cited in both the Supreme Court judgments C.A. 1410/2019 and C.R.P. 410/2023?",
     "local", ["Case", "Case", "Case"], lambda g: shared_precedents(g, "SC_c.a._1410_2019", "SC_c.r.p._410_2023"), None),
    ("MH_21", "Which precedents do the Lahore High Court judgments in W.P. No. 43022 of 2026 and Writ Petition No. 6349 of 2026 both rely on?",
     "local", ["Case", "Case", "Case"], lambda g: shared_precedents(g, "LHC_2026LHC8618", "LHC_2026LHC8384"), None),
    # --- judge -> co-judge
    ("MH_22", "With which judges did Justice Malik Shahzad Ahmad Khan sit on a bench?",
     "local", ["Judge", "Case", "Judge"], lambda g: judges_of(g, g.cases_of_judge[judge_key(g, "Malik Shahzad Ahmad Khan")]) - {"Malik Shahzad Ahmad Khan"}, None),
    ("MH_23", "Which judges sat with Justice Amin-ud-Din Khan, and in which cases?",
     "local", ["Judge", "Case", "Judge"], lambda g: {f"{g.label(c)}: {', '.join(sorted(judges_of(g, {c}) - {'Amin-ud-Din Khan'}))}" for c in g.cases_of_judge[judge_key(g, "Amin-ud-Din Khan")]}, None),
    ("MH_24", "Which judgments decided by Justice Mirza Viqas Rauf refer to the Contract Act, 1872, and to which sections?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: {f"{g.label(c)}: {', '.join(sorted(provisions_in(g, {c}, 'contract')))}" for c in g.cases_of_judge[judge_key(g, "Mirza Viqas Rauf")] if provisions_in(g, {c}, "contract")}, None),
    # --- global (aggregation over the whole graph)
    ("MH_25", "Which precedent (law-report citation) is cited by the largest number of judgments in the corpus?",
     "global", ["Case", "Case"], lambda g: {d[4:] for d in top(Counter({d: len(c) for d, c in g.cited_by.items() if d.startswith("CIT:")}))}, None),
    ("MH_26", "Which judge sat on the largest number of corpus cases that refer to Article 199 of the Constitution?",
     "global", ["Section", "Case", "Judge"], lambda g: set(top(Counter(g.judge_name[j] for c in cases_of(g, P("constitution", "Article 199")) for j in g.judges[c]))), None),
    ("MH_27", "Which provision of the Code of Civil Procedure is referred to by the most judgments in the corpus?",
     "global", ["Act", "Section", "Case"], lambda g: set(top(Counter({p.split("::")[1]: len(c) for p, c in g.prov_cases.items() if p.startswith(ACT["cpc"] + "::")}))), None),
    ("MH_28", "Which judge sat on the largest number of cases in the corpus?",
     "global", ["Judge", "Case"], lambda g: set(top(Counter({g.judge_name[j]: len(c) for j, c in g.cases_of_judge.items()}))), None),
    ("MH_29", "Which Article of the Constitution is referred to by the most Lahore High Court judgments?",
     "global", ["Act", "Section", "Case", "Court"], lambda g: set(top(Counter({p.split("::")[1]: len({c for c in cs if g.court(c).startswith("Lahore")}) for p, cs in g.prov_cases.items() if p.startswith(ACT["constitution"] + "::")}))), None),
    ("MH_30", "Which section of the Code of Criminal Procedure is referred to by the most Supreme Court judgments that also refer to Section 302 PPC?",
     "global", ["Section", "Case", "Section", "Act"], lambda g: set(top(Counter(p.split("::")[1] for c in cases_of(g, P("ppc", "Section 302"), "Supreme") for p in g.case_provs[c] if p.startswith(ACT["crpc"] + "::")))), None),
]
ACT["contract"] = "PKLAW_012"

# Held-out: the 10 graph questions of evaluations/router_eval_extra.jsonl, written after GraphRAG's rules
# were developed on SPECS and never used to change them. Same walks, same checks.
HELDOUT_OUT = Path("evaluations/multihop_heldout.jsonl")
HELDOUT_SPECS = [
    ("HO_01", "Which judges sat on the cases that refer to Section 9 of the Code of Civil Procedure?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("cpc", "Section 9"))), ("cpc", "9", "Section")),
    ("HO_02", "How many judgments in the corpus cite PLD 2023 SC 588?",
     "global", ["Case", "Case"], lambda g: {str(len(g.cited_by[CIT("PLD 2023 SC 588")]))}, ("cit", "PLD 2023 SC 588", None)),
    ("HO_03", "Which Lahore High Court cases refer to Section 22A of the CrPC?",
     "local", ["Section", "Case", "Court"], lambda g: {g.label(c) for c in cases_of(g, P("crpc", "Section 22A"), "Lahore")}, ("crpc", "22A", "Section")),
    ("HO_04", "Which precedents are cited by both C.A. 435-L/2012 and C.R.P. 410/2023?",
     "local", ["Case", "Case", "Case"], lambda g: shared_precedents(g, "SC_c.a._435_l_2012", "SC_c.r.p._410_2023"), None),
    ("HO_05", "Which judge has sat most often with Justice Musarrat Hilali?",
     "global", ["Judge", "Case", "Judge"], lambda g: set(top(Counter(g.judge_name[j] for c in g.cases_of_judge[judge_key(g, "Musarrat Hilali")] for j in g.judges[c] if g.judge_name[j] != "Musarrat Hilali"))), None),
    ("HO_06", "Kaun se judges ne Section 302 PPC ke muqadmat sune?",
     "local", ["Section", "Case", "Judge"], lambda g: judges_of(g, cases_of(g, P("ppc", "Section 302"))), ("ppc", "302", "Section")),
    ("HO_07", "Which Constitution Articles came up in the cases heard by Justice Qazi Faez Isa?",
     "local", ["Judge", "Case", "Section", "Act"], lambda g: provisions_in(g, g.cases_of_judge[judge_key(g, "Qazi Faez Isa")], "constitution"), None),
    ("HO_08", "Which courts decided the judgments that cite PLD 2003 SC 315?",
     "local", ["Case", "Case", "Court"], lambda g: {f"{g.label(c)}: {g.court(c)}" for c in g.cited_by[CIT("PLD 2003 SC 315")]}, ("cit", "PLD 2003 SC 315", None)),
    ("HO_09", "Which judgments cite both 2017 SCMR 1218 and 2019 SCMR 906?",
     "local", ["Case", "Case", "Case"], lambda g: {g.label(c) for c in g.cited_by[CIT("2017 SCMR 1218")] & g.cited_by[CIT("2019 SCMR 906")]}, None),
    ("HO_10", "Which section of the Code of Criminal Procedure appears in the most Lahore High Court judgments?",
     "global", ["Act", "Section", "Case", "Court"], lambda g: set(top(Counter({p.split("::")[1]: len({c for c in cs if g.court(c).startswith("Lahore")}) for p, cs in g.prov_cases.items() if p.startswith(ACT["crpc"] + "::")}))), None),
]


# ----------------------------------------------------------------------------- review helpers
def _texts() -> Dict[str, str]:
    return {p.stem: re.sub(r"\s+", " ", " ".join(x["text"] for x in json.loads(p.read_text(encoding="utf-8"))["paragraphs"]))
            for p in JUDGMENTS.glob("*.json")}


def text_search(anchor, texts: Dict[str, str]) -> Set[str]:
    """Judgments whose text mentions the anchor provision / citation (loose, for the recall check)."""
    law, number, kind = anchor
    if law == "cit":
        parts = number.split()
        pattern = re.compile(r"\b" + r"[\s.]*".join(map(re.escape, parts)) + r"\b", re.I)
        return {d for d, t in texts.items() if pattern.search(t)}
    if kind == "Order":
        order, rule = number.split(" Rule ")
        pattern = re.compile(rf"Order\s+{order}\s*,?\s*Rule\s+{rule}\b", re.I)
    else:
        pattern = re.compile(rf"\b(?:{kind}s?|ss?\.|u/s|Art\.)\s*{number}\b(?![-\d])", re.I)
    law_re = re.compile(LAW_TEXT[law], re.I)
    return {d for d, t in texts.items() if pattern.search(t) and law_re.search(t)}


def review(specs=None) -> None:
    specs = specs or SPECS
    g, texts = G(), _texts()
    doc_case = {g.doc(c): c for c in g.corpus}
    for qid, question, scope, path, walk, anchor in specs:
        print(f"\n=== {qid} [{scope}] {question}\n    answer: {sorted(walk(g))}")
        if anchor:
            start = CIT(anchor[1]) if anchor[0] == "cit" else (
                P(anchor[0], f"Order {anchor[1]}") if anchor[2] == "Order" else P(anchor[0], f"{anchor[2]} {anchor[1]}"))
            linked = g.cited_by[start] if anchor[0] == "cit" else g.prov_cases[start]
            for c in sorted(linked):
                ev = g.evidence[(c, start)][0]
                m = re.search(re.escape(anchor[1].split()[-1]), ev["sentence"])
                snippet = ev["sentence"][max(0, m.start() - 110): m.end() + 60] if m else ev["sentence"][:170]
                print(f"    + {g.doc(c)} p{ev.get('paragraph')} [{ev.get('method')}]: ...{snippet}...")
            missed = text_search(anchor, texts) - {g.doc(c) for c in linked}
            for d in sorted(missed):
                m = re.search(rf"{anchor[1].split()[-1]}\b", texts[d])
                print(f"    ? text-only {d}: ...{texts[d][max(0, m.start() - 120): m.end() + 60] if m else ''}...")


# ----------------------------------------------------------------------------- answer-key corrections
# question id -> (answer to use, reason). Filled in after --review.
# How answers without a single starting provision / citation were checked.
_JUDGE_CHECK = "computed from the graph; every provision in the answer was found in that judge's judgments by a text search"
_SHARED_CHECK = "computed from the graph; every precedent in the answer was found in the text of both judgments"
_MARGIN_CHECK = "computed from the graph; the winner and the runner-up were re-counted on the full text of all judgments"
CHECKED = {"MH_10": _JUDGE_CHECK, "MH_11": _JUDGE_CHECK, "MH_12": _JUDGE_CHECK, "MH_13": _JUDGE_CHECK, "MH_24": _JUDGE_CHECK,
           "MH_18": _SHARED_CHECK, "MH_20": _SHARED_CHECK, "MH_21": _SHARED_CHECK,
           "MH_25": _MARGIN_CHECK, "MH_27": _MARGIN_CHECK, "MH_29": _MARGIN_CHECK, "MH_30": _MARGIN_CHECK,
           "MH_28": "computed from the bench lines (judges: 100% precision and recall in the extraction evaluation); "
                    "lead of 7 cases, more than the 5 judgments whose bench is not in the text",
           "HO_04": _SHARED_CHECK, "HO_05": _MARGIN_CHECK, "HO_09": _SHARED_CHECK,
           "HO_10": "computed from the graph after fixing a sentence-splitting error ('Cr. P.C.') that the full-text recount "
                    "exposed; the recount confirms the tie (6 Lahore High Court judgments each)",
           "MH_19": "computed from the graph (provision links: 92-96% recall in the extraction evaluation); not re-checked link by link",
           "MH_22": "computed from the bench lines (judges: 100% precision and recall in the extraction evaluation)",
           "MH_23": "computed from the bench lines (judges: 100% precision and recall in the extraction evaluation)"}
UNNAMED = "(judge not named in the judgment text)"
OVERRIDES: Dict[str, tuple] = {
    "MH_02": (["Aqeel Ahmed Abbasi", "Irfan Saadat Khan", "Ishtiaq Ibrahim", "Khalid Ibn-i-Aziz", "Muhammad Hashim Khan Kakar",
               "Muhammad Sajid Mehmood Sethi", "Salahuddin Panhwar", "Shahid Bilal Hassan", "Shahid Waheed", "Yahya Afridi"],
              "graph answer plus Khalid Ibn-i-Aziz: the text search found Article 129 QSO in LHC_2026LHC8563 ('Article 129, "
              "illustration (g), of the Qanun-e-Shahadat Order'), which the graph missed. LHC_2026LHC8526 also refers to it, "
              "but its judge is not named in the text (signed 'Chief Justice')."),
    "MH_04": (["Irfan Saadat Khan", "Ishtiaq Ibrahim", "Jamal Khan Mandokhail", "Miangul Hassan Aurangzeb", "Muhammad Hashim Khan Kakar",
               "Muhammad Shafi Siddiqui", "Musarrat Hilali", "Shahid Waheed", "Syed Hasan Azhar Rizvi", "Yahya Afridi"],
              "graph answer plus the bench of SC_crl.a._649_2022 (Irfan Saadat Khan, Jamal Khan Mandokhail, Shahid Waheed): "
              "it convicts 'under section 7(1)(a) of the ATA of 1997', which the graph missed."),
    "MH_14": (["Muhammad Ajmal Zahid", "Muhammad Jawad Zafar", "Tariq Mahmood Bajwa"],
              "computed from the graph and checked; a fourth citing judgment, SC_i.c.a._5_2023_dn, does not name its bench in the text."),
    "MH_15": (["Crl. Appeal No. 77604-J of 2021 (LHC_2026LHC8526): " + UNNAMED,
               "Crl. Appeal No.210897 of 2018 (LHC_2026LHC8563): Khalid Ibn-i-Aziz",
               "Crl. Appeal No.67154-J of 2022 (LHC_2026LHC8508): Aalia Neelum",
               "Criminal Revision No. 383/J/2025 (LHC_2026LHC8763): Tariq Saleem Sheikh"],
              "computed from the graph and checked; LHC_2026LHC8526 is signed 'Chief Justice' without a name."),
    "HO_07": (["Article 106", "Article 17", "Article 184", "Article 185", "Article 186", "Article 187", "Article 199",
               "Article 209", "Article 213", "Article 218", "Article 219", "Article 222", "Article 224", "Article 225",
               "Article 34", "Article 51", "Article 59", "Article 63"],
              "graph answer minus 'Article 4': its only evidence is 'Article 51(3) & 4', i.e. clause (4) of Article 51, "
              "which the extractor reads as a separate Article 4 (a known regex limitation)."),
    "MH_26": (["Muhammad Ali Mazhar", "Yahya Afridi"],
              "tie, 5 cases each: the graph alone gives Muhammad Ali Mazhar (5) ahead of Yahya Afridi (4), but it missed the "
              "Article 199 reference in SC_c.p._1011_2020 (bench includes Yahya Afridi), found by the text search."),
}


def write(specs=None, out: Path = OUT) -> None:
    specs = specs or SPECS
    g = G()
    with out.open("w", encoding="utf-8") as handle:
        for qid, question, scope, path, walk, anchor in specs:
            answer, note = sorted(walk(g)), CHECKED.get(qid) or (
                "computed from the graph; the evidence sentence of every link from the starting provision / citation "
                "was read, and a full-text search of all judgments found no judgment the graph missed" if anchor else
                "computed from the graph; not re-checked link by link")
            if qid in OVERRIDES:
                answer, note = sorted(OVERRIDES[qid][0]), OVERRIDES[qid][1]
            handle.write(json.dumps({"id": qid, "question": question, "scope": scope, "path": " -> ".join(path),
                                     "hops": len(path) - 1, "answer": answer, "review_note": note,
                                     "language": "Roman Urdu" if qid in ("MH_02", "MH_13", "HO_06") else "English"},
                                    ensure_ascii=False) + "\n")
    print(f"Wrote {len(specs)} questions to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--heldout", action="store_true", help="the 10 held-out questions instead of the 30")
    args = parser.parse_args()
    specs, out = (HELDOUT_SPECS, HELDOUT_OUT) if args.heldout else (SPECS, OUT)
    review(specs) if args.review else write(specs, out)
