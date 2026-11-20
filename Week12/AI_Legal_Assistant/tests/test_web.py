"""Tests for the web app (web/server.py) with a fake LLM: no Gemini or Neo4j calls."""
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.contracts.compare import Impact, Impacts
from src.contracts.drafting import Draft, DraftSection
from src.contracts.review import Finding, Review
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
def client(monkeypatch):
    monkeypatch.setattr(server, "_gemini", lambda: FakeLLM())
    return TestClient(server.app)


def test_meta_lists_samples_and_reports(client):
    meta = client.get("/api/meta").json()
    assert meta["playbook"] and meta["contracts"] and meta["version_pair"] == ["supply_agreement_v1.json", "supply_agreement_v2.json"]
    assert "LLM_API_KEY" not in json.dumps(meta)   # presence flags only, never values


def test_review_sample_returns_findings_and_word_file(client):
    r = client.post("/api/review", data={"contract_id": "versions/supply_agreement_v2.json", "party": "the Client"}).json()
    cap = next(f for f in r["findings"] if f["item_id"] == "liability_cap")
    assert cap["status"] == "red" and cap["quote"] == "" and cap["quote_note"]   # invented quote removed
    assert len(r["findings"]) == 14 and r["band"] in ("Low", "Medium", "High")
    assert client.get(r["download"]).status_code == 200


def test_review_upload_of_plain_text_contract(client):
    text = ("SERVICES AGREEMENT\n\n1. Payment\nThe Client shall pay each invoice within thirty days of receipt in Pakistani Rupees.\n\n"
            "2. Governing Law\nThis Agreement is governed by the laws of Pakistan and the courts at Karachi have jurisdiction.\n")
    r = client.post("/api/review", data={"party": "the Client"}, files={"file": ("deal.txt", io.BytesIO(text.encode()), "text/plain")})
    assert r.status_code == 200, r.text
    assert len(r.json()["findings"]) == 14


def test_upload_rejects_other_file_types(client):
    r = client.post("/api/review", data={"party": "x"}, files={"file": ("run.exe", io.BytesIO(b"MZ"), "application/octet-stream")})
    assert r.status_code == 400


def test_compare_sample_pair_finds_all_planted_changes(client):
    r = client.post("/api/compare", data={"use_sample": "true", "client": "the Client"}).json()
    assert len(r["changes"]) == 9 and all(c["impact"] for c in r["changes"])


def test_draft_clauses_carry_playbook_and_statute_sources(client):
    r = client.post("/api/draft/clauses", json={"title": "Draft clauses", "facts": {"client": "X"}, "items": ["liability_cap"]}).json()
    sources = r["sections"][0]["sources"]
    assert sources[0]["source"].startswith("Firm playbook") and any("Section 73" in s["source"] for s in sources)


def test_downloads_and_reports_cannot_leave_their_folders(client):
    assert client.get("/api/download/..%2F..%2F.env").status_code == 404
    assert client.get("/api/report/..%2F..%2F.env").status_code == 404


def test_quota_error_becomes_a_plain_message():
    exc = server._fail(RuntimeError("Gemini daily quota exhausted; try again tomorrow or use another key"))
    assert exc.status_code == 503 and "13:00 PKT" in exc.detail
