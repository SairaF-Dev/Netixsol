"""
Day 2, Task 1: build the 100-question RAG evaluation set.

    50 statute questions   gold = Act + Section (+ page)
    30 case-law questions  gold = judgment (document / matter id, case number) + paragraph (+ page)
    20 no-answer questions gold = none; the system must answer "No sufficient source found"

How a question is made (drafted by an LLM, checked by code, then reviewed by a person):

1. Sources are sampled from the structured corpus (data/structured) with a fixed seed:
   statute sections spread over the Acts, and judgment paragraphs (holdings and
   reasoning paragraphs) from Supreme Court and Lahore High Court judgments.
2. Gemini reads ONLY that section / paragraph and writes a question, a short
   expected answer and a verbatim supporting quote. The question language
   (English / Roman Urdu / Urdu) and whether the section number may be named are
   fixed in advance so the set has a known mix.
3. Code check: the quote must appear in the source text (whitespace-normalised);
   otherwise the draft is rejected and the next candidate source is used.
4. No-answer questions: Gemini proposes questions about Pakistani law that is NOT
   in the corpus (it is given every Act title in the corpus, English and Urdu).
   Each candidate is searched with the hybrid index; a judge model reads the top
   5 chunks and the candidate is kept only if none of them answers it.
5. Output: evaluations/rag_eval_set.jsonl (used by the evaluation code) and
   evaluations/rag_eval_set_review.csv for the human review. A row is used as
   gold only after a person marks it ok.

The example question from the brief ("Agar consideration unlawful ho to kya
contract void hai?" -> Contract Act s. 23) is added by hand as STAT_001.

Run:  python -m evaluations.build_eval_set                  (draft + checks, writes jsonl and review csv)
      python -m evaluations.build_eval_set --apply-review   (after filling the status column)
"""

import csv
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.llm.gemini_client import GeminiClient
from src.utils.file_utils import load_json
from src.utils.logger import setup_logger

logger = setup_logger("build_eval_set")

SEED = 12
STRUCTURED = Path("data/structured")
OUT_JSONL = Path("evaluations/rag_eval_set.jsonl")
OUT_REVIEW = Path("evaluations/rag_eval_set_review.csv")

# How many statute questions per Act (sums to 49; +1 hand-written example = 50).
STATUTE_QUOTA = {
    "PKLAW_012": 9,       # Contract Act, 1872
    "PKLAW_010": 10,      # Pakistan Penal Code
    "REAL_STAT_001": 8,   # Constitution
    "PKLAW_008": 6,       # Code of Civil Procedure
    "PKLAW_004": 4,       # Income Tax Ordinance
    "PKLAW_011": 3,       # Anti-Terrorism Act
    "PKLAW_009": 3,       # Muslim Family Laws Ordinance
    "PKLAW_001": 2,       # Anti-Money Laundering Act
    "PKLAW_007": 2,       # Civil Servants Act
    "PKLAW_003": 1,       # Federal Board of Revenue Act
    "PKLAW_005": 1,       # National Command Authority Act
}
CASE_QUOTA = {"Supreme Court of Pakistan": 20, "Lahore High Court": 10}
NO_ANSWER_COUNT = 20

# Question language mix (cycled in a fixed shuffled order) and share naming the section.
LANGUAGES = ["English"] * 10 + ["Roman Urdu"] * 7 + ["Urdu"] * 3
NAME_SECTION_SHARE = 0.3

NO_SOURCE = "No sufficient source found"


# --------------------------------------------------------------------------- LLM schemas
class DraftQA(BaseModel):
    question: str = Field(description="The question a lawyer or client would ask")
    expected_answer: str = Field(description="Short correct answer, 1-2 sentences, based only on the source")
    quote: str = Field(description="One sentence or clause copied EXACTLY, character for character, from the source")


class NoAnswerCandidates(BaseModel):
    questions: List[str]


class JudgeVerdict(BaseModel):
    answered: bool = Field(description="True if any passage contains the information needed to answer the question")
    reason: str


# --------------------------------------------------------------------------- helpers
def _norm(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_in_source(quote: str, source: str) -> bool:
    quote = _norm(quote).strip(" .;,\"'")
    return len(quote.split()) >= 5 and quote in _norm(source)


def _statute_units(doc_id: str) -> List[Dict]:
    doc = load_json(STRUCTURED / "statute" / f"{doc_id}.json")
    units = []
    for chapter in doc["chapters"]:
        for sec in chapter["sections"]:
            label = sec["section_number"]
            if not re.match(r"(Section|Article) \d+[A-Z]*$", label):
                continue  # main sections/articles only (no Order rules or schedule items)
            text = " ".join([sec["content"]] + sec["subsections"]).strip()
            words = len(text.split())
            if words < 35 or words > 700 or re.search(r"\[?(omitted|repealed)\]?", sec["title"], re.I):
                continue
            units.append({"document_id": doc_id, "act": doc["act_name"], "section": label,
                          "title": sec["title"], "page": sec["page_start"], "text": text})
    return units


def _judgment_units(court: str) -> List[Dict]:
    units = []
    for path in sorted((STRUCTURED / "judgment").glob("*.json")):
        doc = load_json(path)
        if doc["court"] != court or doc["case_number"] == "Unknown" or len(doc["paragraphs"]) < 3:
            continue
        paragraphs = [p for p in doc["paragraphs"] if p["number"] and 60 <= len(p["text"].split()) <= 450]
        if not paragraphs:
            continue
        units.append({"doc": doc, "paragraphs": paragraphs})
    return units


def _prompt_statute(unit: Dict, language: str, name_section: bool) -> str:
    naming = (f"Mention the Act and '{unit['section']}' in the question." if name_section else
              "Do NOT mention the section number in the question; describe the legal situation instead.")
    return f"""You are preparing an evaluation set for a Pakistani legal research assistant.

Source: {unit['act']}, {unit['section']} ({unit['title']})
---
{unit['text'][:4000]}
---

Write ONE realistic question that a lawyer or client could ask and that this provision answers.
- Language of the question: {language}{' (Urdu script)' if language == 'Urdu' else ''}{' (Urdu written in Latin letters, the way people type on WhatsApp, legal terms may stay in English)' if language == 'Roman Urdu' else ''}.
- {naming}
- The question must be answerable from this provision alone; do not ask about anything it does not say.
- expected_answer: 1-2 sentences in English, faithful to the text.
- quote: copy one sentence or clause (at least 8 words) EXACTLY from the source text above."""


def _prompt_case(doc: Dict, paragraph: Dict, language: str) -> str:
    parties = f"{doc['parties']['appellant_or_petitioner']} v. {doc['parties']['respondent']}"
    return f"""You are preparing an evaluation set for a Pakistani legal research assistant.

Source: {doc['court']}, {doc['case_number']} ({parties}), paragraph {paragraph['number']}
---
{paragraph['text'][:4000]}
---

Write ONE realistic case-law research question that this paragraph answers.
- Language of the question: {language}{' (Urdu script)' if language == 'Urdu' else ''}{' (Urdu in Latin letters, legal terms may stay in English)' if language == 'Roman Urdu' else ''}.
- Ask about the court's reasoning or holding on the legal point, e.g. "What did the {doc['court']} hold about ...".
  Include enough facts or legal context that this case can be told apart from others,
  but do NOT give the case number or party names.
- expected_answer: 1-2 sentences in English, faithful to the paragraph.
- quote: copy one sentence or clause (at least 8 words) EXACTLY from the paragraph above."""


# --------------------------------------------------------------------------- builders
def build_statute_questions(llm: GeminiClient, rng: random.Random, languages: List[str]) -> List[Dict]:
    items = []
    for doc_id, quota in STATUTE_QUOTA.items():
        units = _statute_units(doc_id)
        if doc_id == "PKLAW_012":  # s. 23 is the hand-written example
            units = [u for u in units if u["section"] != "Section 23"]
        rng.shuffle(units)
        made = 0
        for unit in units:
            if made == quota:
                break
            language = languages[len(items) % len(languages)]
            name_section = rng.random() < NAME_SECTION_SHARE
            try:
                draft = llm.generate_json(_prompt_statute(unit, language, name_section), DraftQA)
            except Exception as exc:
                logger.warning("Draft failed for %s %s: %s", doc_id, unit["section"], exc)
                continue
            if not quote_in_source(draft.quote, unit["text"]):
                logger.info("Rejected %s %s: quote not found in source", doc_id, unit["section"])
                continue
            items.append({
                "type": "statute", "language": language, "names_section": name_section,
                "question": draft.question, "expected_answer": draft.expected_answer,
                "gold": [{"document_id": doc_id, "act": unit["act"], "section": unit["section"],
                          "section_title": unit["title"], "page": unit["page"]}],
                "quote": draft.quote,
            })
            made += 1
        logger.info("%s: %d/%d statute questions", doc_id, made, quota)
    return items


def build_case_questions(llm: GeminiClient, rng: random.Random, languages: List[str]) -> List[Dict]:
    items = []
    for court, quota in CASE_QUOTA.items():
        units = _judgment_units(court)
        rng.shuffle(units)
        used_matters = set()
        made = 0
        for unit in units:
            if made == quota:
                break
            doc = unit["doc"]
            if doc["matter_id"] in used_matters:
                continue  # one question per legal matter
            # Alternate between the holding paragraph and a reasoning paragraph.
            paragraph = unit["paragraphs"][-1] if made % 2 == 0 else rng.choice(unit["paragraphs"][:-1] or unit["paragraphs"])
            language = languages[(len(items) + 3) % len(languages)]
            try:
                draft = llm.generate_json(_prompt_case(doc, paragraph, language), DraftQA)
            except Exception as exc:
                logger.warning("Draft failed for %s: %s", doc["document_id"], exc)
                continue
            if not quote_in_source(draft.quote, paragraph["text"]):
                logger.info("Rejected %s para %s: quote not found", doc["document_id"], paragraph["number"])
                continue
            used_matters.add(doc["matter_id"])
            items.append({
                "type": "case_law", "language": language, "names_section": False,
                "question": draft.question, "expected_answer": draft.expected_answer,
                "gold": [{"document_id": doc["document_id"], "matter_id": doc["matter_id"], "court": court,
                          "case_number": doc["case_number"], "paragraph": paragraph["number"],
                          "page": paragraph["page"]}],
                "quote": draft.quote,
            })
            made += 1
        logger.info("%s: %d/%d case-law questions", court, made, quota)
    return items


def _corpus_act_names(inventory) -> List[str]:
    """Short names of every Act in the corpus, e.g. 'Contract Act', 'Limitation Act', 'Penal Code'."""
    names = set()
    for title in inventory[inventory["type"] == "Statute"]["title"].astype(str):
        core = re.split(r",|\(", title)[0].strip()          # "Pakistan Penal Code, 1860" -> "Pakistan Penal Code"
        names.add(re.sub(r"^(The|Pakistan)\s+", "", core))  # -> "Penal Code"
    urdu = Path("data/urdu_law_english_titles.csv")
    if urdu.exists():
        with urdu.open(encoding="utf-8") as handle:
            names.update(row["match_key"] for row in csv.DictReader(handle))
    names.update({"PPC", "CPC", "Penal Code", "Civil Procedure"})
    return sorted(names, key=len, reverse=True)


def _corpus_suffixed_sections() -> set:
    """Section numbers with a letter (e.g. '489F', '337Q') that exist in the English statutes."""
    found = set()
    for path in (STRUCTURED / "statute").glob("*.json"):
        doc = load_json(path)
        for chapter in doc["chapters"]:
            for sec in chapter["sections"]:
                match = re.fullmatch(r"(?:Section|Article) (\d{2,3}[A-Z])", sec["section_number"])
                if match:
                    found.add(match.group(1))
    return found


def build_no_answer_questions(llm: GeminiClient, judge: GeminiClient, languages: List[str]) -> List[Dict]:
    from src.indexing.bm25_index import LegalBM25Index
    from src.indexing.hybrid_search import HybridLegalSearchEngine
    from src.indexing.vector_store import DenseVectorStore
    import pandas as pd

    inventory = pd.read_csv("inventory.csv")
    titles = sorted(set(inventory[inventory["type"].isin(["Statute", "Scanned/Urdu"])]["title"].astype(str)))
    prompt = f"""A Pakistani legal research assistant has ONLY these statutes in its library
(plus about 225 Supreme Court / Lahore High Court judgments and some US commercial contracts):
{chr(10).join('- ' + t for t in titles)}

Write 40 realistic questions about Pakistani law whose answer is NOT in any of these statutes,
e.g. about other Acts (company law, sales tax, rent, property transfer, cheques, traffic, cyber crime,
consumer protection, labour, banking, elections), procedural fees or current figures.
Avoid anything a general criminal, contract, constitutional, civil-procedure, income-tax, family,
terrorism or money-laundering provision could answer. Mix English and Roman Urdu. One question per item."""
    candidates = llm.generate_json(prompt, NoAnswerCandidates, temperature=0.7).questions

    engine = HybridLegalSearchEngine(LegalBM25Index.load("data/indices/bm25_legal.pkl"),
                                     DenseVectorStore.load("data/indices/vstore_legal.sqlite3"))
    corpus_names = _corpus_act_names(inventory)
    corpus_sections = _corpus_suffixed_sections()
    items = []
    for question in candidates:
        if len(items) == NO_ANSWER_COUNT:
            break
        # Code checks first (the small judge model missed both of these cases):
        named = next((name for name in corpus_names if name.lower() in question.lower()), None)
        if named:
            logger.info("Rejected no-answer candidate (names corpus Act '%s'): %s", named, question)
            continue
        cited = {f"{n}{s.upper()}" for n, s in re.findall(r"\b(\d{2,3})-?([A-Za-z])\b", question)} & corpus_sections
        if cited:
            logger.info("Rejected no-answer candidate (cites corpus section %s): %s", sorted(cited), question)
            continue
        results = engine.search(question, top_k=5)
        passages = "\n\n".join(f"[{i + 1}] {r['content'][:1200]}" for i, r in enumerate(results))
        verdict = judge.generate_json(
            f"""Question: {question}

Passages retrieved from the library:
{passages}

Does ANY passage contain the specific legal information needed to answer the question
(the rule, section, figure or holding asked about)? Related topics do not count.""",
            JudgeVerdict, temperature=0.0)
        if verdict.answered:
            logger.info("Rejected no-answer candidate (answerable): %s", question)
            continue
        items.append({
            "type": "no_answer", "language": "Roman Urdu" if re.search(r"\b(kya|hai|ka|ki|ke|mein|agar)\b", question, re.I) else "English",
            "names_section": False, "question": question, "expected_answer": NO_SOURCE,
            "gold": [], "quote": "", "check": f"top-5 hybrid results judged not to answer: {verdict.reason}",
        })
    logger.info("No-answer: %d kept of %d candidates", len(items), len(candidates))
    return items


def example_item() -> Dict:
    units = {u["section"]: u for u in _statute_units("PKLAW_012")}
    s23 = units["Section 23"]
    return {
        "type": "statute", "language": "Roman Urdu", "names_section": False,
        "question": "Agar consideration unlawful ho to kya contract void hai?",
        "expected_answer": "Yes. Under Section 23 of the Contract Act, 1872, every agreement of which the "
                           "object or consideration is unlawful is void.",
        "gold": [{"document_id": "PKLAW_012", "act": s23["act"], "section": "Section 23",
                  "section_title": s23["title"], "page": s23["page"]}],
        "quote": "Every agreement of which the object or consideration is unlawful is void.",
        "source": "example from the brief, written by hand",
    }


def build(seed: int = SEED) -> List[Dict]:
    rng = random.Random(seed)
    languages = LANGUAGES[:]
    rng.shuffle(languages)
    llm, judge = GeminiClient(), GeminiClient.judge()

    items = [example_item()]
    items += build_statute_questions(llm, rng, languages)
    items += build_case_questions(llm, rng, languages)
    items += build_no_answer_questions(llm, judge, languages)

    prefixes = {"statute": "STAT", "case_law": "CASE", "no_answer": "NOANS"}
    counters: Dict[str, int] = {}
    for item in items:
        counters[item["type"]] = counters.get(item["type"], 0) + 1
        item["id"] = f"{prefixes[item['type']]}_{counters[item['type']]:03d}"
        item.setdefault("source", "drafted by Gemini from the gold source, checked by code")
        item["reviewed"] = False

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps({"id": item.pop("id"), **item}, ensure_ascii=False) + "\n")
    write_review_csv(OUT_JSONL, OUT_REVIEW)
    logger.info("Wrote %d questions to %s (%s); LLM calls %d + judge %d",
                len(items), OUT_JSONL, counters, llm.calls, judge.calls)
    return items


def write_review_csv(jsonl_path: Path, csv_path: Path) -> None:
    """One row per question for a person to mark: status = ok / fix / drop."""
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    hints_path = Path("evaluations/rag_eval_review_hints.json")  # notes from a first pass over the drafts
    hints = json.loads(hints_path.read_text(encoding="utf-8")) if hints_path.exists() else {}
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "type", "language", "question", "expected_answer", "gold_source", "quote",
                         "check_note", "status", "your_note"])
        for row in rows:
            gold = "; ".join(
                f"{g.get('act') or g.get('court')} | {g.get('section') or g.get('case_number')}"
                + (f" | para {g['paragraph']}" if g.get("paragraph") else "") + f" | p.{g.get('page')}"
                for g in row["gold"]) or NO_SOURCE
            writer.writerow([row["id"], row["type"], row["language"], row["question"], row["expected_answer"],
                             gold, row["quote"], hints.get(row["id"], ""),
                             "ok" if row.get("reviewed") else "", row.get("review_note", "")])


OUT_DROPPED = Path("evaluations/rag_eval_set_dropped.jsonl")
TARGET = {"statute": 50, "case_law": 30, "no_answer": 20}
_COUNSEL = re.compile(r"\b(learned counsel|contended|argued|submitted that|it was urged)\b", re.I)


def _prompt_case_strict(doc: Dict, paragraph: Dict, language: str) -> str:
    """Stricter case prompt used for top-up (lessons from the first review)."""
    return _prompt_case(doc, paragraph, language) + """
- The question MUST include at least one concrete fact from this paragraph (an amount, a date, a place,
  a profession, a statute section, a specific relief) so that only this case answers it.
- Ask only about what the COURT decided or held, never about what a party or counsel argued.
- expected_answer must not add anything that is not in the paragraph."""


def _jsonl(path: Path) -> List[Dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def _corpus_text_lower() -> str:
    parts = []
    for path in STRUCTURED.glob("*/*.json"):
        doc = load_json(path)
        if doc.get("language") == "Urdu":
            continue
        for chapter in doc.get("chapters", []):
            parts += [s["content"] + " " + " ".join(s["subsections"]) for s in chapter["sections"]]
        parts += [p["text"] for p in doc.get("paragraphs", [])] + [c["text"] for c in doc.get("clauses", [])]
    return " ".join(parts).lower()


def top_up(seed: int = SEED + 1) -> Dict[str, int]:
    """Add new drafts until the set is back to 50 / 30 / 20, avoiding sources already used or dropped.
    New items are unreviewed and appear in the review CSV."""
    import pandas as pd

    current, dropped = _jsonl(OUT_JSONL), _jsonl(OUT_DROPPED)
    seen = current + dropped
    need = {kind: TARGET[kind] - sum(1 for i in current if i["type"] == kind) for kind in TARGET}
    logger.info("Top-up needed: %s", need)
    rng = random.Random(seed)
    languages = LANGUAGES[:]
    rng.shuffle(languages)
    llm = GeminiClient()
    used_units = {(g["document_id"], g.get("section") or g.get("paragraph")) for i in seen for g in i["gold"]}
    used_matters = {g.get("matter_id") for i in seen for g in i["gold"] if g.get("matter_id")}
    new: List[Dict] = []

    # Statutes: Contract Act and Penal Code only (the Constitution PDF is the 2012 edition).
    for doc_id in ("PKLAW_012", "PKLAW_010"):
        units = [u for u in _statute_units(doc_id) if (doc_id, u["section"]) not in used_units]
        rng.shuffle(units)
        for unit in units:
            if need["statute"] <= 0:
                break
            language = languages[len(new) % len(languages)]
            draft = llm.generate_json(_prompt_statute(unit, language, False), DraftQA)
            if quote_in_source(draft.quote, unit["text"]):
                new.append({"type": "statute", "language": language, "names_section": False,
                            "question": draft.question, "expected_answer": draft.expected_answer,
                            "gold": [{"document_id": doc_id, "act": unit["act"], "section": unit["section"],
                                      "section_title": unit["title"], "page": unit["page"]}], "quote": draft.quote})
                need["statute"] -= 1

    # Case law: per court, holding paragraphs first, no counsel-argument paragraphs.
    for court in CASE_QUOTA:
        have = sum(1 for i in current if i["type"] == "case_law" and i["gold"][0]["court"] == court)
        missing = CASE_QUOTA[court] - have
        units = _judgment_units(court)
        rng.shuffle(units)
        for unit in units:
            if missing <= 0:
                break
            doc = unit["doc"]
            if doc["matter_id"] in used_matters:
                continue
            candidates = [p for p in unit["paragraphs"] if len(p["text"].split()) >= 80 and not _COUNSEL.search(p["text"][:300])]
            if not candidates:
                continue
            paragraph = candidates[-1]
            language = languages[(len(new) + 3) % len(languages)]
            draft = llm.generate_json(_prompt_case_strict(doc, paragraph, language), DraftQA)
            if not quote_in_source(draft.quote, paragraph["text"]):
                continue
            used_matters.add(doc["matter_id"])
            need["case_law"] -= 1
            new.append({"type": "case_law", "language": language, "names_section": False,
                        "question": draft.question, "expected_answer": draft.expected_answer,
                        "gold": [{"document_id": doc["document_id"], "matter_id": doc["matter_id"], "court": court,
                                  "case_number": doc["case_number"], "paragraph": paragraph["number"],
                                  "page": paragraph["page"]}], "quote": draft.quote})
            missing -= 1

    # No-answer: stricter code check - an Act named in the question must not appear anywhere in the corpus.
    if need["no_answer"] > 0:
        inventory = pd.read_csv("inventory.csv")
        corpus = _corpus_text_lower()
        corpus_names = _corpus_act_names(inventory)
        asked = "\n".join("- " + i["question"] for i in seen if i["type"] == "no_answer")
        prompt = f"""Write 30 realistic questions about Pakistani law, each naming one specific Act, Ordinance or Rules
(with its year), on these areas: intellectual property, telecom, aviation, shipping, education boards,
health regulation, insurance, securities, waqf, cooperative societies, mines, forests, wildlife,
food safety, pharmacy, drugs pricing, local government, police rules, prisons, juvenile justice.
Do not repeat or rephrase any of these existing questions:
{asked}
Mix English and Roman Urdu. One question per item."""
        candidates = llm.generate_json(prompt, NoAnswerCandidates, temperature=0.7).questions
        for question in candidates:
            if need["no_answer"] <= 0:
                break
            if any(name.lower() in question.lower() for name in corpus_names):
                continue
            acts = re.findall(r"([A-Z][A-Za-z'&\- ]{3,60}?(?:Act|Ordinance|Rules|Order|Regulations))", question)
            if not acts or any(act.strip().lower() in corpus for act in acts):
                logger.info("Rejected no-answer top-up (Act appears in corpus or none named): %s", question)
                continue
            new.append({"type": "no_answer",
                        "language": "Roman Urdu" if re.search(r"\b(kya|hai|ka|ki|ke|mein|agar)\b", question, re.I) else "English",
                        "names_section": False, "question": question, "expected_answer": NO_SOURCE, "gold": [], "quote": "",
                        "check": "named Act does not occur anywhere in the English corpus text"})
            need["no_answer"] -= 1

    prefixes = {"statute": "STAT", "case_law": "CASE", "no_answer": "NOANS"}
    for item in new:
        numbers = [int(i["id"].split("_")[1]) for i in seen + new if "id" in i and i["type"] == item["type"]]
        item["id"] = f"{prefixes[item['type']]}_{max(numbers) + 1:03d}"
        item.update(source="top-up: drafted by Gemini from the gold source, checked by code", reviewed=False)
    with OUT_JSONL.open("a", encoding="utf-8") as handle:
        for item in new:
            handle.write(json.dumps({"id": item.pop("id"), **item}, ensure_ascii=False) + "\n")
    write_review_csv(OUT_JSONL, OUT_REVIEW)
    added = {kind: sum(1 for i in new if i["type"] == kind) for kind in TARGET}
    logger.info("Top-up added %s; still missing %s; LLM calls %d", added, need, llm.calls)
    return added


def apply_review(csv_path: Path = OUT_REVIEW, jsonl_path: Path = OUT_JSONL) -> Dict[str, int]:
    """Apply the person's review: status ok -> reviewed; fix -> take the edited question /
    expected_answer from the CSV and mark reviewed; drop -> remove; empty -> left unreviewed."""
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        review = {row["id"]: row for row in csv.DictReader(handle)}
    kept, dropped, counts = [], [], {"ok": 0, "fix": 0, "drop": 0, "unreviewed": 0}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        row = review.get(item["id"], {})
        status = (row.get("status") or "").strip().lower()
        if status == "drop":
            counts["drop"] += 1
            dropped.append({**item, "drop_reason": (row.get("your_note") or "").strip()})
            continue
        if status in ("ok", "fix"):
            if status == "fix":
                item["question"] = row["question"].strip() or item["question"]
                item["expected_answer"] = row["expected_answer"].strip() or item["expected_answer"]
            item["reviewed"] = True
            item["review_note"] = (row.get("your_note") or "").strip()
            counts[status] += 1
        else:
            counts["unreviewed"] += 1
        kept.append(item)
    jsonl_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in kept), encoding="utf-8")
    if dropped:  # kept with the reason, so dropped sources are not drafted again by top_up()
        with (jsonl_path.parent / OUT_DROPPED.name).open("a", encoding="utf-8") as handle:
            for item in dropped:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info("Review applied: %s; %d questions remain", counts, len(kept))
    return counts


if __name__ == "__main__":
    import sys
    if "--apply-review" in sys.argv:
        apply_review()
    elif "--top-up" in sys.argv:
        top_up()
    else:
        build()
