# Administration and Troubleshooting

Configure secrets from `.env.example` in a secret manager. Start PostgreSQL,
n8n, Day 4, then Day 7. Verify `/health` and `/metrics`; confirm VAPI uses HTTPS
and the shared webhook secret. Import the n8n workflow and validate Calendar and
SMTP with `day4/audit_integrations.py`.

Common failures:

- **403 webhook:** VAPI secret mismatch.
- **No properties:** verify `DATABASE_URL`, schema/seed, and repository logs.
- **RAG unavailable:** verify `DAY2_ROOT`, model cache/network, provider key, and
  vector-store path.
- **409 appointment:** slot overlap; request an alternative.
- **Email warning:** booking can remain valid; inspect SMTP credentials/logs.
- **Calendar failure:** verify service-account access to the target calendar.
- **Slow voice:** inspect `/metrics`, STT/LLM/TTS timing, connection warming, and
  response length.

Never paste secrets into logs or tickets. Rotate a key immediately if exposed.
