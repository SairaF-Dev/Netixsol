# ShopKaro — AI Commerce Intelligence Platform
# Production-ready Dockerfile for containerized deployment

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
# CPU-only PyTorch first (the default Linux wheel pulls ~2 GB of CUDA libraries); libgomp1 is needed by LightGBM.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && \
    pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt
# Search models (~0.9 GB) download on first use into /root/.cache/huggingface; docker-compose keeps them in the hf-cache volume.

# Copy project configuration and source tree
COPY pyproject.toml .
COPY src/ src/
COPY .streamlit/ .streamlit/
COPY scripts/ scripts/

# Install local package in editable mode
RUN pip install -e .

# Expose API service port
EXPOSE 8000

# Default command: FastAPI server
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "shopkaro.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

