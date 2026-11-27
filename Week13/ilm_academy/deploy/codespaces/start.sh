#!/usr/bin/env bash
# Starts the platform inside the codespace (devcontainer.json "postStartCommand", i.e. on every start).
# Runs in the background so the codespace finishes starting; output goes to the log below.
# Safe to run again by hand: does nothing if the platform is already running.
set -u
cd "$(dirname "$0")/../.."          # Week13/ilm_academy
LOG=/tmp/ilm-academy.log
PORT=8010

# 1. things setup.sh builds must exist
missing=""
for f in web/dist/index.html data/processed/chroma data/app/class_week3.json models/bkt_concept_params.csv; do
  [ -e "$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
  echo "Ilm Academy NOT started - missing:$missing"
  echo "Run: bash deploy/codespaces/setup.sh   (see docs/deployment.md)"
  exit 0
fi

# 2. secrets from the codespace environment (GitHub > Settings > Codespaces > Secrets). A command run
#    through `gh codespace ssh` does not get them, so read them from the codespace secrets file (base64).
#    Only names are ever printed.
SECRETS_FILE=/workspaces/.codespaces/shared/.env-secrets
if [ -f "$SECRETS_FILE" ]; then
  while IFS= read -r line; do
    key="${line%%=*}"
    case "$key" in
      LLM_API_KEY|ILM_DEMO_PASSWORD|ILM_JWT_SECRET)
        [ -n "${!key:-}" ] || export "$key=$(printf '%s' "${line#*=}" | base64 -d)" ;;
    esac
  done < "$SECRETS_FILE"
fi
if [ -z "${ILM_DEMO_PASSWORD:-}" ]; then
  echo "Ilm Academy NOT started - the secret ILM_DEMO_PASSWORD is not set (docs/deployment.md, step 1)"
  exit 0
fi
if [ "${ILM_DEMO_PASSWORD}" = "ilm-demo-2026" ]; then
  echo "Ilm Academy NOT started - ILM_DEMO_PASSWORD is the dev default, which is published in the code."
  echo "Choose your own password in the codespace secrets (docs/deployment.md, step 1)."
  exit 0
fi
[ -n "${LLM_API_KEY:-}" ] || echo "warning: LLM_API_KEY is not set - the tutor will say it is unavailable"
if [ -z "${ILM_JWT_SECRET:-}" ]; then                 # generated once per codespace, kept outside git
  SECRET_FILE="$HOME/.ilm_jwt_secret"
  [ -s "$SECRET_FILE" ] || (umask 077; python -c "import secrets; print(secrets.token_hex(32))" > "$SECRET_FILE")
  export ILM_JWT_SECRET="$(cat "$SECRET_FILE")"
fi

# 3. Docker for the sandbox
for _ in $(seq 1 45); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker image inspect python:3.11-slim >/dev/null 2>&1 || docker pull python:3.11-slim

# 4. already running?
if curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "Ilm Academy already running on port $PORT"
  exit 0
fi

# 5. start
export ILM_ENV=prod OPENBLAS_NUM_THREADS=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
setsid nohup python -m uvicorn ilm.api.main:app --host 0.0.0.0 --port "$PORT" >>"$LOG" 2>&1 < /dev/null &

for _ in $(seq 1 90); do
  if curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    echo "Ilm Academy running on port $PORT (log: $LOG)"
    exit 0
  fi
  sleep 2
done
echo "Ilm Academy did not answer within 3 minutes - see $LOG"
