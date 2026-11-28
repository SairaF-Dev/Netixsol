"""Run STUDENT code in a locked-down Docker container (Day 4 Task 1).

Isolation (docker run flags, see DOCKER_FLAGS):
  --network none            no network at all (no DNS, no sockets out)
  --memory / --memory-swap  256 MB RAM, no swap: a memory bomb is OOM-killed
  --cpus 1                  one CPU: spinning threads cannot starve the machine
  --pids-limit 64           a fork bomb hits the ceiling instead of the host
  --read-only + --tmpfs     the image is read-only; /tmp is a 16 MB scratch area in RAM
  --user 65534 (nobody)     not root inside the container
  --cap-drop ALL, no-new-privileges   no mount, no setuid, no raw sockets
  --ulimit fsize / nofile   max 1 MB per file written, 64 open files
  no env, no volumes        host variables (the API key) and host files are never passed in
  wall-clock limit          the host kills the container after the time limit
  output cap                the host reads at most MAX_OUTPUT bytes, then kills it

Grade integrity. Student code runs in the same process as the test loop, so it can read and
patch anything in that process. So the container is never trusted with the verdict:
  - the EXPECTED answers never enter the container; only the test calls do. The container
    reports what each call returned, as plain values (or the exception name); the HOST
    compares with the expected answers. Faking a pass means producing the right return values
    for the hidden tests, which is solving the task.
  - only plain built-in values (int, str, list, dict, ...) are reported; an object whose
    __eq__ always says True is reported as "not a plain value" and fails
  - the result line carries a per-run random nonce and must appear exactly once; the harness
    ends with os._exit(0), so an atexit handler cannot print after it. Any other result-like
    line in the raw output = tampering, flagged for the teacher (never an automatic penalty)
  - student prints go to a buffer, so they cannot interleave with the result line
"""
from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field

IMAGE = "python:3.11-slim"
WALL_SEC = 10
TEST_SEC = 2                     # per-test alarm inside the container (best effort)
MAX_OUTPUT = 64_000              # bytes read from the container before it is killed
MEMORY = "256m"
STARTUP_SEC = 3                  # container start-up allowance (measured about 0.8 s)
DOCKER_FLAGS = [
    "--rm", "-i", "--network", "none",
    "--memory", MEMORY, "--memory-swap", MEMORY,
    "--cpus", "1", "--pids-limit", "64",
    "--read-only", "--tmpfs", "/tmp:rw,size=16m,mode=1777", "--workdir", "/tmp",
    "--user", "65534:65534", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
    "--ulimit", "fsize=1048576:1048576", "--ulimit", "nofile=64:64",
    "--env", "PYTHONDONTWRITEBYTECODE=1",
    "--env", "PYTHONHASHSEED=0",    # same code, same set/dict order, same mark on every run
]

HARNESS = r'''
import sys, os, io, json, signal
_type, _repr, _len, _write, _exit, _str = type, repr, len, os.write, os._exit, str
_dumps, _sorted, _list = json.dumps, sorted, list
payload = json.loads(sys.stdin.read())
NONCE, TEST_SEC, CALLS = payload["nonce"], payload["test_sec"], payload["calls"]
del payload
PLAIN = {int: "int", float: "float", bool: "bool", str: "str", type(None): "none"}

def enc(v, depth=0):
    """Plain built-in values only, with exact types; anything else -> None (not plain)."""
    t = _type(v)
    if depth > 30:
        return None
    if t in PLAIN:
        return [PLAIN[t], _repr(v) if t is float else v]
    if t in (list, tuple):
        items = [enc(x, depth + 1) for x in v]
        return None if None in items else ["list" if t is list else "tuple", items]
    if t is dict:
        items = [[enc(k, depth + 1), enc(x, depth + 1)] for k, x in v.items()]
        return None if any(None in kv for kv in items) else ["dict", items]
    if t in (set, frozenset):
        items = [enc(x, depth + 1) for x in v]
        return None if None in items else [t.__name__, _sorted(items, key=_dumps)]
    return None

def alarm(signum, frame):
    raise TimeoutError("test took longer than " + _str(TEST_SEC) + "s")

out = {"results": []}
captured = io.StringIO()
sys.stdout = captured
ns = {"__name__": "solution"}
try:
    exec(compile(SOURCE_PLACEHOLDER, "solution.py", "exec"), ns)
except BaseException as e:
    out = {"load_error": _type(e).__name__ + ": " + _str(e)[:200]}
if "load_error" not in out:
    for call in CALLS:
        try:
            signal.signal(signal.SIGALRM, alarm)
            signal.alarm(TEST_SEC)
            got = eval(call, ns)
            signal.alarm(0)
            e = enc(got)
            out["results"].append(["value", e] if e is not None else ["not_plain", _repr(got)[:200]])
        except BaseException as e:
            signal.alarm(0)
            out["results"].append(["raised", _type(e).__name__, _str(e)[:150]])
out["printed"] = captured.getvalue()[:2000]
_write(1, ("@@ILM@@" + NONCE + "@@" + _dumps(out) + "\n").encode("utf-8", "replace"))
_exit(0)
'''


@dataclass
class SandboxResult:
    passed: list[bool] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    error: str | None = None             # load error, timeout, crash, tampering: no test passed
    status: str = "ok"                   # ok | load_error | timeout | killed | output_limit | no_result | tampered
    exit_code: int | None = None
    seconds: float = 0.0
    printed: str = ""                    # what the student code printed (captured inside)
    raw_tail: str = ""                   # last bytes of raw container output (for the report)

    @property
    def all_passed(self) -> bool:
        return self.error is None and bool(self.passed) and all(self.passed)

    @property
    def score(self) -> float:
        return sum(self.passed) / len(self.passed) if self.passed else 0.0


class SandboxUnavailable(RuntimeError):
    """Docker itself failed (daemon down, image missing): the SERVER's fault, never a mark of 0."""


# what the docker CLI says when it cannot start a container at all (student code cannot reach the
# CLI's own stderr before the container starts; a student faking it only turns their run into an error)
_DOCKER_DOWN = re.compile(r"^docker: |Cannot connect to the Docker daemon|docker API at|error during connect|"
                          r"Unable to find image|dockerDesktopLinuxEngine", re.M)


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True,
                              timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# ------------------------------------------------------------------ host-side verdict ----
def decode(e):
    """Inverse of the harness's enc(): plain values only (built on the host, never eval'd)."""
    kind, v = e
    if kind in ("int", "bool", "str", "none"):
        return v
    if kind == "float":
        return float(v)
    if kind == "list":
        return [decode(x) for x in v]
    if kind == "tuple":
        return tuple(decode(x) for x in v)
    if kind == "dict":
        return {_hashable(decode(k)): decode(x) for k, x in v}
    if kind in ("set", "frozenset"):
        return (set if kind == "set" else frozenset)(_hashable(decode(x)) for x in v)
    raise ValueError(kind)


def _hashable(v):
    return tuple(_hashable(x) for x in v) if isinstance(v, list) else v


def same(got, want) -> bool:
    """Exact types all the way down (True is not 1, 1.0 is not 1)."""
    if type(got) is not type(want):
        return False
    if isinstance(want, (list, tuple)):
        return len(got) == len(want) and all(same(a, b) for a, b in zip(got, want))
    if isinstance(want, dict):
        return got.keys() == want.keys() and all(same(got[k], want[k]) for k in want)
    return got == want


def verdict(result, test: dict) -> tuple[bool, str]:
    if result[0] == "raised":
        name, msg = result[1], result[2]
        return bool(test.get("raises")) and name == test["raises"], f"{name}: {msg}"
    if result[0] == "not_plain":
        return False, f"returned a non-plain object: {result[1]}"
    try:
        got = decode(result[1])
    except (ValueError, TypeError, KeyError, IndexError):
        return False, "unreadable result"
    if test.get("raises"):
        return False, f"returned {got!r}, expected {test['raises']}"
    return same(got, eval(test["expect"], {"__builtins__": {}}, {})), repr(got)[:200]


# ------------------------------------------------------------------ running ----
def _drain(stream, cap: int, box: dict):
    """Keep the first `cap` bytes, count the rest, and keep reading to EOF: if we stopped
    reading, the pipe would fill and block the container AND `docker kill` (found by the
    output-flood attack)."""
    kept = bytearray()
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        box["total"] = box.get("total", 0) + len(chunk)
        if len(kept) < cap:
            kept += chunk[:cap - len(kept)]
    box["data"] = bytes(kept)


def _quiet(cmd: list[str], timeout: int = 20):
    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        pass


def run(source: str, tests: list[dict], wall_sec: int = WALL_SEC, test_sec: int = TEST_SEC) -> SandboxResult:
    """Run `source` against `tests` in a fresh container. Never raises for student behaviour."""
    nonce = secrets.token_hex(16)
    name = f"ilm-sbx-{uuid.uuid4().hex[:12]}"
    harness = HARNESS.replace("SOURCE_PLACEHOLDER", "SRC")
    harness = "SRC = " + repr(source) + "\n" + harness      # source travels inside the -c argument
    # -s -S, not -I: isolated mode ignores PYTHON* variables, and PYTHONHASHSEED must apply.
    # Safe here: the container environment is only what DOCKER_FLAGS sets (nothing from the host).
    cmd = ["docker", "run", "--name", name, *DOCKER_FLAGS, IMAGE, "python", "-s", "-S", "-c", harness]
    payload = json.dumps({"calls": [t["call"] for t in tests], "nonce": nonce, "test_sec": test_sec}).encode()
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = {}, {}
    readers = [threading.Thread(target=_drain, args=(proc.stdout, MAX_OUTPUT + 1, out), daemon=True),
               threading.Thread(target=_drain, args=(proc.stderr, 8_000, err), daemon=True)]
    for r in readers:
        r.start()
    try:
        proc.stdin.write(payload)
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    status = None
    deadline = t0 + wall_sec + STARTUP_SEC
    while proc.poll() is None:
        if time.time() > deadline:
            status = "timeout"
            break
        if out.get("total", 0) > MAX_OUTPUT:
            status = "output_limit"
            break
        time.sleep(0.05)
    if status:
        _quiet(["docker", "kill", name])
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
    _quiet(["docker", "rm", "-f", name])
    for r in readers:
        r.join(timeout=5)
    raw = out.get("data", b"").decode("utf-8", "replace")
    stderr = err.get("data", b"").decode("utf-8", "replace")
    res = SandboxResult(exit_code=proc.returncode, seconds=round(time.time() - t0, 2), raw_tail=raw[-300:])
    n = len(tests)
    if status is None and out.get("total", 0) > MAX_OUTPUT:
        status = "output_limit"
    if status:
        res.status, res.passed = status, [False] * n
        res.error = f"killed after {wall_sec}s" if status == "timeout" else f"output over {MAX_OUTPUT} bytes"
        return res
    tag = f"@@ILM@@{nonce}@@"
    lines = raw.splitlines()
    tagged = [l for l in lines if l.startswith(tag)]
    fakes = [l for l in lines if "@@ILM" in l and not l.startswith(tag)]
    if len(tagged) != 1:
        res.passed = [False] * n
        if len(tagged) > 1:
            res.status, res.error = "tampered", "several result lines: output tampering"
        elif proc.returncode == 137:
            res.status, res.error = "killed", "killed (exit 137: out of memory or process limit)"
        elif not raw and (proc.returncode == 125 or _DOCKER_DOWN.search(stderr)):
            raise SandboxUnavailable(stderr.strip().splitlines()[-1][:200] if stderr.strip() else f"exit {proc.returncode}")
        else:
            res.status, res.error = "no_result", f"no result (exit {proc.returncode}): {stderr[-200:]}"
        return res
    data = json.loads(tagged[0][len(tag):])
    res.printed = data.get("printed", "")
    if fakes:
        res.status, res.passed = "tampered", [False] * n
        res.error = "output contains fake result lines (flagged for the teacher)"
        return res
    if "load_error" in data:
        res.status, res.error, res.passed = "load_error", data["load_error"], [False] * n
        return res
    for result, test in zip(data["results"], tests):
        ok, detail = verdict(result, test)
        res.passed.append(ok)
        res.details.append(detail)
    if len(res.passed) != n:
        res.status, res.error, res.passed = "no_result", "wrong number of results", [False] * n
    return res
