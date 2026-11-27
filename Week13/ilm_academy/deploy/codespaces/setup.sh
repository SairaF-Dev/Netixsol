#!/usr/bin/env bash
# Runs once when the codespace is created (devcontainer.json "onCreateCommand").
# Everything the platform needs that is not in git is rebuilt here from what is in git.
set -euo pipefail
cd "$(dirname "$0")/../.."          # Week13/ilm_academy
export OPENBLAS_NUM_THREADS=1        # see tests/conftest.py: one BLAS thread per process

echo "== 1/5 Python libraries (CPU-only torch)"
python -m pip install --upgrade pip
python -m pip install -r requirements-server.txt

echo "== 2/5 web app (web/dist)"
(cd web && npm ci && npm run build)

echo "== 3/5 course search index (data/processed/chroma): transcripts are in git; slides and notes"
echo "   are downloaded (CC BY-NC-SA, no audio/video) so the index has the same 1,093 chunks"
python -m ilm.content.download --roles slides notes
python -m ilm.content.index

echo "== 4/5 the teacher's class (data/app/class_week3.json: dropout model + mastery)"
python -m ilm.api.classroom

echo "== 5/5 sandbox image"
for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker pull python:3.11-slim || echo "docker not ready yet: start.sh pulls the sandbox image"

echo "setup done"
