"""Login and roles for the API.

Demo accounts only (Ali and Sara are the simulator's two demo learners; the teacher account is
labelled "Teacher (demo)"). Passwords are bcrypt hashes; the plain demo password comes from
ILM_DEMO_PASSWORD in .env. In dev, if it is empty, the dev default below is used so the app
runs out of the box; in prod an empty password or JWT secret stops the API from starting.

The session is a signed JWT in an httpOnly cookie (JavaScript cannot read it), SameSite=Lax.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from functools import lru_cache

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from ilm import config

COOKIE = "ilm_session"
SESSION_SEC = 8 * 3600
DEV_PASSWORD = "ilm-demo-2026"


@dataclass(frozen=True)
class User:
    username: str
    name: str
    role: str                 # student | teacher
    learner: str | None = None  # key into reports/learning_path/<learner>.json


USERS = {
    "ali": User("ali", "Ali", "student", "ali"),
    "sara": User("sara", "Sara", "student", "sara"),
    "teacher": User("teacher", "Teacher (demo)", "teacher"),
}


def _password() -> str:
    if config.ILM_ENV == "prod":
        if not config.DEMO_PASSWORD:
            raise RuntimeError("ILM_DEMO_PASSWORD must be set in prod")
        if config.DEMO_PASSWORD == DEV_PASSWORD:      # it is in this public repo: anyone could log in
            raise RuntimeError("ILM_DEMO_PASSWORD must not be the dev default (it is published in the code)")
    return config.DEMO_PASSWORD or DEV_PASSWORD


@lru_cache(maxsize=1)
def _hash() -> bytes:
    return bcrypt.hashpw(_password().encode(), bcrypt.gensalt(rounds=10))


@lru_cache(maxsize=1)
def _secret() -> str:
    if config.JWT_SECRET:
        return config.JWT_SECRET
    if config.ILM_ENV == "prod":
        raise RuntimeError("ILM_JWT_SECRET must be set in prod")
    return secrets.token_hex(32)              # dev: sessions end when the API restarts


def check_password(username: str, password: str) -> User | None:
    user = USERS.get(username.strip().lower())
    ok = bcrypt.checkpw(password.encode(), _hash())   # always run: same time for unknown users
    return user if user and ok else None


def make_token(user: User) -> str:
    now = int(time.time())
    return jwt.encode({"sub": user.username, "role": user.role, "iat": now, "exp": now + SESSION_SEC},
                      _secret(), algorithm="HS256")


def current_user(request: Request) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Please log in.")
    try:
        data = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has ended. Please log in again.")
    user = USERS.get(data.get("sub", ""))
    if user is None or user.role != data.get("role"):
        raise HTTPException(401, "Please log in.")
    return user


def require(role: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role != role:
            raise HTTPException(403, "This page is for " + ("teachers" if role == "teacher" else "students") + ".")
        return user
    return dep
