# API reference

All endpoints are served by `web/server.py`. An interactive page that lists every endpoint with its fields is
built in: **`/api/docs`** (for example `http://127.0.0.1:8000/api/docs`, or on the live link). This page
explains how to use them and what each one checks.

## Basics

* **Sign in first.** `POST /api/login` returns a token. Send it on every other call as
  `Authorization: Bearer <token>`. A token is valid for 8 hours. Without a valid token: `401`.
* **Matters.** Contracts belong to client matters. A user sees public law plus the contracts of their own
  matters; partners and the admin see all matters. Asking for a document on another matter gives `404`
  (deliberately not `403`, so its existence is not revealed).
* **Long tasks are jobs.** Review, compare, drafting and upload indexing return `{"job_id", "status": "queued"}`
  at once. Poll `GET /api/jobs/{job_id}` every 1-2 seconds until `status` is `done` (the result is in
  `result`) or `failed` (a plain-English reason is in `error`).
* **Errors** are JSON: `{"detail": "message a lawyer can act on"}`.

| Code | Meaning |
|---|---|
| 400 | Something in the request is missing or wrong (the message says what) |
| 401 | Not signed in, or the token is invalid or expired |
| 403 | Signed in but not allowed (e.g. an associate opening the audit log, uploading to another matter) |
| 404 | Not found - or on a matter you are not on |
| 409 | Conflict (blind rating: ratings are final after the reveal) |
| 422 | Upload blocked: it contains instructions addressed to an AI (details in `detail.findings`) |
| 429 | Too many failed sign-ins: locked for 5 minutes |
| 503 | A service is down or the daily Gemini quota is used up (the message says which) |

Every call that reads or changes client data is written to the audit log.

## Example: sign in and ask a question

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/login -H "Content-Type: application/json" \
  -d '{"username": "ayesha", "password": "..."}' | python -c "import sys, json; print(json.load(sys.stdin)['token'])")

curl -s -X POST http://127.0.0.1:8000/api/ask -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "Agar consideration unlawful ho to kya contract void hai?", "mode": "auto"}'
```

```python
import time, httpx
B = "http://127.0.0.1:8000"
h = {"Authorization": "Bearer " + httpx.post(f"{B}/api/login", json={"username": "ayesha", "password": "..."}).json()["token"]}
job = httpx.post(f"{B}/api/review", data={"contract_id": "CONT_SYNTH_001", "party": "the Client"}, headers=h).json()
while (r := httpx.get(f"{B}/api/jobs/{job['job_id']}", headers=h).json())["status"] not in ("done", "failed"):
    time.sleep(2)
print(r["result"]["risk_score"], [f["status"] for f in r["result"]["findings"]])
```

## Endpoints

### Sign-in

| Method and path | Sign-in | Send | Returns |
|---|---|---|---|
| `POST /api/login` | - | JSON `{username, password}` | `{token, user}`. 401 wrong password; 429 after 5 failures in 5 minutes (even with the right password) |
| `GET /api/me` | yes | - | `{username, name, role, matters}` |

### Reference data

| Method and path | Sign-in | Returns |
|---|---|---|
| `GET /api/meta` | yes | Everything the pages need: the user, their matters, the contracts they may see (grouped by matter), judgments, playbook items, drafting samples, the list of reports, whether Gemini and the graph are configured |
| `GET /api/report/{file}` | yes | `{title, markdown}` of an evaluation report. Only the files listed by `/api/meta` are served |

### Research

`POST /api/ask` (signed in) - JSON `{question, mode}`

* `question`: 3-600 characters, English, Urdu or Roman Urdu.
* `mode`: `auto` (the router decides), `vector` (statutes and judgment text), `graph` (case-law relationships),
  `hybrid` (both).

Returns `{question, route, mode, chosen_by, answer, graph, errors}`:

* `answer` (vector / hybrid): `short_answer`, `explanation`, `citations` (each with `act_or_case`, `reference`,
  `title`, `page`, `document_id`, `quote` - every quote has been checked against its source),
  `removed_citations` (citations the checker removed, with the reason), `conclusion_check`
  (`verdict`: supported / partly / not_supported, `redrafted`, `withheld`), `retrieved` (the passages searched).
  When nothing can be verified, `short_answer` is exactly `"No sufficient source found"` and there are no
  citations.
* `graph` (graph / hybrid): `method` (linked question or text-to-Cypher), `cypher` (the query that ran),
  `items`, `error` (e.g. `"rejected: not a read-only query"`).

Search only returns public law and contracts of the user's own matters.

### Contracts (each returns a job)

| Method and path | Send (form fields) | Job result |
|---|---|---|
| `POST /api/review` | `party` (whose side, default "the Client"); either `contract_id` (a sample or uploaded contract the user may see) or `file` + `matter` | `title`, `risk_score` (0-100), `band`, `findings` (one per playbook item: `status` green / amber / red / missing, `clause_ids`, `quote`, `reason`, `suggested_wording`), `download` (Word file with margin comments), `hidden_text` (warnings) |
| `POST /api/compare` | `client`; either `use_sample=true` or `old_file` + `new_file` + `matter` | `changes` (each with the old and new text, a one-line summary, the legal impact for the client, which side it favours, a risk level high / medium / low / none, and the matching playbook item), `download` (Word redline) |

Uploaded files go through the injection scanner first: an instruction addressed to an AI gives `422` before
any AI call. Accepted types: `.pdf`, `.docx`, `.txt`, `.json`; at most 15 MB.

### Drafting (each returns a job)

| Method and path | Send (JSON) | Job result |
|---|---|---|
| `POST /api/draft/brief` | `{document_id}` of a judgment (from `/api/meta`) | A case brief - Facts, Issues, Holding, Reasoning, Outcome - each with paragraph quotes checked against the judgment, plus the precedents and provisions it relies on (from the knowledge graph); `download` |
| `POST /api/draft/notice` | `{sender, recipient, date, contract, facts: [...], demand, legal_questions: [...]}` (max 20 facts, 5 legal questions) | A legal notice; every legal reference in the text must be a verified source, otherwise the sentence is removed and marked (`removed_statements`); `download` |
| `POST /api/draft/clauses` | `{title, facts: {name: value}, items: [playbook ids]}` | Clauses from the firm's standard wording adapted to the facts; `download` |

Every draft is marked "DRAFT - for lawyer review".

### Uploads and jobs

| Method and path | Sign-in | Send / returns |
|---|---|---|
| `POST /api/upload` | yes | Form `matter`, `file` -> `{job_id, document_id, hidden_text}`. 403 if not on the matter, 400 bad file, 422 blocked. The job indexes the contract for that matter's users |
| `GET /api/uploads` | yes | Uploaded contracts on the user's matters |
| `GET /api/jobs/{job_id}` | yes (owner or admin) | `{id, kind, status, progress, result, error, created, started, finished}`; 404 for someone else's job |
| `GET /api/jobs` | yes | The user's recent jobs (without results) |
| `GET /api/download/{file}` | yes (owner or admin) | The Word file; 404 for someone else's file or any path trick |

### Blind rating (Day 5)

| Method and path | Send | Returns |
|---|---|---|
| `GET /api/rating` | - | `{items, ratings, complete}` - 30 answers without their version. When all 30 are rated, also `key` and `results` (per version) |
| `POST /api/rating/{item_id}` | JSON `{correctness: correct/partly/wrong/refused, support: yes/partly/no/none, useful: 1-5, note}` | `{rated, total, complete}`. 409 after the reveal |

### Administration

| Method and path | Sign-in | Returns |
|---|---|---|
| `GET /api/admin/audit?n=200` | admin only (others 403, logged) | `{intact, entries, first_broken_line, log}`: whether the hash chain is unbroken, and the last `n` entries (max 1000), newest first |

### Health (no sign-in, for monitoring)

| Method and path | Returns |
|---|---|
| `GET /api/health/live` | `{"status": "ok"}` while the process runs (used by Docker's health check) |
| `GET /api/health` | `status` plus a check per part: `search_index` (passages), `graph` (cases, response time), `llm` (key present - not called, to save quota), `worker` (last heartbeat, job counts), `audit_log` (entries), `disk` (free GB). `503` when the search index is missing. No keys, names or documents are included |
