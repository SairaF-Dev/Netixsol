"""Question generation gates, offline: each gate rejects the flaw it exists for, and a good
draft passes all of them. No LLM calls (drafts are written by hand here)."""
from __future__ import annotations

import copy
import json

from ilm.graph.concept_graph import load_concepts
from ilm.questions.generate import (examples, gen_prompt, solve, solver_verdict, summarise,
                                    validate_drafts)
from ilm.questions.validate import load_bank

BANK, _ = load_bank()
IDS = {c["id"] for c in load_concepts()}

GOOD_MCQ = {"type": "mcq", "concepts": ["modulo"], "difficulty": 2, "bloom": "apply",
            "stem": "What does this program print?", "code": "minutes = 135\nprint(minutes // 60, minutes % 60)\n",
            "check_output": True, "options": ["2 15", "2.25 15", "2 0.25", "15 2"], "answer": 0,
            "misconceptions": {"1": "// does normal division and keeps the decimals",
                               "2": "% gives the fraction left over, not the remainder",
                               "3": "% gives the quotient and // the remainder"}}
GOOD_CODE = {"type": "code", "concepts": ["modulo"], "difficulty": 2, "bloom": "apply",
             "stem": "Write last_digit(n) that returns the last digit of a whole number n >= 0.",
             "function": "last_digit",
             "solution": "def last_digit(n):\n    return n % 10\n",
             "buggy": "def last_digit(n):\n    return n // 10\n",
             "tests": [{"call": "last_digit(123)", "expect": "3"}, {"call": "last_digit(7)", "expect": "7", "hidden": True},
                       {"call": "last_digit(40)", "expect": "0", "hidden": True}]}


def run(*items, concept="modulo"):
    return validate_drafts([{"concept": concept, "asked_types": ["mcq"], "items": list(items)}], BANK, IDS)


def gate(item, **kw):
    return run(item, **kw)[0]["gate"]


def changed(base, **kw):
    d = copy.deepcopy(base)
    d.update(kw)
    return d


def test_good_drafts_pass_every_gate():
    r = run(GOOD_MCQ, GOOD_CODE)
    assert [x["gate"] for x in r] == [None, None]
    assert [x["id"] for x in r] == ["modulo-51", "modulo-52"]


def wrong_key(base, k=1):
    """Same question, key moved to option k (misconceptions moved too, so only the key is wrong)."""
    m = {str(i): f"wrong belief number {i} about // and %" for i in range(len(base["options"])) if i != k}
    return changed(base, answer=k, misconceptions=m)


def test_wrong_key_is_caught_by_running_the_code():
    assert gate(wrong_key(GOOD_MCQ)) == "truth"                 # it prints "2 15", not "2.25 15"


def test_buggy_that_passes_the_tests_means_weak_tests():
    # 0 and 11 are exactly the inputs where n % 10 == n // 10, so the buggy version passes too
    weak = changed(GOOD_CODE, tests=[{"call": "last_digit(0)", "expect": "0"},
                                     {"call": "last_digit(11)", "expect": "1", "hidden": True}])
    r = run(weak)[0]
    assert r["gate"] == "truth" and "buggy solution passes" in r["why"][0]


def test_item_writing_flaws():
    assert gate(changed(GOOD_MCQ, options=["2", "3", "12", "All of the above"])) == "flaws"
    assert gate(changed(GOOD_MCQ, check_output=False)) == "flaws"            # output question, unchecked key
    no_bug = changed(GOOD_CODE)
    no_bug.pop("buggy")
    assert gate(no_bug) == "flaws"
    long_key = changed(GOOD_MCQ, code=None, check_output=False, stem="What does % do?",
                       options=["It returns the remainder left over after dividing the first number by the second",
                                "Division", "Power", "Rounding"])
    assert gate(long_key) == "flaws"


def test_misconception_for_every_wrong_option_is_required():
    m = changed(GOOD_MCQ, misconceptions={"1": "% gives the quotient (17 // 5)"})
    assert gate(m) == "format"


def test_concepts_must_exist_and_lead_with_the_target():
    assert gate(changed(GOOD_MCQ, concepts=["not_a_concept"])) == "format"
    assert gate(changed(GOOD_MCQ, concepts=["integers", "modulo"])) == "format"


def test_different_bank_questions_are_not_duplicates_of_each_other():
    """The 0.85 line, checked on pairs that are different questions by definition."""
    import itertools
    from ilm.questions.generate import DUP_SIMILAR, similarity, text_of
    assert max(similarity(text_of(a), text_of(b)) for a, b in itertools.combinations(BANK, 2)) < DUP_SIMILAR


def test_copy_of_a_bank_question_is_a_duplicate():
    copy17 = changed(GOOD_MCQ, code="print(17 % 5)\n", options=["2", "3", "3.4", "12"],
                     misconceptions={"1": "% gives the quotient (17 // 5)", "2": "% does normal division",
                                     "3": "% subtracts the divisor once"})
    assert gate(copy17) == "duplicate"                          # modulo-01 with one option changed
    bank_q = next(q for q in BANK if q.id == "modulo-02")
    dup = changed(GOOD_CODE, stem=bank_q.stem, function="is_even2",
                  solution="def is_even2(n):\n    return n % 2 == 0\n", buggy="def is_even2(n):\n    return True\n",
                  tests=[{"call": "is_even2(2)", "expect": "True"}, {"call": "is_even2(3)", "expect": "False", "hidden": True}])
    assert gate(dup) == "duplicate"


def test_non_string_expect_values_are_normalised():
    d = changed(GOOD_CODE, tests=[{"call": "last_digit(123)", "expect": 3},
                                  {"call": "last_digit(40)", "expect": 0, "hidden": True}])
    assert gate(d) is None


def test_solver_verdicts():
    mcq = {**GOOD_MCQ, "answer": 0}
    assert solver_verdict(mcq, 0) is None and "ambiguous" in solver_verdict(mcq, 1)
    short = {"type": "short", "accept": ["print"]}
    assert solver_verdict(short, "Print") is None and solver_verdict(short, "echo")
    assert solver_verdict(GOOD_CODE, "```python\ndef last_digit(n):\n    return int(str(n)[-1])\n```") is None
    assert "fails the tests" in solver_verdict(GOOD_CODE, "def last_digit(n):\n    return n\n")


def test_solver_runs_only_on_survivors_and_matches_by_id():
    r = run(GOOD_MCQ, wrong_key(GOOD_MCQ))
    calls = []

    def fake(prompt, **kw):
        calls.append(prompt)
        return json.dumps({"answers": [{"id": "modulo-51", "answer": 0}]})
    solved = solve(r, fake)
    assert set(solved) == {"modulo-51"} and solved["modulo-51"]["verdict"] is None
    assert "modulo-52" not in calls[0]


def test_prompt_shows_lectures_existing_questions_and_asks_code_only_where_the_course_has_it():
    concepts = {c["id"]: c for c in load_concepts()}
    p, types = gen_prompt(concepts["modulo"], BANK, concepts, [], examples(BANK))
    assert types == ["mcq", "short", "code"] and "is_even" in p
    _, types = gen_prompt(concepts["comments"], BANK, concepts, [], examples(BANK))
    assert types == ["mcq", "short"]


def test_summary_funnel_adds_up():
    r = run(GOOD_MCQ, wrong_key(GOOD_MCQ), GOOD_CODE)
    s = summarise([{"concept": "modulo", "asked_types": ["mcq", "short", "code"], "items": []}], r, solver_ran=False)
    assert s["generated"] == 3 and s["accepted"] == 2 and s["funnel"][-1]["still_in"] == 2


def test_missing_type_is_read_from_the_fields():
    d = changed(GOOD_CODE)
    d.pop("type")
    r = run(d)[0]
    assert r["type"] == "code" and r["gate"] is None


def test_function_name_already_used_by_the_bank_is_a_flaw():
    clash = changed(GOOD_CODE, function="square", stem="Write square(n) that returns n to the power 2, using **.",
                    solution="def square(n):\n    return n ** 2\n", buggy="def square(n):\n    return n * 2\n",
                    tests=[{"call": "square(3)", "expect": "9"}, {"call": "square(-2)", "expect": "4", "hidden": True}])
    r = run(clash)[0]
    assert r["gate"] == "flaws" and "already used" in r["why"][0]


def test_v2_prompt_carries_a_target_per_question():
    from ilm.questions.generate import TARGET_PLAN
    concepts = {c["id"]: c for c in load_concepts()}
    p, _ = gen_prompt(concepts["modulo"], BANK, concepts, [], examples(BANK), TARGET_PLAN[1])
    assert "one mcq at difficulty 4 (analyze" in p and "one code at difficulty 3" in p
