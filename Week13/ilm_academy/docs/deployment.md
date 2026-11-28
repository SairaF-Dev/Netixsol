# Deployment: GitHub Codespaces (free live link)

The platform runs in one GitHub codespace. The API also serves the React app, so there is one
address. Student code runs in Docker containers inside the codespace (the sandbox).

| | |
|---|---|
| Machine | 2 cores, 8 GB (free personal quota: about 60 hours a month at 2 cores) |
| Address | `https://<codespace-name>-8010.app.github.dev` |
| Sleeps | after the idle timeout (up to 4 hours); wake it before a demo |
| Config | `.devcontainer/ilm-academy/` (repo root), scripts in `deploy/codespaces/` |

## One-time setup (you)

**1. Secrets.** GitHub → your profile → Settings → Codespaces → *Secrets* → **New secret**, each with
repository access to `SairaF-Dev/Netixsol`:

| name | value |
|---|---|
| `LLM_API_KEY` | your Gemini API key (from Google AI Studio) |
| `ILM_DEMO_PASSWORD` | a password you choose for the demo accounts `ali`, `sara`, `teacher` |
| `ILM_JWT_SECRET` | optional: any long random text (if empty, the codespace generates one) |

**2. Idle timeout.** Settings → Codespaces → *Default idle timeout* → 240 minutes.

**3. Create the codespace.** Repo page → **Code** → **Codespaces** → **⋯** → *New with options* →
Dev container configuration **"Week13 Ilm Academy"**, machine **2-core** → *Create codespace*.
The first build installs the libraries, builds the web app, rebuilds the search index and the
class data, and pulls the sandbox image: about 15-20 minutes. Watch it in the *Creation log*.

**4. Make the address public.** In the codespace, open the **Ports** tab → right-click port
**8010** → *Port visibility* → **Public**. Copy the *Forwarded address*: that is the live link.
(Private shows a GitHub sign-in page to everyone else.)

## Before a demo or a review

1. Wake the codespace: open it from github.com/codespaces (or `gh codespace ssh -c <name> -- echo up`).
   `start.sh` starts the platform automatically on every start.
2. Port 8010 goes back to **private** after a restart: set it **Public** again (step 4).
3. Open the link, log in as `teacher` and as `ali` with `ILM_DEMO_PASSWORD`.

## If something is wrong

| symptom | fix |
|---|---|
| link shows a GitHub sign-in page | port 8010 is private: set it Public |
| link gives 404 / does not load | the codespace is asleep: wake it |
| "NOT started - missing: ..." in the start log | run `bash Week13/ilm_academy/deploy/codespaces/setup.sh` in the codespace terminal |
| "ILM_DEMO_PASSWORD is not set" | add the secret (step 1), then *Codespaces → ⋯ → Restart* |
| a run says "Grading is not available right now" | Docker in the codespace is not ready (just after a start) or stopped: wait 30 s; else `docker info` in the terminal |
| tutor says it is unavailable | `LLM_API_KEY` missing, or the free daily Gemini quota is used up |
| anything else | `tail -50 /tmp/ilm-academy.log` in the codespace terminal |

## What runs where

- `onCreateCommand` → `deploy/codespaces/setup.sh` (once): `requirements-server.txt` (CPU-only
  torch), `npm ci && npm run build`, `python -m ilm.content.index`, `python -m ilm.api.classroom`,
  `docker pull python:3.11-slim`.
- `postStartCommand` → `deploy/codespaces/start.sh` (every start): reads the secrets, generates a
  session secret if none is set, waits for Docker, starts `uvicorn ilm.api.main:app` on port 8010
  with `ILM_ENV=prod` (secure cookies, no dev password).
- Not deployed: the Day 1-3 research pipelines (Whisper, ASSISTments, model training). The server
  uses their outputs, which are in git (reports, transcripts, simulated cohort, BKT parameters).
