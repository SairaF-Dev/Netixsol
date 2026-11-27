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
