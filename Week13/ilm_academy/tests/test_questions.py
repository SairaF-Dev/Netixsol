"""The question bank and its validator.

A validator that never fails proves nothing, so most tests here PLANT a mistake
and check that it is caught.
"""
from __future__ import annotations

import yaml

from ilm.questions import runner
from ilm.questions.validate import (check_truth, load_bank, normalise_answer,
                                    normalise_output, validate)

MCQ = {"id": "strings-90", "type": "mcq", "concepts": ["strings"], "difficulty": 1,
       "bloom": "understand", "stem": "What does this print?", "code": 'print("1" + "2")',
       "check_output": True, "options": ["12", "3", "1 2"], "answer": 0,
       "misconceptions": {1: "+ adds numbers in quotes", 2: "+ adds a space"}}
CODE = {"id": "defining_functions-90", "type": "code", "concepts": ["defining_functions"],
        "difficulty": 1, "bloom": "apply", "stem": "Write square(n).", "function": "square",
        "solution": "def square(n):\n    return n * n\n",
        "buggy": "def square(n):\n    return n * 2\n",
        "tests": [{"call": "square(3)", "expect": "9"},
                  {"call": "square(-4)", "expect": "16", "hidden": True}]}


def _bank(tmp_path, *items, raw: str | None = None):
    (tmp_path / "bank.yaml").write_text(raw if raw is not None else
                                        yaml.safe_dump({"questions": list(items)}), encoding="utf-8")
    return tmp_path


def _errors(tmp_path, *items, raw=None) -> list[str]:
    """Validator errors, minus the coverage ones a tiny test bank always has."""
    _, _, rep = validate(_bank(tmp_path, *items, raw=raw))
    return [e for e in rep.errors if "need 200+" not in e and "fewer than" not in e]


def _one(tmp_path, item):
    questions, rep = load_bank(_bank(tmp_path, item))
    return questions, rep.errors


# ------------------------------------------------------------- the real bank ----
def test_real_bank_is_valid_and_big_enough():
    questions, summary, rep = validate()
    assert rep.ok, rep.errors[:5]
    assert summary["total"] >= 200
    assert set(summary["by_type"]) == {"mcq", "short", "code"}
    assert min(summary["per_concept"].values()) >= 3
    assert all(summary["by_bloom"].values()) and all(summary["by_difficulty"].values())


def test_good_examples_pass(tmp_path):
    assert _errors(tmp_path, MCQ, CODE) == []


# ----------------------------------------------------------- truth: run it ----
def test_wrong_marked_answer_is_caught(tmp_path):
    bad = {**MCQ, "answer": 1, "misconceptions": {0: "x", 2: "y"}}
    assert any("marked answer '3' but the code prints '12'" in e for e in _errors(tmp_path, bad))


def test_short_answer_must_include_real_output(tmp_path):
    bad = {"id": "strings-91", "type": "short", "concepts": ["strings"], "difficulty": 1,
           "bloom": "apply", "stem": "Type the output.", "code": 'print("ab" * 2)',
           "check_output": True, "accept": ["ab ab"]}
    assert any("do not include the real output 'abab'" in e for e in _errors(tmp_path, bad))


def test_output_check_is_case_sensitive(tmp_path):
    # "hello world" must not be accepted for "Hello World" in a .title() question
    bad = {**MCQ, "code": 'print("hello world".title())',
           "options": ["hello world", "Hello World", "HELLO WORLD"], "answer": 0,
           "misconceptions": {1: "x", 2: "y"}}
    assert any("marked answer" in e for e in _errors(tmp_path, bad))


def test_broken_reference_solution_is_caught(tmp_path):
    bad = {**CODE, "solution": "def square(n):\n    return n + n\n"}
    assert any("reference solution fails" in e for e in _errors(tmp_path, bad))


def test_tests_that_a_do_nothing_stub_passes_are_caught(tmp_path):
    weak = {**CODE, "solution": "def square(n):\n    print(n * n)\n", "buggy": None,
            "tests": [{"call": "square(3)", "expect": "None"},
                      {"call": "square(1)", "expect": "None", "hidden": True}]}
    assert any("do-nothing stub passes" in e for e in _errors(tmp_path, weak))


def test_tests_that_miss_the_buggy_solution_are_caught(tmp_path):
    # square(2) == 4 and 2 * 2 == 4: the buggy solution slips through
    weak = {**CODE, "tests": [{"call": "square(2)", "expect": "4"},
                              {"call": "square(0)", "expect": "0", "hidden": True}]}
    assert any("buggy solution passes" in e for e in _errors(tmp_path, weak))


def test_infinite_loop_in_a_solution_times_out(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "TIMEOUT_SEC", 1)
    loop = {**CODE, "solution": "def square(n):\n    while True:\n        pass\n", "buggy": None}
    assert any("timeout" in e for e in _errors(tmp_path, loop))


# ------------------------------------------------------- format and references ----
def test_every_wrong_option_needs_a_misconception(tmp_path):
    _, errors = _one(tmp_path, {**MCQ, "misconceptions": {1: "only one"}})
    assert errors and "every wrong option needs a misconception" in errors[0]


def test_answer_index_must_exist(tmp_path):
    _, errors = _one(tmp_path, {**MCQ, "answer": 7})
    assert errors


def test_typo_in_a_field_name_is_an_error_not_ignored(tmp_path):
    item = {**MCQ}
    item["anwser"] = item.pop("answer")
    _, errors = _one(tmp_path, item)
    assert errors


def test_code_question_cannot_be_remember_level(tmp_path):
    _, errors = _one(tmp_path, {**CODE, "bloom": "remember"})
    assert errors and "at least 'apply'" in errors[0]


def test_code_question_needs_visible_and_hidden_tests(tmp_path):
    all_visible = [{**t, "hidden": False} for t in CODE["tests"]]
    _, errors = _one(tmp_path, {**CODE, "tests": all_visible})
    assert errors and "visible and one hidden" in errors[0]


def test_test_needs_exactly_one_outcome(tmp_path):
    both = [{"call": "square(3)", "expect": "9", "raises": "ValueError"}, CODE["tests"][1]]
    _, errors = _one(tmp_path, {**CODE, "tests": both})
    assert errors


def test_unknown_concept_wrong_id_prefix_and_duplicates(tmp_path):
    errors = _errors(tmp_path, {**MCQ, "concepts": ["strings", "quantum_loops"]},
                     {**MCQ, "stem": "Another stem?", "id": "variables-90"},
                     {**CODE}, {**CODE, "stem": "Different stem."})
    text = " | ".join(errors)
    assert "unknown concepts ['quantum_loops']" in text
    assert "variables-90: id must start with its main concept 'strings'" in text
    assert "duplicate id defining_functions-90" in text


def test_broken_yaml_is_reported_not_a_crash(tmp_path):
    errors = _errors(tmp_path, raw="questions:\n  - stem: returns {a: 1}: oops\n")
    assert any("not valid YAML" in e for e in errors)


# ------------------------------------------------------------------- runner ----
def test_runner_keeps_solution_names_apart_from_its_own():
    src = "json = None\nresults = 'mine'\ndef f():\n    return results\n"
    assert runner.run_tests(src, [{"call": "f()", "expect": "'mine'"}]).all_passed


def test_runner_checks_raises_and_exact_types():
    src = "def f(n):\n    if n < 0:\n        raise ValueError\n    return n * 1.0\n"
    run = runner.run_tests(src, [{"call": "f(-1)", "raises": "ValueError"},
                                 {"call": "f(2)", "expect": "2.0"},
                                 {"call": "f(2)", "expect": "2"}])     # 2.0 is not the int 2
    assert run.passed == [True, True, False]


def test_snippet_crash_reports_the_exception_name():
    assert runner.run_snippet('print("a")\nprint(1 + "x")') == "a\nTypeError"


# ------------------------------------------------------------- normalising ----
def test_grading_is_lenient_but_author_checking_is_exact():
    assert normalise_answer("  An   Argument. ") == "an argument"
    assert normalise_output("Hello World  \n") == "Hello World"
    assert normalise_output("Hello World") != normalise_output("hello world")
