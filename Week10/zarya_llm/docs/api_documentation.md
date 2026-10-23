# Zarya Digital Bank: Serving & Core Operations API Reference
**Version:** 2.0.0 (Production Release)  
**Base URL:** `http://localhost:8000` (or `https://api.zaryabank.com.pk`)  
**Specification:** OpenAPI 3.1.0 Compliant (Interactive Swagger docs available at `/docs`)  

---

## 1. Authentication & Protocols
* **Authentication:** Bearer token via `Authorization: Bearer <API_KEY>` (in production reverse proxy).
* **Wire Protocol:** HTTP/1.1 and HTTP/2 over TLS 1.3.
* **Content Types:** `application/json` for standard requests; `text/event-stream` for token streaming.

---

## 2. OpenAI-Compatible Chat Completions

### `POST /v1/chat/completions`
Executes an end-to-end turn through **Input Guardrails $\rightarrow$ RAG Retrieval $\rightarrow$ Inference Engine $\rightarrow$ Output Guardrails $\rightarrow$ Automated Ticketing**.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Payload
```json
{
  "model": "zarya-qwen2.5-3b-dpo-q4_k_m",
  "messages": [
    {"role": "system", "content": "You are Zarya Bank's AI customer support assistant. Follow bank tone strictly."},
    {"role": "user", "content": "Mera ATM card block karna hai gum ho gaya hai."}
  ],
  "temperature": 0.3,
  "max_tokens": 128,
  "stream": false,
  "customer_id": "CUST-90214"
}
```

#### Response Payload (200 OK)
```json
{
  "id": "chatcmpl-a1b2c3d4e5f6",
  "object": "chat.completion",
  "created": 1729639200,
  "model": "zarya-qwen2.5-3b-dpo-q4_k_m",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Ji, aap ki card block karne ki darkhwast darj kar li gayi hai. Hifazat ke pesh-e-nazar, kya aap apne registered mobile number ki tasdeeq kar sakte hain?\n\n[Complaint Ticket: ZAR-20261022-4075 | TAT: 7 business days for PayPak / 14 days for Visa disputes | Status: OPEN]"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 32,
    "completion_tokens": 46,
    "total_tokens": 78
  },
  "ticket_created": {
    "ticket_id": "ZAR-20261022-4075",
    "category": "CARD",
    "priority": "LOW",
    "tat": "7 business days for PayPak / 14 days for Visa disputes",
    "status": "OPEN"
  },
  "guardrail_status": "PASSED"
}
```

---

## 3. Core Banking Ticketing Endpoints

### `GET /v1/tickets`
Lists recent complaint tickets recorded in the core SQLite database.
* **Query Parameters:**
  - `limit` (integer, default 50): Number of records.
  - `status` (string, optional): Filter by `OPEN`, `ESCALATED`, or `RESOLVED`.

### `POST /v1/tickets`
Explicitly creates a complaint ticket.
```json
{
  "category": "IBFT",
  "summary": "Raast transfer deducted but not credited",
  "details": "Customer sent Rs. 65,000 via Raast at 14:30 PKT. Amount deducted.",
  "customer_id": "CUST-90214",
  "amount": 65000.0,
  "sentiment": "concerned"
}
```

### `POST /v1/tickets/{ticket_id}/resolve`
Marks a complaint ticket as `RESOLVED`.
* **Path Parameter:** `ticket_id` (e.g. `ZAR-20261022-7168`).

---

## 4. Operational Telemetry & Active Learning

### `POST /v1/feedback`
Captures customer thumbs-up/down ratings for continuous DPO alignment.
```json
{
  "turn_id": "turn-1729639200",
  "rating": "down",
  "comment": "Model did not mention the 4-hour Raast TAT",
  "query": "Raast transfer fail ho gaya",
  "response": "Please contact helpline."
}
```

### `POST /v1/compare`
Generates live side-by-side comparison between Base `Qwen2.5-3B` and Zarya DPO.
```json
{
  "query": "Mera ATM card block karna hai gum ho gaya hai."
}
```

### `GET /health`
Returns system health, uptime, active model, and KV-cache telemetry.
```json
{
  "status": "healthy",
  "service": "zarya-serving-engine",
  "model": "zarya-qwen2.5-3b-dpo-q4_k_m",
  "uptime_seconds": 3600.25,
  "total_requests": 1420,
  "total_tokens_generated": 58400,
  "kv_cache_allocated_mb": 128.0,
  "paged_attention": "enabled",
  "continuous_batching": "active",
  "guardrails": "active",
  "database": "sqlite_connected"
}
```

