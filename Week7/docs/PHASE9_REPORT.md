# Phase 9 implementation and verification report

Phase 9 is complete for authenticated website text chat. No subsequent phase
was started. Verification date: 2026-09-05.

| Item | Findings / implementation |
| --- | --- |
| A. Audit findings | Inspected git status/diff before edits, Day 3 runtime/chatbot/state/understanding/policies and legacy LangGraph nodes, VAPI session/tool handling, website services, preference and interaction repositories, and appointment ownership routes. The tree already contained substantial prior-phase changes and untracked application files; those were preserved. Day 3's reusable current core is synchronous structured understanding plus memory/planning/presentation policies. The legacy LangGraph/VAPI wrapper references older imports and an older understanding signature; website chat does not route through that wrapper. Existing Day 3 and VAPI session dictionaries cannot provide multi-worker website ownership. |
| B. Reused Sara components | UserUnderstandingService and its existing prompt; ConversationState, QueryPlanner, ConversationPolicy, ResultPresentationPolicy, NaturalSpeechPolicy, and verified property formatters. Existing CustomerService/PreferenceRepository, WebServices.recommendations, rankers, InteractionRepository and authenticated appointment routes remain authoritative. |
| C. Files changed | See the scoped manifest below. No ML training, browser voice, VAPI tool transport, Day 4 business-rule or deployment changes were made. |
| D. Shared adapter architecture | POST /api/me/chat → authenticated ChatAdapter → shared SaraService → existing Day 3 structured capabilities and website domain services. A small property-reference resolver is now shared with VapiSessionManager. There is no new Sara agent, second assistant prompt, search implementation, recommendation engine or graph. The existing NLU gained complete-extraction mode and optional appointment slots; default callers retain their previous strategy. |
| E. Conversation persistence | Additive PostgreSQL chat_sessions migration. Server-generated UUID, customer/auth-user ownership, created/updated/expiry timestamps, status and compact JSON state. Per-customer PostgreSQL transaction advisory locks serialize chat turns across workers; row locking protects the selected conversation. Sync PostgreSQL operations run in worker threads for Windows/Unix event-loop compatibility. |
| F. Authentication/ownership | Identity is derived from the HttpOnly authenticated session. Request schema accepts only message and optional conversation_id; customer_id, user_id, email and phone inputs are rejected. Missing/foreign conversations return the same 404. Expired conversations return 410. |
| G. Preference hydration | Every turn loads the authenticated customer's persisted preferences into the existing Day 3 state. Known fields are skipped by the existing requirement policy. The live scenario correctly asked purchase versus rental because purpose was omitted. |
| H. Preference update flow | Structured NLU → Day 3 QueryPlanner/state merge → validated partial preference update → existing CustomerService/PreferenceRepository immediately. City changes clear stale area; explicit relaxation uses Day 3 semantics. Persistence failures return safe errors rather than claiming success. |
| I. Verified property flow | Existing PostgreSQL search restricts candidates to available properties with verified pricing. Only returned rows reach Day 3's deterministic result/detail formatters and browser cards. The LLM extracts intent and fields; it never authors property claims for website responses. Details refresh through the verified property repository. |
| J. Ranking/ML reuse | Unchanged WebServices.recommendations invokes the existing deterministic ranker and Phase 5 model service. off remains the default; shadow/active_dev retain their prior behavior. Normal chat responses omit ML mode/probability data. |
| K. Recommendation sessions | Uses the existing Phase 8B PostgreSQL recommendation tables, ownership, ordered property membership and historical preference/property snapshots. Each new presentation gets its own recommendation ID. Only the returned batch (up to five properties) receives shown events. |
| L. Feedback resolution | Structured action/index/reference/explicit ID resolves against the most recent presentation. Ambiguous references, invalid indices, arbitrary IDs and expired recommendation context cannot write events. Liked/rejected/shortlisted events delegate to the authenticated interaction contract and InteractionRepository with historical snapshots. |
| M. Appointments | Chat collects selected property and timezone-aware date/time and delegates to the existing authenticated booking route/Day 4 gateway. Reschedule/cancel collect an appointment ID and reuse ownership checks before external mutations. Missing dates, ambiguous requests, foreign IDs and unavailable services fail safely. Calendar/CRM/email and slot rules remain in Day 4. Card booking reuses BookVisit. The optional appointment_booked event was not added. |
| N. UrduLish/persona | Reuses Sara's existing understanding prompt, requirement policy, natural speech and verified-result formatting. Added ordinal UrduLish feedback examples to that same NLU prompt. Responses are concise and ask one necessary question at a time; no repeated opening greeting or invented facts. |
| O. Privacy/history | No raw chat transcript is persisted. PostgreSQL stores latest presentation IDs, selected ID, pending workflow fields, flexible/excluded state and the last six intent/action/index summaries. Only the current message plus bounded structured context goes to NLU; no auth identity/contact/session secrets are injected. Absolute chat expiry is 24 hours. Browser component history is capped at 40 messages and clears on reload/navigation/account change; stale replies from a previous account are discarded. Expiry denies reuse but is not physical deletion. Full NLU output is bounded to 700–900 tokens per attempt, with one malformed-JSON retry using the same prompt. |
| P. CSRF | No chat exemption. Existing Phase 8B middleware protects POST /api/me/chat. The frontend uses the central credentialed API client, including its CSRF token fetch/retry flow. |
| Q. Multi-instance verification | PASSED with real processes on 8010 and 8011, real PostgreSQL and configured live NLU. Conversation started on A and continued on B; preference/context continuity, recommendation resolution, feedback and cross-user 404 denial all verified. Workers were stopped and the isolated disposable schema removed. See phase9-live-verification.json. |
| R. End-to-end scenario | PASSED: Lahore/DHA/3 bedrooms/3 crore persisted; purpose clarified as purchase; verified options and shown membership returned; “second wali pasand” wrote liked for exactly the displayed second property; budget became 4 crore; old snapshots stayed 3 crore; a new recommendation ID had 4-crore snapshots. Test listings were explicit disposable fixtures in an isolated PostgreSQL schema, not modifications to existing customer/property rows. |
| S. Backend tests | 212 passed, 10 warnings: 30 new Phase 9 + 182 prior regression tests. Includes auth, Phase 8B security, website API, ML, VAPI, Day 4 and collector tests. An additional targeted Day 3 run passed 19 tests (1 warning). Total backend checks across both runs: 231 passed. |
| T. Frontend tests | 28 passed across 6 files (16 previous + 12 added). Covers authentication/loading, submission, safe errors, conversation continuity, cards, authenticated feedback/recommendation ID usage, booking form, account-change reply isolation, CSRF reuse and existing no-direct-provider/no-browser-ML checks. |
| U. VAPI regression | All 105 VAPI integration tests passed, including property tools, appointments, webhook behavior, ownership/preferences, feedback and guardrails. VAPI voice transport was not redesigned. |
| V. Build | Next.js production build passed: compilation, TypeScript, page-data collection and static generation including /sara. git diff --check passed. |
| W. Remaining limitations | Listed below; no hidden live external booking/notification claim is made. |
| X. Completion statement | Phase 9 is complete within the requested authenticated text-chat scope, with the explicit limitations below. No Phase 10/browser voice/retraining work was started. |

## Scoped file manifest

New implementation:

- day7/shared/__init__.py
- day7/shared/sara_service.py
- day7/web_api/chat.py
- day7/web_api/conversation_service.py
- day7/web_api/chat_schema.sql
- day7/web_api/scripts/verify_phase9.py

Updated integration:

- day3/src/sara_agent/models.py — optional structured appointment slots.
- day3/src/sara_agent/understanding.py — same shared NLU prompt, complete
  extraction option, bounded malformed-JSON retry, appointment fields and
  explicit UrduLish ordinal-feedback examples.
- day7/vapi_integration/session_manager.py — delegates ordinal resolution to
  the shared resolver; preserves existing call lifecycle/tool behavior.
- day7/web_api/services.py — production conversation-store initialization and
  injectable adapter dependencies.
- day7/web_api/app.py — authenticated CSRF-protected route and safe errors.
- day7/web_api/schemas.py — strict chat request and structured response.
- day7/web_frontend/app/sara/page.tsx — authenticated chat UI.
- day7/web_frontend/app/globals.css — small chat presentation additions.
- day7/web_frontend/components/FeedbackButtons.tsx — existing component can
  use the authenticated /api/me feedback contract without a customer argument.
- day7/web_frontend/lib/api.ts and types/api.ts — central typed chat contract.

Tests, documentation and evidence:

- day7/tests/test_phase9_chat.py
- day7/web_frontend/tests/chat.test.tsx
- day7/web_frontend/tests/chat-api.test.ts
- day7/web_api/README.md
- day7/web_frontend/README.md
- docs/PHASE9_REPORT.md
- docs/phase9-live-verification.json
- docs/phase9-regression.xml
- docs/phase9-worker-8010.log and phase9-worker-8011.log (local test logs).

Prior-phase files were already modified/untracked at entry, so a repository-wide
git diff is not a Phase 9-only change inventory. Python/test/build tools also
created normal local cache artifacts.

## Regression breakdown

| Suite | Passed |
| --- | ---: |
| New Phase 9 backend | 30 |
| Website API | 12 |
| Authentication | 9 |
| Phase 8B security | 4 |
| ML / Phase 4–5 | 39 |
| Streamlit collector | 2 |
| VAPI integration | 105 |
| Day 4 | 11 |
| Combined required backend regression | 212 |
| Additional targeted Day 3 regression | 19 |
| Frontend | 28 |

Backend execution required the existing day7/day3/day4/Day2 module paths and
an explicit test-only DAY4_API_KEY for mocked appointment tests. Initial runs
hit a pytest temporary-directory sandbox restriction and missing test-only
configuration; the corrected final runs above passed. The first live attempt
also exposed Windows async PostgreSQL incompatibility, incomplete fast-path
NLU extraction, and malformed provider JSON; those were fixed and the final
live scenario passed. No failed initial run is counted as a passing check.

## Remaining limitations

- Calendar/CRM/email provider delivery was not exercised live: Day 4 delegation,
  ownership and failure behavior were tested with the existing regression
  suites and injected gateways. The actual configured live test covers NLU,
  PostgreSQL, auth, recommendations, feedback and snapshots. There is no claim
  of a real customer booking or email being sent.
- The adapter intentionally does not expose all Day 3 RAG/FAQ/comparison
  capabilities. The existing website recommendation contract cannot express
  exclusion/relative-comparison filters; chat requests clarification rather
  than claiming these filters were applied.
- Chat transcript recovery after reload is not provided. The server retains
  structured continuity, and the page retains its conversation ID while open.
- No automatic retention deletion, retraining, model promotion, or browser
  voice was introduced. Expired structured rows require an operator retention
  policy if physical removal is desired.
- Existing recommendation/interaction/appointment services use separate
  transactions. There is no distributed atomic rollback or exactly-once
  external appointment delivery guarantee. A failure after an external side
  effect requires checking appointment status before retrying.
- Existing legacy VAPI/Day 3 wrapper import/signature inconsistencies remain
  outside this phase. The shared website adapter uses the current exported
  Day 3 capabilities directly; VAPI regression behavior was preserved.
