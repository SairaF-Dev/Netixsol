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
    from ilm.api import auth
    auth._password(), auth._secret()   # in prod: refuse to start without safe secrets, not at first login
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
    """Is the server up?"""
    return {"ok": True}


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    """Log in; sets the session cookie. Same answer and timing for an unknown user and a wrong password."""
    user = check_password(body.username, body.password)
    if user is None:
        raise HTTPException(401, "That username and password don't match.")
    response.set_cookie(COOKIE, make_token(user), max_age=SESSION_SEC, httponly=True, samesite="lax",
                        secure=config.ILM_ENV == "prod", path="/")
    return _me(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    """Log out; clears the session cookie."""
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    """Who is logged in (username, name, role)."""
    return _me(user)


# ------------------------------------------------------------------ student ----
@app.get("/api/me/path")
def my_path(user: User = Depends(require("student"))):
    """The student's learning plan: mastered and weakest concepts, the ordered path with time estimates."""
    plan = service.learner_plan(user.learner) if user.learner else None
    if plan is None:
        raise HTTPException(404, "No learning plan yet.")
    return plan


@app.get("/api/exercises")
def exercises(user: User = Depends(current_user)):
    """All coding exercises in learning order (function, concept, difficulty, lesson)."""
    return service.list_exercises()


@app.get("/api/exercises/{qid}")
def exercise(qid: str, user: User = Depends(current_user)):
    """One exercise: task, starter code, visible tests, number of hidden tests; for a student also their last 5 runs."""
    ex = service.exercise_detail(qid)
    if ex is None:
        raise HTTPException(404, "No such exercise.")
    if user.role == "student":
        ex["recent"] = service.recent_submissions(user.username, qid)
    return ex


@app.post("/api/submissions", status_code=202)
def submit(body: SubmissionIn, user: User = Depends(require("student"))):
    """Submit code to grade. Returns an id at once (202); grading runs in the sandbox in the background."""
    if service.exercise_detail(body.exercise) is None:
        raise HTTPException(404, "No such exercise.")
    if not body.code.strip():
        raise HTTPException(422, "Write some code first.")
    if service.rate_limited(user.username):
        raise HTTPException(429, "That's a lot of runs in one minute. Wait a moment and try again.")
    return {"id": service.submit(user.username, body.exercise, body.code)}


@app.get("/api/submissions/{sid}")
def submission(sid: str, user: User = Depends(require("student"))):
    """A submission's status (queued, running, done, error) and, when done, the mark and feedback."""
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
    """The next MCQ or short-answer question on a concept (untried ones first). The key is not sent."""
    if concept not in service.concepts():
        raise HTTPException(404, "No such concept.")
    return practice.next_question(user.username, user.learner, concept)


@app.post("/api/answers")
def practice_answer(body: AnswerIn, user: User = Depends(require("student"))):
    """Grade an answer on the server: right or wrong, the misconception behind a wrong option, mastery before and after."""
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
    """Ask the Socratic tutor a course question; answered from course sources, with lesson links."""
    return _tutor_call(lambda: tutor_api.ask(user.username, user.learner, body.message, body.language))


@app.post("/api/tutor/hint")
def tutor_hint(body: HintIn, user: User = Depends(require("student"))):
    """One rung of the hint ladder for an exercise (1 question, 2 concept, 3 partial hint, 4 similar example). Never the solution."""
    return _tutor_call(lambda: tutor_api.hint(user.username, user.learner, body.exercise, body.code,
                                              body.message, body.level, body.language))


# ------------------------------------------------------------------ teacher ----
class DecisionIn(BaseModel):
    decision: str = Field(max_length=60)
    note: str = Field(default="", max_length=500)


@app.get("/api/class/overview")
def class_overview(user: User = Depends(require("teacher"))):
    """Class KPIs, weakest concepts and the section x concept mastery heatmap."""
    c = classroom.load()
    q = review.queue()
    return {k: c[k] for k in ("cohort", "week", "enrolled", "in_class", "left_before_week", "active_this_week",
                              "high", "medium", "avg_mastered", "concepts_total", "weakest", "heatmap",
                              "section_note")} | {"review_open": q["open"]}


@app.get("/api/class/at-risk")
def class_at_risk(user: User = Depends(require("teacher"))):
    """Students the dropout model flags this week, with the reason in words and a suggested action."""
    c = classroom.load()
    return {"week": c["week"], "in_class": c["in_class"], "students": c["at_risk"]}


@app.get("/api/review")
def review_queue(user: User = Depends(require("teacher"))):
    """Items waiting for a teacher: possible copying, low marks, tampering flags."""
    return review.queue()


@app.get("/api/review/{item_id}")
def review_item(item_id: str, user: User = Depends(require("teacher"))):
    """One review item in detail (for copying: both programs side by side, matching lines)."""
    d = review.detail(item_id)
    if d is None:
        raise HTTPException(404, "No such review item.")
    return d


@app.post("/api/review/{item_id}")
def review_decide(item_id: str, body: DecisionIn, user: User = Depends(require("teacher"))):
    """Record the teacher's decision on a review item. Nothing is ever decided automatically."""
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
    """Question bank health: IRT evidence per question, retire/relabel suggestions, generated-question pipeline."""
    return insights.question_health()


@app.post("/api/questions/{qid}/decision")
def question_decision(qid: str, body: QuestionDecisionIn, user: User = Depends(require("teacher"))):
    """Record a teacher's decision on a question (Retire, Relabel with a level, Keep)."""
    try:
        return insights.decide_question(qid, body.decision, body.level, user.username)
    except KeyError:
        raise HTTPException(404, "No such question.")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/tutor/safety")
def tutor_safety(user: User = Depends(require("teacher"))):
    """Tutor evaluation runs and live usage (metadata only; no student text is stored)."""
    return insights.tutor_safety()


@app.get("/api/impact")
def impact(user: User = Depends(require("teacher"))):
    """Impact numbers: adaptive vs fixed, dropout model, grading agreement, safety, the A/B test design."""
    return insights.impact()


# ------------------------------------------------------------------ the web app ----
# In production the API also serves the built React app (web/dist), so the whole platform is one
# address and the session cookie stays same-origin. Any path that is not /api/... gets index.html,
# so reloading /student/path works. In dev, Vite serves the app instead (web/vite.config.ts).
_DIST = config.PROJECT_ROOT / "web" / "dist"
if _DIST.exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        f = (_DIST / path).resolve()
        if path and f.is_file() and _DIST.resolve() in f.parents:      # favicon.svg etc., never outside dist
            return FileResponse(f)
        return FileResponse(_DIST / "index.html")
