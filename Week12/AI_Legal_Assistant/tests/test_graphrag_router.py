"""Tests for Day 3, Tasks 4-5: the router and the multi-hop answer scoring (no Neo4j or LLM needed)."""
from evaluations.graph_vs_vector import coverage, item_key, prf
from src.graph.entities import acts_named_in, canonical_act
from src.rag.router import route


def test_router_sends_content_to_vector_links_to_graph_and_both_to_hybrid():
    assert route("Agar consideration unlawful ho to kya contract void hai?")["mode"] == "vector"
    assert route("Which section of the Pakistan Penal Code deals with qatl-e-amd?")["mode"] == "vector"
    assert route("Which judges sat on the cases that refer to Section 324 PPC?")["mode"] == "graph"
    assert route("Which precedent is cited by the largest number of judgments?")["mode"] == "graph"
    assert route("Which judges dealt with cases under Order VII Rule 10 CPC?")["mode"] == "graph"   # "Rule" is not "ruled"
    assert route("Which judgments refer to Section 324 PPC, and what did the courts hold about the sentence?")["mode"] == "hybrid"


def test_answer_items_are_compared_by_identity():
    assert item_key("C.A. 1410/2019 (SC_c.a._1410_2019): Supreme Court of Pakistan") == item_key("anything (SC_c.a._1410_2019)")
    assert item_key("PLD 2019 Supreme Court 504") == item_key("PLD 2019 SC 504")
    assert item_key("Order VII Rule 10") == item_key("Order VII Rule 10")
    scores = prf(["Muhammad Hashim Khan Kakkar", "Wrong Judge"], ["Muhammad Hashim Khan Kakar", "Ishtiaq Ibrahim"])
    assert scores["precision"] == 0.5 and scores["recall"] == 0.5


def test_coverage_counts_answer_items_present_in_context():
    context = "Justice Ishtiaq Ibrahim relied on PLD 2019 SC 504 and Section 302 PPC."
    assert coverage(["Ishtiaq Ibrahim", "PLD 2019 SC 504", "Section 302", "Yahya Afridi"], context, set()) == 0.75


def test_laws_are_recognised_however_they_are_written():
    assert canonical_act("EXT:qanoon-e-shahadat-order") == canonical_act("PKCODE_URDU_002", "Qanun-e-Shahadat Order") == "qso"
    assert acts_named_in("Kin judges ne Qanun-e-Shahadat ke Article 129 ka hawala diya?") == ["qso"]
    assert acts_named_in("Section 302 PPC and the Code of Criminal Procedure") == ["ppc", "crpc"]
