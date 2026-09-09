Returning-customer preference editing audit — 2026-09-08

1. Root cause and traced execution

   Website chat is wired by `day7/web_api/services.py` to `ChatAdapter.turn` in
   `day7/web_api/chat.py`. It retrieves the identified customer's preferences,
   hydrates Day 3 search memory through `shared/sara_service.py`, and runs the
   Day 3 understanding service. The returning-customer greeting sets
   `pending_returning_confirm` in the conversation's saved dictionary.

   Previously, the next turn temporarily cleared that flag but, when extraction
   produced no new required values or relaxations, set it back to true and emitted
   `Saved requirement continue karni hai ya koi preference change karni hai?`.
   A fieldless change request naturally contains no new filter values. There was
   no separate edit action or pending preference field, so the fallback repeated
   indefinitely. The state store was retaining the flag correctly; the wrong
   transition was being retained. This was an application routing problem, not
   a prompt-generated question or a LangGraph edge looping.

   The repository also contains Day 3 `langgraph_schema.py` / `langgraph_nodes.py`
   and Day 5 `state.py` / `graph.py`. Neither generates this chat question.
   The Day 7 adapters use Day 3 understanding and memory/planning policies directly;
   the phone manager also uses the Day 3 profile schema. No graph replacement was
   necessary. The standalone Day 3 chatbot retains its existing routing.

2. Files changed

   | File | Change |
   | --- | --- |
   | `day3/src/sara_agent/models.py` | Optional structured preference action and field list; existing positional fields retained. |
   | `day3/src/sara_agent/understanding.py` | Semantic schema/prompt support, UrduLish fallback, replacement-value normalization, and pending-field context for short answers. |
   | `day3/src/sara_agent/preference_edit.py` | Shared edit transitions, pending fields, cancellation, clarification and confirmation. |
   | `day7/web_api/chat.py` | Run edit routing before returning-confirmation fallback; retain partial profiles; validate updates and finish edits after persistence. |
   | `day7/vapi_integration/session_manager.py` | Per-call editing state, returning greeting/continuation, shared policy and conflict-aware partial persistence for edits. |
   | `day7/vapi_integration/guardrails.py` | Accept narrow UrduLish change follow-ups in conversation context, after existing security/off-topic checks. |
   | `day1/05_system_prompt/system_prompt.md` | Align persona instructions with the state transitions. |
   | `day7/web_frontend/components/SaraVoice.tsx` | Include editing guidance alongside saved preferences in the existing VAPI per-call system message. |
   | `day7/tests/test_preference_edit_flow.py` | 28 regression cases using real extraction, HTTP chat, browser transcript webhook, and phone session orchestration. |
   | `day7/web_frontend/tests/voice.test.tsx` | Verify saved preferences and edit guidance reach the voice SDK. |
   | `docs/preference-edit-tests.xml` | Machine-readable final Python test results. |
   | `docs/preference-edit-audit.md` | This audit. |

3. Exact logic

   Change intent is represented independently of property-search filters using
   `preference_action` and `preference_fields`. The existing LLM schema can
   recognize paraphrases; conservative language rules handle common UrduLish
   commands and provider-unavailable scenarios. Field-only commands do not invent
   values. Replacement clauses extract the new value, and a bare answer receives
   the pending field as extraction context.

   `advance_edit` consumes the change decision before the old confirmation
   fallback. It remembers all missing requested fields, permits multiple supplied
   values, and keeps the edit active on repeated change requests. Appointment and
   feedback intents retain their existing routes. Invalid values request a corrected
   value without writing them. `finish_edit` runs after successful persistence;
   if another requested value is missing, only that value is requested.

4. State transitions

   Before: greeting → pending confirmation → fieldless change → pending
   confirmation again.

   After: greeting → pending confirmation → `editing_preferences` →
   `selecting_preference_field` or `providing_preference_value` → validated
   partial update → `ready_for_search`. Supplied fields/values skip their questions.
   Continue uses `continuing_saved_preferences` → `ready_for_search`.
   Explicit cancellation leaves the edit and resumes saved preferences.

5. Persistence and conflicts

   Chat's existing `PostgresConversationStore` stores the state dictionary as
   JSONB on successful exit from the turn context, including early clarification
   returns. Hydration fetches customer preferences again on subsequent turns.
   Changed fields pass through `PreferencesUpdate` and
   `CustomerService.update_preferences` → `PreferenceRepository.update_partial`.
   The existing PostgreSQL upsert updates only supplied columns, not the full row.
   Phone edits use the same planner and validation schema, then update the customer
   service before updating call memory or acknowledging success.

   Existing Day 3 conflict rules remain: changing city clears an old city-scoped
   area; changing purchase/rental purpose clears an incompatible budget; a plot
   does not retain a bedroom requirement. Other preferences remain intact.
   Chat also retains the edit and asks for a valid maximum if it conflicts with
   the stored minimum budget. Changed constraints invalidate stale results.

6. Chat and voice

   Authenticated chat and browser VAPI final transcripts share `ChatAdapter`.
   Phone transcripts reach `VapiSessionManager.process_turn` through the existing
   VAPI webhook, and now use the shared edit policy. Tests exercise both paths.

   Browser transcripts are observation-only: their server responses do not drive
   speech. The hosted VAPI assistant owns speech and tool calls, so its existing
   per-call system context now includes the matching edit instructions. Local
   tests verify that delivery; they do not prove a live hosted conversation.
   No hosted assistant configuration was published and no live call was placed.

7. Automated coverage

   The 28 new Python cases cover all ten requested scenarios, the listed UrduLish
   variants, multiple and partial edits, fresh-session preference retrieval,
   semantic edit routing, continuation, cancellation, invalid bedrooms, budget
   conflicts, appointment isolation, browser transcript persistence, phone updates
   and conflicts, and phone persistence failure without a success claim.
   Provider calls are replaced in tests; production extraction and orchestration
   still run. Profile persistence/retrieval tests use recording/in-memory services.

8. Results

   Final focused/regression Python run: **267 passed, 2 skipped** in 27.74 seconds.
   It covers the new flow, existing chat/ranking modes, refined conversation flow,
   area disambiguation, browser voice, verified voice retrieval, VAPI persistence,
   webhook and guardrails, and Day 3 memory/planner/NLU/hardening checks.
   See `preference-edit-tests.xml` for individual cases. The two skips require an
   explicitly configured PostgreSQL integration-test database.

   Frontend voice suite: **6 passed**.

   Separately, `test_returning_scope.py`: **11 passed, 7 failed**. All seven failures
   compare exact wording in the unchanged named-city area-list response:
   tests expect `available hain: ... Kis area ke options ...`; the implementation
   says `available hain jesay: ... ap knsey area mein ...`. These are outside the
   preference-edit change and were not rewritten to hide the failures.

9. Remaining limits

   Live PostgreSQL round trips and hosted VAPI speech were not verified. Phone
   edit state follows the existing in-process per-call session lifecycle; durable
   cross-worker phone session recovery was not introduced. Unusual language outside
   the deterministic rules depends on the existing semantic provider.

   Git status could not be read because the workspace reports
   `.git/index: index file smaller than expected`. No Git repair, reset, or commit
   was attempted; this report lists the files edited during this task.
