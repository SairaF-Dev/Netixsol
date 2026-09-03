FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/day3/src:/app/day7

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY day3/requirements.txt /tmp/day3-requirements.txt
COPY day7/vapi_integration/requirements.txt /tmp/day7-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/day3-requirements.txt \
    -r /tmp/day7-requirements.txt

COPY day2 /app/day2
COPY day3/src /app/day3/src
COPY day4 /app/day4
COPY day7 /app/day7

EXPOSE 8007

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8007/health || exit 1

CMD ["uvicorn", "vapi_integration.webhook_server:app", "--host", "0.0.0.0", "--port", "8007"]
