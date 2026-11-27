"""Code feedback, offline: hidden tests stay hidden, one improvement by priority, tool tips never
contradict the task, and the LLM explanation cannot leak the solution."""
from __future__ import annotations

import json

from ilm.grading.feedback import (failures, feedback, leaks_hidden, llm_explanation, one_improvement,
                                  quality, render)
from ilm.questions.validate import load_bank

BANK = {q.id: q for q in load_bank()[0]}
BY_FN = {q.function: q for q in BANK.values() if q.type == "code"}


def T(call, expect, passed, got, hidden=False):
    return {"call": call, "expect": expect, "raises": None, "hidden": hidden, "passed": passed, "got": got}


GRADED = {"id": "x", "mark": 3.3, "rules_broken": [], "slow": None, "run_error": None,
          "test_results": [T("count_letters('aab')", "{'a': 2, 'b': 1}", False, "{'a': 1, 'b': 1}"),
                           T("count_letters('zzzq')", "{'z': 3, 'q': 1}", False, "{'z': 1, 'q': 1}", hidden=True),
                           T("count_letters('')", "{}", True, "{}", hidden=True)]}
CODE = "def count_letters(word):\n    counts = {}\n    for ch in word:\n        counts[ch] = 1\n    return counts\n"


def test_hidden_tests_are_counted_but_never_shown():
    fb = feedback(GRADED, BANK["dictionaries-03"], CODE)
    page = render(fb)
    assert "count_letters('aab')" in page                      # visible: shown in full
    assert "zzzq" not in page and "'z': 3" not in page          # hidden: input and answer stay hidden
    assert "1 hidden test(s)" in page and not leaks_hidden(fb, page)
    assert leaks_hidden(fb, page + " try count_letters('zzzq')")


def test_explanations_name_the_error_kind():
    f = failures([T("f(1)", "1", False, "KeyError: 'a'"), T("f(2)", "2", False, "None", hidden=True)])
    assert "dictionary key" in f["visible_failed"][0]["why"]
    assert "print the answer instead of returning" in f["hidden_failed_how"][0]["how"]


def test_one_improvement_follows_priority():
    q = {"issues": [{"hint": "style tip"}], "complex": False, "max_complexity": 1}
    crash = failures([T("f(1)", "1", False, "RecursionError: maximum recursion depth exceeded")])
    assert one_improvement(crash, ["not recursive"], None, q, "")["kind"] == "make it run"
    ok = failures([T("f(1)", "1", True, "1")])
    assert one_improvement(ok, ["not recursive"], None, q, "")["kind"] == "follow the task"
    assert one_improvement(ok, [], True, q, "")["kind"] == "speed"
    assert one_improvement(ok, [], False, q, "")["kind"] == "code quality"
    assert one_improvement(ok, [], False, {"issues": [], "complex": False, "max_complexity": 1}, "")["kind"] == "well done"


def test_quality_tip_never_suggests_a_forbidden_function():
    code = "def largest(nums):\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n    return best\n"
    assert any("max(" in i["hint"] for i in quality(code)["issues"])          # pylint says "use max()"
    assert not any("max(" in i["hint"] for i in quality(code, {"max"})["issues"])


def test_syntax_error_is_one_plain_message():
    q = quality("def f(n)\n    return n\n")
    assert q["syntax_error"] and len(q["issues"]) == 1 and q["issues"][0]["hint"].startswith("Python cannot read line")


def test_bare_except_gets_a_beginner_hint():
    q = quality("def to_int(s):\n    try:\n        return int(s)\n    except:\n        return None\n")
    assert any("Name the error you expect" in i["hint"] for i in q["issues"])


class FakeLLM:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, prompt, **kw):
        self.prompts.append(prompt)
        return json.dumps({"explanation": self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]})


def test_llm_never_sees_hidden_tests_or_the_solution_and_leaks_are_blocked():
    q = BANK["dictionaries-03"]
    fb = feedback(GRADED, q, CODE)
    good = FakeLLM("You set every count to 1. What should happen the second time you see a letter?")
    out = llm_explanation(fb, q, CODE, good, BY_FN)
    assert out["text"] and not out["blocked"]
    assert "zzzq" not in good.prompts[0] and q.solution.strip() not in good.prompts[0]
    leak = FakeLLM(f"Here is the fix:\n```python\n{q.solution}```")
    out = llm_explanation(fb, q, CODE, leak, BY_FN)
    assert out["blocked"] and out["text"] is None and len(leak.prompts) == 2


def test_a_loop_that_never_ends_comes_before_the_task_rule():
    f = failures([T("sum_to(0)", "0", True, "0"), T("sum_to(5)", "15", False, "killed after 10s", hidden=True)])
    imp = one_improvement(f, ["no for loop"], None, {"issues": [], "complex": False, "max_complexity": 1}, "")
    assert imp["kind"] == "make it run" and "never ends" in imp["text"]


def test_rule_message_does_not_claim_right_answers_when_some_are_wrong():
    q = {"issues": [], "complex": False, "max_complexity": 1}
    some_wrong = failures([T("f(1)", "1", True, "1"), T("f(2)", "2", False, "3", hidden=True)])
    assert "come out right" not in one_improvement(some_wrong, ["uses max()"], None, q, "")["text"]
    assert "not to use max()" in one_improvement(failures([T("f(1)", "1", True, "1")]), ["uses max()"], None, q, "")["text"]
