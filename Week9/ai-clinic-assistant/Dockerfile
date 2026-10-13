# Multi-Agent AI Clinic Assistant - Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential, sqlite3, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and data
COPY src/ ./src/
COPY data/ ./data/
COPY docs/ ./docs/
COPY README.md .

# Expose primary port (FastAPI REST API & HTML5 SPA)
EXPOSE 8000

# Healthcheck targeting FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl --fail http://localhost:${PORT:-8000}/health || exit 1

# Run FastAPI & SPA with production Uvicorn worker (dynamically adapts to Railway $PORT)
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

