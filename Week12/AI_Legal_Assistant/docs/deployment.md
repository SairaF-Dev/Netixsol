# Deployment guide

The same code runs three ways. Pick by what you need.

| | Laptop | Docker (full stack) | Hugging Face Space (live link) |
|---|---|---|---|
| Start | `python -m web.server` | `docker compose up -d` | push `build/hf_space` to a Space (needs HF PRO) |
| Web app + API | one process | `api` container | one container |
| Background jobs | thread in the web process | `worker` container | thread in the web process |
| Vector search | SQLite file, in memory | **Qdrant** container | SQLite file, in memory |
| Knowledge graph | Neo4j AuraDB | **Neo4j** container | Neo4j AuraDB |
| Uploads, audit log | `data/` | `data/` (host folder) + `state` volume | temporary disk (reset on restart) |

Search results are identical on the in-memory index and Qdrant (same top result on 25/25 evaluation
questions, 100% of the top-30 passages shared), so the three setups answer the same way.

## The two local models run without PyTorch

The embedding model (`intfloat/multilingual-e5-small`) and the reranker
(`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) run with **ONNX Runtime**, using the official ONNX files from
the same Hugging Face repositories (`src/indexing/onnx_models.py`). The servers install
`requirements-server.txt`, which has no PyTorch; `requirements.txt` (with PyTorch) is for development,
building the index and fine-tuning. Results are identical to PyTorch (same vectors as the stored index, same
top-5 passages on all 100 evaluation questions) - see `evaluations/onnx_equivalence_report.md`.

| | PyTorch (before) | ONNX Runtime (now) |
|---|---|---|
| Docker image | 4.41 GB | 2.68 GB |
| API container memory (index + models loaded, after use) | - | about 1.7 GB |

`MODEL_BACKEND=torch` switches back to PyTorch (needs `requirements.txt`).

## Secrets (never in files that are committed or copied into an image)

| Name | What | Where it is set |
|---|---|---|
| `LLM_API_KEY` | Gemini API key | `.env` / Space secret |
| `APP_SECRET` | signs sign-in tokens; any long random string. Without it tokens stop working on every restart | `.env` / Space secret |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | AuraDB (laptop, Space) | `.env` / Space secrets |
| `NEO4J_LOCAL_PASSWORD` | password of the Neo4j container (Docker) | `.env` |
| `APP_PORT` | host port of the Docker API (default 8000) | shell or `.env` |

Not secret, optional: `MODEL_BACKEND` (`onnx` default, or `torch`), `ONNX_THREADS` (CPU threads, default all),
`ONNX_MEMORY_ARENA=1` (faster but memory keeps growing), `ONNX_SHARED_TOKENIZER=0`.

## 1. Laptop

```powershell
.\.venv\Scripts\python.exe -m src.security.access seed     # first time: users, matters, data/security/initial_passwords.txt
.\.venv\Scripts\python.exe -m web.server                   # http://127.0.0.1:8000
```

## 2. Docker: API, worker, Qdrant, Neo4j

Needs the search index in `data/indices/` (`python main.py --index`) and Docker Desktop running.

```powershell
docker compose up -d --build            # first build ~5 min (libraries + the two ONNX models baked in)
docker compose ps                       # all services "healthy"; bootstrap "exited (0)"
$env:APP_PORT=8080; docker compose up -d   # if port 8000 is taken by another app
docker compose logs -f api worker
docker compose down                     # stop (data in volumes is kept)
```

`bootstrap` runs before the API and worker start: it copies the passages into Qdrant and loads the graph
into Neo4j only if they are not there yet, and creates the demo users if `data/security/users.json` is
missing. Health: `GET /api/health` (each dependency) and `GET /api/health/live`. Neo4j Browser:
http://localhost:7474, Qdrant dashboard: http://localhost:6333/dashboard (this machine only).

## 3. Hugging Face Space (the live link)

A free Space runs one container (2 vCPU, 16 GB RAM), so the worker runs inside the web process and the
graph uses AuraDB. The code is public on a public Space; the data copied in is the corpus, the search index,
the graph files, the saved Gemini answers and the account list (password hashes only).

1. `python deploy/build_space.py` → `build/hf_space/` (allowlisted files only; refuses to build if a
   secret file slipped in).
2. `hf auth login` (a token with write access, from huggingface.co/settings/tokens).
3. Create the Space and upload:
   ```powershell
   hf repo create <user>/legal-assistant --repo-type space --space-sdk docker
   hf upload <user>/legal-assistant build/hf_space . --repo-type space
   ```
4. Space **Settings → Variables and secrets**: add the secrets in the table above (not `NEO4J_LOCAL_PASSWORD`).
5. The Space builds the image (~15 min) and starts; check `https://<user>-legal-assistant.hf.space/api/health`.
6. Give reviewers a demo sign-in (e.g. an associate account) with the submission; do not publish the
   admin password.

Notes: uploads, jobs and the audit log are on the Space's temporary disk and reset on restart; a free Space
sleeps after 48 hours without visits and takes about a minute to wake. Gemini answers asked before are in
the shipped cache and cost nothing; new questions use the free daily quota (about 500 requests).

## 4. GitHub Codespaces (free live link, no card)

A codespace is a free Linux machine from GitHub (2 cores, 8 GB) that runs the app with plain Python - one
process, worker thread, in-memory search, graph on AuraDB - and makes port 8000 public. A GitHub Free
account includes about 120 core-hours a month (~60 hours on this machine). It stops when idle (set the idle
timeout to the maximum, 4 hours), so start it before a demo or a grading window.

Files: `.devcontainer/legal-assistant/devcontainer.json` (repository root), `deploy/codespaces/setup.sh`
(once: libraries without PyTorch + the ONNX models), `deploy/codespaces/start.sh` (every start: checks data
and secrets, starts the server in the background, log in `/tmp/legal-assistant.log`),
`deploy/codespaces/pack_data.py` (the data git does not hold: index, saved Gemini answers, accounts, matters).

**Once**

1. Codespaces secrets - github.com > Settings > Codespaces > Secrets, each with access to this repository:
   `LLM_API_KEY`, `APP_SECRET` (any long random string), `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.
2. Create the codespace with the GitHub CLI (`winget install GitHub.cli`, `gh auth login`):
   ```powershell
   gh codespace create -R SairaF-Dev/Netixsol -b main --devcontainer-path .devcontainer/legal-assistant/devcontainer.json -m basicLinux32gb --idle-timeout 240m
   gh codespace list                                    # its name
   ```
3. Copy the data in and start:
   ```powershell
   python deploy/codespaces/pack_data.py               # build/codespace_data.tar.gz (~36 MB)
   gh codespace cp -e -c <name> build/codespace_data.tar.gz remote:/tmp/codespace_data.tar.gz   # -e: needed with Windows scp
   gh codespace ssh -c <name> -- "cd /workspaces/Netixsol/Week12/AI_Legal_Assistant && tar -xzf /tmp/codespace_data.tar.gz && bash deploy/codespaces/start.sh"
   gh codespace ports visibility 8000:public -c <name>
   ```
4. The link: `https://<name>-8000.app.github.dev` (same link every time this codespace is started).

**Each demo / grading day**: github.com/codespaces > the codespace > Open (the app starts by itself, about
30 s); open the AuraDB console too, since a free AuraDB instance pauses after a few days without use. Stop the
codespace afterwards to save free hours. Uploads and the audit log survive stop/start, and are lost only if
the codespace is deleted.

## Before re-running an evaluation

The command-line tools and evaluation scripts search without a signed-in user, so they also see contracts
uploaded through the web app. Remove test uploads from the index first, or the Day 2 numbers can change.
