"""
Shared entity resolution for laws: one short name per law, whatever the spelling.

Used by the extraction evaluation (to compare the extractor's Act nodes with the answer key) and by
GraphRAG (to link "Qanun-e-Shahadat", "QSO" or "the Pakistan Penal Code" in a question to Act nodes).
"""

import re
from typing import List, Tuple

# Act node (key + name) or text from a question, lower case -> canonical law name. First match wins.
ACT_PATTERNS: List[Tuple[str, str]] = [
    ("constitution", r"real_stat_001|constitution|\baain\b|\bdastoor"),
    ("indian-penal-code", r"indian.penal"),
    ("banking-companies-ordinance", r"banking.companies"),
    ("ppc", r"pklaw_010|penal code|\bppc\b|p\.p\.c"),
    ("crpc", r"criminal procedure|criminal-procedure|cr\.?\s?p\.?\s?c"),
    ("cpc", r"pklaw_008|civil procedure|\bc\.?\s?p\.?\s?c\b"),
    ("qso", r"shahadat|\bq\.?s\.?o\b"),
    ("contract-act", r"pklaw_012|contract act"),
    ("mflo", r"pklaw_009|muslim family law"),
    ("family-courts-act", r"family.courts"),
    ("elections-act", r"elections?.act"),
    ("customs-act", r"customs"),
    ("sales-tax-act", r"sales.tax"),
    ("ata", r"pklaw_011|anti.?terrorism|\bata\b"),
    ("companies-ordinance", r"companies.ordinance"),
    ("companies-act", r"companies.act"),
    ("limitation-act", r"limitation"),
    ("police-rules", r"police.rules"),
    ("transfer-of-property-act", r"transfer.of.property"),
    ("harassment-act", r"harassment"),
    ("indian-evidence-act", r"indian.evidence"),
    ("sc-practice-procedure-act", r"pkcode_urdu_021|practice.{1,5}procedure"),
    ("specific-relief-act", r"specific.relief"),
    ("bharatiya-nyaya-sanhita", r"nyaya"),
    ("bharatiya-sakshya-adhiniyam", r"sakshya"),
    ("udhr", r"universal declaration|udhr"),
    ("iccpr", r"civil.{1,5}political|iccpr"),
    ("icescr", r"economic|icescr"),
]


def canonical_act(key: str, name: str = "") -> str:
    text = f"{key} {name}".lower()
    for act, pattern in ACT_PATTERNS:
        if re.search(pattern, text):
            return act
    return key


def acts_named_in(text: str) -> List[str]:
    """Canonical names of every law mentioned anywhere in a text, in order of first mention."""
    low = text.lower()
    found = sorted((m.start(), act) for act, pattern in ACT_PATTERNS for m in [re.search(pattern, low)] if m)
    return list(dict.fromkeys(act for _, act in found))
