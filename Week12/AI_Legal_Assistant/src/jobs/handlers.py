"""
What each background job does. Every handler gets the job's parameters and the user who asked, re-checks
that user's access (permissions can change between asking and running), does the work, writes the audit
entry and returns a JSON result for the page.

    review        playbook review of a contract -> findings + Word file with comments
    compare       two versions -> changes, impacts, Word redline
    brief         case brief of a judgment
    notice        legal notice from facts, legal basis retrieved within the user's access
    clauses       contract clauses from the playbook
    index_upload  an uploaded contract -> section-level chunks -> BM25 + vector index, so Research finds
                  it (only for users on its matter)
"""

import json
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict

from src.security import access, audit

OUT = Path("data/web_outputs")
UPLOADS = OUT / "uploads"
OWNERS = OUT / "owners.json"
INDEX_DIR = Path("data/indices")
INDEX_VERSION = INDEX_DIR / "index_version.txt"
_owners_lock = threading.Lock()


class JobError(Exception):
    """A failure with a message the lawyer can act on."""


@lru_cache(maxsize=1)
def _llm():
    from src.llm.gemini_client import GeminiClient
    return GeminiClient()


def friendly_error(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, (JobError, PermissionError)):
        return message
    if "quota" in message.lower() or "PerDay" in message or "RESOURCE_EXHAUSTED" in message:
        return ("The free Gemini limit for today is used up. It resets at about 13:00 PKT. "
                "Work done before is saved and still opens instantly.")
    if "LLM_API_KEY" in message:
        return "Gemini is not configured on this server (LLM_API_KEY is missing)."
    return f"Something went wrong ({type(exc).__name__}). The error has been logged."


# ----------------------------------------------------------------------------- generated files
def new_name(stem: str, suffix: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", stem)[:60].strip("_") or "file"
    return OUT / f"{safe}_{uuid.uuid4().hex[:8]}{suffix}"


def register_download(path: Path, username: str) -> str:
    """Only the user who created a file (or the admin) may download it."""
    with _owners_lock:
        owners = json.loads(OWNERS.read_text(encoding="utf-8")) if OWNERS.exists() else {}
        owners[path.name] = username
        OWNERS.write_text(json.dumps(owners), encoding="utf-8")
    return f"/api/download/{path.name}"


def owner_of(name: str) -> str:
    owners = json.loads(OWNERS.read_text(encoding="utf-8")) if OWNERS.exists() else {}
    return owners.get(name, "")


def _check(user: access.User, document_id: str) -> None:
    if not user.can_see_document(document_id):
        audit.record(user.username, "job", "denied", matter=access.matter_of(document_id), target=document_id)
        raise PermissionError("This document is not on one of your matters.")


# ----------------------------------------------------------------------------- handlers
def review(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.contracts.review import export_docx, review_contract, risk_band
    _check(user, params["target"])
    report("Finding the relevant clauses and rating each playbook position")
    result = review_contract(params["source"], params["party"], _llm())
    report("Writing the Word file")
    path = export_docx(result, new_name(f"review_{result['title'] or 'contract'}", ".docx"))
    audit.record(user.username, "review", matter=access.matter_of(params["target"]), target=params["target"],
                 detail=f"risk {result['risk_score']}")
    return {**result, "band": risk_band(result["risk_score"]), "download": register_download(path, user.username),
            "hidden_text": params.get("hidden_text", [])}


def compare(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.contracts.compare import compare as run_compare, to_docx
    for doc in params["documents"]:
        _check(user, doc)
    report("Matching clauses and explaining each change")
    result = run_compare(Path(params["old"]), Path(params["new"]), params["client"], _llm())
    path = to_docx(result, new_name("comparison", ".docx"))
    audit.record(user.username, "compare", matter=access.matter_of(params["target"]), target=params["target"],
                 detail=f"{len(result['changes'])} changes")
    return {**result, "download": register_download(path, user.username), "hidden_text": params.get("hidden_text", [])}


def _draft(doc: Dict, stem: str, user: access.User) -> Dict:
    from src.contracts.drafting import to_docx
    doc["download"] = register_download(to_docx(doc, new_name(stem, ".docx")), user.username)
    audit.record(user.username, f"draft {doc['kind']}", detail=doc.get("title", ""))
    return doc


def brief(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.contracts.drafting import case_brief
    report("Reading the judgment and checking each quote")
    return _draft(case_brief(params["document_id"], llm=_llm()), f"brief_{params['document_id']}", user)


def notice(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.contracts.drafting import legal_notice
    report("Researching the legal basis and verifying citations")
    allow = lambda chunk: user.can_see_document(chunk["document_id"], chunk.get("document_type"))
    return _draft(legal_notice(params, llm=_llm(), allow=allow), "legal_notice", user)


def clauses(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.contracts.drafting import clauses as draft_clauses
    report("Adapting the firm's standard wording")
    return _draft(draft_clauses(params, llm=_llm()), "clauses", user)


@contextmanager
def _index_lock(timeout: float = 300):
    """One writer at a time for the search indexes (a lock file works across processes and containers)."""
    from src.utils.filelock import LockTimeout, file_lock
    try:
        with file_lock(INDEX_DIR / ".write.lock", timeout=timeout, stale=900, poll=1):
            yield
    except LockTimeout:
        raise JobError("The search index is busy; please try again in a few minutes.")


def index_upload(params: Dict, user: access.User, report: Callable[[str], None]) -> Dict:
    from src.chunking.section_chunker import SectionLevelChunker
    from src.indexing.bm25_index import LegalBM25Index
    from src.indexing.vector_store import DenseVectorStore
    from src.utils.schemas import ContractDocument

    document_id = params["document_id"]
    _check(user, document_id)
    data = json.loads(Path(params["path"]).read_text(encoding="utf-8"))
    doc = ContractDocument.model_validate({**data, "document_id": document_id,
                                           "contract_title": data.get("contract_title") or document_id,
                                           "contract_type": data.get("contract_type") or "Uploaded contract"})
    chunks = SectionLevelChunker().chunk_contract(doc)
    report(f"Embedding {len(chunks)} passages")
    with _index_lock():
        vectors = DenseVectorStore.load(INDEX_DIR / "vstore_legal.sqlite3")   # writes straight to the SQLite file
        vectors.remove_documents([document_id])
        vectors.add_chunks(chunks)
        vectors.connection.close()
        if os.getenv("VECTOR_BACKEND", "sqlite").lower() == "qdrant":   # Docker: copy the new vectors to Qdrant
            from src.indexing.qdrant_store import sync_documents
            report("Copying the vectors to Qdrant")
            sync_documents([document_id])
        report("Updating the keyword index")
        bm25 = LegalBM25Index.load(INDEX_DIR / "bm25_legal.pkl")
        bm25.remove_documents([document_id])
        bm25.add_chunks(chunks)
        tmp = INDEX_DIR / "bm25_legal.pkl.tmp"
        bm25.save(tmp)
        os.replace(tmp, INDEX_DIR / "bm25_legal.pkl")   # atomic: a reader never sees half a file
        INDEX_VERSION.write_text(str(time.time()), encoding="utf-8")   # the web app reloads its search
    audit.record(user.username, "index upload", matter=access.matter_of(document_id), target=document_id,
                 detail=f"{doc.contract_title}: {len(doc.clauses)} clauses, {len(chunks)} passages")
    return {"document_id": document_id, "title": doc.contract_title, "clauses": len(doc.clauses), "passages": len(chunks),
            "matter": access.matter_of(document_id)}


HANDLERS = {"review": review, "compare": compare, "brief": brief, "notice": notice, "clauses": clauses,
            "index_upload": index_upload}
