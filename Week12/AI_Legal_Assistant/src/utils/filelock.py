"""
A lock that works across processes and containers sharing a folder: whoever creates the lock file
first (O_CREAT | O_EXCL is atomic) holds it. Used where the web app and the worker container write the
same file: the audit log (its hash chain needs one writer at a time) and the search indexes.
A lock file older than `stale` seconds is treated as left behind by a crash and removed.
"""

import os
import time
from contextlib import contextmanager
from pathlib import Path


class LockTimeout(Exception):
    pass


@contextmanager
def file_lock(path: Path, timeout: float = 30, stale: float = 600, poll: float = 0.05):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > stale:
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.time() - start > timeout:
                raise LockTimeout(f"{path} is held by another process")
            time.sleep(poll)
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        path.unlink(missing_ok=True)
