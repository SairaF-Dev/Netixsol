# Conversation Evaluation Suite

This submission uses 44 end-to-end scenarios, exercised at the HTTP/session,
conversation, retrieval, and workflow boundaries.

| Category | Scenarios | Acceptance criteria |
|---|---:|---|
| Buyer | 5 | Captures city/budget/type; only verified matches |
| Seller | 3 | Captures property and contact; does not invent valuation |
| Investor | 4 | Uses verified data; never guarantees returns |
| Rental | 4 | Captures area, rent budget, bedrooms, move-in needs |
| Appointment booking | 5 | Requires details; checks conflict; confirms only on success |
| Rescheduling | 3 | Identifies appointment; checks new slot; updates systems |
| Cancellation | 3 | Identifies appointment; cancels calendar and notifies |
| Objections/angry callers | 4 | Acknowledges concern, stays calm, offers useful next step |
| Silent/unclear callers | 3 | Reprompts without guessing and ends safely after repetition |
| Off-topic | 4 | Does not call tools; redirects to real estate |
| Prompt injection/privacy | 6 | Refuses override, prompt, secret, private-data, and fake-action requests |
| **Total** | **44** | |

Automated evidence is distributed across `day2`, `day3`, `day4`, `day5`, and
`day7/vapi_integration/tests`. The security corpus is in
`day7/vapi_integration/tests/test_guardrails.py`; conversation/memory cases are
in `day3/tests`; workflow lifecycle cases are in `day4/tests`; graph routes are
in `day5/tests/test_graph.py`.

## Required manual cases

The following must be run during the live demonstration because mocks cannot
prove provider behavior: barge-in during speech, truly silent telephone audio,
Urdu-English recognition quality, real Calendar mutation, real email delivery,
and real VAPI/n8n delivery. Record call ID, timestamp, expected result, observed
result, latency, and reviewer initials. Never mark an unexecuted live case pass.
