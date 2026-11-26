"""Run AUTHOR code (reference solutions, snippets) in a separate process with a timeout.

This is NOT a sandbox for student code: no memory limit, file or network isolation.
Day 4 builds the real sandbox. Here we only protect the validator from our own
mistakes (an accidental infinite loop) and keep each run's names separate.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass

TIMEOUT_SEC = 5
_MARK = "@@ILM_RESULT@@"

# Runs inside the child process. The solution is exec'd in its own namespace so its
# names cannot clash with the runner's (e.g. a solution defining `json` or `results`).
_TEST_HARNESS = r"""
import json, sys
payload = json.loads(sys.stdin.read())
ns = {"__name__": "solution"}
results = []
try:
    exec(compile(payload["source"], "solution.py", "exec"), ns)
except Exception as e:
    print("@@ILM_RESULT@@" + json.dumps({"load_error": f"{type(e).__name__}: {e}"}))
    raise SystemExit
for t in payload["tests"]:
    try:
        got = eval(t["call"], ns)
        if t.get("raises"):
            results.append({"ok": False, "got": repr(got)[:200]})
        else:
            want = eval(t["expect"], {})
            results.append({"ok": got == want and type(got) == type(want), "got": repr(got)[:200]})
    except Exception as e:
        ok = bool(t.get("raises")) and type(e).__name__ == t["raises"]
        results.append({"ok": ok, "got": f"{type(e).__name__}: {e}"[:200]})
print("@@ILM_RESULT@@" + json.dumps({"results": results}))
"""


@dataclass
class TestRun:
    passed: list[bool]
    details: list[str]
    error: str | None = None   # load error or timeout: nothing passed

    @property
    def all_passed(self) -> bool:
        return self.error is None and all(self.passed)


def _python(args: list[str], stdin: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as cwd:  # code that writes files writes them here
        return subprocess.run([sys.executable, "-I", *args], input=stdin, capture_output=True,
                              text=True, timeout=TIMEOUT_SEC, cwd=cwd, encoding="utf-8")


def run_tests(source: str, tests: list[dict]) -> TestRun:
    try:
        proc = _python(["-c", _TEST_HARNESS], json.dumps({"source": source, "tests": tests}))
    except subprocess.TimeoutExpired:
        return TestRun([False] * len(tests), [], error=f"timeout after {TIMEOUT_SEC}s")
    line = next((l for l in proc.stdout.splitlines() if l.startswith(_MARK)), None)
    if line is None:
        return TestRun([False] * len(tests), [], error=f"no result (stderr: {proc.stderr[-300:]})")
    out = json.loads(line[len(_MARK):])
    if "load_error" in out:
        return TestRun([False] * len(tests), [], error=out["load_error"])
    return TestRun([r["ok"] for r in out["results"]], [r["got"] for r in out["results"]])


def run_snippet(code: str) -> str:
    """stdout of a snippet, stripped. A crash adds the exception NAME as the last line
    (e.g. "TypeError"), so an option can simply say TypeError."""
    try:
        proc = _python(["-c", code], "")
    except subprocess.TimeoutExpired:
        return f"<timeout after {TIMEOUT_SEC}s>"
    if proc.returncode != 0:
        last = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "Error"
        return (proc.stdout + last.split(":")[0]).strip()
    return proc.stdout.strip()
