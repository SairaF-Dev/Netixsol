#!/usr/bin/env bash
# Starts the web app inside the codespace (devcontainer.json "postStartCommand", i.e. on every start).
# The server runs in the background so the codespace finishes starting; its output goes to the log below.
# Safe to run again by hand: it does nothing if the app is already running.
set -u
cd "$(dirname "$0")/../.."          # the project folder
LOG=/tmp/legal-assistant.log

# 1. the data that is not in git must have been copied in (deploy/codespaces/pack_data.py on the laptop)
missing=""
for f in data/indices/vstore_legal.sqlite3 data/indices/bm25_legal.pkl data/security/users.json data/security/matters.json; do
  [ -e "$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
  echo "Legal Assistant NOT started - data not copied yet:$missing"
  echo "See docs/deployment.md, section 'GitHub Codespaces'."
  exit 0
fi

# 2. secrets come from the codespace's environment (GitHub > Settings > Codespaces > Secrets); names only
for v in LLM_API_KEY APP_SECRET NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD; do
  [ -n "${!v:-}" ] || echo "warning: secret $v is not set for this codespace"
done

# 3. already running?
if curl -fs http://127.0.0.1:8000/api/health/live >/dev/null 2>&1; then
  echo "Legal Assistant already running on port 8000"
  exit 0
fi

# 4. start: one process (web app + background worker thread), vector search in memory, models on ONNX
export HOST=0.0.0.0 PORT=8000 WORKER_MODE=thread VECTOR_BACKEND=sqlite MODEL_BACKEND=onnx \
       HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
setsid nohup python -m web.server >>"$LOG" 2>&1 < /dev/null &

for _ in $(seq 1 90); do                     # the index and models take ~10-30 s to load
  if curl -fs http://127.0.0.1:8000/api/health/live >/dev/null 2>&1; then
    echo "Legal Assistant running on port 8000 (log: $LOG)"
    exit 0
  fi
  sleep 2
done
echo "Legal Assistant did not answer within 3 minutes - see $LOG"
