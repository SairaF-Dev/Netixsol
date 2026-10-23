# ==============================================================================
# Zarya Digital Bank: Production Inference Engine Dockerfile
# Base: Python 3.11 Slim (Debian Bookworm)
# ==============================================================================

FROM python:3.11-slim as base

# Set working directory & environment variables
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install essential system dependencies and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install fastapi uvicorn httpx

# Copy project directories
COPY src/ /app/src/
COPY data/rag_documents/ /app/data/rag_documents/
COPY checkpoints/ /app/checkpoints/
COPY configs/ /app/configs/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose standard serving port
EXPOSE 8000

# Docker Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn ASGI Server
CMD ["python", "-m", "uvicorn", "src.serve_api:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

