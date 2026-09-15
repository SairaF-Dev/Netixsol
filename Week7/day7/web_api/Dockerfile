FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/day3/src:/app/day7:/app/day2/03_structured_retrieval

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY day3/requirements.txt /tmp/day3-requirements.txt
COPY day7/vapi_integration/requirements.txt /tmp/day7-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/day3-requirements.txt \
    -r /tmp/day7-requirements.txt

# Copy all needed source code
COPY day2 /app/day2
COPY day3/src /app/day3/src
COPY day4 /app/day4
COPY day7 /app/day7

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:${PORT:-8010}/health || exit 1

# Railway injects $PORT at runtime — web_api.app startup auto-applies schema migrations
CMD ["sh", "-c", "uvicorn web_api.app:app --host 0.0.0.0 --port ${PORT:-8010}"]

