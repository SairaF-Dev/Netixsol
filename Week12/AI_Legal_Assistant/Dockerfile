# One image for the API, the worker and the bootstrap task (docker-compose.yml picks the command).
# Code and the two models are inside; data (indices, graph CSVs, structured corpus, uploads) is mounted
# at /app/data, and secrets come from the environment - never baked into the image.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# The app runs as a normal user. Create it first and give it only its own folders: a `chown -R` at the
# end would copy every file it touches into a new layer (it doubled the image by the 1 GB of models).
RUN useradd --create-home --uid 1000 app \
 && mkdir -p /app/data /app/state /app/.cache \
 && chown app:app /app /app/data /app/state /app/.cache

# No PyTorch: the two local models run with ONNX Runtime (src/indexing/onnx_models.py)
COPY requirements-server.txt .
RUN pip install -r requirements-server.txt

USER app

# Bake in the official ONNX files of the embedding model and the reranker, so containers start offline
# (HF_HUB_OFFLINE=1 at run time)
RUN python -c "from huggingface_hub import hf_hub_download as get; \
[get(r, f) for r in ('intfloat/multilingual-e5-small', 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1') \
 for f in ('onnx/model.onnx', 'tokenizer.json')]"

COPY --chown=app:app src ./src
COPY --chown=app:app web ./web
COPY --chown=app:app main.py ./
COPY --chown=app:app evaluations/*.md evaluations/blind_rating_*.json evaluations/dashboard.json ./evaluations/

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=4)" || exit 1

CMD ["python", "-m", "web.server"]
