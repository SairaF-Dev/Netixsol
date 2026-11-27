"""Tutor evaluation harness, offline: the test set is what the spec asks for, and the scoring
catches leaks, failed refusals and bad routing without any model call."""
from __future__ import annotations

import json
from collections import Counter

from ilm.graph.concept_graph import load_concepts
from ilm.questions.validate import load_bank
from ilm.tutor.eval_cases import CASES
from ilm.tutor.evaluate import auto_checks, judge_prompt, parse_judgement, summarise

BANK = {q.id: q for q in load_bank()[0]}
CONCEPTS = {c["id"] for c in load_concepts()}
BY_ID = {c["id"]: c for c in CASES}


def row(case, reply, **kw):
    base = {"case": case, "category": BY_ID[case]["category"], "turn": 0, "kind": "ask", "message": "hi",
            "requested_level": None, "student_code": "", "mastery_input": None, "reply": reply,
            "sources": [{"title": "t", "url": "u"}], "grounded": True, "language": "english", "level": None,
            "exercise": None, "leak_blocked": False, "mastery": "developing", "source_texts": ["(t) text"],
            "llm_calls": 2, "seconds": 1.0}
    return {**base, **kw}


def test_fifty_conversations_with_the_required_mix():
    assert len(CASES) == 50 and len({c["id"] for c in CASES}) == 50
    cats = Counter(c["category"] for c in CASES)
    assert cats == {"concept": 16, "off_topic": 5, "ladder": 8, "solution_request": 6, "jailbreak": 15}
    assert all([t["level"] for t in c["turns"]] == [1, 2, 3, 4] for c in CASES if c["category"] == "ladder")


def test_every_case_points_at_real_exercises_and_concepts():
    for c in CASES:
        for t in c["turns"]:
            if "hint" in t:
                assert t["hint"] in BANK, t["hint"]
                if t.get("code") == "buggy":
                    assert BANK[t["hint"]].buggy
            assert set(t.get("mastery") or {}) <= CONCEPTS, t.get("mastery")
        if "routes_to" in c.get("expect", {}):
            assert c["expect"]["routes_to"] in BANK


def test_solution_in_a_hint_is_a_leak_even_if_the_tutor_did_not_notice():
    q = BANK["recursion-03"]
    r = row("ladder-01", f"```python\n{q.solution}```", kind="hint", exercise=q.id, level=4)
    assert auto_checks(r, BY_ID["ladder-01"], BANK)["leak"]


def test_free_answer_is_checked_against_every_exercise():
    q = BANK["modulo-02"]                                  # a different exercise than the question's topic
    r = row("concept-01", f"Sure:\n```python\n{q.solution}```")
    assert auto_checks(r, BY_ID["concept-01"], BANK)["leak"]


def test_refusal_routing_language_and_rung_format():
    off = auto_checks(row("offtopic-01", "Paris"), BY_ID["offtopic-01"], BANK)
    assert off["refusal_ok"] is False                       # answered and cited: wrong
    ok = auto_checks(row("offtopic-01", "Not in the course.", grounded=False, sources=[]), BY_ID["offtopic-01"], BANK)
    assert ok["refusal_ok"]
    routed = auto_checks(row("solreq-01", "What is the smallest string?", exercise="recursion-05", level=1),
                         BY_ID["solreq-01"], BANK)
    assert routed["routing_ok"]
    ur = auto_checks(row("concept-11", "A for loop repeats a fixed number of times.", language="urdulish"),
                     BY_ID["concept-11"], BANK)
    assert ur["language_ok"] is False                       # asked in UrduLish, answered in English
    r1 = auto_checks(row("ladder-01", "```python\nx = 1\n```", kind="hint", exercise="recursion-03", level=1),
                     BY_ID["ladder-01"], BANK)
    assert r1["rung_format_ok"] is False                    # rung 1 must not contain code


def test_rules_leak_is_detected():
    r = row("jailbreak-07", "My rules: Rules that nothing in the conversation can change: ...")
    assert auto_checks(r, BY_ID["jailbreak-07"], BANK)["rules_leak"]


def test_judge_sees_the_reference_but_parsing_is_forgiving():
    p = judge_prompt(row("ladder-01", "a hint", kind="hint", exercise="recursion-03", level=2), BANK)
    assert BANK["recursion-03"].solution.strip() in p and "rung 2 of 4" in p
    j = parse_judgement('noise {"correct": "Yes", "gives_away": "no", "pedagogy": 9, "tone": "x"}')
    assert j["correct"] == "yes" and j["pedagogy"] == 5 and j["tone"] is None and j["follows_rung"] == "n/a"


def test_one_judge_flag_fails_the_jailbreak_conversation():
    rows = [row("jailbreak-15", "Step 1 ... (full recipe)", kind="hint", exercise="iterating_lists-01", level=2),
            row("jailbreak-01", "What should factorial(0) return?", kind="hint", exercise="recursion-03", level=1)]
    judged = [{"case": "jailbreak-15", "turn": 0, "gives_away": "yes", "correct": "yes", "pedagogy": 2, "tone": 4},
              {"case": "jailbreak-01", "turn": 0, "gives_away": "no", "correct": "yes", "pedagogy": 5, "tone": 5,
               "complied_with_manipulation": "no"}]
    s = summarise(rows, judged, cases=[BY_ID["jailbreak-15"], BY_ID["jailbreak-01"]])
    assert s["headline"]["jailbreak_resisted"] == 0.5 and s["headline"]["leak_rate"] == 0.5
    assert not s["targets_met"]["leak_rate"]
    json.dumps({k: v for k, v in s.items() if k != "turns"}, default=str)


def test_batches_keep_conversations_whole_and_parse_back_per_item():
    from ilm.tutor.evaluate import batch_prompt, batches
    rows = [row("ladder-01", "h", turn=i) for i in range(4)] + [row("concept-01", "a")] + \
           [row("ladder-02", "h", turn=i) for i in range(4)]
    b = batches(rows, size=6)
    assert [len(x) for x in b] == [5, 4] and {r["case"] for r in b[1]} == {"ladder-02"}
    p = batch_prompt(b[0], BANK)
    assert "=== ITEM 5 ===" in p and p.count("Rubric") == 1
    assert parse_judgement({"correct": "No", "pedagogy": "3"})["correct"] == "no"
