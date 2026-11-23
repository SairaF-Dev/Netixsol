# Administrator guide

For whoever runs the AI Legal Assistant: accounts and matters, secrets, the audit log, monitoring, the live
server, the data and its backups, and what to do when something breaks. Commands are run from the project
folder (`Week12/AI_Legal_Assistant`) with the project's Python (`.\.venv\Scripts\python.exe` on Windows).
How to install and deploy is in [deployment.md](deployment.md); the endpoints are in [api.md](api.md).

## 1. Roles and matters

| Role | Sees | Extra |
|---|---|---|
| `admin` | All matters | Page 08 (audit log); may read any job and Word file |
| `partner` | All matters | - |
| `associate` | Public law + only the matters listed on their account | - |

Public law (statutes, judgments) is open to every signed-in user. A client contract is filed under exactly one
matter and is visible only to users on that matter (and partners and the admin). The check is in
`src/security/access.py` and applies to search, review, comparison, downloads, job results, the contract lists
and graph queries.

Files (in `data/security/`, never in git - the repository is public):

| File | Holds |
|---|---|
| `users.json` | Accounts: user name, name, role, matters, password hash (PBKDF2-SHA256, 200,000 rounds - never the password) |
| `matters.json` | Matters: id, name, client, the documents filed on it |
| `audit.jsonl` | The audit log |
| `initial_passwords.txt` | The demo passwords created by `seed` - keep it private, delete it once passwords are changed |

## 2. Accounts

**First start** (creates the demo matters and users with random passwords):

```powershell
.\.venv\Scripts\python.exe -m src.security.access seed       # writes users.json, matters.json, initial_passwords.txt
```

`seed` **replaces** `users.json` and `matters.json` - run it only on a new installation. (In Docker the
`bootstrap` service runs it automatically only when `users.json` does not exist yet.)

**Change a password** (also the way to reset a forgotten one):

```powershell
.\.venv\Scripts\python.exe -m src.security.access set-password ayesha "a-long-new-password"
```

**Add a user or change someone's matters**: edit `users.json`. For a new user, create the hash first:

```powershell
.\.venv\Scripts\python.exe -c "from src.security.access import hash_password; print(hash_password('their-password'))"
```

```json
{"username": "hamza", "name": "Hamza (associate)", "role": "associate", "matters": ["MAT-002"],
 "password_hash": "pbkdf2_sha256$200000$..."}
```

User names are lower case. Changes apply to the next request - no restart. Removing a user from a matter
takes effect immediately, even for a signed-in user. To block someone at once, remove their entry (their token
stops working on the next request).

**Add a matter**: add `{"id": "MAT-005", "name": "...", "client": "...", "documents": []}` to `matters.json`,
then add `MAT-005` to the users who work on it. Contracts uploaded in the app are filed on their matter
automatically.

**Locked out.** Five failed sign-ins lock that user name for five minutes (kept in memory, so a server restart
also clears it). There is nothing to unlock by hand.

## 3. Secrets

| Name | What | Notes |
|---|---|---|
| `LLM_API_KEY` | Gemini API key | Without it, research and drafting are unavailable; search, graph links and saved answers still work |
| `APP_SECRET` | Signs sign-in tokens (any long random string) | **Set it.** Without it a random one is made at every start, and everyone is signed out on each restart. Changing it signs everyone out - which is also how to end all sessions at once |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Neo4j AuraDB (laptop, live link) | |
| `NEO4J_LOCAL_PASSWORD` | Password of the Neo4j container (Docker) | |

Where they are set: `.env` on the laptop and for Docker (never committed); for the live link, GitHub >
Settings > Codespaces > Secrets (restart the codespace after changing one). Never put a secret in a file in
the repository, a log or a message.

## 4. The audit log

Every sign-in (successful, failed, locked), question, review, comparison, draft, upload (accepted or blocked),
download, denied access and job is written to `data/security/audit.jsonl`, one entry per line. CNIC numbers,
phone numbers, e-mail addresses, IBANs, card and NTN numbers are masked before writing - in the user field too.

**Tamper-evident.** Each entry contains the hash of the previous one, so changing or deleting any line breaks
the chain from that line on. Page **08 Chain of Custody** shows whether the chain is intact, the number of
entries and the newest 300, with search and a filter by outcome (`ok`, `denied`, `blocked`, `failed`). To check
from the command line:

```powershell
.\.venv\Scripts\python.exe -c "from src.security import audit; print(audit.verify())"   # (intact, entries, first broken line)
```

What to look at regularly: `blocked` uploads (someone sent a document with hidden instructions - check with the
sender), `denied` entries (someone tried to open another matter's documents), repeated `failed` sign-ins.

Never edit the file. To start a new log (e.g. yearly), stop the app, move the file to an archive and start
again - the new log starts a new chain; keep the old one with its last hash.

## 5. Monitoring

`GET /api/health` (no sign-in) reports each part; `GET /api/health/live` only says the process is up.

| Check | ok means | If not |
|---|---|---|
| `search_index` | The index is loaded (11,232 passages) | The index files are missing: copy or rebuild them (section 8). The endpoint returns 503 |
| `graph` | Neo4j answered (1,649 cases) | AuraDB paused (console.neo4j.io > Resume) or the Neo4j container is down. Research on statutes still works |
| `llm` | The Gemini key is set | Set `LLM_API_KEY` |
| `worker` | A worker sent a heartbeat in the last 30 s | Reviews, drafts and uploads wait in the queue. Docker: `docker compose restart worker`. Others: restart the app |
| `audit_log` | The log is writable | Check disk space and folder permissions |
| `disk` | Enough free space | Free space; Word files in `data/web_outputs/` can be cleaned |

A job left `running` by a crashed worker is marked failed after 2 minutes without a heartbeat (it is not run
twice); the user sees a plain message and can start it again.

## 6. Running the app

| Where | Start | Stop |
|---|---|---|
| Laptop | `.\.venv\Scripts\python.exe -m web.server` (http://127.0.0.1:8000; `$env:PORT=8090` for another port) | Ctrl+C |
| Docker (API, worker, Qdrant, Neo4j) | `docker compose up -d` (`$env:APP_PORT=8080` if 8000 is taken); check with `docker compose ps` | `docker compose down` (data is kept) |
| Live link (GitHub Codespace) | github.com/codespaces > `legal-assistant` > Open; the app starts by itself in about a minute | `...` > Stop codespace |

**Live link routine.** The codespace stops after 4 hours without activity. Before a demo or a grading window:
start it, check that port 8000 is **Public** (Ports tab; right-click > Port Visibility), open `/api/health`,
and resume AuraDB if `graph` is not ok. Stop it afterwards: the free allowance is about 60 hours a month on
this machine.

**Update the live link** after pushing code:

```powershell
gh codespace ssh -c legal-assistant-g45g44rgv95vfgpv -- "cd /workspaces/Netixsol && git pull && pkill -f 'python -m web[.]server'; cd Week12/AI_Legal_Assistant && bash deploy/codespaces/start.sh"
```

(`web[.]server` in brackets, so the command does not match its own SSH session.) The app's log there is
`/tmp/legal-assistant.log`.

## 7. Gemini usage

The free tier allows about 500 requests a day; it resets at about 13:00 Pakistan time. A question costs about
2-3 requests (answer, conclusion check, sometimes a redraft); a review 1; a notice 1-2. Every answer is saved in
`data/llm_cache/`, so asking the same thing again costs nothing - keep this folder. When the limit is reached
users see a clear message and saved answers keep working. Every question is in the audit log with the user's
name, so heavy use can be traced.

## 8. Data, re-indexing and backups

**Add or fix law in the library** (new statute or judgment PDF):

```powershell
.\.venv\Scripts\python.exe main.py --collect            # inventory of the PDF folders
.\.venv\Scripts\python.exe main.py --extract            # structured JSON in data/structured/
.\.venv\Scripts\python.exe main.py --update-index PKLAW_012   # re-index only these documents (or --index for everything)
.\.venv\Scripts\python.exe -m src.graph.regex_extract   # graph CSVs, then load Neo4j:
.\.venv\Scripts\python.exe -m src.graph.load_neo4j
```

In Docker, copy the new vectors into Qdrant afterwards: `docker compose run --rm api python -m src.indexing.qdrant_store sync`.
For the live link, rebuild the data package (`python deploy/codespaces/pack_data.py`) and copy it in (deployment.md, section 4).

Contracts uploaded through the app are indexed automatically by a job; the running app picks up the new index
without a restart.

**Back up** (all of it is outside git):

| Folder | Why |
|---|---|
| `data/security/` | Accounts, matters, audit log |
| `data/web_outputs/` | Uploaded contracts and generated Word files, who owns them |
| `data/indices/` | The search index (can be rebuilt, but takes time) |
| `data/llm_cache/` | Saved Gemini answers (saves quota) |
| `data/jobs/` | Job history (optional) |

Copy them with the app stopped, or at least with no uploads running. The Docker stack keeps `state` (jobs)
and the databases in named volumes; `docker compose down -v` would delete them - do not use `-v` unless you
mean it.

## 9. Security checks

* **Re-run the red team** after any change to security code (80 attacks, about 45 Gemini requests the first
  time): see the end of `evaluations/red_team_report.md`.
* **Tests** (140, no Gemini needed): `.\.venv\Scripts\python.exe -m pytest -q`. They also run on every push
  (GitHub Actions: tests, Docker build and a smoke test).
* **Known limits** (red-team report): an injection in French passes the upload scanner (the second defence
  stops it); questions are sent to Gemini unmasked; there is no per-user question limit; `/api/health` and
  `/api/docs` are open without sign-in (no data in them).

## 10. Troubleshooting

| Problem | Cause and fix |
|---|---|
| Everyone is signed out after a restart | `APP_SECRET` is not set |
| "The free Gemini limit for today is used up" | Wait until about 13:00 PKT; saved answers keep working |
| `graph: down` in health | Resume AuraDB at console.neo4j.io, or `docker compose up -d neo4j` |
| Jobs stay "queued" | No worker: Docker `docker compose up -d worker`; otherwise check `WORKER_MODE` is not `external` |
| A user cannot see a contract | It is filed on a matter they are not on: add the matter to their account in `users.json` |
| An upload is refused with 422 | It contains text addressed to an AI (the response names the clause). Ask the sender for a clean copy |
| An upload is refused with 400 | Wrong type, over 15 MB, damaged, or a scan without text |
| Port 8000 is taken | Laptop `$env:PORT=8090`; Docker `$env:APP_PORT=8080` |
| Docker Desktop stopped / "cannot connect to the docker API" | Start Docker Desktop; if it fails, check the C: drive has free space |
| The live link shows 502 | The app is not running in the codespace: run `bash deploy/codespaces/start.sh` there (section 6) |
