# API endpoint security

Configure three different random credentials and never commit their real values:

- `SARA_API_KEY` authenticates Day 3 chat, TTS, voice, and WebSocket clients.
- `DAY4_API_KEY` authenticates service-to-service appointment operations.
- `VAPI_WEBHOOK_SECRET` authenticates requests sent by VAPI to Day 7.

Generate each independently (for example, `openssl rand -hex 32`) and place the
values in the untracked `.env` file.

HTTP clients send `Authorization: Bearer <service-key>`. VAPI sends its secret
in `X-Vapi-Secret`. WebSocket clients use an `Authorization` header or the
`access_token` query parameter. Avoid query tokens behind proxies that log URLs;
public browser deployments should exchange credentials for short-lived tokens.

Only landing/static pages and health/readiness checks remain unauthenticated.
Metrics, business mutations, paid-provider endpoints, and WebSockets require
authentication. Missing server credentials fail closed with HTTP 503.

Deployment requirements:

- Terminate TLS at a trusted reverse proxy; never transmit keys over HTTP.
- Restrict ports 8004, 8007, 5432, and 5678 to private networks/firewalls.
- Rotate the previously committed VAPI key and purge it from Git history.
- Rate-limit chat, TTS, voice, and webhook routes at the reverse proxy.
- For multiple end users, replace the shared Day 3 key with short-lived JWTs and
  add per-user appointment ownership checks. The Day 4 key authenticates the
  calling service, not an individual customer.
