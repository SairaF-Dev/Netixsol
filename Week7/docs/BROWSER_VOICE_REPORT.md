# Existing Sara assistant: browser voice integration

Audit date: 2026-09-05. Continued from the current worktree without resetting Git.
`git status` succeeded: no corrupt index error. Existing unrelated changes,
cache permission warnings, and the deleted frontend `.env.example` were preserved.
Read Phase 9 report, VAPI webhook/session/tool code, website API/auth/chat services,
`/sara`, and environment variable names. `NEXT_PUBLIC_VAPI_PUBLIC_KEY` was present
and nonempty in `day7/web_frontend/.env.local`; its value was not printed.

## Implementation

- Official `@vapi-ai/web` 2.7.0, dynamically loaded after authenticated bootstrap.
  Starts the existing backend-configured `VAPI_ASSISTANT_ID`; no new assistant,
  model, search, ranking engine or appointment workflow was created.
- `/sara` has start/cancel/end/mute controls, connection errors and a bounded
  in-memory transcript. Navigation/account replacement stops the SDK and revokes
  the capability. Pending bootstrap replies cannot start a stale account's call.
- Authenticated, CSRF-protected `/api/me/voice-sessions` generates a random
  capability. PostgreSQL stores only its SHA-256 digest, links it to the auth
  session and chat context, and binds it atomically to one VAPI call/assistant.
  Initial binding expires after two minutes; absolute capability lifetime is
  35 minutes. SDK calls are capped at 30 minutes. Logout/session expiry invalidates
  further browser events. A new start invalidates the preceding capability for
  that login. Closing another account's capability cannot revoke it.
- VAPI forwards `sara_voice_session` in `assistantOverrides.variableValues`.
  The shared-secret-authenticated webhook forwards web calls to the website API;
  the website API independently verifies the secret and persisted mapping.
  Browser customer IDs, telephone numbers and appointment contact arguments
  cannot choose identity. Invalid browser events never fall back to phone identity.
- Browser tools reuse website preference updates, recommendations (including
  ranking/ML, shown interactions and recommendation snapshots), and authenticated
  Day 4 appointment routes. Booking requires membership in the voice recommendation;
  cancel/reschedule require website appointment ownership. Tool IDs are cached
  in the existing locked conversation state to suppress completed webhook retries.
- Final user transcripts reuse the Phase 9 adapter for preferences and feedback
  only. They cannot independently trigger duplicate search/appointment tools.
  Saved preference data is supplied to the existing assistant on connection;
  no identity/contact/auth secrets are included in this context message.
- Normal phone events retain their existing transport and identity path. The
  location parser is shared by the two tool adapters.
- Build exposed existing duplicate default components in preferences and
  recommendations pages. Removed only each older duplicate, retaining `/api/me`.

## Verification

- Existing auth, CSRF, web API, Phase 9 chat and all 105 VAPI regression tests pass.
- New route tests cover identity injection, CSRF, secret validation, denied
  browser-to-phone fallback, preference/recommendation reuse, duplicate tool
  delivery, final-transcript feedback, and appointment ownership/contact mapping.
- Real PostgreSQL test uses a disposable isolated schema, removed after completion.
  Verified independent store instances share identity/context, wrong-call and
  wrong-assistant rejection, initial-binding/absolute expiry, foreign close denial,
  explicit close, and logout invalidation.
- Frontend suite: 35 tests pass. Production Next.js build passes, including `/sara`.
- `git diff --check` passes for changed source files.

## Running and remaining live checks

Restart the website API (8010), existing VAPI webhook service, and frontend.
Website startup initializes `web_api/voice_schema.sql` after auth/chat schemas.
For separate containers, set `SARA_WEB_API_INTERNAL_URL` to the website API's
internal address. Both backends must share `DATABASE_URL` and `VAPI_WEBHOOK_SECRET`.
Retain the existing assistant's public HTTPS webhook URL and secret configuration.
The SDK overrides server event subscriptions for browser calls only.

The configured frontend public key was checked for presence, not validated
against VAPI. Its VAPI allowed origins/assistants must permit this site and Sara.
No remote assistant configuration was changed. No paid live voice call or real
calendar/email delivery was exercised. Confirm microphone/audio, actual VAPI event
delivery, and provider latency with an authenticated browser call after restart.

VAPI owns spoken responses; transcript-observed memory writes do not control the
assistant's spoken confirmation. They depend on final transcript delivery and NLU.
The existing multi-service external-side-effect atomicity limitation remains:
after a crash between Day 4 completion and local commit, check appointment status
before retrying. Expiry denies access but does not physically delete stored rows;
operator retention policy is unchanged.

SDK references: [official Web SDK](https://github.com/VapiAI/client-sdk-web),
[public/private API keys](https://docs.vapi.ai/security-and-privacy/api-keys).
Version 2.7.0 incorrectly types the `serverMessages` REST array as a scalar union;
a local `@ts-expect-error` documents that specific generated declaration mismatch.
