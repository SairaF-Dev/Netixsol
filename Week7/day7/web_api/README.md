# Sara Shared Website API

This development API is the website-facing HTTP layer over Sara's existing
customer, preference, verified-property, deterministic-ranking, optional
development-ML, interaction, and Day 4 appointment services. Website identity is resolved from the authenticated HttpOnly session and mapped
server-side to `customer_id`.

## Authentication and ownership (Phase 8A)

On startup the additive `auth_schema.sql` migration creates `auth_users`,
`auth_sessions`, and `auth_appointment_ownership`. Passwords use bcrypt;
opaque session tokens are stored only as SHA-256 digests and delivered in an
HttpOnly, SameSite=Lax cookie. Set `SARA_AUTH_SECURE_COOKIE=1` behind HTTPS.

Primary website routes are `/api/auth/register`, `/api/auth/login`,
`/api/auth/logout`, `/api/auth/me`, and `/api/me/...`. Legacy customer-ID
routes validate cookie ownership whenever authentication is configured.
VAPI and the internal Streamlit collector retain their separate trusted
development identity paths.

## Run

```powershell
cd E:\Netixsol\Week7\day7

python -m uvicorn web_api.app:app `
    --host 127.0.0.1 `
    --port 8010 `
    --reload
```

Open `http://127.0.0.1:8010/health` and
`http://127.0.0.1:8010/docs`.

### Diagnosing chat failures

If a chat POST returns 403 followed by 503, the client has refreshed its CSRF
token and retried; investigate the 503 in the API terminal (`Chat turn failed`).
The health endpoint checks the database, but does not test AI understanding.
From the repository root, run `python day7/diagnose_chat.py` using the API's
Python environment to send a sample greeting to the configured provider. The
probe reports exception types and provider status without printing credentials
or customer messages. A successful probe verifies that connection at that moment;
it does not verify the entire authenticated chat flow or a particular failed turn.

## Authenticated website requests

Use `/api/auth/register` or `/api/auth/login` to establish a cookie session.
Include that cookie on subsequent requests, fetch `/api/auth/csrf`, and send
the returned token in `X-CSRF-Token` on mutations. The website's central API
client manages this flow. Use `/api/me/...` for website requests; identity is
derived on the server. See [security](../../docs/API_SECURITY.md).

For example, update saved preferences with `PATCH /api/me/preferences`:

```json
{"city":"Lahore","area":"DHA","budget_max":50000000,"property_type":"Apartment","purpose":"purchase"}
```

Load recommendations with `POST /api/me/recommendations` and `{"limit":10}`.
Use the returned `recommendation_session_id` and one of its property IDs for
`POST /api/me/interactions`, with action `liked`, `rejected`, or `shortlisted`.
Book through `POST /api/me/appointments` using `property_id`, timezone-aware
`starts_at`, and optional `duration_minutes`/`meeting_notes`. Read owned visits
with `GET /api/me/appointments`. Rescheduling and cancellation still use the
owned `/api/appointments/{appointment_id}` routes described below.

## Legacy development request examples

These routes remain for compatibility. Customer-ID requests validate ownership
when authentication is configured. `POST /api/customers` is a development
creation endpoint without a route-level login requirement; it does not register
a website login. Restrict legacy development access before public deployment.

Create or reuse a customer (the backend creates the UUID):

```json
{
  "full_name": "Ali Khan",
  "email": "ali@example.com",
  "phone": "0300-1234567"
}
```

Send to `POST /api/customers`.

Partially update preferences without clearing omitted fields:

```json
{
  "city": "Lahore",
  "area": "DHA",
  "budget_max": 50000000,
  "bedrooms": 3,
  "property_type": "Apartment",
  "purpose": "purchase",
  "amenities": ["Parking", "Gym"]
}
```

Send to `PATCH /api/customers/{customer_id}/preferences`.

Search verified properties:

```json
{
  "customer_id": "11111111-1111-1111-1111-111111111111",
  "city": "Lahore",
  "budget_max": 50000000,
  "limit": 20
}
```

Send to `POST /api/properties/search`.

Get recommendations and optionally reuse a session ID to avoid duplicate
`shown` events:

```json
{
  "recommendation_session_id": "22222222-2222-2222-2222-222222222222",
  "limit": 10
}
```

Send to `POST /api/customers/{customer_id}/recommendations`.

Record one explicit human action (`liked`, `rejected`, or `shortlisted`):

```json
{
  "customer_id": "11111111-1111-1111-1111-111111111111",
  "property_id": "LHR-DHA-APT-001",
  "action": "liked",
  "recommendation_session_id": "22222222-2222-2222-2222-222222222222"
}
```

Send to `POST /api/interactions`.

Book a visit through the authoritative Day 4 workflow:

```json
{
  "customer_id": "11111111-1111-1111-1111-111111111111",
  "property_id": "LHR-DHA-APT-001",
  "starts_at": "2030-01-02T10:00:00+05:00",
  "duration_minutes": 60,
  "meeting_notes": "Call before arrival"
}
```

Send to `POST /api/appointments`. Reschedule with
`PATCH /api/appointments/{appointment_id}/reschedule`; cancel with
`DELETE /api/appointments/{appointment_id}`.

## Authenticated shared chat (Phase 9)

`POST /api/me/chat` accepts only `message` (1-2,000 characters) and an optional
UUID `conversation_id`. Identity fields are rejected. Omit the conversation ID
for a new server-generated conversation. The endpoint uses the same CSRF
middleware as other authenticated mutations; the frontend uses `lib/api.ts`.

```json
{"message": "Options dikha dein."}
```

Responses contain `conversation_id`, `message`, and `requires_clarification`.
`properties`, `recommendation_session_id`, and `appointment` are included only
when applicable. Ownership failures return 404; expired conversations or
recommendations return 410. Dependency failures return safe 503 messages.

The adapter reuses Day 3 understanding, QueryPlanner, ConversationState,
ConversationPolicy, ResultPresentationPolicy, and NaturalSpeechPolicy. It uses
complete structured extraction through the existing NLU prompt, with validated JSON
output, one retry for malformed JSON, and a bounded 700-900 output-token allowance per attempt. Other Day 3/VAPI callers
retain their existing default extraction strategy. Configure the existing
`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `SARA_LLM_MODEL` on the backend.
No new assistant prompt, property retrieval, ranker, or ML pipeline is created.

Startup applies the additive `chat_schema.sql` migration after auth tables.
`chat_sessions` stores customer and auth-user ownership, UUID, timestamps,
status, and compact JSON state. PostgreSQL transaction/advisory locks serialize
turns for the same customer across processes. Blocking DB/LLM calls use worker
threads, including Windows-compatible PostgreSQL connections.

### History and privacy policy

- Absolute conversation lifetime: 24 hours, not extended on activity.
- Persisted state: latest recommendation ID and ordered property IDs, selected
  property ID, pending requirement/appointment fields, flexible/excluded fields, and the
  last six structured turn summaries (intent/action/index). No raw user or
  assistant transcript is persisted, logged, or sent as history.
- The current message is sent to the existing LLM, together with persisted
  property preferences, bounded structured continuity, and date/time context.
  Auth identity, email, phone, password hashes, cookies, CSRF values, and API
  secrets are never added to the NLU context.
- Browser history is component memory only, capped at 40 messages; reload or
  navigation starts a new conversation. Conversation ID persists across sends
  while the page is open. Account changes clear visible chat and discard stale
  in-flight responses. No chat content is saved to browser storage.
- Expiry prevents reuse; it does not physically erase database rows. No automatic
  cleanup/retraining is introduced. Apply an operator-selected retention policy
  to expired structured state and existing historical recommendation snapshots.

Preferences hydrate on every turn. Structured changes persist immediately via
CustomerService/PreferenceRepository. Existing saved values are not repeatedly
requested. Purpose is asked when genuinely missing, to distinguish purchase
budgets from monthly rent. Day 3 owns city/area invalidation and relaxation.


Recommendations call `WebServices.recommendations`, which retrieves verified
available PostgreSQL rows, applies the existing deterministic/ML service, and
stores the existing Phase 8B membership and historical snapshots. Only the
returned presentation batch gets shown events. The latest ordered presentation
resolves ordinal feedback; ambiguous or arbitrary IDs cannot write feedback.
Feedback calls the existing authenticated interaction contract.

Visits collect property and date/time, then invoke the existing authenticated
appointment route and Day 4 gateway. Reschedule/cancel require an owned
appointment ID. Day 4 retains slot validation, Calendar, CRM and email behavior.
The adapter makes no notification-delivery claims and returns only appointment
ID/status from a successful workflow response. It does not add the optional
`appointment_booked` event. Existing recommendation and appointment side effects
use their own transactions; chat does not promise atomic rollback across those
services or exactly-once external booking delivery.

### Verification

Run `day7/web_api/scripts/verify_phase9.py` from the workspace root. It starts
workers on 8010/8011, exercises real NLU and PostgreSQL in a disposable isolated
schema, and checks cross-user denial, second-result feedback, preference changes
and historical snapshots. It stops its own workers and drops only its generated
schema. Ports must be free; existing processes are never stopped. Fixture
listings are test data, not real listings offered to customers.

See `../../docs/PHASE9_REPORT.md` for exact test counts and limitations.
The current website recommendation contract does not express exclusion or relative
comparison filters; Sara asks for explicit supported criteria instead of silently
using such filters. This adapter does not expose the full Day 3 RAG/FAQ/comparison
surface.

## Browser voice and preference editing

Browser voice is implemented through `POST /api/me/voice-sessions`,
`POST /api/me/voice-sessions/close`, and the secret-authenticated
`POST /api/internal/voice/webhook`. Startup applies `voice_schema.sql` after
auth/chat schemas. The website API needs `VAPI_ASSISTANT_ID`; it must share
`DATABASE_URL` and `VAPI_WEBHOOK_SECRET` with the VAPI webhook. Configure
`SARA_WEB_API_INTERNAL_URL` on the webhook when the API is not at localhost:8010.
See the [browser voice report](../../docs/BROWSER_VOICE_REPORT.md).

Returning-customer editing uses the shared preference-edit policy. A request to
change preferences can name a field before providing a replacement value;
pending fields are retained and validated changes are persisted. See the
[preference-edit audit](../../docs/preference-edit-audit.md).

Automated retraining and model promotion are not implemented. ML defaults to
`off`; `shadow` and `active_dev` retain synthetic-development constraints.
For installation, environment loading, and all service commands, use the
[root setup](../../README.md). Dated reports record historical verification,
not a fresh pass for the current checkout.
