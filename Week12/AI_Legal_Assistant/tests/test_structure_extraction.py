"""
Unit tests for Task 3: legal structure extraction on real document formats.

Inline-text tests always run; tests on real PDFs skip when the data folder is absent.
"""
from pathlib import Path

import pytest

from src.extraction.contract_extractor import ContractStructureExtractor
from src.extraction.judgment_extractor import JudgmentStructureExtractor
from src.extraction.statute_extractor import StatuteStructureExtractor
from src.extraction.structure_extractor import UnifiedStructureExtractor, _supreme_court_case_number

STATUTE_PAGES = [
    # Table of contents page: headings with no text between them must be dropped.
    "Page 1 of 3\nTHE SAMPLE ACT, 2010\nCONTENTS\n1.\nShort title and commencement.\n2.\nDefinitions.\n3.\nOffence.\n",
    "Page 2 of 3\nTHE SAMPLE ACT, 2010\n(ACT No. VII OF 2010)\n"
    "WHEREAS it is expedient to provide for the matters hereinafter appearing;\n"
    "CHAPTER I\nPRELIMINARY\n"
    "1. Short title and commencement.—(1) This Act may be called the Sample Act, 2010.\n"
    "(2) It shall come into force at once.\n"
    "2. Definitions.— In this Act, unless there is anything repugnant in the subject or context, words have their meaning.\n",
    "Page 3 of 3\nCHAPTER II\nOFFENCES\n"
    "3. Offence. Whoever does the prohibited act shall be punished with imprisonment.\n"
    "1. a numbered list item inside section 3 that is not a new section\n"
    "4. Punishment.— The punishment shall extend to seven years.\n",
]


def test_statute_sections_chapters_pages_and_toc_removal():
    doc = StatuteStructureExtractor().extract_from_pages(STATUTE_PAGES, "T1", act_name="Sample Act, 2010")
    sections = [s for c in doc.chapters for s in c.sections]
    assert [s.section_number for s in sections] == ["Section 1", "Section 2", "Section 3", "Section 4"]
    assert [c.chapter_number for c in doc.chapters] == ["Chapter I", "Chapter II"]
    assert sections[0].title == "Short title and commencement"
    assert sections[0].subsections[0].startswith("(1) This Act")
    assert [s.page_start for s in sections] == [2, 2, 3, 3]
    assert doc.year == 2010
    assert doc.act_number == "ACT No. VII OF 2010"
    assert doc.preamble.startswith("WHEREAS")


JUDGMENT_TEXT = """IN THE SUPREME COURT OF PAKISTAN
(Appellate Jurisdiction)
PRESENT:
MR. JUSTICE ALPHA BETA
Mr. Justice Gamma Delta
Civil Petition No. 624 of 2023
(Against the judgment dated 01.02.2023 passed by the Lahore High Court in W.P. No. 1 of 2020)
Ahmad Ali
…Petitioner(s)
Versus
Province of Punjab through Secretary
…Respondent(s)
For the Petitioner(s): Mr. X, ASC
Date of Hearing: 10.06.2026
JUDGMENT
GAMMA DELTA, J.- This petition arises under Article 185(3) of the Constitution against an order.
2. The learned High Court relied on Muhammad Akram v. State (2019 SCMR 1234) and PLD 2016 SC 358.
3. For the foregoing reasons, the petition is dismissed and leave to appeal is refused.
(GAMMA DELTA)
JUDGE"""


def test_judgment_header_parties_dates_citations_and_holding():
    doc = JudgmentStructureExtractor().extract_from_text(JUDGMENT_TEXT, doc_id="J1", case_number_hint="C.P. 624/2023")
    assert doc.court == "Supreme Court of Pakistan"
    assert doc.case_number == "C.P. 624/2023"
    assert doc.matter_id == "SC:C-P-624-2023"
    assert doc.parties.appellant_or_petitioner == "Ahmad Ali"
    assert doc.parties.respondent == "Province of Punjab through Secretary"
    assert doc.bench == ["Justice Alpha Beta", "Justice Gamma Delta"]
    assert doc.date_of_hearing == "2026-06-10" and doc.year == 2026
    assert doc.citations == ["2019 SCMR 1234", "PLD 2016 SC 358"]
    assert any(s.startswith("Article 185(3) of the Constitution") for s in doc.statutes_cited)
    assert [p.number for p in doc.paragraphs] == [None, "2", "3"]
    assert doc.outcome == "dismissed"
    assert doc.holding.startswith("For the foregoing reasons")
    assert "JUDGE" not in doc.holding


def test_judgment_missing_fields_stay_empty():
    doc = JudgmentStructureExtractor().extract_from_text("Some text without any header.", doc_id="J2")
    assert doc.case_number == "Unknown"
    assert doc.date_of_judgment == "" and doc.date_of_hearing is None
    assert doc.issues == [] and doc.citations == []


CONTRACT_TEXT = """EXHIBIT 10.1
DISTRIBUTION AGREEMENT
This Agreement is made and entered into as of March 3, 2015 by and between Alpha Corp., a Delaware corporation ("Alpha"), and Beta LLC, a Nevada company ("Beta").
1. Definitions. Terms have the meanings set out below.
1.1 "Products" means the goods listed in Exhibit A.
2. Appointment. Alpha appoints Beta as distributor.
3. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of New York.
"""


def test_contract_metadata_and_clauses():
    doc = ContractStructureExtractor().extract_from_text(CONTRACT_TEXT, doc_id="C1", contract_type="Distributor")
    assert doc.contract_title == "Distribution Agreement"
    assert doc.parties == ["Alpha Corp", "Beta LLC"]
    assert doc.effective_date == "March 3, 2015"
    assert doc.governing_law == "Laws of State of New York"
    assert doc.dispute_resolution is None
    assert [c.clause_id for c in doc.clauses] == ["Clause 1", "Clause 2", "Clause 3"]
    assert "1.1" in doc.clauses[0].text


FILLER = "The parties agree to the terms of this clause, which continue for several more words here."


def _clause_ids(text):
    return [c.clause_id for c in ContractStructureExtractor().extract_from_text(text, doc_id="C").clauses]


def test_contract_table_of_contents_is_not_taken_as_the_clauses():
    toc = "TABLE OF CONTENTS\n1. Rights Granted\n2. Fees\n3. Term\n"
    body = f"1. Rights Granted. {FILLER}\n2. Fees. {FILLER}\n3. Term. {FILLER}\n"
    doc = ContractStructureExtractor().extract_from_text("FRANCHISE AGREEMENT\n" + toc + body, doc_id="C")
    assert [c.clause_id for c in doc.clauses] == ["Clause 1", "Clause 2", "Clause 3"]
    assert all(FILLER in c.text for c in doc.clauses)   # the body, not the empty contents lines


def test_contract_heading_styles():
    # decimal headings only ('1.1 Scope'), no space after the number, a Greek question mark for ';'
    assert _clause_ids(f"1.1 Scope\n{FILLER}\n1.2 More\n{FILLER}\n2.1 Definitions\n{FILLER}\n3.1 General Terms\n{FILLER}") == \
        ["Clause 1", "Clause 2", "Clause 3"]
    assert _clause_ids(f"1. DEFINITIONS:\n{FILLER}\n2.TERM:\n{FILLER}\n3.GRANT OF RIGHTS; STATIONS:\n{FILLER}") == \
        ["Clause 1", "Clause 2", "Clause 3"]
    # numbered paragraphs without titles, and Roman-numbered parts
    assert _clause_ids(f"1. mPhase may apply only the exact logo. {FILLER}\n2. mPhase agrees to the guidelines. {FILLER}\n"
                       f"3. Lucent may inspect the goods. {FILLER}") == ["Clause 1", "Clause 2", "Clause 3"]
    assert _clause_ids(f"I. Object of the Program\n{FILLER}\nII. Affiliate Program\n{FILLER}\nIII. General terms\n{FILLER}") == \
        ["Part I", "Part II", "Part III"]


def test_very_long_contract_clause_is_split_into_sub_clauses():
    long_text = " ".join([FILLER] * 200)   # ~3,000 words
    text = (f"1. Scope. {FILLER}\n2. General Terms.\n2.1 Affiliate. {long_text}\n2.2 Access.\n2.3 Notices. {long_text}\n"
            f"2.4 Waiver. {FILLER}\n3. Signatures. {FILLER}")
    ids = _clause_ids(text)
    assert ids == ["Clause 1", "Clause 2.1", "Clause 2.3", "Clause 2.4", "Clause 3"]   # 2.2 is only a heading: joins 2.3


def test_supreme_court_case_number_from_file_name():
    assert _supreme_court_case_number("SC_c.p._2413_l_2025") == "C.P. 2413-L/2025"
    assert _supreme_court_case_number("SC_c.a._333_2024_23092024_hj3") == "C.A. 333/2024"
    assert _supreme_court_case_number("SC_c.a._333_2024_mv") == "C.A. 333/2024"
    assert _supreme_court_case_number("SC_crl.p._316_2018_r1") == "CRL.P. 316/2018"
    assert _supreme_court_case_number("SC_crl.p._467_2023.") == "CRL.P. 467/2023"


PPC = Path("data/raw/pakistani_laws/administrator92ada0936848e501425591b4ad0cd417.pdf")
CONSTITUTION = Path("data/statutes/REAL_STAT_001.pdf")
SC_JUDGMENT = Path("data/scp_judgments_pdfs/002_c.p._624_2023.pdf")


@pytest.mark.skipif(not PPC.exists(), reason="Pakistan Penal Code PDF not available")
def test_real_penal_code_section_302():
    doc = StatuteStructureExtractor().extract_from_file(PPC, act_name="Pakistan Penal Code, 1860")
    sections = {s.section_number: s for c in doc.chapters for s in c.sections}
    assert "Section 511" in sections
    assert sections["Section 302"].title.startswith("Punishment of qatl")
    assert sections["Section 302"].page_start == 103


@pytest.mark.skipif(not CONSTITUTION.exists(), reason="Constitution PDF not available")
def test_real_constitution_articles_in_order():
    doc = StatuteStructureExtractor().extract_from_file(
        CONSTITUTION, act_name="Constitution of the Islamic Republic of Pakistan, 1973")
    articles = [s.section_number for c in doc.chapters for s in c.sections if s.section_number.startswith("Article")]
    assert articles[:4] == ["Article 1", "Article 2", "Article 2A", "Article 3"]
    assert "Article 199" in articles and articles[-1] == "Article 280"
    assert doc.year == 1973
    # 27th Amendment edition: margin-note titles taken from the contents, new articles present.
    sections = {s.section_number: s for c in doc.chapters for s in c.sections}
    assert sections["Article 6"].title == "High treason"
    assert "Federal Constitutional Court" in " ".join(sections["Article 6"].subsections + [sections["Article 6"].content])
    assert "Article 175B" in sections


@pytest.mark.skipif(not SC_JUDGMENT.exists(), reason="Supreme Court judgment PDFs not available")
def test_real_supreme_court_judgment_via_inventory_record():
    record = {"document_id": "SC_c.p._624_2023", "type": "Judgment", "title": "", "file_path": str(SC_JUDGMENT)}
    doc = UnifiedStructureExtractor().extract_record(record)
    assert doc.court == "Supreme Court of Pakistan"
    assert doc.case_number == "C.P. 624/2023"
    assert doc.bench and all("Justice" in name for name in doc.bench)
    assert doc.parties.appellant_or_petitioner != "Unknown"
    assert len(doc.paragraphs) >= 3 and doc.outcome is not None


CONTRACT_ACT = Path("data/raw/pakistani_laws/administrator8332a6df32386960ac7d81a5cf7aade2.pdf")


@pytest.mark.skipif(not CONTRACT_ACT.exists(), reason="Contract Act PDF not available")
def test_real_contract_act_section_23_and_repealed_gap():
    doc = StatuteStructureExtractor().extract_from_file(CONTRACT_ACT, act_name="Contract Act, 1872")
    sections = {s.section_number: (c.chapter_number, s) for c in doc.chapters for s in c.sections}
    chapter, s23 = sections["Section 23"]
    assert s23.title.startswith("What considerations and objects are lawful")
    assert s23.page_start == 19 and chapter == "Chapter II"
    # Sections 76-123 are repealed: 75 is followed by 124, and numbering continues to 238.
    assert "Section 124" in sections and "Section 238" in sections and "Section 100" not in sections
    # Sections 1-2 are preliminary, not the last chapter listed in the contents.
    assert sections["Section 1"][0] == "General"
