"""When Docker itself fails, the student must not get a mark of 0 or see Docker's error text."""
import json
import subprocess
import sys

import pytest

from ilm.api import service
from ilm.grading import sandbox

DOWN = "docker: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine\n"


def _fake_docker(stderr: str, code: int, stdout: str = ""):
    real = subprocess.Popen

    def popen(cmd, *a, **k):
        if cmd[:2] == ["docker", "run"]:
            script = f"import sys; sys.stdout.write({stdout!r}); sys.stderr.write({stderr!r}); sys.exit({code})"
            cmd = [sys.executable, "-c", script]
        return real(cmd, *a, **k)
    return popen


@pytest.fixture
def no_cleanup(monkeypatch):
    monkeypatch.setattr(sandbox, "_quiet", lambda *a, **k: None)


def test_docker_down_raises_instead_of_failing_the_student(monkeypatch, no_cleanup):
    monkeypatch.setattr(sandbox.subprocess, "Popen", _fake_docker(DOWN, 1))
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.run("def f():\n    return 1\n", [{"call": "f()"}])


def test_image_missing_raises(monkeypatch, no_cleanup):
    monkeypatch.setattr(sandbox.subprocess, "Popen", _fake_docker("Unable to find image 'python:3.11-slim' locally\n", 125))
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.run("x = 1\n", [{"call": "x"}])


def test_student_crash_is_still_a_normal_result(monkeypatch, no_cleanup):
    """A program that dies with output of its own is the student's result, not an outage."""
    monkeypatch.setattr(sandbox.subprocess, "Popen", _fake_docker("Traceback: boom\n", 1, stdout="hello\n"))
    res = sandbox.run("x = 1\n", [{"call": "x"}])
    assert res.status == "no_result" and res.passed == [False]


def test_service_reports_outage_without_a_mark(monkeypatch, tmp_path):
    monkeypatch.setattr(service.config, "API_DB", tmp_path / "t.sqlite3")
    monkeypatch.setattr(service, "lesson_index", lambda: None)

    def down(*a, **k):
        raise sandbox.SandboxUnavailable("docker API at npipe")
    monkeypatch.setattr("ilm.grading.grader.sandbox.run", down)
    qid = next(q.id for q in service.bank().values() if q.type == "code")
    sid = "t1"
    with service._db_lock, service._db() as con:
        con.execute("INSERT INTO submissions VALUES (?, 'ali', ?, 'x', 'queued', NULL, 0, NULL)", (sid, qid))
    service._grade(sid, qid, "def f():\n    return 1\n")
    s = service.get_submission(sid, "ali")
    assert s["status"] == "error"
    assert "not marked" in s["result"]["message"] and "docker" not in json.dumps(s["result"]).lower()
