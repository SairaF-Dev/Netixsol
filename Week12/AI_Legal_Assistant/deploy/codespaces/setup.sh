#!/usr/bin/env bash
# Runs once when the codespace is created (devcontainer.json "onCreateCommand").
# Installs the server libraries - no PyTorch, the models run on ONNX Runtime - and downloads the two models.
set -euo pipefail
cd "$(dirname "$0")/../.."          # the project folder

python -m pip install --upgrade pip
python -m pip install -r requirements-server.txt

python - <<'EOF'
from huggingface_hub import hf_hub_download
for repo in ("intfloat/multilingual-e5-small", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
    for name in ("onnx/model.onnx", "tokenizer.json"):
        hf_hub_download(repo, name)
print("models ready")
EOF
