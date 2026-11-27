"""Attack the sandbox with malicious student code and record what happened (Day 4 Task 1).

    python -m ilm.grading.attacks      -> reports/sandbox/attack_report.{md,json}

Every attack is a "solution" to a trivial exercise, add(a, b), so a successful attack would
show up either as harm (the host is affected or a secret leaks) or as a FALSE PASS (the
grader says the tests passed). Each attack has an expectation and a check on the result;
the host's health is checked after the whole suite (Docker still answers, no stray containers).

These attacks are only ever run INSIDE the sandbox. Never run them with the plain local runner.
"""
from __future__ import annotations

import json
import subprocess
import time

from ilm import config
from ilm.grading import sandbox

TESTS = [{"call": "add(2, 3)", "expect": "5"}, {"call": "add(-1, 1)", "expect": "0", "hidden": True}]
GOOD = "def add(a, b):\n    return a + b\n"


def no_pass(r):
    return not any(r.passed)


def secret_free(r):
    text = r.printed + r.raw_tail + " ".join(r.details)
    key = config.LLM_API_KEY
    return (not key or key not in text) and "LLM_API_KEY" not in text and "GEMINI" not in text


# name, category, code, what a safe sandbox does, check(result) -> bool
ATTACKS = [
    ("infinite loop", "resource", "while True:\n    pass\n" + GOOD,
     "killed at the time limit; no test passes", lambda r: r.status == "timeout" and no_pass(r)),
    ("sleep forever", "resource", "import time\ntime.sleep(10**6)\n" + GOOD,
     "killed at the time limit", lambda r: r.status == "timeout" and no_pass(r)),
    ("fork bomb", "resource",
     "import os\nwhile True:\n    try:\n        os.fork()\n    except OSError:\n        pass\n" + GOOD,
     "stopped by the 64-process limit, then the time limit; host unaffected",
     lambda r: r.status in ("timeout", "killed", "no_result") and no_pass(r)),
    ("memory bomb", "resource", "x = []\nwhile True:\n    x.append('a' * 10**7)\n" + GOOD,
     "MemoryError or OOM kill at 256 MB", lambda r: r.status in ("killed", "load_error", "no_result") and no_pass(r)),
    ("CPU threads", "resource",
     "import threading\ndef spin():\n    while True:\n        pass\nfor _ in range(32):\n"
     "    threading.Thread(target=spin, daemon=True).start()\n" + GOOD,
     "limited to 1 CPU; the tests still run (threads do not block grading)", lambda r: r.status in ("ok", "timeout")),
    ("output flood", "resource", "import os\nwhile True:\n    os.write(1, b'x' * 65536)\n" + GOOD,
     "killed at the output cap", lambda r: r.status == "output_limit" and no_pass(r)),
    ("disk fill /tmp", "resource",
     "f = open('/tmp/big', 'wb')\ntry:\n    while True:\n        f.write(b'0' * 10**6)\nexcept OSError as e:\n"
     "    print('stopped:', e)\n" + GOOD,
     "stopped by the 1 MB file-size limit / 16 MB tmpfs; grading continues",
     lambda r: r.status in ("ok", "no_result", "killed") and ("stopped" in r.printed or r.status != "ok")),
    ("deep recursion", "resource", "import sys\nsys.setrecursionlimit(10**6)\ndef f(n):\n    return f(n + 1)\nf(0)\n" + GOOD,
     "crash stays inside the container", lambda r: r.status in ("load_error", "no_result", "killed") and no_pass(r)),
    ("read environment", "secrets", "import os\nprint(dict(os.environ))\n" + GOOD,
     "no host variables, no API key", secret_free),
    ("read /proc/1/environ", "secrets", "print(open('/proc/1/environ', 'rb').read())\n" + GOOD,
     "only the container's own variables", secret_free),
    ("read project .env", "secrets",
     "import glob\nfor p in ['/ilm_academy/.env', '/app/.env', '/home/.env'] + [p for d in ('/home', '/root', '/app', '/srv', '/mnt', '/opt', '/tmp', '/workspace') for p in glob.glob(d + '/**/.env', recursive=True)]:\n"
     "    try:\n        print(p, open(p).read()[:100])\n    except Exception as e:\n        print(p, type(e).__name__)\n" + GOOD,
     "host files are not mounted, so there is no .env to find", secret_free),
    ("read /etc/shadow", "secrets",
     "try:\n    print(open('/etc/shadow').read()[:50])\nexcept Exception as e:\n    print('blocked', type(e).__name__)\n" + GOOD,
     "PermissionError (runs as nobody)", lambda r: "blocked PermissionError" in r.printed),
    ("network: raw socket", "network",
     "import socket\ntry:\n    socket.create_connection(('1.1.1.1', 80), timeout=3)\n    print('CONNECTED')\nexcept Exception as e:\n"
     "    print('blocked', type(e).__name__)\n" + GOOD,
     "no route out", lambda r: "blocked" in r.printed and "CONNECTED" not in r.printed),
    ("network: HTTP + DNS", "network",
     "import urllib.request\ntry:\n    urllib.request.urlopen('http://example.com', timeout=3)\n    print('CONNECTED')\n"
     "except Exception as e:\n    print('blocked', type(e).__name__)\n" + GOOD,
     "no DNS, no HTTP", lambda r: "blocked" in r.printed and "CONNECTED" not in r.printed),
    ("write outside /tmp", "filesystem",
     "for p in ['/usr/local/lib/evil.py', '/etc/evil', '/evil']:\n    try:\n        open(p, 'w').write('x')\n"
     "        print('WROTE', p)\n    except Exception as e:\n        print('blocked', p, type(e).__name__)\n" + GOOD,
     "read-only filesystem", lambda r: "WROTE" not in r.printed and r.printed.count("blocked") == 3),
    ("become root", "privilege",
     "import os\nfor f in (lambda: os.setuid(0), lambda: os.system('mount -t tmpfs x /mnt')):\n    try:\n"
     "        print('result', f())\n    except Exception as e:\n        print('blocked', type(e).__name__)\n"
     "print('uid', os.getuid())\n" + GOOD,
     "setuid fails, mount fails, uid stays 65534",
     lambda r: "uid 65534" in r.printed and "blocked PermissionError" in r.printed),
    ("fake result line", "grade integrity",
     "import os\nos.write(1, b'@@ILM@@0123@@{\"results\": [[\"value\", [\"int\", 5]], [\"value\", [\"int\", 0]]]}\\n')\n"
     "def add(a, b):\n    return -999\n",
     "flagged as tampering; no test passes", lambda r: r.status == "tampered" and no_pass(r)),
    ("steal nonce + forge + exit", "grade integrity",
     "import sys, os, json\ng = sys._getframe(1).f_globals\nres = [['value', ['int', 999]] for _ in g['CALLS']]\n"
     "os.write(1, ('@@ILM@@' + g['NONCE'] + '@@' + json.dumps({'results': res}) + '\\n').encode())\nos._exit(0)\n",
     "the forged line is accepted as the result, but the HOST compares 999 with the expected "
     "answers, so nothing passes (expected answers never enter the container)", lambda r: no_pass(r)),
    ("always-equal object", "grade integrity",
     "class Yes:\n    def __eq__(self, other):\n        return True\n    def __repr__(self):\n        return '5'\n"
     "def add(a, b):\n    return Yes()\n",
     "reported as a non-plain object; fails", lambda r: no_pass(r) and "non-plain" in " ".join(r.details)),
    ("int subclass", "grade integrity",
     "class Fake(int):\n    def __eq__(self, other):\n        return True\ndef add(a, b):\n    return Fake(0)\n",
     "exact type check: Fake is not int; fails", lambda r: no_pass(r)),
    ("patch builtins", "grade integrity",
     "import builtins, json\nbuiltins.type = lambda x: int\nbuiltins.repr = lambda x: '5'\njson.dumps = lambda *a, **k: '{}'\n"
     "def add(a, b):\n    return -999\n",
     "the harness kept its own references; 0 is reported and fails", lambda r: no_pass(r)),
    ("atexit fake line", "grade integrity",
     "import atexit, os\natexit.register(lambda: os.write(1, b'@@ILM@@x@@{}\\n'))\ndef add(a, b):\n    return -999\n",
     "os._exit skips atexit; fails normally", lambda r: no_pass(r) and r.status == "ok"),
    ("hardcode visible test", "grade integrity",
     "def add(a, b):\n    return 5\n",
     "passes the visible test only; the hidden test catches it (partial marks)", lambda r: r.passed == [True, False]),
    ("control: correct solution", "control", GOOD,
     "both tests pass (the sandbox does not break honest code)", lambda r: r.passed == [True, True]),
]


def host_health() -> dict:
    t0 = time.time()
    ok = sandbox.docker_available()
    left = subprocess.run(["docker", "ps", "-a", "--filter", "name=ilm-sbx-", "--format", "{{.Names}}"],
                          capture_output=True, text=True, timeout=30).stdout.split()
    return {"docker_responds": ok, "seconds_to_respond": round(time.time() - t0, 2), "leftover_containers": left}


def main():
    out_dir = config.PROJECT_ROOT / "reports" / "sandbox"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, cat, code, expect, check in ATTACKS:
        r = sandbox.run(code, TESTS)
        ok = bool(check(r))
        rows.append({"attack": name, "category": cat, "expected": expect, "contained": ok, "status": r.status,
                     "passed_tests": r.passed, "exit_code": r.exit_code, "seconds": r.seconds,
                     "error": (r.error or "")[:160], "printed": r.printed[:200].replace(config.LLM_API_KEY or "\0", "<KEY>")})
        print(f"{'OK ' if ok else 'BAD'} {name}: {r.status} {r.passed} {r.seconds}s", flush=True)
    health = host_health()
    report = {"image": sandbox.IMAGE, "flags": sandbox.DOCKER_FLAGS, "wall_sec": sandbox.WALL_SEC,
              "attacks": len(rows), "contained": sum(r["contained"] for r in rows), "host_after": health, "rows": rows}
    (out_dir / "attack_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (out_dir / "attack_report.md").write_text(to_markdown(report), encoding="utf-8")
    print(f"\n{report['contained']}/{report['attacks']} contained; host after: {health}")


def to_markdown(rep: dict) -> str:
    L = ["# Sandbox attack report", "",
         f"Image `{rep['image']}`, time limit {rep['wall_sec']} s (+ start-up). Flags: `{' '.join(rep['flags'])}`.", "",
         f"**{rep['contained']} of {rep['attacks']} attacks behaved as expected.** After the suite: Docker "
         f"responds = {rep['host_after']['docker_responds']}, leftover sandbox containers = "
         f"{len(rep['host_after']['leftover_containers'])}.", "",
         "Every attack is a submission for `add(a, b)` with one visible and one hidden test, so a "
         "successful attack would show up as harm or as a false pass.", "",
         "| attack | category | expected | result | tests passed | time | ok |", "|---|---|---|---|---|---|---|"]
    for r in rep["rows"]:
        what = r["status"] + (f": {r['error']}" if r["error"] else "") + (f" / printed: `{r['printed'][:80]}`" if r["printed"] else "")
        L.append(f"| {r['attack']} | {r['category']} | {r['expected']} | {what.replace('|', '/')} | "
                 f"{sum(r['passed_tests'])}/{len(r['passed_tests'])} | {r['seconds']}s | {'yes' if r['contained'] else '**NO**'} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
