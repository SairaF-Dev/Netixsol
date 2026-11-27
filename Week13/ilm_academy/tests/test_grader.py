"""Grader: rules come from the task text and are checked on the code; partial marks, rule cap,
and timeout rescue work (the last two need Docker)."""
from __future__ import annotations

import pytest

from ilm.grading import sandbox
from ilm.grading.grader import EDGE, agreement, grade, rule_violations, rules_from_stem
from ilm.questions.validate import load_bank

BANK = {q.id: q for q in load_bank()[0]}


def test_rules_are_read_from_the_task_text():
    assert rules_from_stem(BANK["recursion-03"].stem) == ["recursive"]
    assert rules_from_stem(BANK["while_loops-03"].stem) == ["while_loop", "no_str"]
    assert rules_from_stem(BANK["iterating_lists-03"].stem) == ["no_max"]
    assert rules_from_stem(BANK["try_except-02"].stem) == ["try_except"]
    assert rules_from_stem(BANK["sets-02"].stem) == []


def test_rule_violations_are_found_on_the_ast():
    loop_fact = "def factorial(n):\n    r = 1\n    for i in range(2, n + 1):\n        r *= i\n    return r\n"
    assert rule_violations(loop_fact, "factorial", ["recursive"]) == ["not recursive"]
    rec = "def factorial(n):\n    return 1 if n == 0 else n * factorial(n - 1)\n"
    assert rule_violations(rec, "factorial", ["recursive"]) == []
    assert rule_violations("def largest(xs):\n    return max(xs)\n", "largest", ["no_max"]) == ["uses max()"]
    assert rule_violations("def f(\n", "f", ["recursive"]) == []          # syntax error: tests decide


def test_edge_tests_only_use_exercises_in_the_bank():
    for qid, tests in EDGE.items():
        assert qid in BANK and all(call.startswith(BANK[qid].function + "(") for call, _ in tests)


def test_edge_tests_are_right_for_the_reference_solutions():
    from ilm.questions.runner import run_tests
    for qid, tests in EDGE.items():
        q = BANK[qid]
        assert run_tests(q.solution, [{"call": c, "expect": e} for c, e in tests]).all_passed, qid


def test_agreement_numbers():
    a = agreement([10, 5, 0, 8], [10, 6, 0, 4])
    assert a["mae"] == 1.25 and a["within_1"] == 0.75 and a["mean_grader_minus_ref"] == 0.75


needs_docker = pytest.mark.skipif(not sandbox.docker_available(), reason="Docker is not running")


@needs_docker
def test_rule_cap_and_partial_marks():
    q = BANK["recursion-03"]
    loop = {"id": "x", "code": "def factorial(n):\n    r = 1\n    for i in range(2, n + 1):\n        r *= i\n    return r\n"}
    g = grade(loop, q, "bank", use_rules=True, use_speed=False)
    assert g["passed"] == g["tests"] and g["mark"] == 4 and g["rules_broken"] == ["not recursive"]
    off = {"id": "y", "code": "def factorial(n):\n    if n == 1:\n        return 1\n    return n * factorial(n - 1)\n"}
    g2 = grade(off, q, "edge", use_rules=True, use_speed=False)
    assert 0 < g2["mark"] < 10                                      # crashes on 0, right elsewhere


@needs_docker
def test_one_infinite_loop_does_not_wipe_out_the_other_tests():
    q = BANK["modulo-02"]
    # the bank calls is_even(4), (7), (0), (-2): loop forever on 7 only, and disable the alarm
    sub = {"id": "z", "code": "import signal\nsignal.alarm = lambda s: 0\n"
                              "def is_even(n):\n    while n == 7:\n        pass\n    return n % 2 == 0\n"}
    g = grade(sub, q, "bank", use_rules=False, use_speed=False)
    assert g["status"] == "timeout_rescued" and g["passed"] == g["tests"] - 1
