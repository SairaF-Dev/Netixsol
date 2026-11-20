"""Tests for Day 4: contract comparison, playbook review checks and drafting checks (no LLM needed)."""
import json
from pathlib import Path

import pytest

from src.contracts.compare import align, changes, word_diff
from src.contracts.review import Finding, Review, playbook, review_contract, risk_score

V1 = Path("data/contracts/versions/supply_agreement_v1.json")
V2 = Path("data/contracts/versions/supply_agreement_v2.json")


def test_word_diff_shows_only_what_changed():
    ops = word_diff("paid within thirty (30) days in PKR", "paid within sixty (60) days in PKR")
    assert [(op, t) for op, t in ops if op != "equal"] == [("delete", "thirty (30)"), ("insert", "sixty (60)")]


def test_clauses_are_aligned_by_content_not_number():
    old = [{"clause_id": "1", "clause_title": "Payment", "text": "Invoices are paid within thirty days."},
           {"clause_id": "2", "clause_title": "Confidentiality", "text": "Each party keeps the other's secrets confidential."}]
    new = [{"clause_id": "1", "clause_title": "Confidentiality", "text": "Each party keeps the other's secrets confidential for two years."},
           {"clause_id": "2", "clause_title": "Payment", "text": "Invoices are paid within sixty days."},
           {"clause_id": "3", "clause_title": "Force Majeure", "text": "Neither party is liable for events beyond its control."}]
    pairs = [(a and a["clause_title"], b and b["clause_title"]) for a, b in align(old, new)]
    assert pairs == [("Payment", "Payment"), ("Confidentiality", "Confidentiality"), (None, "Force Majeure")]


def test_planted_changes_between_versions_are_all_found():
    found = changes(json.loads(V1.read_text(encoding="utf-8")), json.loads(V2.read_text(encoding="utf-8")))
    assert len(found) == 9 and all(c["kind"] == "changed" for c in found)   # recital (clause 1) unchanged
    payment = next(c for c in found if c["old_clause"].startswith("4 "))
    assert ("delete", "thirty (30)") in payment["diff"] and ("insert", "sixty (60)") in payment["diff"]


def test_risk_score_weights_red_amber_and_missing_required():
    findings = [{"status": "red", "weight": 10, "required": True}, {"status": "amber", "weight": 4, "required": False},
                {"status": "missing", "weight": 6, "required": True}, {"status": "missing", "weight": 5, "required": False},
                {"status": "green", "weight": 5, "required": True}]
    assert risk_score(findings) == round(100 * (10 + 2 + 6) / 30)


def test_review_removes_a_quote_that_is_not_in_the_clause():
    contract = json.loads(V2.read_text(encoding="utf-8"))
    cap = next(c for c in contract["clauses"] if c["clause_title"] == "Limitation of Liability")

    class Fake:
        def generate_json(self, prompt, schema, system=None, temperature=0.0):
            return Review(findings=[
                Finding(item_id="liability_cap", status="red", clause_ids=[cap["clause_id"]],
                        quote="shall not exceed the fees paid in the one (1) month", reason="one-sided", suggested_wording="x"),
                Finding(item_id="governing_law", status="green", clause_ids=["10"], quote="governed by the laws of England", reason="", suggested_wording="")])

    review = review_contract(str(V2), "the Client", llm=Fake())
    by_id = {f["item_id"]: f for f in review["findings"]}
    assert by_id["liability_cap"]["quote"] and not by_id["governing_law"]["quote"]
    assert by_id["governing_law"]["quote_note"]
    assert {f["item_id"] for f in review["findings"]} == {i["id"] for i in playbook()}   # skipped items are reported
    assert any(s["section"] == "Section 73" for s in by_id["liability_cap"]["sources"])  # source quoted from the corpus
