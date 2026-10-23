# Zarya Digital Bank: IT Operations & Production Runbook
**Project:** Zarya Digital Bank Bilingual Assistant (UrduLish & English)  
**Milestone:** Capstone Day 5 — Task 5: DevOps & IT Runbook  
**Target Audience:** Bank IT Operations, DevOps Engineers, Infrastructure Leads  
**Version:** 1.0.0  

---

## 1. Production Architecture Overview

The Zarya Bank AI service runs as a stateless containerized microservice connecting to an embedded SQLite / PostgreSQL database and an in-memory RAG vector index:

```
[Customer Traffic] -> [NGINX / F5 Load Balancer (SSL Offload)]
                           |
                           v
            +-------------------------------+
            |  Docker: zarya-bank-ai:2.0    |
            |  - Uvicorn / FastAPI (:8000)  |
            |  - Guardrails Engine (<15ms)  |
            |  - RAG Index (Hot-Reloadable) |
            |  - Model Inference (Q4_K_M)   |
            +-------------------------------+
                           |
                           v
            [Persistent Volume: /app/data]
            - zarya_banking.db (SQLite)
            - audit_logs.jsonl (PII Masked)
            - feedback.jsonl
```

---

## 2. Service Management Commands

### Starting the Service via Docker Compose
```bash
# Build and start container in detached daemon mode
docker-compose up -d --build

# Inspect running container status
docker-compose ps

# View live streaming application logs
docker-compose logs -f zarya-bank-ai
```

### Stopping or Restarting the Service
```bash
# Restart container (reloads RAG documents and cache)
docker-compose restart zarya-bank-ai

# Stop the service cleanly
docker-compose down
```

---

## 3. Health Checks & Synthetic Monitoring

* **Automated Health Probe Endpoint:** `GET /health`
* **Success Criteria:** HTTP status `200 OK` with `"status": "healthy"`.

### Synthetic Smoke Test (cURL)
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Mera card block karna hai."}]
  }'
```
Expected output must contain confirmation and registered mobile verification question.

---

## 4. Zero-Downtime Policy & Tariff Updates (Hot-Reloading RAG)

When the State Bank of Pakistan or Zarya Bank management updates a tariff or fee schedule:
1. Edit the relevant Markdown file in `data/rag_documents/` (e.g. `data/rag_documents/fees_and_charges.md`).
2. The RAG index dynamically monitors document timestamps and hot-reloads chunks into memory without dropping active TCP connections or requiring model recompilation.

---

## 5. Security, Secrets & PII Compliance

1. **Zero Secret Hardcoding:** API tokens and sensitive database credentials must be injected via Kubernetes Secrets or Docker `.env` files.
2. **State Bank PII Directives:** The application enforces automated PII masking on incoming logs. Never disable `ZaryaGuardrailsPipeline.mask_pii_for_logging()`.
3. **Database Backups:**
   ```bash
   # Daily SQLite backup cronjob
   sqlite3 /app/data/zarya_banking.db ".backup '/app/data/backups/zarya_banking_$(date +%Y%m%d).db'"
   ```

---

## 6. Incident Response & Troubleshooting

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| **HTTP 500 on Chat Completions** | Corrupted SQLite database or lock timeout | Verify file permissions on `/app/data/zarya_banking.db`. Run `PRAGMA integrity_check;`. |
| **p95 Latency $> 500$ ms** | Concurrency saturation or CPU throttling | Increase CPU quota in Docker Compose (`deploy.resources.limits.cpus`). |
| **Continuous Batching Memory Growth** | KV cache allocation overflow | Restart container to clear virtual pages (`docker-compose restart`). |

