# Performance and Integration Report

## Verified results

- Day 2 routing regression: 8/8 passed after payment-plan route correction.
- Day 3 automated suite: 53/53 passed with a workspace-local test directory.
- Day 4 workflow suite: 10/10 passed.
- Day 5 graph/tool/state suite: 14/14 passed.
- Day 7 webhook/tool/guardrail/metrics suite: 78/78 passed.
- Guardrail fixed corpus: 40/40 primary classifications passed.
- Guardrail microbenchmark: approximately 0.0054 ms per evaluation.
- PostgreSQL live read: passed; appointment table was reachable.
- SMTP live authentication: passed; no email was sent by the audit.
- Google Calendar live free/busy read: passed; no event was created.

## Not passed or inconclusive

- Recorded voice round trip: 10,709 ms; the <2,000 ms target was not met.
- UrduLish STT accuracy: failed in the recorded call; purchase intent and budget
  were mistranscribed.
- RAG live probe: inconclusive; external model/provider execution hung and was
  terminated. Unit and integration contracts pass, but this is not a live pass.
- Docker Compose validation: unavailable because Docker is not installed here.
- VAPI and n8n live delivery: configured artifacts exist, but no safe fresh
  external event was executed during this audit.

## Runtime metrics

`GET /metrics` on the Day 7 service reports privacy-safe counters and bounded
samples for average, p50, p95, and p99 conversation/tool latency, guardrail block
reasons, tool calls, and failures. Production monitoring should scrape this
endpoint and retain time-series data outside the process.
