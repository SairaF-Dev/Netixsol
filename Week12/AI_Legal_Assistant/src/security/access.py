"""
Client-matter access control.

Documents are of two kinds:
* public law - statutes and published judgments: every signed-in user may search and read them;
* client documents - contracts and anything uploaded: each belongs to one client matter
  (data/security/matters.json) and is visible only to users assigned to that matter. A client document
  with no matter on record is denied to everyone but the admin (deny by default).

Roles: admin (all matters, the audit log), partner (all matters), associate (assigned matters only).
Users are in data/security/users.json with PBKDF2-SHA256 password hashes (never plain passwords).

The rule is enforced where data is read, not only in the page:
* retrieval drops other matters' passages BEFORE they reach Gemini (src/rag/advanced.py `allow`), so an
  answer cannot quote them, and the answer cache cannot serve them (the cache key includes the passages);
* contract review / comparison check the contract's matter; uploads must name a matter the user is on;
* graph text-to-Cypher may not read Contract or Clause nodes (src/graph/graphrag.py);
* generated files can be downloaded only by the user who made them (or the admin).

Sign-in returns a token signed with HMAC-SHA256 (APP_SECRET in .env; a random secret per run if unset,
so tokens then expire on restart) that is valid for 8 hours.

Run:  python -m src.security.access seed       (demo matters + users; random passwords written to
                                                 data/security/initial_passwords.txt, not in git)
      python -m src.security.access set-password <user> <password>
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

SECURITY_DIR = Path("data/security")
USERS = SECURITY_DIR / "users.json"
MATTERS = SECURITY_DIR / "matters.json"
TOKEN_HOURS = 8
ROLES_ALL_MATTERS = {"admin", "partner"}
CLIENT_PREFIXES = ("CONT_", "CUAD_", "REAL_CUAD_", "UPLOAD_", "versions/")
_ITERATIONS = 200_000
_lock = threading.Lock()


# ----------------------------------------------------------------------------- passwords and tokens
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    test = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(test.hex(), digest)


@lru_cache(maxsize=1)
def _secret() -> bytes:
    from dotenv import load_dotenv
    load_dotenv(Path(".env"))
    value = os.getenv("APP_SECRET")
    return value.encode("utf-8") if value else secrets.token_bytes(32)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(username: str, hours: float = TOKEN_HOURS) -> str:
    payload = _b64(json.dumps({"u": username, "exp": int(time.time() + hours * 3600)}).encode("utf-8"))
    signature = _b64(hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_token(token: str) -> Optional[str]:
    """The username in a valid, unexpired token, else None."""
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        return data["u"] if data["exp"] > time.time() else None
    except Exception:
        return None


# ----------------------------------------------------------------------------- users and matters
@dataclass
class User:
    username: str
    name: str
    role: str
    matters: Set[str] = field(default_factory=set)

    @property
    def all_matters(self) -> bool:
        return self.role in ROLES_ALL_MATTERS

    def can_see_matter(self, matter: Optional[str]) -> bool:
        return bool(matter) and (self.all_matters or matter in self.matters)

    def can_see_document(self, document_id: str, document_type: Optional[str] = None) -> bool:
        if not is_client_document(document_id, document_type):
            return True
        matter = matter_of(document_id)
        if matter is None:
            return self.role == "admin"   # unassigned client document: deny by default
        return self.can_see_matter(matter)

    def public(self) -> Dict:
        return {"username": self.username, "name": self.name, "role": self.role,
                "matters": sorted(m["id"] for m in matters() if self.can_see_matter(m["id"]))}


def _read(path: Path, key: str) -> List[Dict]:
    return json.loads(path.read_text(encoding="utf-8"))[key] if path.exists() else []


def matters() -> List[Dict]:
    return _read(MATTERS, "matters")


def matter_of(document_id: str) -> Optional[str]:
    for m in matters():
        if document_id in m["documents"]:
            return m["id"]
    return None


def is_client_document(document_id: str, document_type: Optional[str] = None) -> bool:
    return ((document_type or "").lower() == "contract" or document_id.startswith(CLIENT_PREFIXES)
            or matter_of(document_id) is not None)


def get_user(username: str) -> Optional[User]:
    for u in _read(USERS, "users"):
        if u["username"] == username:
            return User(u["username"], u["name"], u["role"], set(u.get("matters", [])))
    return None


def authenticate(username: str, password: str) -> Optional[User]:
    stored = next((u for u in _read(USERS, "users") if u["username"] == username), None)
    if stored is None:
        check_password(password, hash_password("timing"))   # same work for unknown users
        return None
    return get_user(username) if check_password(password, stored["password_hash"]) else None


def add_document(document_id: str, matter: str) -> None:
    """Put an uploaded document on a client matter."""
    with _lock:
        data = json.loads(MATTERS.read_text(encoding="utf-8"))
        for m in data["matters"]:
            if m["id"] == matter and document_id not in m["documents"]:
                m["documents"].append(document_id)
        MATTERS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# ----------------------------------------------------------------------------- demo data
DEMO_MATTERS = [
    {"id": "MAT-001", "name": "IT services and supply", "client": "Pak Telecom Enterprises",
     "documents": [f"CONT_SYNTH_{i:03d}" for i in range(1, 11)] + ["versions/supply_agreement_v1.json", "versions/supply_agreement_v2.json"]},
    {"id": "MAT-002", "name": "Service level agreements", "client": "Pak Telecom Enterprises",
     "documents": [f"CONT_SYNTH_{i:03d}" for i in range(11, 21)]},
    {"id": "MAT-003", "name": "Franchise and distribution review", "client": "Franchise and distribution clients (CUAD)",
     "documents": [f"CUAD_REAL_{i:03d}" for i in range(1, 24)]},
    {"id": "MAT-004", "name": "Licensing and affiliate programmes", "client": "Licensing clients (CUAD)",
     "documents": [f"REAL_CUAD_{i:03d}" for i in range(1, 31)]},
]
DEMO_USERS = [
    {"username": "admin", "name": "System administrator", "role": "admin", "matters": []},
    {"username": "sana", "name": "Sana Khan (managing partner)", "role": "partner", "matters": []},
    {"username": "ayesha", "name": "Ayesha (associate)", "role": "associate", "matters": ["MAT-001", "MAT-002"]},
    {"username": "bilal", "name": "Bilal (associate)", "role": "associate", "matters": ["MAT-003", "MAT-004"]},
]


def seed() -> None:
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    MATTERS.write_text(json.dumps({"matters": DEMO_MATTERS}, ensure_ascii=False, indent=1), encoding="utf-8")
    passwords, users = {}, []
    for u in DEMO_USERS:
        passwords[u["username"]] = secrets.token_urlsafe(9)
        users.append({**u, "password_hash": hash_password(passwords[u["username"]])})
    USERS.write_text(json.dumps({"users": users}, ensure_ascii=False, indent=1), encoding="utf-8")
    (SECURITY_DIR / "initial_passwords.txt").write_text(
        "Demo sign-ins (keep private; change with: python -m src.security.access set-password <user> <password>)\n"
        + "\n".join(f"{k}: {v}" for k, v in passwords.items()) + "\n", encoding="utf-8")
    print(f"wrote {MATTERS}, {USERS} and {SECURITY_DIR / 'initial_passwords.txt'}")


def set_password(username: str, password: str) -> None:
    data = json.loads(USERS.read_text(encoding="utf-8"))
    user = next(u for u in data["users"] if u["username"] == username)
    user["password_hash"] = hash_password(password)
    USERS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"password changed for {username}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    sp = sub.add_parser("set-password")
    sp.add_argument("user")
    sp.add_argument("password")
    args = parser.parse_args()
    seed() if args.cmd == "seed" else set_password(args.user, args.password)
