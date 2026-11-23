"""
Web app for the AI Legal Assistant: one page, six tools, all calling the Day 2-4 code.

    Research      question -> router -> verified answer (vector) / graph list (graph) / both (hybrid)
    Case law      GraphRAG over Neo4j (no LLM for linked questions; text-to-Cypher as fallback)
    Review        playbook review of a sample or uploaded contract -> findings + Word file with comments
    Compare       two versions (sample pair or uploads) -> word diff + impact explanation + Word redline
    Drafting      case brief / legal notice / clauses, every source checked -> Word file
    Evaluation    the evaluation reports in evaluations/*.md
    Audit         (admin) the tamper-evident audit log

Security (Day 5, src/security/):
* every API call except sign-in needs a signed token; users only see public law plus the client
  matters they are assigned to - enforced in retrieval, review, comparison, graph and downloads;
* uploads are screened for prompt injection (instructions to the AI, hidden text) and blocked if found;
* every action is written to the audit log (PII-masked, hash-chained); server logs are PII-masked.

Gemini answers are cached on disk (data/llm_cache), so a question asked before costs nothing.
Generated Word files and uploads go to data/web_outputs/ (not in git).

Run:  python -m web.server            then open http://127.0.0.1:8000
      PORT=7860 HOST=0.0.0.0 python -m web.server   (Hugging Face Spaces)
"""

import csv
import json
import logging
import os
import re
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)   # the project code uses paths relative to the project folder

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.jobs import queue as jobs
from src.jobs.handlers import UPLOADS as UPLOAD_DIR, owner_of
from src.security import access, audit
from src.security.injection import scan_file
from src.security.pii import protect
from src.utils.logger import setup_logger

load_dotenv(ROOT / ".env")

STATIC = Path(__file__).parent / "static"
OUT = ROOT / "data" / "web_outputs"
UPLOADS = OUT / "uploads"
OWNERS = OUT / "owners.json"
VERSIONS = ROOT / "data" / "contracts" / "versions"
DRAFTING = ROOT / "data" / "contracts" / "drafting"
REPORTS = {   # file -> title shown on the Evaluation page (only these files are served)
    "rag_comparison_report.md": "Naive vs advanced retrieval (Day 2)",
    "citation_verification_report.md": "Citation verification (Day 2)",
    "demo_verified_answers.md": "Five verified answers (Day 2)",
    "conclusion_check_report.md": "Conclusion check: does the answer follow? (Day 2)",
    "graph_precision_recall.md": "Graph extraction precision / recall (Day 3)",
    "graph_vs_vector_report.md": "Vector vs graph vs hybrid (Day 3)",
    "clause_classification_report.md": "Clause classification: LLM vs fine-tuned (Day 4)",
    "long_context_vs_rag_report.md": "Long context vs RAG on 10 contracts (Day 4)",
    "ocr_comparison_report.md": "Urdu OCR benchmark (Day 1)",
    "chunking_comparison_report.md": "Chunking strategies (Day 1)",
}
UPLOAD_TYPES = {".pdf", ".docx", ".txt", ".json"}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_FAILED_LOGINS, LOCKOUT_SECONDS = 5, 300

log = setup_logger("web")
app = FastAPI(title="Khan & Associates - AI Legal Assistant", docs_url="/api/docs")


@app.on_event("startup")
def _startup() -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        protect(logging.getLogger(name))
    if os.getenv("WORKER_MODE", "thread") == "thread":   # Docker: WORKER_MODE=external + the worker container
        from src.jobs.worker import start_thread
        start_thread()


@app.middleware("http")
async def _request_log(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, 1000 * (time.time() - start))
    return response


# ----------------------------------------------------------------------------- sign-in
_failed: Dict[str, List[float]] = {}
_failed_lock = threading.Lock()


class Login(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(body: Login) -> Dict:
    name = body.username.strip().lower()[:40]
    with _failed_lock:
        recent = [t for t in _failed.get(name, []) if time.time() - t < LOCKOUT_SECONDS]
        _failed[name] = recent
    if len(recent) >= MAX_FAILED_LOGINS:
        audit.record(name, "login", "denied", detail="locked out after repeated failures")
        raise HTTPException(429, "Too many failed sign-ins. Try again in 5 minutes.")
    user = access.authenticate(name, body.password)
    if user is None:
        with _failed_lock:
            _failed.setdefault(name, []).append(time.time())
        audit.record(name, "login", "failed")
        raise HTTPException(401, "Wrong user name or password.")
    with _failed_lock:
        _failed.pop(name, None)
    audit.record(user.username, "login")
    return {"token": access.issue_token(user.username), "user": user.public()}


def current_user(request: Request) -> access.User:
    header = request.headers.get("authorization", "")
    username = access.read_token(header[7:]) if header.lower().startswith("bearer ") else None
    user = access.get_user(username) if username else None
    if user is None:
        raise HTTPException(401, "Please sign in.")
    return user


def _allow(user: access.User) -> Callable[[Dict], bool]:
    """Retrieval filter: public law, plus client documents of this user's matters."""
    return lambda chunk: user.can_see_document(chunk["document_id"], chunk.get("document_type"))


def _deny(user: access.User, action: str, target: str) -> HTTPException:
    audit.record(user.username, action, "denied", matter=access.matter_of(target), target=target)
    # 404, not 403: a user must not learn that another matter's document exists
    return HTTPException(404, "Not found, or not on one of your matters.")


@app.get("/api/me")
def me(user: access.User = Depends(current_user)) -> Dict:
    return user.public()


# ----------------------------------------------------------------------------- helpers
def _fail(exc: Exception) -> HTTPException:
    """Turn a backend failure into a message a lawyer can act on (never echoes keys or env values)."""
    message = str(exc)
    if "quota" in message.lower() or "PerDay" in message or "RESOURCE_EXHAUSTED" in message:
        return HTTPException(503, "The free Gemini limit for today is used up. It resets at about 13:00 PKT. "
                                  "Questions asked before still work, because their answers are saved.")
    if "LLM_API_KEY" in message:
        return HTTPException(503, "Gemini is not configured on this server (LLM_API_KEY is missing).")
    if "NEO4J" in message.upper() or "ServiceUnavailable" in type(exc).__name__ or "neo4j" in type(exc).__module__:
        return HTTPException(503, "The case-law graph (Neo4j) is not reachable right now.")
    log.error("request failed: %s: %s", type(exc).__name__, message[:300])
    return HTTPException(500, f"Something went wrong ({type(exc).__name__}). The error has been logged.")


async def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in UPLOAD_TYPES:
        raise HTTPException(400, f"Upload a PDF, Word (.docx), text or JSON file, not '{suffix or 'no extension'}'.")
    data = await upload.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "The file is larger than 15 MB.")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / f"UPLOAD_{uuid.uuid4().hex[:12]}{suffix}"
    path.write_bytes(data)
    return path


def contract_from_file(path: Path, title: str) -> Path:
    """Any uploaded contract -> the structured JSON the review and comparison code read (clauses)."""
    from src.extraction.contract_extractor import ContractStructureExtractor

    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(400, "The JSON file could not be read.")
        if not isinstance(data, dict) or not data.get("clauses"):
            raise HTTPException(400, "The JSON file has no 'clauses' list.")
        data.setdefault("contract_title", title)
        data.setdefault("contract_type", None)
    else:
        extractor = ContractStructureExtractor()
        if path.suffix == ".docx":
            from docx import Document
            text = "\n".join(p.text for p in Document(str(path)).paragraphs)
            data = extractor.extract_from_text(text, doc_id=path.stem).model_dump()
        else:
            data = extractor.extract_from_file(path, doc_id=path.stem).model_dump()
            text = None
        if not data.get("clauses"):   # no numbered headings found: fall back to one clause per paragraph
            if text is None:
                text = path.read_text(encoding="utf-8", errors="ignore") if path.suffix == ".txt" else ""
                if path.suffix == ".pdf":
                    from src.ingestion.pdf_parser import LegalPDFParser
                    text = "\n\n".join(p["text"] for p in LegalPDFParser().extract_page_texts(path))
            paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n|\n(?=[A-Z0-9])", text)]
            paras = [p for p in paras if len(p.split()) >= 8]
            data["clauses"] = [{"clause_id": f"P{i}", "clause_title": " ".join(p.split()[:6]) + "...", "text": p, "page_number": None}
                               for i, p in enumerate(paras, 1)]
        if not data["clauses"]:
            raise HTTPException(400, "No contract text could be read from this file (is it a scanned image?).")
        data["contract_title"] = data.get("contract_title") or title
    data["document_id"] = path.stem
    out = path.with_suffix(".contract.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


async def _accept_upload(upload: UploadFile, matter: Optional[str], user: access.User, action: str) -> Dict:
    """Save -> parse -> screen for prompt injection -> put on the matter. Raises 422 if blocked."""
    if not user.can_see_matter(matter):
        audit.record(user.username, action, "denied", matter=matter, detail="upload to a matter the user is not on")
        raise HTTPException(403, "Choose one of your matters for the upload.")
    raw = await _save_upload(upload)
    contract_path = contract_from_file(raw, Path(upload.filename or "upload").stem)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    pieces = [("title", contract.get("contract_title") or "")] + \
             [(f"clause {c['clause_id'].replace('Clause ', '')} ({c['clause_title'][:40]})", f"{c['clause_title']}\n{c['text']}")
              for c in contract["clauses"]]
    screen = scan_file(raw, pieces)
    if screen["blocked"]:
        audit.record(user.username, action, "blocked", matter=matter, target=raw.stem,
                     detail=f"prompt injection in {upload.filename}: " + "; ".join(f"{f['kind']} at {f['location']}" for f in screen["findings"]))
        raise HTTPException(422, {"blocked": True, "file": upload.filename,
                                  "message": "This document contains text addressed to an AI system, which looks like a prompt-injection "
                                             "attempt. It was not processed. Check it with the sender.",
                                  "findings": screen["findings"]})
    access.add_document(raw.stem, matter)
    audit.record(user.username, "upload", matter=matter, target=raw.stem, detail=f"{upload.filename}, {len(contract['clauses'])} clauses")
    return {"path": contract_path, "document_id": raw.stem, "hidden_text": screen["hidden_text"]}


@lru_cache(maxsize=1)
def _gemini():
    from src.llm.gemini_client import GeminiClient
    return GeminiClient()


@lru_cache(maxsize=1)
def _graph():
    from src.graph.graphrag import GraphRAG
    try:
        llm = _gemini()
    except Exception:
        llm = None   # linked questions need no LLM; only the text-to-Cypher fallback does
    return GraphRAG(llm=llm)


# ----------------------------------------------------------------------------- reference data
@lru_cache(maxsize=1)
def _judgments() -> List[Dict]:
    path = ROOT / "data" / "graph" / "nodes_case.csv"
    out = []
    if path.exists():
        for r in csv.DictReader(path.open(encoding="utf-8")):
            if r.get("in_corpus") == "True" and (ROOT / "data" / "structured" / "judgment" / f"{r['document_id']}.json").exists():
                out.append({"id": r["document_id"], "label": f"{r['case_number'] or r['name']} ({r['court']}, {r['year']})"})
    return sorted(out, key=lambda j: j["label"])


@lru_cache(maxsize=1)
def _contracts() -> List[Dict]:
    out = []
    for path in sorted((ROOT / "data" / "structured" / "contract").glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        title = re.sub(r"\s+", " ", d.get("contract_title") or path.stem).strip()
        out.append({"id": path.stem, "label": f"{title[:80]} ({len(d.get('clauses', []))} clauses)", "synthetic": path.stem.startswith("CONT_SYNTH")})
    for path in sorted(VERSIONS.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        out.insert(0, {"id": f"versions/{path.name}", "label": f"{d['contract_title']} ({len(d['clauses'])} clauses)", "synthetic": True})
    return out


def _uploaded() -> List[Dict]:
    """Contracts uploaded in the web app and filed on a matter (data/web_outputs/uploads/UPLOAD_*.contract.json)."""
    out = []
    for path in sorted(UPLOAD_DIR.glob("UPLOAD_*.contract.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        doc_id = path.name.split(".")[0]
        if access.matter_of(doc_id) is None:
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        title = re.sub(r"\s+", " ", d.get("contract_title") or doc_id).strip()
        out.append({"id": doc_id, "label": f"{title[:80]} ({len(d.get('clauses', []))} clauses, uploaded)", "synthetic": False,
                    "uploaded": True, "title": title, "clauses": len(d.get("clauses", []))})
    return out


def _contract_path(contract_id: str) -> str:
    if contract_id.startswith("UPLOAD_"):
        path = UPLOAD_DIR / f"{contract_id}.contract.json"
        if not re.fullmatch(r"UPLOAD_[0-9a-f]{12}", contract_id) or not path.exists():
            raise HTTPException(404, "Unknown uploaded contract.")
        return str(path)
    if contract_id.startswith("versions/"):
        path = VERSIONS / Path(contract_id).name
        if not path.exists():
            raise HTTPException(404, "Unknown sample contract.")
        return str(path)
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", contract_id) or not (ROOT / "data" / "structured" / "contract" / f"{contract_id}.json").exists():
        raise HTTPException(404, "Unknown sample contract.")
    return contract_id


def _graph_counts() -> Dict[str, int]:
    graph = ROOT / "data" / "graph"
    rows = lambda name: max(0, sum(1 for _ in (graph / f"{name}.csv").open(encoding="utf-8")) - 1) if (graph / f"{name}.csv").exists() else 0
    return {"cases": rows("nodes_case"), "sections": rows("nodes_section"), "judges": rows("nodes_judge"),
            "case_links": sum(rows(f"edges_{t}") for t in ("cites", "follows", "distinguishes", "overrules")),
            "law_links": sum(rows(f"edges_{t}") for t in ("refers_to", "interprets"))}


@app.get("/api/meta")
def meta(user: access.User = Depends(current_user)) -> Dict:
    from src.contracts.review import playbook
    names = {m["id"]: m for m in access.matters()}
    contracts = []
    for c in _uploaded() + _contracts():
        matter = access.matter_of(c["id"])
        if user.can_see_document(c["id"]):
            contracts.append({**c, "matter": matter, "matter_name": names.get(matter, {}).get("name", "")})
    return {
        "user": user.public(),
        "matters": [{"id": m["id"], "name": m["name"], "client": m["client"]} for m in access.matters() if user.can_see_matter(m["id"])],
        "gemini": bool(os.getenv("LLM_API_KEY")),
        "graph": bool(os.getenv("NEO4J_URI")),
        "graph_counts": _graph_counts(),
        "contracts": contracts,
        "judgments": _judgments(),
        "playbook": [{"id": i["id"], "title": i["title"], "required": i["required"]} for i in playbook()],
        "version_pair": [p.name for p in sorted(VERSIONS.glob("*.json"))] if user.can_see_document("versions/supply_agreement_v1.json") else [],
        "notice_sample": {k: v for k, v in json.loads((DRAFTING / "notice_facts.json").read_text(encoding="utf-8")).items() if k != "_about"},
        "clause_sample": {k: v for k, v in json.loads((DRAFTING / "clause_request.json").read_text(encoding="utf-8")).items() if k != "_about"},
        "reports": [{"file": f, "title": t} for f, t in REPORTS.items() if (ROOT / "evaluations" / f).exists()],
    }


# ----------------------------------------------------------------------------- research
class Ask(BaseModel):
    question: str
    mode: str = "auto"   # auto | vector | graph | hybrid


@app.post("/api/ask")
def ask(body: Ask, user: access.User = Depends(current_user)) -> Dict:
    from src.rag.router import route

    question = body.question.strip()
    if not 3 <= len(question) <= 600:
        raise HTTPException(400, "Ask a question of 3 to 600 characters.")
    routed = route(question)
    mode = routed["mode"] if body.mode == "auto" else body.mode
    if mode not in ("vector", "graph", "hybrid"):
        raise HTTPException(400, "Unknown mode.")
    audit.record(user.username, "ask", detail=f"[{mode}] {question}")
    out = {"question": question, "route": routed, "mode": mode, "chosen_by": "router" if body.mode == "auto" else "you",
           "answer": None, "graph": None, "errors": []}
    if mode in ("graph", "hybrid"):
        try:
            g = _graph().answer(question)
            out["graph"] = {"method": g["method"], "cypher": g["cypher"], "items": g["items"], "error": g["error"]}
            if (g["error"] or "").startswith("rejected"):
                audit.record(user.username, "graph query", "denied", detail=f"{g['error']}: {question}")
        except Exception as exc:
            if mode == "graph":
                raise _fail(exc)
            out["errors"].append(_fail(exc).detail)
    if mode in ("vector", "hybrid"):
        from src.rag.pipeline import answer_with_citations
        try:
            out["answer"] = answer_with_citations(question, allow=_allow(user))
        except Exception as exc:
            if mode == "vector" or not out["graph"]:
                raise _fail(exc)
            out["errors"].append(_fail(exc).detail)
    return out


# ----------------------------------------------------------------------------- contract review
def _queued(user: access.User, kind: str, params: Dict) -> Dict:
    return {"job_id": jobs.enqueue(user.username, kind, params), "status": "queued"}


@app.post("/api/review")
async def review(party: str = Form("the Client"), contract_id: Optional[str] = Form(None), matter: Optional[str] = Form(None),
                 file: Optional[UploadFile] = File(None), user: access.User = Depends(current_user)) -> Dict:
    hidden_text: List[str] = []
    if file is not None and file.filename:
        accepted = await _accept_upload(file, matter, user, "review upload")
        source, target, hidden_text = str(accepted["path"]), accepted["document_id"], accepted["hidden_text"]
    elif contract_id:
        if not user.can_see_document(contract_id):
            raise _deny(user, "review", contract_id)
        source, target = _contract_path(contract_id), contract_id
    else:
        raise HTTPException(400, "Choose a sample contract or upload one.")
    return _queued(user, "review", {"source": source, "target": target, "party": party.strip()[:120] or "the Client",
                                    "hidden_text": hidden_text})


@app.post("/api/compare")
async def compare_versions(client: str = Form("the Client"), use_sample: bool = Form(False), matter: Optional[str] = Form(None),
                           old_file: Optional[UploadFile] = File(None), new_file: Optional[UploadFile] = File(None),
                           user: access.User = Depends(current_user)) -> Dict:
    hidden_text: List[str] = []
    if use_sample:
        names = sorted(p.name for p in VERSIONS.glob("*.json"))[:2]
        documents = [f"versions/{n}" for n in names]
        if not all(user.can_see_document(d) for d in documents):
            raise _deny(user, "compare", documents[0])
        old_path, new_path = (str(VERSIONS / n) for n in names)
    elif old_file is not None and new_file is not None and old_file.filename and new_file.filename:
        old = await _accept_upload(old_file, matter, user, "compare upload")
        new = await _accept_upload(new_file, matter, user, "compare upload")
        old_path, new_path, documents = str(old["path"]), str(new["path"]), [old["document_id"], new["document_id"]]
        hidden_text = old["hidden_text"] + new["hidden_text"]
    else:
        raise HTTPException(400, "Use the sample pair or upload both versions.")
    return _queued(user, "compare", {"old": old_path, "new": new_path, "documents": documents, "target": documents[-1],
                                     "client": client.strip()[:120] or "the Client", "hidden_text": hidden_text})


# ----------------------------------------------------------------------------- drafting
class BriefRequest(BaseModel):
    document_id: str


class NoticeRequest(BaseModel):
    sender: str
    recipient: str
    date: str = ""
    contract: str = ""
    facts: List[str]
    demand: str
    legal_questions: List[str]


class ClauseRequest(BaseModel):
    title: str = "Draft clauses"
    facts: Dict[str, str] = {}
    items: List[str]


@app.post("/api/draft/brief")
def draft_brief(body: BriefRequest, user: access.User = Depends(current_user)) -> Dict:
    if body.document_id not in {j["id"] for j in _judgments()}:
        raise HTTPException(404, "Unknown judgment.")
    return _queued(user, "brief", {"document_id": body.document_id})


@app.post("/api/draft/notice")
def draft_notice(body: NoticeRequest, user: access.User = Depends(current_user)) -> Dict:
    facts = body.model_dump()
    facts["facts"] = [f.strip() for f in facts["facts"] if f.strip()][:20]
    facts["legal_questions"] = [q.strip() for q in facts["legal_questions"] if q.strip()][:5]
    if not facts["facts"] or not facts["legal_questions"]:
        raise HTTPException(400, "Give at least one fact and one legal point to research.")
    return _queued(user, "notice", facts)


@app.post("/api/draft/clauses")
def draft_clauses(body: ClauseRequest, user: access.User = Depends(current_user)) -> Dict:
    from src.contracts.review import playbook
    items = [i for i in body.items if i in {p["id"] for p in playbook()}]
    if not items:
        raise HTTPException(400, "Choose at least one clause.")
    return _queued(user, "clauses", {"title": body.title, "facts": body.facts, "items": items})


# ----------------------------------------------------------------------------- upload and jobs
@app.post("/api/upload")
async def upload(matter: str = Form(...), file: UploadFile = File(...), user: access.User = Depends(current_user)) -> Dict:
    """Add a contract to a client matter: parse, screen for prompt injection, then index it (a job), so
    Research and Review can use it - for the users on that matter only."""
    accepted = await _accept_upload(file, matter, user, "upload")
    queued = _queued(user, "index_upload", {"document_id": accepted["document_id"], "path": str(accepted["path"])})
    return {**queued, "document_id": accepted["document_id"], "hidden_text": accepted["hidden_text"]}


@app.get("/api/uploads")
def uploads(user: access.User = Depends(current_user)) -> List[Dict]:
    return [{**d, "matter": access.matter_of(d["id"])} for d in _uploaded() if user.can_see_document(d["id"])]


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, user: access.User = Depends(current_user)) -> Dict:
    job = jobs.get(job_id) if re.fullmatch(r"[0-9a-f]{12}", job_id) else None
    if job is None or (job["user"] != user.username and user.role != "admin"):
        raise HTTPException(404, "No such job.")
    return job


@app.get("/api/jobs")
def my_jobs(user: access.User = Depends(current_user)) -> List[Dict]:
    return jobs.list_for(user.username)


# ----------------------------------------------------------------------------- files, reports, audit
@app.get("/api/download/{name}")
def download(name: str, user: access.User = Depends(current_user)) -> FileResponse:
    path = OUT / name
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.docx", name) or not path.exists():
        raise HTTPException(404, "File not found.")
    if owner_of(name) != user.username and user.role != "admin":
        audit.record(user.username, "download", "denied", target=name)
        raise HTTPException(404, "File not found.")
    audit.record(user.username, "download", target=name)
    return FileResponse(path, filename=name,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/api/report/{name}")
def report(name: str, user: access.User = Depends(current_user)) -> Dict:
    if name not in REPORTS or not (ROOT / "evaluations" / name).exists():
        raise HTTPException(404, "Report not found.")
    return {"title": REPORTS[name], "markdown": (ROOT / "evaluations" / name).read_text(encoding="utf-8")}


@app.get("/api/admin/audit")
def audit_log(n: int = 200, user: access.User = Depends(current_user)) -> Dict:
    if user.role != "admin":
        audit.record(user.username, "view audit log", "denied")
        raise HTTPException(403, "Only the administrator can view the audit log.")
    intact, entries, broken = audit.verify()
    return {"intact": intact, "entries": entries, "first_broken_line": broken, "log": audit.tail(max(1, min(n, 1000)))[::-1]}


# ----------------------------------------------------------------------------- health
_graph_health: Dict = {"checked": 0.0, "result": None}


def _check_graph() -> Dict:
    """Neo4j round trip, cached for 30 s so health polling does not load the database."""
    if time.time() - _graph_health["checked"] < 30 and _graph_health["result"]:
        return _graph_health["result"]
    if not os.getenv("NEO4J_URI"):
        result = {"status": "not configured"}
    else:
        start = time.time()
        try:
            from src.graph.neo4j_client import database, get_driver
            driver = get_driver()
            try:
                with driver.session(database=database()) as session:
                    n = session.run("MATCH (c:Case) RETURN count(c) AS n").single()["n"]
            finally:
                driver.close()
            result = {"status": "ok", "cases": n, "ms": round(1000 * (time.time() - start))}
        except Exception as exc:
            result = {"status": "down", "error": type(exc).__name__}
    _graph_health.update(checked=time.time(), result=result)
    return result


@app.get("/api/health/live")
def live() -> Dict:
    """Liveness: the web process answers (Docker restarts the container if this fails)."""
    return {"status": "alive"}


@app.get("/api/health")
def health() -> JSONResponse:
    """Readiness: each dependency, without secrets. ok / degraded (the app works with reduced features) /
    down (search cannot work: HTTP 503)."""
    checks: Dict[str, Dict] = {}
    index = ROOT / "data" / "indices" / "vstore_legal.sqlite3"
    if index.exists():
        import sqlite3
        with sqlite3.connect(f"file:{index.as_posix()}?mode=ro", uri=True) as con:
            checks["search_index"] = {"status": "ok", "passages": con.execute("SELECT COUNT(*) FROM legal_chunks").fetchone()[0]}
    else:
        checks["search_index"] = {"status": "down", "error": "index files missing"}
    checks["graph"] = _check_graph()
    checks["llm"] = {"status": "ok" if os.getenv("LLM_API_KEY") else "not configured"}   # no call: it would spend quota
    beat = jobs.last_heartbeat()
    age = None if beat is None else round(time.time() - beat)
    checks["worker"] = {"status": "ok" if age is not None and age < 30 else "down", "last_heartbeat_s": age, "jobs": jobs.counts()}
    intact, entries, _ = audit.verify()
    checks["audit_log"] = {"status": "ok" if intact else "tampered", "entries": entries}
    free = __import__("shutil").disk_usage(ROOT).free
    checks["disk"] = {"status": "ok" if free > 1 << 30 else "low", "free_gb": round(free / (1 << 30), 1)}
    if checks["search_index"]["status"] != "ok":
        overall = "down"
    elif all(c["status"] == "ok" for c in checks.values()):
        overall = "ok"
    else:
        overall = "degraded"
    return JSONResponse({"status": overall, "checks": checks}, status_code=503 if overall == "down" else 200)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
