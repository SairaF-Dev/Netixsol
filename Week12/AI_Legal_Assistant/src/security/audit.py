"""
Audit log: who did what, when, on which client matter, and with what outcome.

* Append-only JSON lines in data/security/audit.jsonl (not in git).
* Tamper-evident: every entry stores the SHA-256 hash of the previous entry and its own hash over
  (previous hash + its content). Changing, deleting or reordering any past entry breaks the chain from
  that point; `verify()` reports the first broken line. (It shows tampering; it cannot prevent someone
  with file access from rewriting the whole chain - for that, entries would also be shipped to a separate
  write-once store, see the admin guide.)
* Details are PII-masked (src/security/pii.py) and cut to 300 characters: the log records actions and
  document ids, never document text.

Outcomes: ok | denied (access control) | blocked (prompt injection) | failed (login) | error.
"""

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.security.pii import mask
from src.utils.filelock import file_lock

AUDIT_LOG = Path(os.getenv("AUDIT_LOG", "data/security/audit.jsonl"))
_GENESIS = "0" * 64
_lock = threading.Lock()


def _digest(prev: str, entry: Dict) -> str:
    body = json.dumps({k: v for k, v in entry.items() if k != "hash"}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def _last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return _GENESIS
    with path.open("rb") as handle:   # read only the last line
        handle.seek(0, 2)
        size, block, data = handle.tell(), 4096, b""
        while size > 0 and data.count(b"\n") < 2:
            step = min(block, size)
            size -= step
            handle.seek(size)
            data = handle.read(step) + data
    last = [line for line in data.splitlines() if line.strip()][-1]
    return json.loads(last)["hash"]


def record(user: str, action: str, outcome: str = "ok", matter: Optional[str] = None,
           target: Optional[str] = None, detail: str = "", path: Optional[Path] = None) -> Dict:
    path = path or AUDIT_LOG
    # thread lock inside this process + file lock across processes (web app and worker container):
    # the chain needs exactly one writer between reading the last hash and appending
    with _lock, file_lock(path.with_name(path.name + ".lock")):
        path.parent.mkdir(parents=True, exist_ok=True)
        prev = _last_hash(path)
        # the user field is masked too: a failed sign-in records whatever was typed as the user name (red team H1)
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "user": mask(user or ""), "action": action,
                 "outcome": outcome, "matter": matter, "target": mask(target or "") or None,
                 "detail": mask(detail or "")[:300], "prev": prev}
        entry["hash"] = _digest(prev, entry)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


def verify(path: Optional[Path] = None) -> Tuple[bool, int, Optional[int]]:
    """(chain intact, number of entries, first broken line number or None)."""
    path = path or AUDIT_LOG
    if not path.exists():
        return True, 0, None
    prev, n = _GENESIS, 0
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return False, n, n
        if entry.get("prev") != prev or entry.get("hash") != _digest(prev, entry):
            return False, n, n
        prev = entry["hash"]
    return True, n, None


def tail(n: int = 200, path: Optional[Path] = None) -> List[Dict]:
    path = path or AUDIT_LOG
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[-n:]]
