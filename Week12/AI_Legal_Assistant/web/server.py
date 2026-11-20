"""
Web app for the AI Legal Assistant: one page, six tools, all calling the Day 2-4 code.

    Research      question -> router -> verified answer (vector) / graph list (graph) / both (hybrid)
    Case law      GraphRAG over Neo4j (no LLM for linked questions; text-to-Cypher as fallback)
    Review        playbook review of a sample or uploaded contract -> findings + Word file with comments
    Compare       two versions (sample pair or uploads) -> word diff + impact explanation + Word redline
    Drafting      case brief / legal notice / clauses, every source checked -> Word file
    Evaluation    the evaluation reports in evaluations/*.md

Gemini answers are cached on disk (data/llm_cache), so a question asked before costs nothing.
Generated Word files and uploads go to data/web_outputs/ (not in git).

Run:  python -m web.server            then open http://127.0.0.1:8000
      PORT=7860 HOST=0.0.0.0 python -m web.server   (Hugging Face Spaces)
"""

import csv
import json
import os
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)   # the project code uses paths relative to the project folder

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv(ROOT / ".env")

STATIC = Path(__file__).parent / "static"
OUT = ROOT / "data" / "web_outputs"
UPLOADS = OUT / "uploads"
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

app = FastAPI(title="Khan & Associates - AI Legal Assistant", docs_url="/api/docs")


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
    return HTTPException(500, f"Something went wrong: {type(exc).__name__}: {message[:300]}")


def _download(path: Path) -> str:
    return f"/api/download/{path.name}"


def _new_name(stem: str, suffix: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", stem)[:60].strip("_") or "file"
    return OUT / f"{safe}_{uuid.uuid4().hex[:8]}{suffix}"


async def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in UPLOAD_TYPES:
        raise HTTPException(400, f"Upload a PDF, Word (.docx), text or JSON file, not '{suffix or 'no extension'}'.")
    data = await upload.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "The file is larger than 15 MB.")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return path


def contract_from_file(path: Path, title: str) -> Path:
    """Any uploaded contract -> the structured JSON the review and comparison code read (clauses)."""
    from src.extraction.contract_extractor import ContractStructureExtractor

    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
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
    out = path.with_suffix(".contract.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


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


def _contract_path(contract_id: str) -> str:
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
def meta() -> Dict:
    from src.contracts.review import playbook
    return {
        "gemini": bool(os.getenv("LLM_API_KEY")),
        "graph": bool(os.getenv("NEO4J_URI")),
        "graph_counts": _graph_counts(),
        "contracts": _contracts(),
        "judgments": _judgments(),
        "playbook": [{"id": i["id"], "title": i["title"], "required": i["required"]} for i in playbook()],
        "version_pair": [p.name for p in sorted(VERSIONS.glob("*.json"))],
        "notice_sample": {k: v for k, v in json.loads((DRAFTING / "notice_facts.json").read_text(encoding="utf-8")).items() if k != "_about"},
        "clause_sample": {k: v for k, v in json.loads((DRAFTING / "clause_request.json").read_text(encoding="utf-8")).items() if k != "_about"},
        "reports": [{"file": f, "title": t} for f, t in REPORTS.items() if (ROOT / "evaluations" / f).exists()],
    }


# ----------------------------------------------------------------------------- research
class Ask(BaseModel):
    question: str
    mode: str = "auto"   # auto | vector | graph | hybrid


@app.post("/api/ask")
def ask(body: Ask) -> Dict:
    from src.rag.router import route

    question = body.question.strip()
    if not 3 <= len(question) <= 600:
        raise HTTPException(400, "Ask a question of 3 to 600 characters.")
    routed = route(question)
    mode = routed["mode"] if body.mode == "auto" else body.mode
    if mode not in ("vector", "graph", "hybrid"):
        raise HTTPException(400, "Unknown mode.")
    out = {"question": question, "route": routed, "mode": mode, "chosen_by": "router" if body.mode == "auto" else "you",
           "answer": None, "graph": None, "errors": []}
    if mode in ("graph", "hybrid"):
        try:
            g = _graph().answer(question)
            out["graph"] = {"method": g["method"], "cypher": g["cypher"], "items": g["items"], "error": g["error"]}
        except Exception as exc:
            if mode == "graph":
                raise _fail(exc)
            out["errors"].append(_fail(exc).detail)
    if mode in ("vector", "hybrid"):
        from src.rag.pipeline import answer_with_citations
        try:
            out["answer"] = answer_with_citations(question)
        except Exception as exc:
            if mode == "vector" or not out["graph"]:
                raise _fail(exc)
            out["errors"].append(_fail(exc).detail)
    return out


# ----------------------------------------------------------------------------- contract review
@app.post("/api/review")
async def review(party: str = Form("the Client"), contract_id: Optional[str] = Form(None),
                 file: Optional[UploadFile] = File(None)) -> Dict:
    from starlette.concurrency import run_in_threadpool
    from src.contracts.review import export_docx, risk_band, review_contract

    if file is not None and file.filename:
        source = str(contract_from_file(await _save_upload(file), Path(file.filename).stem))
    elif contract_id:
        source = _contract_path(contract_id)
    else:
        raise HTTPException(400, "Choose a sample contract or upload one.")
    party = party.strip()[:120] or "the Client"
    try:
        result = await run_in_threadpool(review_contract, source, party, _gemini())
        path = await run_in_threadpool(export_docx, result, _new_name(f"review_{result['title'] or 'contract'}", ".docx"))
    except HTTPException:
        raise
    except Exception as exc:
        raise _fail(exc)
    result["band"] = risk_band(result["risk_score"])
    result["download"] = _download(path)
    return result


# ----------------------------------------------------------------------------- comparison
@app.post("/api/compare")
async def compare_versions(client: str = Form("the Client"), use_sample: bool = Form(False),
                           old_file: Optional[UploadFile] = File(None), new_file: Optional[UploadFile] = File(None)) -> Dict:
    from starlette.concurrency import run_in_threadpool
    from src.contracts.compare import compare, to_docx

    if use_sample:
        old_path, new_path = (VERSIONS / n for n in sorted(p.name for p in VERSIONS.glob("*.json"))[:2])
    elif old_file is not None and new_file is not None and old_file.filename and new_file.filename:
        old_path = contract_from_file(await _save_upload(old_file), Path(old_file.filename).stem)
        new_path = contract_from_file(await _save_upload(new_file), Path(new_file.filename).stem)
    else:
        raise HTTPException(400, "Use the sample pair or upload both versions.")
    try:
        result = await run_in_threadpool(compare, old_path, new_path, client.strip()[:120] or "the Client", _gemini())
        path = await run_in_threadpool(to_docx, result, _new_name("comparison", ".docx"))
    except HTTPException:
        raise
    except Exception as exc:
        raise _fail(exc)
    result["download"] = _download(path)
    return result


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


def _finish_draft(doc: Dict, stem: str) -> Dict:
    from src.contracts.drafting import to_docx
    doc["download"] = _download(to_docx(doc, _new_name(stem, ".docx")))
    return doc


@app.post("/api/draft/brief")
def draft_brief(body: BriefRequest) -> Dict:
    from src.contracts.drafting import case_brief
    if body.document_id not in {j["id"] for j in _judgments()}:
        raise HTTPException(404, "Unknown judgment.")
    try:
        return _finish_draft(case_brief(body.document_id, llm=_gemini()), f"brief_{body.document_id}")
    except Exception as exc:
        raise _fail(exc)


@app.post("/api/draft/notice")
def draft_notice(body: NoticeRequest) -> Dict:
    from src.contracts.drafting import legal_notice
    facts = body.model_dump()
    facts["facts"] = [f.strip() for f in facts["facts"] if f.strip()][:20]
    facts["legal_questions"] = [q.strip() for q in facts["legal_questions"] if q.strip()][:5]
    if not facts["facts"] or not facts["legal_questions"]:
        raise HTTPException(400, "Give at least one fact and one legal point to research.")
    try:
        return _finish_draft(legal_notice(facts, llm=_gemini()), "legal_notice")
    except Exception as exc:
        raise _fail(exc)


@app.post("/api/draft/clauses")
def draft_clauses(body: ClauseRequest) -> Dict:
    from src.contracts.drafting import clauses
    from src.contracts.review import playbook
    items = [i for i in body.items if i in {p["id"] for p in playbook()}]
    if not items:
        raise HTTPException(400, "Choose at least one clause.")
    try:
        return _finish_draft(clauses({"title": body.title, "facts": body.facts, "items": items}, llm=_gemini()), "clauses")
    except Exception as exc:
        raise _fail(exc)


# ----------------------------------------------------------------------------- files and reports
@app.get("/api/download/{name}")
def download(name: str) -> FileResponse:
    path = OUT / name
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.docx", name) or not path.exists():
        raise HTTPException(404, "File not found.")
    return FileResponse(path, filename=name,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/api/report/{name}")
def report(name: str) -> Dict:
    if name not in REPORTS or not (ROOT / "evaluations" / name).exists():
        raise HTTPException(404, "Report not found.")
    return {"title": REPORTS[name], "markdown": (ROOT / "evaluations" / name).read_text(encoding="utf-8")}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
