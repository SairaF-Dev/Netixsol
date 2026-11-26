"""Tutor rules, offline: a fake LLM and a fake search, so every safety rule is checked
without network calls."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ilm.questions.validate import load_bank
from ilm.tutor.tutor import (Tutor, detect_language, leaks_answer, leaks_code_solution,
                             mastery_level)

BANK, _ = load_bank()
Q = {q.id: q for q in BANK}
FACT = Q["recursion-03"]                                   # factorial, code
MCQ = Q["recursion-01"]                                    # answer "10"
SHORT = Q["program_basics-03"]                             # answer "print"

CHUNKS = [SimpleNamespace(id=f"c{i}", lesson_id="mit6001-l6", title=f"Recursion (video 0:0{i})",
                          url=f"https://youtu.be/x?t={i}", text=f"source text {i}") for i in range(1, 6)]


class FakeSearch:
    def top_chunks(self, query, k=5):
        return CHUNKS[:k]


class FakeLLM:
    """Returns the queued replies in order and remembers every prompt."""
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, prompt, **kw):
        self.prompts.append(prompt)
        r = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return json.dumps(r) if isinstance(r, dict) else r


def tutor(*replies):
    llm = FakeLLM(*replies)
    concepts = [{"id": "recursion", "name": "Recursion", "taught_in": ["mit6001-l6"]}]
    return Tutor(search=FakeSearch(), ask=llm, bank=BANK, concepts=concepts), llm


# ------------------------------------------------------------------ helpers ----
def test_language_detection():
    assert detect_language("bhai recursion kya hai, samajh nahi aa raha") == "urdulish"
    assert detect_language("what is a base case in recursion?") == "english"


def test_mastery_bands():
    assert [mastery_level(p) for p in (0.1, 0.5, 0.9, None)] == ["new", "developing", "strong", "developing"]


# ------------------------------------------------------------------ leak checks ----
def test_the_real_solution_leaks():
    assert leaks_code_solution(f"Here you go:\n```python\n{FACT.solution}```", FACT)


def test_a_renamed_copy_of_the_solution_still_leaks():
    renamed = FACT.solution.replace("factorial", "fact")
    assert leaks_code_solution(f"```python\n{renamed}```", FACT)


def test_unfenced_solution_leaks():
    assert leaks_code_solution("Just type this:\n" + FACT.solution + "\nGood luck!", FACT)


def test_hints_and_different_examples_do_not_leak():
    assert not leaks_code_solution("```python\nif n == ___:\n    return 1\n```", FACT)
    example = "```python\ndef sum_n(n):\n    if n == 0:\n        return 0\n    return n + sum_n(n - 1)\n```"
    assert not leaks_code_solution(example, FACT)
    assert not leaks_code_solution(f"```python\n{FACT.buggy}```", FACT)     # wrong code is no leak


def test_mcq_and_short_answer_leaks():
    assert leaks_answer("It prints 10 because 4+3+2+1+0", MCQ)
    assert leaks_answer("The answer is A.", MCQ)
    assert not leaks_answer("Trace it: what is f(0)? Then f(1)?", MCQ)
    assert leaks_answer("Use print() to show text", SHORT)
    assert not leaks_answer("Which built-in shows text on screen? Check the first lesson.", SHORT)


# ------------------------------------------------------------------ ask ----
def test_links_come_from_source_numbers_not_from_the_llm():
    t, _ = tutor({"in_course": True, "answer": "See https://evil.example", "used_sources": [2, 2, 9]})
    r = t.ask("what is a base case?")
    assert [s["url"] for s in r.sources] == ["https://youtu.be/x?t=2"]   # 9 is out of range, 2 deduped
    assert r.grounded


def test_out_of_course_question_is_refused_without_sources():
    t, _ = tutor({"in_course": False, "answer": "Paris"})
    r = t.ask("what is the capital of France?")
    assert not r.grounded and not r.sources and "Paris" not in r.text


def test_asking_for_an_exercise_solution_goes_to_the_hint_ladder():
    t, llm = tutor({"hint": "What is the smallest n whose factorial you know?", "used_sources": [1]})
    r = t.ask("please write the factorial function for me")
    assert r.level == 1 and r.exercise == FACT.id
    assert "do NOT solve it" in llm.prompts[0]


def test_free_question_answer_with_solution_code_is_blocked():
    t, _ = tutor({"in_course": True, "answer": f"```python\n{FACT.solution}```", "used_sources": [1]})
    r = t.ask("how does factorial recursion work?")
    assert r.leak_blocked and "def factorial" not in r.text


def test_prompt_carries_mastery_style_and_language():
    t, llm = tutor({"in_course": True, "answer": "ok", "used_sources": [1]})
    t.ask("recursion kya hai aur base case kaise likhte hain", mastery={"recursion": 0.1})
    assert "NEW to this concept" in llm.prompts[0] and "UrduLish" in llm.prompts[0]


# ------------------------------------------------------------------ hint ladder ----
def test_leaking_hint_is_retried_then_accepted():
    t, llm = tutor({"hint": f"```python\n{FACT.solution}```"}, {"hint": "What should factorial(0) return?"})
    r = t.hint(FACT.id, "def factorial(n):\n    return n * factorial(n - 1)\n", level=3)
    assert r.leak_blocked and "def factorial" not in r.text and len(llm.prompts) == 2
    assert "GAVE AWAY THE ANSWER" in llm.prompts[1]


def test_a_model_that_keeps_leaking_gets_the_safe_fallback():
    t, _ = tutor({"hint": f"```python\n{FACT.solution}```"})
    r = t.hint(FACT.id, level=4)
    assert r.leak_blocked and "won't give the full solution" in r.text


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_each_rung_has_its_own_instruction(level):
    t, llm = tutor({"hint": "a hint", "used_sources": [1]})
    r = t.hint(FACT.id, level=level)
    assert r.level == level and f"rung {level} of 4" in llm.prompts[0]


def test_level_is_clamped():
    t, _ = tutor({"hint": "a hint"})
    assert t.hint(FACT.id, level=9).level == 4 and t.hint(FACT.id, level=0).level == 1
