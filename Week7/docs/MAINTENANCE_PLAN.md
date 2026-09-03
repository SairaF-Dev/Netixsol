# Monitoring and Maintenance Plan

Targets: 99.5% monthly availability; p95 text turn under 2 seconds excluding
telephony/TTS; booking success above 98% when dependencies are healthy; grounded
answer rate above 95%; critical tool failure below 1%.

- Daily: review availability, p95/p99 latency, API/tool failures, booking success,
  RAG misses, and guardrail anomalies.
- Weekly: review failed transcripts and human feedback; do not retrain blindly.
- Monthly: refresh changed documents and rebuild/evaluate the vector index;
  review prompt changes through versioned regression tests.
- Quarterly: restore a database backup in isolation, rotate eligible secrets,
  review permissions, and run prompt-injection/security testing.
- Backups: daily encrypted PostgreSQL backup, 30-day retention, monthly restore
  drill; version knowledge documents and n8n workflows.
- Alerts: page on health failure for 5 minutes, p95 >5 seconds for 15 minutes,
  booking failure >5%, or repeated Calendar/email failures.
