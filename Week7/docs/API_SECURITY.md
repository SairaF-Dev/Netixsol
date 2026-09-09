# API Endpoint Security

## Website API (port 8010)

Website registration/login establishes an opaque HttpOnly session cookie.
Passwords use bcrypt and stored session tokens are SHA-256 digests. Authenticated
`/api/me/...` routes derive customer identity from the session and check ownership.

Clients include cookies on requests. Obtain a token from `GET /api/auth/csrf`
and send `X-CSRF-Token` on authenticated POST/PATCH/PUT/DELETE requests. Login and
registration are exempt from CSRF middleware. The frontend's `lib/api.ts` handles
this flow and retries once after refreshing a rejected CSRF token.

Authentication routes include register, login, logout, me, csrf, sessions, and
logout-all under `/api/auth`. Login and registration have application rate limits.
Set `SARA_AUTH_SECURE_COOKIE=1` behind HTTPS; production mode (`SARA_ENV=production`)
rejects insecure session-cookie configuration. CORS uses `SARA_WEB_CORS_ORIGINS`.

Browser voice starts through `POST /api/me/voice-sessions`. The capability is
stored as a digest and bound to the login, assistant, and VAPI call. The internal
`POST /api/internal/voice/webhook` validates `VAPI_WEBHOOK_SECRET` independently.
Invalid browser events cannot fall back to phone identity.

Legacy routes are still present. Customer-ID routes check ownership when auth is
configured, but `POST /api/customers` remains a development customer-creation path
without a route-level login requirement. Do not assume every `/api` route is
protected. Review/restrict legacy development routes before public deployment.
Health and generated OpenAPI documentation are also publicly accessible.

## Service credentials

| Credential | Scope | Transport |
| --- | --- | --- |
| `SARA_API_KEY` | Standalone Day 3 chat, voice, TTS, and WebSockets | Bearer header; WebSockets also accept `access_token` |
| `DAY4_API_KEY` | Internal Day 4 appointment/workflow operations | Bearer header |
| `VAPI_WEBHOOK_SECRET` | VAPI webhook, its metrics, and internal browser-event forwarding | `X-Vapi-Secret` for webhook requests |

Generate independent random values. Do not place them in frontend environment
variables. `NEXT_PUBLIC_VAPI_PUBLIC_KEY` is the browser public key; `VAPI_API_KEY`
is a private management credential. The Day 4 service key does not identify an
individual customer; website ownership is enforced by the website API.

Missing required service credentials fail closed. Invalid VAPI webhook secrets
return 403; bearer-authenticated service failures return 401. Exact website
statuses depend on authentication, CSRF, ownership, and resource expiry.

## Deployment checks

- Use HTTPS and Secure cookies, with explicit allowed website origins.
- Restrict Day 4, PostgreSQL, n8n, and the internal voice callback to trusted access.
  Expose the authenticated VAPI webhook through a public HTTPS endpoint for VAPI.
- Apply proxy rate limits to chat, voice, TTS, webhook, and legacy creation routes.
- Avoid WebSocket query tokens in logged URLs. Public Day 3 clients need a
  reviewed per-user authentication design; the website already uses sessions.
- Keep credentials out of Git and logs, and rotate exposed credentials.
- Test cross-account denial and expired sessions before release. Runtime text
  guardrails supplement authentication and tool authorization.
