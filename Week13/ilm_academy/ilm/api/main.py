"""Ilm Academy API (Day 5).

    uvicorn ilm.api.main:app --reload --port 8010      (from ilm_academy/, venv active)

Everything under /api. The React app (web/) calls it with the session cookie.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ilm import config
from ilm.api import classroom, insights, practice, review, service, tutor_api
from ilm.api.auth import COOKIE, SESSION_SEC, User, check_password, current_user, make_token, require


@asynccontextmanager
async def lifespan(_app):
    service.warm_up()          # the first student should not wait for the search model to load
    tutor_api.warm_up()
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


# ------------------------------------------------------------------ question practice ----
class AnswerIn(BaseModel):
    question: str = Field(max_length=60)
    choice: int | None = Field(default=None, ge=0, le=9)
    text: str | None = Field(default=None, max_length=300)


@app.get("/api/practice/next")
def practice_next(concept: str, user: User = Depends(require("student"))):
    if concept not in service.concepts():
        raise HTTPException(404, "No such concept.")
    return practice.next_question(user.username, user.learner, concept)


@app.post("/api/answers")
def practice_answer(body: AnswerIn, user: User = Depends(require("student"))):
    try:
        return practice.answer(user.username, user.learner, body.question, body.choice, body.text)
    except KeyError:
        raise HTTPException(404, "No such question.")
    except ValueError as e:
        raise HTTPException(422, str(e))


# ------------------------------------------------------------------ tutor ----
class AskIn(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    language: str = Field(default="auto", pattern="^(auto|english|urdulish)$")


class HintIn(BaseModel):
    exercise: str = Field(max_length=60)
    code: str = Field(default="", max_length=service.MAX_CODE_CHARS)
    message: str = Field(default="", max_length=1500)
    level: int = Field(default=1, ge=1, le=4)
    language: str = Field(default="auto", pattern="^(auto|english|urdulish)$")


def _tutor_call(fn):
    try:
        return fn()
    except tutor_api.TutorLimited as e:
        raise HTTPException(429, str(e))
    except tutor_api.TutorUnavailable as e:
        raise HTTPException(503, str(e))
    except KeyError:
        raise HTTPException(404, "No such exercise.")


@app.post("/api/tutor/ask")
def tutor_ask(body: AskIn, user: User = Depends(require("student"))):
    return _tutor_call(lambda: tutor_api.ask(user.username, user.learner, body.message, body.language))


@app.post("/api/tutor/hint")
def tutor_hint(body: HintIn, user: User = Depends(require("student"))):
    return _tutor_call(lambda: tutor_api.hint(user.username, user.learner, body.exercise, body.code,
                                              body.message, body.level, body.language))


# ------------------------------------------------------------------ teacher ----
class DecisionIn(BaseModel):
    decision: str = Field(max_length=60)
    note: str = Field(default="", max_length=500)


@app.get("/api/class/overview")
def class_overview(user: User = Depends(require("teacher"))):
    c = classroom.load()
    q = review.queue()
    return {k: c[k] for k in ("cohort", "week", "enrolled", "in_class", "left_before_week", "active_this_week",
                              "high", "medium", "avg_mastered", "concepts_total", "weakest", "heatmap",
                              "section_note")} | {"review_open": q["open"]}


@app.get("/api/class/at-risk")
def class_at_risk(user: User = Depends(require("teacher"))):
    c = classroom.load()
    return {"week": c["week"], "in_class": c["in_class"], "students": c["at_risk"]}


@app.get("/api/review")
def review_queue(user: User = Depends(require("teacher"))):
    return review.queue()


@app.get("/api/review/{item_id}")
def review_item(item_id: str, user: User = Depends(require("teacher"))):
    d = review.detail(item_id)
    if d is None:
        raise HTTPException(404, "No such review item.")
    return d


@app.post("/api/review/{item_id}")
def review_decide(item_id: str, body: DecisionIn, user: User = Depends(require("teacher"))):
    if review.detail(item_id) is None:
        raise HTTPException(404, "No such review item.")
    try:
        return review.decide(item_id, body.decision, user.username, body.note)
    except ValueError as e:
        raise HTTPException(422, str(e))


class QuestionDecisionIn(BaseModel):
    decision: str = Field(max_length=20)
    level: int | None = Field(default=None, ge=1, le=5)


@app.get("/api/questions/health")
def questions_health(user: User = Depends(require("teacher"))):
    return insights.question_health()


@app.post("/api/questions/{qid}/decision")
def question_decision(qid: str, body: QuestionDecisionIn, user: User = Depends(require("teacher"))):
    try:
        return insights.decide_question(qid, body.decision, body.level, user.username)
    except KeyError:
        raise HTTPException(404, "No such question.")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/tutor/safety")
def tutor_safety(user: User = Depends(require("teacher"))):
    return insights.tutor_safety()


@app.get("/api/impact")
def impact(user: User = Depends(require("teacher"))):
    return insights.impact()
