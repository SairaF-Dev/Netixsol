"""Tests for the web app (web/server.py) and its background jobs, with a fake LLM: no Gemini or Neo4j calls.
Users, matters, the audit log, the job database and the search index are temporary copies."""
import io
import json
import time

import pytest
from fastapi.testclient import TestClient

from src.contracts.compare import Impact, Impacts
from src.contracts.drafting import Draft, DraftSection
from src.contracts.review import Finding, Review
from src.jobs import handlers, queue, worker
from web import server


class FakeLLM:
    def generate_json(self, prompt, schema, system=None, temperature=0.0):
        if schema is Review:
            return Review(findings=[
                Finding(item_id="liability_cap", status="red", clause_ids=["7"], quote="not a quote from the contract",
                        reason="one-sided", suggested_wording="Cap at 12 months' fees.")])
        if schema is Impacts:
            numbers = [int(line.split(".")[0]) for line in prompt.split("CHANGES\n")[1].splitlines() if line[:1].isdigit()]
            return Impacts(impacts=[Impact(n=n, summary="changed", legal_impact="effect", favours="neither", risk="low",
                                           playbook_item="none") for n in numbers])
        if schema is Draft:
            return Draft(title="Draft clauses", sections=[DraftSection(heading="Limitation of Liability", text="Liability is capped.", citations=[])])
        raise AssertionError(f"unexpected schema {schema}")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    from src.security import access, audit
    users = [{**u, "password_hash": access.hash_password("pw-" + u["username"])} for u in access.DEMO_USERS]
    (tmp_path / "users.json").write_text(json.dumps({"users": users}), encoding="utf-8")
    (tmp_path / "matters.json").write_text(json.dumps({"matters": access.DEMO_MATTERS}), encoding="utf-8")
    monkeypatch.setattr(access, "USERS", tmp_path / "users.json")
    monkeypatch.setattr(access, "MATTERS", tmp_path / "matters.json")
    monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "audit.jsonl")
    monkeypatch.setattr(queue, "JOB_DB", tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(handlers, "_llm", lambda: FakeLLM())
    monkeypatch.setattr(server, "_gemini", lambda: FakeLLM())
    server._failed.clear()   # sign-in lockouts from other tests (the lockout itself is tested in test_security)
    c = TestClient(server.app)

    def sign_in(name):
        return {"Authorization": "Bearer " + c.post("/api/login", json={"username": name, "password": "pw-" + name}).json()["token"]}
    return c, sign_in, tmp_path


@pytest.fixture()
def client(env):
    """Signed in as the partner (all matters)."""
    c, sign_in, _ = env
    c.headers.update(sign_in("sana"))
    return c


def done(client, response):
    """Run the queued job (as the worker would) and return its result."""
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    worker.process_all()
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "done", job
    return job["result"]


def test_meta_lists_samples_and_reports(client):
    meta = client.get("/api/meta").json()
    assert meta["playbook"] and meta["contracts"] and meta["version_pair"] == ["supply_agreement_v1.json", "supply_agreement_v2.json"]
    assert "LLM_API_KEY" not in json.dumps(meta)   # presence flags only, never values


def test_review_runs_as_a_job_and_returns_findings_and_word_file(client):
    r = client.post("/api/review", data={"contract_id": "versions/supply_agreement_v2.json", "party": "the Client"})
    assert r.json()["status"] == "queued"                 # the request returns at once
    result = done(client, r)
    cap = next(f for f in result["findings"] if f["item_id"] == "liability_cap")
    assert cap["status"] == "red" and cap["quote"] == "" and cap["quote_note"]   # invented quote removed
    assert len(result["findings"]) == 14 and result["band"] in ("Low", "Medium", "High")
    assert client.get(result["download"]).status_code == 200


def test_review_upload_of_plain_text_contract(client):
    text = ("SERVICES AGREEMENT\n\n1. Payment\nThe Client shall pay each invoice within thirty days of receipt in Pakistani Rupees.\n\n"
            "2. Governing Law\nThis Agreement is governed by the laws of Pakistan and the courts at Karachi have jurisdiction.\n")
    r = client.post("/api/review", data={"party": "the Client", "matter": "MAT-001"}, files={"file": ("deal.txt", io.BytesIO(text.encode()), "text/plain")})
    assert len(done(client, r)["findings"]) == 14


def test_upload_rejects_other_file_types(client):
    r = client.post("/api/review", data={"party": "x", "matter": "MAT-001"}, files={"file": ("run.exe", io.BytesIO(b"MZ"), "application/octet-stream")})
    assert r.status_code == 400


def test_compare_sample_pair_finds_all_planted_changes(client):
    result = done(client, client.post("/api/compare", data={"use_sample": "true", "client": "the Client"}))
    assert len(result["changes"]) == 9 and all(c["impact"] for c in result["changes"])


def test_draft_clauses_carry_playbook_and_statute_sources(client):
    result = done(client, client.post("/api/draft/clauses", json={"title": "Draft clauses", "facts": {"client": "X"}, "items": ["liability_cap"]}))
    sources = result["sections"][0]["sources"]
    assert sources[0]["source"].startswith("Firm playbook") and any("Section 73" in s["source"] for s in sources)


def test_a_job_is_visible_only_to_its_owner(env):
    c, sign_in, _ = env
    r = c.post("/api/draft/clauses", json={"items": ["liability_cap"]}, headers=sign_in("ayesha"))
    job_id = r.json()["job_id"]
    assert c.get(f"/api/jobs/{job_id}", headers=sign_in("ayesha")).status_code == 200
    assert c.get(f"/api/jobs/{job_id}", headers=sign_in("bilal")).status_code == 404


def test_a_failing_job_reports_a_plain_message(client, monkeypatch):
    class QuotaLLM:
        def generate_json(self, *a, **k):
            raise RuntimeError("Gemini daily quota exhausted; try again tomorrow or use another key")
    monkeypatch.setattr(handlers, "_llm", lambda: QuotaLLM())
    job_id = client.post("/api/draft/clauses", json={"items": ["liability_cap"]}).json()["job_id"]
    worker.process_all()
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed" and "13:00 PKT" in job["error"]


def test_job_left_running_by_a_dead_worker_is_failed_not_rerun(env):
    queue.enqueue("sana", "clauses", {"items": ["liability_cap"]})
    queue.claim("dead-worker")                       # claimed, then the worker "crashed" (no heartbeat)
    assert queue.fail_stale() == 1
    assert queue.counts() == {"failed": 1}


def test_upload_is_indexed_for_its_matter_only(env, monkeypatch):
    from src.indexing.bm25_index import LegalBM25Index
    from src.indexing.vector_store import DenseVectorStore
    c, sign_in, tmp = env
    index = tmp / "indices"; index.mkdir()
    from src.chunking.section_chunker import SectionLevelChunker
    from src.utils.schemas import ContractDocument
    DenseVectorStore(persist_directory=index / "vstore_legal.sqlite3").connection.close()   # an empty vector index
    bm25 = LegalBM25Index()   # BM25 cannot load an empty corpus (average length 0): seed one passage
    bm25.add_chunks(SectionLevelChunker().chunk_contract(ContractDocument(document_id="SEED", contract_title="Seed", contract_type="x")))
    bm25.save(index / "bm25_legal.pkl")
    monkeypatch.setattr(handlers, "INDEX_DIR", index)
    monkeypatch.setattr(handlers, "INDEX_VERSION", index / "index_version.txt")
    text = ("SUPPLY AGREEMENT\n1. Payment. The Client shall pay each invoice within thirty days of receipt.\n"
            "2. Governing Law. This Agreement is governed by the laws of Pakistan.\n3. Notices. Notices are given in writing.\n")
    ayesha = sign_in("ayesha")
    r = c.post("/api/upload", data={"matter": "MAT-001"}, files={"file": ("supply.txt", io.BytesIO(text.encode()), "text/plain")}, headers=ayesha)
    assert r.status_code == 200, r.text
    worker.process_all()
    job = c.get(f"/api/jobs/{r.json()['job_id']}", headers=ayesha).json()
    assert job["status"] == "done" and job["result"]["passages"] >= 3, job
    store = DenseVectorStore.load(index / "vstore_legal.sqlite3")
    assert store.connection.execute("SELECT COUNT(*) FROM legal_chunks WHERE document_id = ?", (r.json()["document_id"],)).fetchone()[0] >= 3
    store.connection.close()
    assert (index / "index_version.txt").exists()                     # tells the web app to reload search
    assert [d["id"] for d in c.get("/api/uploads", headers=ayesha).json()] == [r.json()["document_id"]]
    assert c.get("/api/uploads", headers=sign_in("bilal")).json() == []


def test_health_reports_each_part_without_secrets(client, monkeypatch):
    monkeypatch.setattr(server, "_check_graph", lambda: {"status": "ok"})   # no network in tests
    r = client.get("/api/health")
    body = r.json()
    assert set(body["checks"]) >= {"search_index", "graph", "llm", "worker", "audit_log", "disk"}
    assert body["checks"]["worker"]["status"] == "down"              # no worker running in this test
    if body["checks"]["search_index"]["status"] == "ok":
        assert body["status"] == "degraded" and r.status_code == 200
    else:                                                            # a fresh checkout (CI) has no index: 503
        assert body["status"] == "down" and r.status_code == 503
    assert "bolt" not in json.dumps(body) and "neo4j+s" not in json.dumps(body)
    assert client.get("/api/health/live").json() == {"status": "alive"}


def test_downloads_and_reports_cannot_leave_their_folders(client):
    assert client.get("/api/download/..%2F..%2F.env").status_code == 404
    assert client.get("/api/report/..%2F..%2F.env").status_code == 404


def test_quota_error_becomes_a_plain_message():
    exc = server._fail(RuntimeError("Gemini daily quota exhausted; try again tomorrow or use another key"))
    assert exc.status_code == 503 and "13:00 PKT" in exc.detail
