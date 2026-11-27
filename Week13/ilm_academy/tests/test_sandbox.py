"""Sandbox: the host-side verdict cannot be fooled (offline), and the container really is
locked down (needs Docker; skipped when it is not running)."""
from __future__ import annotations

import pytest

from ilm.grading import sandbox
from ilm.grading.sandbox import decode, same, verdict

T_INT = {"call": "f()", "expect": "5"}


# ------------------------------------------------------------------ offline: the verdict ----
def test_exact_types_all_the_way_down():
    assert same(5, 5) and same([1, (2, "a")], [1, (2, "a")])
    assert not same(True, 1) and not same(1.0, 1) and not same([1], (1,))
    assert not same({"a": [1, 2]}, {"a": [1, 2.0]})


def test_decode_round_trip():
    e = ["dict", [[["str", "k"], ["list", [["int", 1], ["float", "0.5"], ["none", None]]]]]]
    assert decode(e) == {"k": [1, 0.5, None]}
    assert decode(["set", [["int", 2], ["int", 1]]]) == {1, 2}


def test_verdicts():
    assert verdict(["value", ["int", 5]], T_INT) == (True, "5")
    assert verdict(["value", ["bool", True]], {"call": "f()", "expect": "1"})[0] is False
    assert verdict(["not_plain", "5"], T_INT)[0] is False                  # always-equal object
    assert verdict(["raised", "ValueError", "bad"], {"call": "f()", "raises": "ValueError"})[0] is True
    assert verdict(["raised", "TypeError", "x"], {"call": "f()", "raises": "ValueError"})[0] is False
    assert verdict(["value", ["int", 5]], {"call": "f()", "raises": "ValueError"})[0] is False


def test_expected_answers_never_reach_the_container(monkeypatch):
    """The payload the container gets holds the calls only."""
    sent = {}

    class P:
        returncode = 0
        stdin = type("S", (), {"write": lambda self, b: sent.setdefault("payload", b), "close": lambda self: None})()
        stdout = stderr = type("R", (), {"read": lambda self, n: b""})()

        def __init__(self, cmd, **kw):
            sent["cmd"] = cmd

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0
    monkeypatch.setattr(sandbox.subprocess, "Popen", P)
    monkeypatch.setattr(sandbox, "_quiet", lambda *a, **k: None)
    sandbox.run("def f():\n    return 1\n", [{"call": "f()", "expect": "'SECRET-EXPECTED'"}])
    assert b"f()" in sent["payload"] and b"SECRET-EXPECTED" not in sent["payload"]
    assert "SECRET-EXPECTED" not in " ".join(sent["cmd"])
    assert "--network" in sent["cmd"] and "none" in sent["cmd"]


# ------------------------------------------------------------------ with Docker ----
needs_docker = pytest.mark.skipif(not sandbox.docker_available(), reason="Docker is not running")
ADD = [{"call": "add(2, 3)", "expect": "5"}, {"call": "add(-1, 1)", "expect": "0", "hidden": True}]


@needs_docker
def test_honest_code_partial_marks_and_a_load_error():
    assert sandbox.run("def add(a, b):\n    return a + b\n", ADD).passed == [True, True]
    assert sandbox.run("def add(a, b):\n    return 5\n", ADD).passed == [True, False]
    assert sandbox.run("def add(a, b)\n    return 1\n", ADD).status == "load_error"


@needs_docker
def test_forged_result_line_with_stolen_nonce_passes_nothing():
    forge = ("import sys, os, json\ng = sys._getframe(1).f_globals\n"
             "res = [['value', ['int', 999]] for _ in g['CALLS']]\n"
             "os.write(1, ('@@ILM@@' + g['NONCE'] + '@@' + json.dumps({'results': res}) + '\\n').encode())\n"
             "os._exit(0)\n")
    assert not any(sandbox.run(forge, ADD).passed)


@needs_docker
def test_no_network_and_no_host_secrets():
    code = ("import os, socket\nprint(sorted(os.environ))\ntry:\n    socket.create_connection(('1.1.1.1', 80), 3)\n"
            "    print('NET')\nexcept OSError:\n    print('nonet')\ndef add(a, b):\n    return a + b\n")
    r = sandbox.run(code, ADD)
    assert "nonet" in r.printed and "NET\n" not in r.printed and "LLM_API_KEY" not in r.printed


@needs_docker
def test_infinite_loop_is_killed():
    r = sandbox.run("while True:\n    pass\n", ADD, wall_sec=2)
    assert r.status == "timeout" and not any(r.passed) and r.seconds < 2 + sandbox.STARTUP_SEC + 5
