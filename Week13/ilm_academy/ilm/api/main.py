"""Ilm Academy API (Day 5).

    uvicorn ilm.api.main:app --reload --port 8010      (from ilm_academy/, venv active)

Everything under /api. The React app (web/) calls it with the session cookie.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ilm import config
from ilm.api import service
from ilm.api.auth import COOKIE, SESSION_SEC, User, check_password, current_user, make_token, require

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    service.warm_up()          # the first student should not wait for the search model to load
    yield


app = FastAPI(title="Ilm Academy API", version="0.1", docs_url="/api/docs", openapi_url="/api/openapi.json",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class SubmissionIn(BaseModel):
    exercise: str = Field(max_length=60)
    code: str = Field(max_length=service.MAX_CODE_CHARS)


def _me(user: User) -> dict:
    return {"username": user.username, "name": user.name, "role": user.role}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    user = check_password(body.username, body.password)
    if user is None:
        raise HTTPException(401, "That username and password don't match.")
    response.set_cookie(COOKIE, make_token(user), max_age=SESSION_SEC, httponly=True, samesite="lax",
                        secure=config.ILM_ENV == "prod", path="/")
    return _me(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return _me(user)


# ------------------------------------------------------------------ student ----
@app.get("/api/me/path")
def my_path(user: User = Depends(require("student"))):
    plan = service.learner_plan(user.learner) if user.learner else None
    if plan is None:
        raise HTTPException(404, "No learning plan yet.")
    return plan


@app.get("/api/exercises")
def exercises(user: User = Depends(current_user)):
    return service.list_exercises()


@app.get("/api/exercises/{qid}")
def exercise(qid: str, user: User = Depends(current_user)):
    ex = service.exercise_detail(qid)
    if ex is None:
        raise HTTPException(404, "No such exercise.")
    if user.role == "student":
        ex["recent"] = service.recent_submissions(user.username, qid)
    return ex


@app.post("/api/submissions", status_code=202)
def submit(body: SubmissionIn, user: User = Depends(require("student"))):
    if service.exercise_detail(body.exercise) is None:
        raise HTTPException(404, "No such exercise.")
    if not body.code.strip():
        raise HTTPException(422, "Write some code first.")
    if service.rate_limited(user.username):
        raise HTTPException(429, "That's a lot of runs in one minute. Wait a moment and try again.")
    return {"id": service.submit(user.username, body.exercise, body.code)}


@app.get("/api/submissions/{sid}")
def submission(sid: str, user: User = Depends(require("student"))):
    s = service.get_submission(sid, user.username)
    if s is None:
        raise HTTPException(404, "No such submission.")
    return s
