"""
Day 3, Task 2 (regex part): build knowledge-graph nodes and relationships from the
structured corpus (data/structured), following docs/graph_schema.md.

* Corpus nodes: Acts and their Sections (English statutes), Cases (225 judgments), Courts,
  Judges, Parties, Contracts and Clauses.
* From every judgment paragraph, sentence by sentence:
    - case citations (PLD / SCMR / CLC ... reporter citations, LHC neutral citations,
      case numbers such as "Civil Petition No. 624 of 2023") -> CITES / FOLLOWS /
      DISTINGUISHES / OVERRULES, typed by cue words in the same sentence;
    - statute references ("section 302(b) PPC", "Article 199 of the Constitution")
      -> REFERS_TO, or INTERPRETS when the sentence talks about meaning or scope.
* Entity resolution: normalised reporter citations, case numbers -> TYPE-NUMBER-YEAR,
  Act aliases -> corpus Acts, section labels -> "Section N" / "Article N".

Each relationship keeps its evidence (sentence, paragraph, page). Regex typing is a
candidate: OVERRULES / DISTINGUISHES / INTERPRETS are flagged `needs_check` for the LLM step.

Output: data/graph/nodes_*.csv and edges_*.csv (for Neo4j LOAD CSV) and
evaluations/graph_extraction_report.md.

Run:  python -m src.graph.regex_extract
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.extraction.judgment_extractor import _CASE_NO, _CITATION
from src.utils.file_utils import load_json
from src.utils.logger import setup_logger

logger = setup_logger("graph_regex")

STRUCTURED = Path("data/structured")
OUT = Path("data/graph")
REPORT = Path("evaluations/graph_extraction_report.md")

_SENTENCE = re.compile(r"(?<=[.;?!])\s+(?=[A-Z(“\"])")
# A full stop after these is an abbreviation, not the end of a sentence: "section 340(2) of the Cr. P.C.",
# "C.P. No. 12", "Mr. Justice", "Art. 199", "v. State".
_ABBREVIATION_END = re.compile(r"(?:\b(?:Cr|Crl|No|Nos|Mr|Mrs|Ms|Mst|Dr|Ch|Art|Arts|Sec|Ss|Vs|v|vs|Pvt|Ltd|Co|Messrs|Hon|"
                               r"Govt|Addl|Dy|Asstt|Sr|Jr|St|ibid|i\.e|e\.g|viz|etc|[A-Z])\.)$")


def split_sentences(text: str) -> List[str]:
    sentences: List[str] = []
    for piece in _SENTENCE.split(text):
        if sentences and _ABBREVIATION_END.search(sentences[-1]):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    return sentences
_CUES = [
    ("OVERRULES", re.compile(r"\boverrul\w*|\bper\s+incuriam\b|\bnot\s+(?:a\s+)?good\s+law\b|\bno\s+longer\s+good\s+law\b", re.I)),
    ("DISTINGUISHES", re.compile(r"\bdistinguish\w*", re.I)),
    ("FOLLOWS", re.compile(r"\brel(?:ied|y|ying)\s+(?:up)?on\b|\breliance\s+(?:is|was|has been)?\s*placed\b|\bfollow(?:ed|ing)\b|"
                           r"\bapproved\b|\baffirmed\b|\bsupported\s+by\b|\breiterated\b", re.I)),
]
_APPEAL = re.compile(r"against\s+the\s+(?:judgment|order|decree)|impugned|arising\s+out\s+of|passed\s+in|on\s+appeal\s+from", re.I)
_INTERPRETS = re.compile(r"\binterpret\w*|\bconstru\w*|\bmeaning\s+of\b|\bscope\s+of\b|\bambit\s+of\b|\bconnotation\b", re.I)

# ----------------------------------------------------------------------------- normalisation
_REPORTER_COURTS = [(r"SUPREME\s+COURT", "SC"), (r"LAHORE|LAH\.?", "LAH"), (r"KARACHI|KAR\.?", "KAR"),
                    (r"PESHAWAR|PESH\.?", "PESH"), (r"ISLAMABAD|ISL\.?", "ISL"), (r"BALOCHISTAN|BAL\.?", "QUETTA")]


def norm_citation(text: str) -> str:
    """'PLD 2016 Supreme Court 358' -> 'PLD 2016 SC 358'; 'PCr. LJ' -> 'PCRLJ'."""
    t = re.sub(r"\(\s*PAK\.?\s*\)", " ", text.upper())          # 'PLD 1958 SC (Pak.) 41'
    t = re.sub(r"\s+", " ", t.replace(".", " ")).strip()
    t = re.sub(r"\bPCR\s*LJ\b", "PCRLJ", t)
    for pattern, short in _REPORTER_COURTS:
        t = re.sub(rf"\b(?:{pattern})\b", short, t)
    return re.sub(r"\s+", " ", t).strip()


_CASE_TYPES = [
    (r"civil\s+review|c\.?\s?r\.?\s?p", "CRP"), (r"crl\.?\s?r\.?\s?p|criminal\s+review", "CRLRP"),
    (r"civil\s+petition|c\.?\s?p\.?\s?l\.?\s?a|c\.\s?p\b|\bcp\b", "CP"), (r"civil\s+appeal|c\.\s?a\b|\bca\b", "CA"),
    (r"criminal\s+petition|crl\.?\s?p\.?\s?l\.?\s?a|crl\.?\s?p\b", "CRLP"),
    (r"criminal\s+appeal|crl\.?\s?a\b|criminal\s+jail\s+appeal", "CRLA"), (r"jail\s+petition|j\.\s?p\b", "JP"),
    (r"writ\s+petition|w\.\s?p\b", "WP"), (r"criminal\s+revision|crl\.?\s?rev", "CRLREV"),
    (r"civil\s+revision|\bc\.?\s?r\b", "CR"), (r"regular\s+first\s+appeal|r\.?\s?f\.?\s?a", "RFA"),
    (r"f\.?\s?a\.?\s?o", "FAO"), (r"intra\s+court\s+appeal|i\.?\s?c\.?\s?a", "ICA"),
    (r"crl\.?\s?misc|criminal\s+misc", "CRLMISC"), (r"constitution(?:al)?\s+petition", "CONSTP"),
    (r"human\s+rights", "HRC"), (r"suo\s+motu", "SMC"), (r"tax\s+reference", "TAXREF"), (r"reference", "REF"),
]


def case_key(case_number: str) -> Optional[str]:
    """'Civil Petition No. 624 of 2023' / 'C.P. 624/2023' -> 'CP-624-2023'; None if not parseable."""
    low = case_number.lower()
    kind = next((short for pattern, short in _CASE_TYPES if re.search(pattern, low)), None)
    match = re.search(r"(\d{1,6})(?:\s*-\s*([A-Za-z]{1,2})\b)?[^\d]{0,40}?(?:of|/)\s*((?:19|20)\d\d)", case_number)
    if not kind or not match:
        return None
    suffix = f"-{match.group(2).upper()}" if match.group(2) else ""
    return f"{kind}-{match.group(1)}{suffix}-{match.group(3)}"


# Citation formats the Day 1 pattern does not cover: Indian AIR / SCC reports, the Supreme Court's
# own "SCP" series and pre-1960 "PLD 1958 SC (Pak.) 41".
_CITATION_EXTRA = re.compile(
    r"\bAIR\s+(?:19|20)\d{2}\s+(?:[A-Z][A-Za-z]{0,6}\.?\s?){1,2}\s*\d+\b"
    r"|\(\s*(?:19|20)\d{2}\s*\)\s*\d+\s+SCC\s+\d+\b|\b(?:19|20)\d{2}\s*\(\s*\d+\s*\)\s*SCC\s+\d+\b"
    r"|\b(?:19|20)\d{2}\s+SCP\s+\d+\b|\bPLD\s+(?:19|20)\d{2}\s+SC\s*\(\s*Pak\.?\s*\)\s*\d+\b")
# A footnote number glued to a citation in the PDF text: "102022 SCMR 1946" (footnote 10).
_GLUED_FOOTNOTE = re.compile(r"\b\d{1,2}((?:19|20)\d{2}\s+(?:SCMR|PLD|CLC|CLD|YLR|MLD|PLC|PTD|PCr|SCP)\b)")


def citations_in(sentence: str) -> List[str]:
    text = _GLUED_FOOTNOTE.sub(r" \1", sentence)
    return [m.group(0) for pattern in (_CITATION, _CITATION_EXTRA) for m in pattern.finditer(text)]


# One judgment reported in two law reports: "(PLJ 2024 SC 114 = 2024 SCP 4)".
_ANY_CITATION = f"(?:{_CITATION.pattern}|{_CITATION_EXTRA.pattern})"
_SAME_CASE = re.compile(rf"({_ANY_CITATION})\s*=\s*({_ANY_CITATION})", re.I)


def equivalent_citations(sentence: str) -> List[Tuple[str, str]]:
    text = _GLUED_FOOTNOTE.sub(r" \1", sentence)
    return [(norm_citation(m.group(1)), norm_citation(m.group(2))) for m in _SAME_CASE.finditer(text)]


# Act names as written -> one display name. Keys are compared after _alias_key (lower case, no
# years, no "(V of 1908)", no leading "the" / "West Pakistan"), with and without spaces.
_ACT_ALIASES = {
    "ppc": "Pakistan Penal Code", "ppg": "Pakistan Penal Code", "penal code": "Pakistan Penal Code",
    "pakistan penal code": "Pakistan Penal Code",
    "cpc": "Code of Civil Procedure", "civil procedure code": "Code of Civil Procedure",
    "code of civil procedure": "Code of Civil Procedure", "civil procedure": "Code of Civil Procedure",
    "crpc": "Code of Criminal Procedure", "criminal procedure code": "Code of Criminal Procedure",
    "code of criminal procedure": "Code of Criminal Procedure", "criminal procedure": "Code of Criminal Procedure",
    "constitution": "Constitution of the Islamic Republic of Pakistan",
    "qso": "Qanun-e-Shahadat Order", "qanun e shahadat": "Qanun-e-Shahadat Order",
    "qanun e shahadat order": "Qanun-e-Shahadat Order", "qanoon e shahadat": "Qanun-e-Shahadat Order",
    "qanoon e shahadat order": "Qanun-e-Shahadat Order",
    "mflo": "Muslim Family Laws Ordinance", "muslim family law ordinance": "Muslim Family Laws Ordinance",
    "muslim family laws ordinance": "Muslim Family Laws Ordinance",
    "ata": "Anti-Terrorism Act", "anti terrorism act": "Anti-Terrorism Act",
    "election act": "Elections Act", "elections act": "Elections Act",
    "family courts act": "West Pakistan Family Courts Act",
    "police rules": "Punjab Police Rules", "punjab police rules": "Punjab Police Rules",
}


def _alias_key(text: str) -> str:
    t = re.sub(r"\([^)]*\)", " ", text.lower())                    # "(V of 1908)", "(“CPC”)"
    t = re.sub(r",?\s*(?:of\s+)?(?:18|19|20)\d\d\b", " ", t)        # ", 1908", "of 1969"
    t = re.sub(r"^.*\b(?:schedule|part)\s+to\s+", "", t)            # "First Schedule to the Limitation Act"
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    for _ in range(2):
        t = re.sub(r"^(?:the|west pakistan)\s+", "", t)
    return t


def act_alias(text: str) -> Optional[str]:
    key = _alias_key(text)
    return _ACT_ALIASES.get(key) or _ACT_ALIASES.get(key.replace(" ", ""))


def norm_name(text: str) -> str:
    text = re.sub(r",?\s*\b(h?cj|acj|j)\b\.?\s*$", " ", text.lower().strip())  # trailing ", CJ" / ", J."
    text = re.sub(r"\b(mr|mrs|ms|mst|dr|syed|justice|hon'?ble|chief)\b\.?", " ", text)
    return re.sub(r"[^a-z؀-ۿ ]+", " ", re.sub(r"\s+", " ", text)).strip()


# ----------------------------------------------------------------------------- graph container
class Graph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Dict]] = defaultdict(dict)   # label -> key -> props
        self.edges: Dict[str, Dict[Tuple, Dict]] = defaultdict(dict)  # type -> (src, dst, extra) -> props

    def node(self, node_label: str, key: str, **props) -> str:
        current = self.nodes[node_label].setdefault(key, {"key": key})
        for name, value in props.items():
            if value not in (None, "") and not current.get(name):
                current[name] = value
        return key

    def edge(self, edge_type: str, src: str, dst: str, dedupe: Tuple = (), **props) -> None:
        self.edges[edge_type].setdefault((src, dst) + dedupe, {"src": src, "dst": dst, **props})

    def merge(self, node_label: str, mapping: Dict[str, str], edge_types: Tuple[str, ...]) -> None:
        """Entity resolution: fold node `old` into `new` for every old -> new in mapping; the old
        spelling is kept in the `aliases` property and the given relationship types are re-pointed."""
        nodes = self.nodes[node_label]
        for old, new in mapping.items():
            if old != new and old in nodes:
                spelling = nodes.pop(old).get("name", old)
                aliases = {a for a in nodes[new].get("aliases", "").split("; ") if a} | {spelling}
                nodes[new]["aliases"] = "; ".join(sorted(aliases))
        for edge_type in edge_types:
            rebuilt = {}
            for key, props in self.edges[edge_type].items():
                src, dst = mapping.get(props["src"], props["src"]), mapping.get(props["dst"], props["dst"])
                rebuilt.setdefault((src, dst) + key[2:], {**props, "src": src, "dst": dst})
            self.edges[edge_type] = rebuilt


def judge_variants(keys_by_frequency: List[str]) -> Dict[str, str]:
    """Spelling variants of one judge's name ('naeem akhter afghan' / 'naeem akhtar afghan',
    'kakar' / 'kakkar'): same first name and 90%+ similar -> the more frequent spelling."""
    from rapidfuzz import fuzz

    kept, mapping = [], {}
    for key in keys_by_frequency:
        same = next((k for k in kept if k.replace(" ", "") == key.replace(" ", "")          # "mian gul" / "miangul"
                     or (key.split()[0] == k.split()[0] and fuzz.ratio(key, k) >= 90)
                     or (len(key.split()) >= 2 and k.split()[:len(key.split())] == key.split())), None)   # "jamal khan" cut short
        mapping[key] = same or key
        if not same:
            kept.append(key)
    return mapping


def _act_resolver(statutes: Dict[str, Dict]):
    # Laws that exist in the corpus only as OCR'd Urdu pages (no section structure).
    urdu_csv = Path("data/urdu_law_english_titles.csv")
    urdu_titles = []
    if urdu_csv.exists():
        with urdu_csv.open(encoding="utf-8") as handle:
            urdu_titles = [(r["document_id"], r["english_title"], r["match_key"]) for r in csv.DictReader(handle)
                           if r["match_key"] not in ("Constitution", "Penal Code", "Contract Act", "Anti-Terrorism",
                                                     "Muslim Family Laws")]  # these have English versions
    # Compare on the core title: "Constitution of ..., 1973 (as amended up to ...)" -> "Constitution of ..."
    names = {doc_id: doc["act_name"] for doc_id, doc in statutes.items()}
    cores = {doc_id: re.split(r"\(|,", name)[0] for doc_id, name in names.items()}
    words = lambda s: {w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in {"the", "act", "and", "of", "ordinance"}}

    def resolve(raw: str) -> Tuple[str, str, bool]:
        """Raw act text -> (act_id, display name, in_corpus)."""
        text = re.sub(r"\s+", " ", raw).strip(" ,.")
        target = act_alias(text) or text
        wanted = words(re.split(r"\(|,", target)[0])
        best = max(((len(wanted & words(core)) / max(1, len(words(core) | wanted)), doc_id) for doc_id, core in cores.items()),
                   default=(0, None))
        if best[0] >= 0.75:
            return best[1], names[best[1]], True
        for doc_id, english, key in urdu_titles:
            if key.lower() in target.lower().replace("&", "and"):
                return doc_id, english, True
        key = "EXT:" + re.sub(r"[^a-z0-9]+", "-", _alias_key(target)).strip("-")
        return key, target, False
    return resolve


def _section_labels(prefix: str) -> List[str]:
    """'Section 46 read with 45B' -> ['Section 46', 'Section 45B']; 'Article 185(3)' -> ['Article 185']."""
    kind = "Article" if re.match(r"\s*(articles?|art\.)", prefix, re.I) else (
        "Order" if re.match(r"\s*order", prefix, re.I) else ("Rule" if re.match(r"\s*rule", prefix, re.I) else "Section"))
    if kind in ("Order", "Rule"):
        return []  # Order/Rule references are kept only when they name both (handled by the caller)
    numbers = re.findall(r"\b(\d{1,4})\s*-?\s*([A-Z]{0,2})\b(?:\s*\([^)]*\))*", prefix)
    return [f"{kind} {n}{s}" for n, s in numbers]


# ----------------------------------------------------------------------------- statute provisions
# "Sections 302, 109 and 449 read with Section 34 of the Pakistan Penal Code", "Section 382-B, Cr.P.C.",
# "Article 10-A of the Constitution", "Order XVII Rule 3, C.P.C.", "section 540 of the Code" ...
# Suffix letters are capitals only (scoped (?-i:...)), although the pattern runs case-insensitive:
# "Sections 4 to 25" must not read as "Section 4TO".
_NUM = r"\d{1,4}(?:\s*-\s*(?-i:[A-Z]{1,2})\b|(?-i:[A-Z]{1,2})\b)?"
_SEP = r"\s*(?:,|&|/|\band\b|\bto\b|\bor\b|\bread\s+with\b)\s*(?:(?:sections?|articles?|ss?\.)\s+)?"
_PROVISION = re.compile(rf"(?<![\w-])(sections?|ss?\.|u/s|articles?|arts?\.)\s+({_NUM}(?:{_SEP}{_NUM})*)", re.I)
_ORDER_RULE = re.compile(r"(?<![\w-])Order\s+([IVXL]+|\d{1,2})\s*,?\s*Rules?\s+(\d{1,3}[A-Z]?)\b", re.I)
_RULE = re.compile(r"(?<![\w-])Rules?\s+(\d{1,3}(?:\.\d{1,3})?)\b(?!\s*of\s+Order)", re.I)
# A law's title: capitalised words, small joining words, and whole bracketed parts
# ("Supreme Court (Practice and Procedure) Act"), ending in Act / Ordinance / Code ...
_TITLE = (r"[A-Z][\w'’&.\-]*(?:\s+(?:of|the|and|for|on|in|to|at|against|&|[A-Z][\w'’&.\-]*|\([^()]{1,40}\))){0,10}?\s+"
          r"(?:Act|Ordinance|Order|Code|Rules|Regulations|Procedure|Sanhita|Adhiniyam)\b")
_TITLE_RE = re.compile(_TITLE)
_ACT_TAIL = re.compile(
    r"^(?:\s*,?\s+of\s+(?:the\s+)?|\s*,\s*|\s+under\s+(?:the\s+)?|\s+)(?:"
    r"(?P<abbr>P\.?\s?P\.?\s?[CG]\b\.?|Cr\.?\s?P\.?\s?C\b\.?|C\.?\s?P\.?\s?C\b\.?|Q\.?\s?S\.?\s?O\b\.?|MFLO\b|ATA\b)"
    r"|(?P<const>Constitution\b(?:\s+of\s+the\s+Islamic\s+Republic\s+of\s+Pakistan)?)"
    r"|(?P<qso>Qan(?:u|oo?)n\s*-?\s*e\s*-?\s*Shahadat(?:\s+Order)?)"
    rf"|(?P<title>{_TITLE})"
    r"|(?P<short>Code|Act|Ordinance|Order|Rules)\b)")
# A short name the judgment defines for a law: '... Act, 2017 (‘the Act’)', '(hereinafter referred to as “CPC”)'.
_DEFINED_AS = re.compile(r"^[\s,]*(?:(?:18|19|20)\d\d)?\s*(?:\([IVXLC]+\s+of\s+\d{4}\)\s*)?\(\s*(?:hereinafter\s+"
                         r"(?:referred\s+to\s+as|called)\s+)?[“‘'\"]+\s*(?:the\s+)?([^”’'\"]{1,40}?)\s*[.]?[”’'\"]+\s*\)", re.I)
_NOT_A_LAW_AFTER = re.compile(r"^\s*(?:of|under|to|in)\s+(?:the\s+)?[A-Z]")   # "Article 1 of the Universal Declaration ..."
_SUBCLAUSE = re.compile(r"\s*\((?:[ivxl]{1,5}|[a-zA-Z]|\d{1,3})\)")


def roman(order: str) -> str:
    """CPC Orders are cited both ways ('Order 39' / 'Order XXXIX'): one label, in Roman numerals."""
    if not order.isdigit():
        return order.upper()
    number, out = int(order), ""
    for value, letters in ((50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while number >= value:
            out, number = out + letters, number - value
    return out


def last_law_in(title: str) -> str:
    """A title match can run over two laws joined by 'and the': keep the last one."""
    return re.split(r"\s+(?:and|&)\s+the\s+", title)[-1]


def _prep_provisions(sentence: str) -> str:
    """Drop sub-clauses ('302(b)' -> '302', '337-L (i), (ii), 506' -> '337-L, 506') and doubled separators."""
    # footnote numbers glued to a sub-clause: "Article 106(3)(c)4 of" -> "Article 106(3)(c) of" (else "Article 1064")
    text = re.sub(r"\)\d{1,2}(?=[\s,;.]|$)", ")", re.sub(r"\s+", " ", sentence))
    text = _SUBCLAUSE.sub("", text)
    return re.sub(r"(?:\s*(?:,|\band\b|&)\s*){2,}", " and ", text)


def provision_refs(sentence: str) -> List[Tuple[List[str], Optional[str], str]]:
    """Every provision reference in a sentence: (labels, act text or None, text after the reference).
    Act text is the law named right after the numbers; None means the law has to come from context."""
    text = _prep_provisions(sentence)
    refs = []
    for match in _ORDER_RULE.finditer(text):
        tail = _ACT_TAIL.match(text[match.end():])
        # Orders with Rules exist only in the Code of Civil Procedure among the laws cited here.
        act = tail.group(tail.lastgroup) if tail and not tail.group("short") else "C.P.C."
        refs.append(([f"Order {roman(match.group(1))} Rule {match.group(2).upper()}"], act.strip(" ,"), text[match.end():]))
    for match in _RULE.finditer(text):
        if re.search(r"Order\s+[IVXL\d]+\s*,?\s*$", text[:match.start()], re.I):
            continue                                    # already counted as "Order X Rule N"
        tail = _ACT_TAIL.match(text[match.end():])
        if tail and (tail.group("title") or tail.group("abbr")):   # a bare "Rule 3" is not linked
            refs.append(([f"Rule {match.group(1)}"], tail.group(tail.lastgroup), text[match.end():]))
    for match in _PROVISION.finditer(text):
        kind = "Article" if match.group(1).lower().startswith("art") else "Section"
        labels = [f"{kind} {n}{s.upper()}" for n, s in re.findall(r"(\d{1,4})\s*-?\s*([A-Z]{0,2})\b", match.group(2))]
        rest = text[match.end():]
        tail = _ACT_TAIL.match(rest)
        refs.append((labels, tail.group(tail.lastgroup) if tail else None, rest))
    return refs


_JUDGE_NOT_NAME = re.compile(r"\b(the|of|in|while|and|for|with|order|court|system|this|that|agreement|observation|"
                             r"opinion|notes?|majority|bench|present|as|under|well|paragraph|which|military|termed|also)\b", re.I)


def clean_judge(raw: str) -> Optional[str]:
    """Bench entry -> judge name, or None if it is page text ('i authority in the large interest of
    justice while'). Drops junk around the name: 'a H Mr. Justice X :' / 'Justice X = y' -> 'Justice X'."""
    text = re.sub(r"\s+", " ", raw)
    start = re.search(r"\bJustice\b", text, re.I)
    if start:
        text = text[start.start():]
    text = re.split(r"[^A-Za-z.,'\- ]", text)[0]                     # cut at digits / symbols
    text = re.sub(r",\s+[a-z].*$", "", text)                          # ", which highlight ..."
    text = re.sub(r"(?:\s+[A-Za-z])+\s*$", "", text.strip(" ,.-"))     # trailing OCR letters: 'Ibrahim S'
    text = re.sub(r"(?:\s+[a-z]+)+\s*$", "", text)                     # trailing lower-case OCR junk: 'Khan eee'
    text = re.sub(r"^(?:Mr|Mrs|Ms)\.?\s+", "", text).strip(" ,.-")
    if not 2 <= len(norm_name(text).split()) <= 6 or _JUDGE_NOT_NAME.search(re.sub(r"(?i)^justice\s+", "", text)):
        return None
    return text


_AUTHOR = re.compile(r"\b([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){1,5}),\s*(?:CJ|J)\s*[.:\-—]")
_SIGNATURE = re.compile(r"\(\s*([A-Z][A-Za-z.\- ]{5,50}?)\s*\)\s*(?:Judge|JUDGE)\b")


def bench_of(doc: Dict) -> List[str]:
    """Clean bench names; if the bench line was unreadable, add the author ('NAME, J.') and the
    signature ('(NAME) Judge') found in the text."""
    raw = [b for b in doc.get("bench", []) if b and b.strip()]
    names = [n for n in (clean_judge(b) for b in raw) if n]
    if len(names) < len(raw) or not names:
        paragraphs = doc.get("paragraphs", [])
        found = [m.group(1) for p in paragraphs[:3] for m in _AUTHOR.finditer(p["text"])]
        found += [m.group(1) for p in paragraphs[-3:] for m in _SIGNATURE.finditer(p["text"])]
        for name in found:
            name = clean_judge(name.title() if name.isupper() else name)
            if name and all(norm_name(name) != norm_name(n) for n in names):
                names.append(name)
    return names


# ----------------------------------------------------------------------------- build
def build() -> Graph:
    graph = Graph()
    statutes = {p.stem: load_json(p) for p in sorted((STRUCTURED / "statute").glob("*.json"))}
    statutes = {k: v for k, v in statutes.items() if v.get("language") != "Urdu"}
    resolve_act = _act_resolver(statutes)
    section_index = {}
    for doc_id, doc in statutes.items():
        graph.node("Act", doc_id, name=doc["act_name"], year=doc.get("year"), in_corpus=True)
        for chapter in doc["chapters"]:
            for sec in chapter["sections"]:
                sid = f"{doc_id}::{sec['section_number']}"
                section_index[sid] = sec
                graph.node("Section", sid, label=sec["section_number"], title=sec["title"], page=sec.get("page_start"),
                           act=doc["act_name"], in_corpus=True)
                graph.edge("PART_OF", sid, doc_id)

    judgments = [load_json(p) for p in sorted((STRUCTURED / "judgment").glob("*.json"))]
    # Corpus cases: one Case node per legal matter (several PDFs can share one).
    key_of_doc, by_case_key, by_neutral = {}, defaultdict(set), {}
    for doc in judgments:
        key = case_key(doc["case_number"]) or doc.get("matter_id") or doc["document_id"]
        key = f"{'SC' if doc['court'].startswith('Supreme') else 'LHC'}:{key}"
        key_of_doc[doc["document_id"]] = key
        by_case_key[key.split(":", 1)[1]].add(key)
        if doc["document_id"].startswith("LHC_"):
            by_neutral[norm_citation(re.sub(r"^LHC_(\d{4})LHC(\d+)$", r"\1 LHC \2", doc["document_id"]))] = key
        display = doc["case_number"] if doc["case_number"] != "Unknown" else doc["document_id"]
        graph.node("Case", key, name=display, case_number=doc["case_number"], court=doc["court"], year=doc.get("year"),
                   document_id=doc["document_id"], outcome=doc.get("outcome"), in_corpus=True)
        graph.node("Court", doc["court"])
        graph.edge("DECIDED_BY", key, doc["court"])
        for judge in bench_of(doc):
            jid = norm_name(judge)
            if jid:
                graph.node("Judge", jid, name=judge)
                graph.edge("SAT_ON", jid, key)
        for role, name in (("petitioner_or_appellant", doc["parties"]["appellant_or_petitioner"]),
                           ("respondent", doc["parties"]["respondent"])):
            pid = norm_name(name)
            if name != "Unknown" and 2 <= len(pid) <= 120:
                graph.node("Party", pid, name=name)
                graph.edge("HAS_PARTY", key, pid, dedupe=(role,), role=role)

    unresolved = Counter()
    same_case: List[Tuple[str, str]] = []   # pairs of citations of one judgment ("X = Y")
    corpus_keys = set(key_of_doc.values())
    for doc in judgments:
        source = key_of_doc[doc["document_id"]]
        own_numbers = {n for n in re.findall(r"\d{2,6}", doc["case_number"] + " " + doc["document_id"])
                       if not re.fullmatch(r"(19|20)\d\d", n)}
        defined, last_of_type = {}, {}      # this judgment's names for laws: "the Code", "the Act", "CPC"
        for paragraph in doc["paragraphs"]:
            paragraph_act = {}              # last law named in this paragraph, per "Section" / "Article"
            for sentence in split_sentences(paragraph["text"]):
                evidence = {"document_id": doc["document_id"], "paragraph": paragraph.get("number") or "",
                            "page": paragraph.get("page") or "", "sentence": sentence[:400]}
                treatment = next((kind for kind, cue in _CUES if cue.search(sentence)), "CITES")

                # Short names defined for a law anywhere in the text: '... Act, 2010 (hereinafter "the Act")'.
                for title in _TITLE_RE.finditer(sentence):
                    definition = _DEFINED_AS.match(sentence[title.end():])
                    if definition:
                        name = last_law_in(title.group(0))   # "the Constitution and the Elections Act" -> "Elections Act"
                        act = resolve_act(name)
                        defined[_alias_key(definition.group(1))] = defined[definition.group(1).strip().lower()] = act
                        last_of_type[name.split()[-1].lower()] = act

                # Case -> Case
                targets = []
                same_case.extend(equivalent_citations(sentence))
                for raw_citation in citations_in(sentence):
                    cit = norm_citation(raw_citation)
                    targets.append(by_neutral.get(cit) or graph.node("Case", f"CIT:{cit}", name=cit, citation=cit, in_corpus=False))
                for match in _CASE_NO.finditer(sentence):
                    ck = case_key(match.group(1))
                    if not ck or own_numbers & set(re.findall(r"\d{2,6}", match.group(1))):
                        continue  # the judgment's own (or connected) case numbers are not citations
                    hits = by_case_key.get(ck, set())
                    target = next(iter(hits)) if len(hits) == 1 else graph.node(
                        "Case", f"NUM:{ck}", name=match.group(1).strip(), case_number=match.group(1).strip(), in_corpus=False)
                    # A bare case number is usually the same litigation (connected petitions, the order
                    # under appeal), not a precedent; precedents are cited by reporter / neutral citation.
                    if target in corpus_keys and treatment != "CITES":
                        targets.append(target)
                    else:
                        graph.edge("RELATED_MATTER", source, target, dedupe=(evidence["paragraph"],), method="regex",
                                   kind="appeal_history" if _APPEAL.search(sentence) else "mentioned", **evidence)
                for target in targets:
                    if target != source:
                        graph.edge(treatment, source, target, dedupe=(evidence["paragraph"],),
                                   needs_check=treatment in ("OVERRULES", "DISTINGUISHES"), method="regex", **evidence)

                # Case -> Section
                for labels, act_text, rest in provision_refs(sentence):
                    family = labels[0].split()[0]
                    act, from_context = None, False
                    if act_text:
                        short = re.fullmatch(r"(?:the\s+)?(Code|Act|Ordinance|Order|Rules)", act_text, re.I)
                        if short:   # "of the Code": the law this judgment calls "the Code"
                            act = defined.get(short.group(1).lower()) or last_of_type.get(short.group(1).lower())
                            from_context = True
                        else:
                            act_text = last_law_in(act_text)
                            act = defined.get(_alias_key(act_text)) or resolve_act(act_text)
                            last_of_type[act[1].split()[-1].lower().rstrip(",")] = act
                            after = rest[rest.find(act_text) + len(act_text):] if act_text in rest else ""
                            definition = _DEFINED_AS.match(after)
                            if definition:
                                defined[_alias_key(definition.group(1))] = act
                                defined[definition.group(1).strip().lower()] = act
                    elif not _NOT_A_LAW_AFTER.match(rest):
                        # "Section 12 further explains ...": the law named last in this paragraph
                        act, from_context = paragraph_act.get(family), True
                    if not act:
                        unresolved["law not named or not found"] += 1
                        continue
                    paragraph_act[family] = act
                    act_id, act_name, in_corpus = act
                    if not in_corpus:
                        graph.node("Act", act_id, name=act_name, in_corpus=False)
                    elif act_id.startswith("PKCODE_URDU_"):
                        graph.node("Act", act_id, name=act_name, in_corpus=True, language="Urdu (OCR pages, no sections)")
                    for label in labels:
                        sid = f"{act_id}::{label}"
                        if sid not in section_index:
                            graph.node("Section", sid, label=label, act=act_name, in_corpus=False)
                            graph.edge("PART_OF", sid, act_id)
                            unresolved["section not in corpus act" if in_corpus else "act not in corpus"] += 1
                        kind = "INTERPRETS" if _INTERPRETS.search(sentence) else "REFERS_TO"
                        graph.edge(kind, source, sid, dedupe=(evidence["paragraph"],), needs_check=kind == "INTERPRETS",
                                   method="regex+context" if from_context else "regex", **evidence)

    for doc in (load_json(p) for p in sorted((STRUCTURED / "contract").glob("*.json"))):
        graph.node("Contract", doc["document_id"], title=doc["contract_title"], type=doc["contract_type"])
        for clause in doc["clauses"]:
            cid = f"{doc['document_id']}::{clause['clause_id']}"
            graph.node("Clause", cid, clause_id=clause["clause_id"], title=clause["clause_title"])
            graph.edge("PART_OF", cid, doc["document_id"])
    # Entity resolution for precedents: citations written as "X = Y" are one judgment. Union-find over
    # the pairs; each group keeps the citation cited most often (its other citations become aliases).
    parent: Dict[str, str] = {}
    find = lambda k: k if parent.setdefault(k, k) == k else find(parent[k])
    for a, b in same_case:
        if a != b:
            parent[find(f"CIT:{a}")] = find(f"CIT:{b}")
    cited = Counter(e["dst"] for kind in ("CITES", "FOLLOWS", "DISTINGUISHES", "OVERRULES") for e in graph.edges[kind].values())
    groups = defaultdict(list)
    for key in parent:
        if key in graph.nodes["Case"]:
            groups[find(key)].append(key)
    mapping = {}
    for members in groups.values():
        keep = max(members, key=lambda k: (cited[k], k))
        mapping.update({k: keep for k in members})
    graph.merge("Case", mapping, ("CITES", "FOLLOWS", "DISTINGUISHES", "OVERRULES"))

    sat_on = Counter(edge["src"] for edge in graph.edges["SAT_ON"].values())
    graph.merge("Judge", judge_variants(sorted(graph.nodes["Judge"], key=lambda k: (-sat_on[k], k))), ("SAT_ON",))
    graph.unresolved = unresolved
    return graph


def write(graph: Graph) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for label, nodes in graph.nodes.items():
        fields = sorted({k for props in nodes.values() for k in props}, key=lambda k: (k != "key", k))
        with (OUT / f"nodes_{label.lower()}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(nodes.values())
    for kind, edges in graph.edges.items():
        fields = sorted({k for props in edges.values() for k in props}, key=lambda k: (k not in ("src", "dst"), k))
        with (OUT / f"edges_{kind.lower()}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(edges.values())


def report(graph: Graph) -> str:
    cases = graph.nodes["Case"]
    corpus_cases = {k for k, v in cases.items() if v.get("in_corpus")}
    case_edges = [e for kind in ("CITES", "FOLLOWS", "DISTINGUISHES", "OVERRULES") for e in graph.edges[kind].values()]
    related = list(graph.edges["RELATED_MATTER"].values())
    internal = [e for e in case_edges if e["dst"] in corpus_cases]
    cited = Counter(e["dst"] for e in case_edges)
    sections = Counter(e["dst"] for kind in ("REFERS_TO", "INTERPRETS") for e in graph.edges[kind].values())
    node_rows = "\n".join(f"| {label} | {len(nodes)} |" for label, nodes in sorted(graph.nodes.items()))
    edge_rows = "\n".join(f"| {kind} | {len(edges)} | {sum(1 for e in edges.values() if e.get('needs_check'))} |"
                          for kind, edges in sorted(graph.edges.items()))
    top_cases = "\n".join(f"| {cases[k].get('citation') or cases[k].get('case_number') or k} | {n} |" for k, n in cited.most_common(8))
    top_sections = "\n".join(f"| {graph.nodes['Section'][k].get('act')} | {graph.nodes['Section'][k].get('label')} | {n} |"
                             for k, n in sections.most_common(10))
    overrules = "\n".join(f"| {cases[e['src']].get('case_number', e['src'])} | {cases[e['dst']].get('citation') or cases[e['dst']].get('case_number') or e['dst']} | "
                          f"{e['sentence'][:160].replace('|', '/')} |" for e in graph.edges["OVERRULES"].values())
    return f"""# Knowledge graph extraction (regex, Day 3)

Built by `src/graph/regex_extract.py` from the structured corpus; schema in `docs/graph_schema.md`.
CSV files for Neo4j in `data/graph/`. Relationship types come from cue words in the citing
sentence; those marked "needs check" (OVERRULES, DISTINGUISHES, INTERPRETS) are candidates for the
LLM step and have not been verified. Precision / recall have not been measured yet.

## Nodes

| Label | Count |
|---|---:|
{node_rows}

## Relationships

| Type | Count | Needs check |
|---|---:|---:|
{edge_rows}

Precedent links (reporter / neutral citations): {len(case_edges)}, of which {len(internal)} point to another
judgment in the corpus. Same-litigation links (bare case numbers): {len(related)}
({sum(1 for e in related if e.get("kind") == "appeal_history")} appeal history).
(most cited cases are reported judgments outside the corpus and become `in_corpus=false` nodes).
Statute references not linked to a corpus section: {dict(graph.unresolved)}.

## Most cited precedents

| Case | Cited by (paragraphs) |
|---|---:|
{top_cases}

## Most referenced provisions

| Act | Provision | References |
|---|---|---:|
{top_sections}

## OVERRULES candidates (to be checked)

| Citing case | Cited case | Sentence |
|---|---|---|
{overrules}
"""


if __name__ == "__main__":
    g = build()
    write(g)
    REPORT.write_text(report(g), encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8")[:4000])
