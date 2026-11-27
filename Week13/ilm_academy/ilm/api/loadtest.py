"""Load test: 500 code submissions in 10 minutes (Day 5 Task 3). Standard library only.

    ILM_LOADTEST_PASSWORD=<demo password> python -m ilm.api.loadtest --base http://127.0.0.1:8010
    python -m ilm.api.loadtest ... --burst 100          (100 at once, like a deadline)

What it sends: the 50 graded submissions (data/grading/submissions.json) cycled, so the mix is
realistic: correct, wrong, crashing and 2 infinite loops (each holds a worker for the full time
limit). Steady arrivals at --total over --minutes (the spec: 500 in 10), alternating the demo
students. Measured per submission: time from POST to a finished result. The server's per-student
limit (12 a minute) must be raised for the test: ILM_SUBMIT_PER_MINUTE.
"""
from __future__ import annotations

import argparse
import os
import json
import statistics
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

SUBMISSIONS = Path(__file__).resolve().parents[2] / "data" / "grading" / "submissions.json"


class Client:
    """Sends the session cookie itself. In prod the cookie is Secure (HTTPS only), and a cookie
    jar rightly will not send it to http://127.0.0.1, so a jar-based test got 401 on every call
    (found in the first codespace run). The test runs on the server itself, so this is safe."""

    def __init__(self, base: str, user: str, password: str):
        self.base = base.rstrip("/")
        self.cookie = ""
        req = urllib.request.Request(self.base + "/api/auth/login",
                                     data=json.dumps({"username": user, "password": password}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for c in r.headers.get_all("Set-Cookie") or []:
                if c.startswith("ilm_session="):
                    self.cookie = c.split(";", 1)[0]
        if not self.cookie:
            raise SystemExit("login returned no session cookie")

    def call(self, path: str, body: dict | None = None):
        headers = {"Cookie": self.cookie}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 2)


def run(base: str, password: str, total: int, minutes: float, burst: bool, poll: float = 1.0) -> dict:
    subs = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))
    clients = [Client(base, u, password) for u in ("ali", "sara")]
    results: dict[int, dict] = {}
    lock = threading.Lock()
    gap = 0 if burst else minutes * 60 / total
    t0 = time.time()

    def submit(i: int):
        s = subs[i % len(subs)]
        c = clients[i % len(clients)]
        start = time.time()
        try:
            sid = c.call("/api/submissions", {"exercise": s["exercise"], "code": s["code"]})["id"]
            with lock:
                results[i] = {"sid": sid, "client": c, "start": start, "kind": s["kind"], "done": None}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            with lock:
                results[i] = {"start": start, "kind": s["kind"], "error": f"submit: {getattr(e, 'code', e)}", "done": start}

    def poller():
        while True:
            with lock:
                pending = [(i, r) for i, r in results.items() if r["done"] is None]
                finished_sending = len(results) == total
            if not pending and finished_sending:
                return
            for i, r in pending:
                try:
                    d = r["client"].call(f"/api/submissions/{r['sid']}")
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                    continue
                if d["status"] in ("done", "error"):
                    with lock:
                        r.update(done=time.time(), status=d["status"],
                                 passed=(d.get("result") or {}).get("passed"), server_seconds=d.get("seconds"))
            time.sleep(poll)

    watcher = threading.Thread(target=poller, daemon=True)
    watcher.start()
    senders = []
    for i in range(total):
        target = t0 + i * gap
        delay = target - time.time()
        if delay > 0:
            time.sleep(delay)
        th = threading.Thread(target=submit, args=(i,), daemon=True)
        th.start()
        senders.append(th)
    for th in senders:
        th.join()
    sent_at = time.time() - t0
    watcher.join(timeout=minutes * 60 + 900)
    end = time.time() - t0

    rows = list(results.values())
    ok = [r for r in rows if r.get("status") == "done"]
    lat = [r["done"] - r["start"] for r in ok]
    lat_normal = [r["done"] - r["start"] for r in ok if r["kind"] != "timeout"]
    last_done = max((r["done"] for r in rows if r["done"]), default=t0) - t0
    return {
        "mode": "burst" if burst else "steady",
        "submissions": total, "planned_minutes": minutes if not burst else 0,
        "sent_in_seconds": round(sent_at, 1), "all_finished_after_seconds": round(last_done, 1),
        "finished_ok": len(ok), "errors": sum(1 for r in rows if r.get("error") or r.get("status") == "error"),
        "unfinished": sum(1 for r in rows if r["done"] is None),
        "seconds_submit_to_result": {"p50": percentile(lat, 50), "p95": percentile(lat, 95), "max": percentile(lat, 100)},
        "seconds_excluding_infinite_loops": {"p50": percentile(lat_normal, 50), "p95": percentile(lat_normal, 95)},
        "throughput_per_minute": round(len(ok) / (last_done / 60), 1) if last_done else None,
        "mix": {k: sum(r["kind"] == k for r in rows) for k in sorted({r["kind"] for r in rows})},
        "total_seconds": round(end, 1),
        "median_server_seconds": statistics.median([r["server_seconds"] for r in ok if r.get("server_seconds")] or [0]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--password", default=os.getenv("ILM_LOADTEST_PASSWORD"),
                    help="better: set ILM_LOADTEST_PASSWORD (a command line is visible to every process)")
    ap.add_argument("--total", type=int, default=500)
    ap.add_argument("--minutes", type=float, default=10)
    ap.add_argument("--burst", type=int, default=0, help="send this many at once instead")
    a = ap.parse_args(argv)
    if not a.password:
        ap.error("set ILM_LOADTEST_PASSWORD")
    if a.burst:
        out = run(a.base, a.password, a.burst, 0, burst=True)
    else:
        out = run(a.base, a.password, a.total, a.minutes, burst=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
