"""
Worker: takes queued jobs one at a time and runs them (src/jobs/handlers.py).

* In Docker it runs as its own container:  python -m src.jobs.worker
* Locally the web app starts one inside itself (WORKER_MODE=thread, the default), so `python -m web.server`
  is enough; set WORKER_MODE=external when a separate worker runs.
Only one worker should run at a time: jobs are claimed safely, but index updates are serialised by a lock
file and Gemini's free tier is rate-limited anyway.
"""

import os
import socket
import threading
import time
import traceback

from src.jobs import queue
from src.jobs.handlers import HANDLERS, friendly_error
from src.security import access
from src.utils.logger import setup_logger

log = setup_logger("worker")


def process_one(worker: str = "inline") -> bool:
    """Run the oldest queued job; False when the queue is empty."""
    job = queue.claim(worker)
    if job is None:
        return False
    started = time.time()
    try:
        user = access.get_user(job["user"])
        if user is None:
            raise PermissionError("The user who asked for this job no longer exists.")
        handler = HANDLERS[job["kind"]]
        result = handler(job["params"], user, lambda text: queue.progress(job["id"], text))
        queue.finish(job["id"], result=result)
        log.info("job %s (%s) done in %.1f s", job["id"], job["kind"], time.time() - started)
    except Exception as exc:
        queue.finish(job["id"], error=friendly_error(exc))
        log.error("job %s (%s) failed: %s: %s", job["id"], job["kind"], type(exc).__name__, str(exc)[:300])
        log.debug(traceback.format_exc())
    return True


def process_all() -> int:
    """Run every queued job now (tests, one-off use)."""
    n = 0
    while process_one():
        n += 1
    return n


def run_forever(worker: str = None, poll: float = 1.0) -> None:
    worker = worker or f"{socket.gethostname()}-{os.getpid()}"
    queue.heartbeat(worker)
    failed = queue.fail_stale()
    if failed:
        log.warning("%d job(s) left running by a stopped worker were marked failed", failed)
    log.info("worker %s waiting for jobs", worker)
    while True:
        try:
            queue.heartbeat(worker)
            if not process_one(worker):
                time.sleep(poll)
        except Exception as exc:   # e.g. the database briefly locked: keep the worker alive
            log.error("worker loop error: %s", exc)
            time.sleep(5)


def start_thread() -> threading.Thread:
    thread = threading.Thread(target=run_forever, kwargs={"worker": f"{socket.gethostname()}-web"}, daemon=True, name="job-worker")
    thread.start()
    return thread


def check(max_age: float = 60) -> int:
    """Docker health check for the worker container: 0 if a worker beat within max_age seconds."""
    beat = queue.last_heartbeat()
    return 0 if beat is not None and time.time() - beat < max_age else 1


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        sys.exit(check())
    run_forever()
