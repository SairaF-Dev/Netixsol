"""Tutor rules, offline: a fake LLM and a fake search, so every safety rule is checked
without network calls."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ilm.questions.validate import load_bank
from ilm.tutor.tutor import (NEAR_COPY, Tutor, closeness, detect_language, leaks_answer,
                             leaks_code_solution, mastery_level)

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
    assert detect_language("koi milta julta example dikha do na") == "urdulish"     # missed in run 1
    assert detect_language("can you show me a similar example?") == "english"


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
    assert not leaks_answer("```python\nif n == ___:\n    return 1\n```", FACT)
    countdown = ("```python\ndef countdown(n):\n    if n == 0:\n        print('Go!')\n        return\n"
                 "    print(n)\n    countdown(n - 1)\n```")
    assert not leaks_answer(countdown, FACT)
    assert not leaks_code_solution(f"```python\n{FACT.buggy}```", FACT)     # wrong code is no leak


# Found by the tutor evaluation (run 1): each passed the test-running check.
def test_renamed_class_is_a_near_copy():
    keeper = ("```python\nclass ScoreKeeper:\n    def __init__(self):\n        self.points = 0\n"
              "    def add_point(self):\n        self.points = self.points + 1\n```")
    assert leaks_answer(keeper, Q["classes_objects-03"])


def test_solution_plus_one_extra_step_is_a_near_copy():
    square = ("```python\ndef get_square(s):\n    try:\n        return int(s) ** 2\n"
              "    except ValueError:\n        return None\n```")
    assert leaks_answer(square, Q["try_except-02"])


def test_one_line_solution_with_the_given_number_blanked_is_a_near_copy():
    assert leaks_answer("```python\nreturn round((f - ___) * 5 / 9, 1)\n```", Q["floats-04"])


def test_whole_function_with_one_blank_is_a_near_copy():
    blanked = ("```python\ndef to_int(s):\n    try:\n        return ___\n    except ValueError:\n"
               "        return None\n```")
    assert leaks_answer(blanked, Q["try_except-02"])


def test_constant_changed_is_a_near_copy():
    assert leaks_answer("```python\ndef calc(x, y, z):\n    return (x + y + z) / 2\n```",
                        Q["arithmetic_operators-03"])


def test_one_operator_away_is_a_near_copy():
    sum_n = "```python\ndef sum_n(n):\n    if n == 0:\n        return 0\n    return n + sum_n(n - 1)\n```"
    assert leaks_answer(sum_n, FACT)                     # + -> *, 0 -> 1 and it is factorial


def test_examples_with_their_own_logic_are_not_near_copies():
    temp = ('```python\ndef check_temp(temp):\n    if temp > 100:\n        return "Too hot"\n'
            '    elif temp > 80:\n        return "Warm"\n    else:\n        return "Normal"\n```')
    assert not leaks_answer(temp, Q["elif_else-01"])
    positive = "```python\ndef is_positive(n):\n    if n > 0:\n        return True\n    else:\n        return False\n```"
    assert not leaks_answer(positive, Q["modulo-02"])


def test_bank_exercises_are_not_near_copies_of_each_other():
    """The 20% line, checked on pairs that are different problems by definition."""
    code = [q for q in BANK if q.type == "code"]
    close = {(a.id, b.id) for a in code for b in code if a.id != b.id and closeness(a.solution, b.solution) <= NEAR_COPY}
    assert close <= {("f_strings-04", "return_values-03"), ("return_values-03", "f_strings-04")}


def test_retry_tells_the_model_why_its_draft_leaked():
    keeper = ("```python\nclass ScoreKeeper:\n    def __init__(self):\n        self.points = 0\n"
              "    def add_point(self):\n        self.points += 1\n```")
    t, llm = tutor({"hint": keeper}, {"hint": "ok", "used_sources": [1]})
    t.hint("classes_objects-03", level=4)
    assert "renamed names" in llm.prompts[1]


def test_rung_three_code_without_a_blank_is_retried():
    """Held-out run 3: 'houses = {s["house"] for s in students}' (no blank) was the core of the
    answer but 0.29 away from the full solution, so only the rung's own rule catches it."""
    core = '```python\n    houses = {s["house"] for s in students}\n```'
    t, llm = tutor({"hint": core}, {"hint": "```python\nhouses = {___ for s in students}\n```"})
    r = t.hint("sets-02", level=3)
    assert "___" in r.text and "no ___ blank" in llm.prompts[1]


def test_a_rung_that_keeps_leaking_drops_to_the_concept_rung():
    leak = f"```python\n{FACT.solution}```"
    t, llm = tutor({"hint": leak}, {"hint": leak}, {"hint": "This is about the base case of recursion."})
    r = t.hint(FACT.id, level=4)
    assert r.level == 2 and r.leak_blocked and "base case" in r.text
    assert "rung 2 of 4" in llm.prompts[2]


def test_example_that_answers_another_exercise_is_blocked():
    rec_sum_to = "```python\ndef sum_to(n):\n    if n == 0:\n        return 0\n    return n + sum_to(n - 1)\n```"
    t, llm = tutor({"hint": rec_sum_to}, {"hint": "Which two values of n can you answer without recursion?"})
    r = t.hint("recursion-04", level=4)
    assert r.leak_blocked and "sum_to" not in r.text and len(llm.prompts) == 2


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
    assert "beginner meeting this for the first time" in llm.prompts[0] and "UrduLish" in llm.prompts[0]


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
