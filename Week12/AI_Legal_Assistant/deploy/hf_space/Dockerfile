# Hugging Face Space (one container): the same app as docker-compose.yml, with the worker running inside
# the web process and vector search in memory. Graph = Neo4j AuraDB; Gemini key, AuraDB password and
# APP_SECRET come from the Space's secrets. The data the app reads is copied in by deploy/build_space.py.
FROM python:3.11-slim-bookworm

# Everything up to the model download is identical to ../../Dockerfile, so a local build reuses those
# layers (libraries, models); keep the two in step.
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
COPY --chown=app:app evaluations ./evaluations
COPY --chown=app:app data ./data

# runtime settings (after the model download: offline mode would block it)
ENV HOST=0.0.0.0 \
    PORT=7860 \
    WORKER_MODE=thread \
    VECTOR_BACKEND=sqlite \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health/live', timeout=4)" || exit 1

CMD ["python", "-m", "web.server"]
