"""API: login and roles work, and no response ever carries a hidden test."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from ilm import config
from ilm.api import auth, service


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "API_DB", tmp_path / "test.sqlite3")
    from ilm.api.main import app
    return TestClient(app)


def login(c, user="ali"):
    r = c.post("/api/auth/login", json={"username": user, "password": auth.DEV_PASSWORD})
    assert r.status_code == 200, r.text
    return r


def test_login_sets_an_httponly_cookie_and_wrong_password_is_refused(client):
    r = login(client)
    assert "httponly" in r.headers["set-cookie"].lower() and r.json()["role"] == "student"
    bad = client.post("/api/auth/login", json={"username": "ali", "password": "wrong"})
    assert bad.status_code == 401 and "don't match" in bad.json()["detail"]


def test_pages_need_a_session_and_the_right_role(client):
    assert client.get("/api/me").status_code == 401
    login(client, "teacher")
    assert client.get("/api/me/path").status_code == 403
    assert client.post("/api/submissions", json={"exercise": "modulo-02", "code": "x"}).status_code == 403


def test_a_forged_or_tampered_token_is_refused(client):
    client.cookies.set(auth.COOKIE, "not.a.jwt")
    assert client.get("/api/me").status_code == 401


def test_student_path_is_the_real_plan(client):
    login(client)
    p = client.get("/api/me/path").json()
    assert p["days"] == 32 and p["concepts_total"] == 65 and p["path"][0]["name"]


def test_exercise_pages_never_carry_hidden_tests(client):
    login(client)
    for ex in client.get("/api/exercises").json():
        page = client.get(f"/api/exercises/{ex['id']}").text
        q = service.bank()[ex["id"]]
        for t in q.tests:
            if t.hidden and t.call not in q.stem:       # a case the task text states is no secret
                assert t.call not in page, (ex["id"], t.call)


def test_public_result_is_a_whitelist_without_hidden_tests():
    fb = {"mark": 3.3, "rules_broken": [], "slow": None, "lesson": None,
          "quality": {"issues": []}, "one_improvement": {"kind": "fix a wrong result", "text": "x"},
          "tests": {"passed": 1, "total": 2,
                    "visible_failed": [{"call": "f(1)", "expected": "1", "got": "2", "why": "wrong"}],
                    "hidden_failed": 1, "hidden_failed_how": [{"how": "returned a wrong value", "count": 1}]},
          "_hidden_calls": [{"call": "f(SECRET)", "expect": "'SECRET'"}]}
    graded = {"status": "ok", "test_results": [{"call": "f(SECRET)", "expect": "'SECRET'", "hidden": True}]}
    assert "SECRET" not in json.dumps(service.public_result(fb, graded))


def test_submissions_are_rate_limited(monkeypatch):
    service._recent.clear()
    monkeypatch.setattr(service, "PER_MINUTE", 2)
    assert [service.rate_limited("u") for _ in range(3)] == [False, False, True]


# ------------------------------------------------------------------ teacher ----
FAKE_CLASS = {"cohort": "test", "week": 3, "enrolled": 10, "in_class": 8, "left_before_week": 2,
              "active_this_week": 6, "high": 1, "medium": 2, "avg_mastered": 1.5, "concepts_total": 65,
              "weakest": [], "heatmap": {"concepts": [], "sections": []}, "section_note": "n",
              "at_risk": [{"student_id": "s1", "level": "high", "risk": 0.9, "reason": "Inactive",
                           "why": ["no answers for 9 days"], "action": "a", "level_action": "b"}]}


@pytest.fixture
def teacher(client, monkeypatch):
    """Reads the real review sources (read-only); decisions go to the temp API_DB."""
    from ilm.api import classroom, review
    monkeypatch.setattr(classroom, "load", lambda: FAKE_CLASS)
    real = config.PROJECT_ROOT / "data"
    monkeypatch.setattr(config, "DATA_DIR", real)
    monkeypatch.setattr(config, "PROCESSED_DIR", real / "processed")
    review._similarity_source.cache_clear()
    review._graded_source.cache_clear()
    login(client, "teacher")
    yield client
    review._similarity_source.cache_clear()
    review._graded_source.cache_clear()


def test_teacher_pages_are_for_teachers_only(client, monkeypatch):
    from ilm.api import classroom
    monkeypatch.setattr(classroom, "load", lambda: FAKE_CLASS)
    login(client, "ali")
    for path in ("/api/class/overview", "/api/class/at-risk", "/api/review"):
        assert client.get(path).status_code == 403


def test_overview_and_at_risk(teacher):
    o = teacher.get("/api/class/overview").json()
    assert o["in_class"] == 8 and "review_open" in o and "at_risk" not in o
    assert teacher.get("/api/class/at-risk").json()["students"][0]["reason"] == "Inactive"


def test_review_queue_never_carries_the_benchmark_answer(teacher):
    q = teacher.get("/api/review").json()
    assert q["counts"]["similarity"] == 30
    sim = next(i for i in q["items"] if i["kind"] == "similarity")
    page = teacher.get(f"/api/review/{sim['id']}").text
    assert "ground_truth" not in page and "disguise" not in page and "copied" not in page.lower()
    d = teacher.get(f"/api/review/{sim['id']}").json()
    assert len(d["sides"]) == 2 and d["sides"][0]["code"]


def test_decisions_are_validated_and_stored(teacher):
    item = teacher.get("/api/review").json()["items"][0]
    assert teacher.post(f"/api/review/{item['id']}", json={"decision": "Delete student"}).status_code == 422
    assert teacher.post(f"/api/review/{item['id']}", json={"decision": item["options"][0]}).status_code == 200
    again = next(i for i in teacher.get("/api/review").json()["items"] if i["id"] == item["id"])
    assert again["decision"] == item["options"][0]


def test_reasons_are_written_in_words():
    from ilm.api.classroom import in_words
    assert in_words("acc_last10", 0.3) == "3 of the last 10 answers right"
    assert in_words("days_since_last", 9) == "no answers for 9 days"
    assert in_words("acc_last10", float("nan")) is None                 # no value: no reason text


# ------------------------------------------------------------------ tutor ----
class FakeTutor:
    def __init__(self, fail=None):
        self.fail, self.calls = fail, []

    def ask(self, message, mastery=None, language="auto"):
        from ilm.tutor.tutor import Reply
        self.calls.append(("ask", message, mastery))
        if self.fail:
            raise self.fail
        return Reply("A base case stops the recursion.", [{"title": "Recursion (video 3:29)", "url": "u"}])

    def hint(self, qid, student_code="", message="", level=1, mastery=None, language="auto"):
        from ilm.tutor.tutor import Reply
        self.calls.append(("hint", qid, level))
        return Reply("What should factorial(0) return?", [], level=level, exercise=qid)


@pytest.fixture
def tutor(monkeypatch):
    from ilm.api import tutor_api
    fake = FakeTutor()
    monkeypatch.setattr(tutor_api, "_tutor", fake)
    tutor_api._calls.clear()
    return fake


def test_tutor_answers_with_sources_and_the_students_mastery(client, tutor):
    login(client)
    r = client.post("/api/tutor/ask", json={"message": "what is a base case?"}).json()
    assert r["sources"][0]["title"].startswith("Recursion") and tutor.calls[0][2]      # mastery from the plan
    h = client.post("/api/tutor/hint", json={"exercise": "recursion-03", "level": 2}).json()
    assert h["level"] == 2 and h["level_name"] == "concept pointer"


def test_tutor_is_for_students_and_validates_input(client, tutor):
    login(client, "teacher")
    assert client.post("/api/tutor/ask", json={"message": "hi"}).status_code == 403
    login(client)
    assert client.post("/api/tutor/hint", json={"exercise": "recursion-03", "level": 9}).status_code == 422
    assert client.post("/api/tutor/hint", json={"exercise": "nope-01", "level": 1}).status_code == 404


def test_tutor_limit_and_honest_unavailable_message(client, tutor, monkeypatch):
    from ilm.api import tutor_api
    login(client)
    monkeypatch.setattr(tutor_api, "PER_MINUTE", 1)
    assert client.post("/api/tutor/ask", json={"message": "a"}).status_code == 200
    assert client.post("/api/tutor/ask", json={"message": "b"}).status_code == 429
    tutor_api._calls.clear()
    monkeypatch.setattr(tutor_api, "_tutor", FakeTutor(fail=RuntimeError("429 RESOURCE_EXHAUSTED")))
    r = client.post("/api/tutor/ask", json={"message": "c"})
    assert r.status_code == 503 and "limit" in r.json()["detail"]


def test_tutor_log_keeps_no_student_text(client, tutor):
    login(client)
    client.post("/api/tutor/ask", json={"message": "MY PRIVATE QUESTION"})
    import sqlite3
    rows = sqlite3.connect(config.API_DB).execute("SELECT * FROM tutor_log").fetchall()
    assert rows and "MY PRIVATE QUESTION" not in str(rows)


def test_starter_shows_the_signature_but_no_line_of_the_answer():
    q = service.bank()["recursion-03"]
    s = service.starter_code(q)
    assert s.startswith("def factorial(n):") and "return" not in s
    for qid, q in service.bank().items():
        if q.type == "code":
            body = [l for l in service.starter_code(q).splitlines()[1:] if l.strip() and l.strip() != "..."]
            assert not body or q.starter, qid           # nothing beyond the header unless the bank wrote a starter


# ------------------------------------------------------------------ question practice ----
@pytest.fixture(autouse=True)
def real_bkt_params(monkeypatch):
    """Practice reads the fitted BKT parameters (read-only) from the real models/ folder."""
    from ilm.api import practice
    monkeypatch.setattr(config, "MODELS_DIR", config.PROJECT_ROOT / "models")
    practice.bkt_params.cache_clear()
    yield
    practice.bkt_params.cache_clear()


def test_questions_go_out_without_their_answer(client):
    login(client)
    r = client.get("/api/practice/next", params={"concept": "modulo"}).json()
    q = r["question"]
    assert q and "answer" not in q and "accept" not in q and "misconceptions" not in q
    assert r["total"] >= 2 and r["mastery"]["p_known"] is not None


def test_wrong_mcq_shows_its_misconception_and_moves_mastery(client):
    """String methods: Ali's plan puts it at P(known) 0.14, so each answer visibly moves it."""
    login(client)
    bank_q = service.bank()["string_methods-01"]               # strip(): prints [Ada]
    wrong = next(i for i in range(len(bank_q.options)) if i != bank_q.answer)
    r = client.post("/api/answers", json={"question": bank_q.id, "choice": wrong}).json()
    assert r["correct"] is False and r["misconception"] == bank_q.misconceptions[wrong]
    assert r["right_answer"] == bank_q.options[bank_q.answer] == r["output"]        # what the code really prints
    assert r["after"]["p_known"] < r["before"]["p_known"]
    ok = client.post("/api/answers", json={"question": bank_q.id, "choice": bank_q.answer}).json()
    assert ok["correct"] and ok["after"]["p_known"] > r["after"]["p_known"]
    nxt = client.get("/api/practice/next", params={"concept": "string_methods"}).json()
    assert nxt["done"] >= 1 and (nxt["question"] is None or nxt["question"]["id"] != bank_q.id)


def test_short_answers_are_graded_leniently_and_bad_input_refused(client):
    login(client)
    assert client.post("/api/answers", json={"question": "program_basics-03", "text": " Print "}).json()["correct"]
    assert client.post("/api/answers", json={"question": "program_basics-03", "text": ""}).status_code == 422
    assert client.post("/api/answers", json={"question": "modulo-01", "choice": 7}).status_code == 422
    assert client.post("/api/answers", json={"question": "recursion-03", "text": "x"}).status_code == 404   # code exercise


def test_a_missed_question_comes_back_only_after_the_others(client):
    login(client)
    first = client.get("/api/practice/next", params={"concept": "string_methods"}).json()["question"]
    q = service.bank()[first["id"]]
    wrong = {"choice": next(i for i in range(len(q.options)) if i != q.answer)} if q.type == "mcq" else {"text": "zzz"}
    client.post("/api/answers", json={"question": q.id, **wrong})
    assert client.get("/api/practice/next", params={"concept": "string_methods"}).json()["question"]["id"] != q.id


# ------------------------------------------------------------------ teacher extras ----
def test_question_health_and_decisions(teacher):
    h = teacher.get("/api/questions/health").json()
    assert h["counts"]["retire"] == 13 and len(h["retire"]) == 13 and h["retire"][0]["stem"]
    qid = h["retire"][0]["id"]
    assert teacher.post(f"/api/questions/{qid}/decision", json={"decision": "Relabel"}).status_code == 422  # needs a level
    assert teacher.post(f"/api/questions/{qid}/decision", json={"decision": "Retire"}).status_code == 200
    again = teacher.get("/api/questions/health").json()
    assert next(r for r in again["retire"] if r["id"] == qid)["decision"]["decision"] == "Retire"


def test_tutor_safety_and_impact_come_from_the_reports(teacher):
    s = teacher.get("/api/tutor/safety").json()
    assert s["evaluation"][0]["leaks"] == 6 and s["judge_caught_code_leaks"] == 0
    i = teacher.get("/api/impact").json()
    assert i["sandbox"]["contained"] == i["sandbox"]["attacks"] == 24
    d = i["adaptive"]["diff"]["dropped_by_week3"]
    assert d["low"] <= d["diff"] <= d["high"] < 0                                 # the whole 95% CI is a drop
    assert i["dropout_model"]["baseline"] > i["dropout_model"]["lightgbm"]       # shown honestly


def test_extras_are_teacher_only(client):
    login(client)
    for path in ("/api/questions/health", "/api/tutor/safety", "/api/impact"):
        assert client.get(path).status_code == 403
