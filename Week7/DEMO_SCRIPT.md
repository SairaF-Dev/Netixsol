# Ten-Minute Stakeholder Demonstration

Prepare a test account and development listings. Start PostgreSQL, Day 4, website
API, webhook, and frontend using the [setup guide](README.md). Verify provider
configuration before demonstrating voice or external Calendar/email delivery.

1. **0:00-0:45 - Goal:** explain Sara and the verified-data rule.
2. **0:45-1:30 - Architecture:** show website/chat, VAPI, PostgreSQL, and Day 4.
3. **1:30-2:30 - Account:** log in and show saved preferences.
4. **2:30-3:30 - Recommendations:** load matches and record explicit feedback.
5. **3:30-4:30 - Chat:** ask for properties in UrduLish and refer to a shown result.
6. **4:30-5:30 - Preference editing:** request a budget change, give the new value,
   and verify it on Preferences.
7. **5:30-6:30 - Browser voice:** start a call on `/sara`, allow the microphone,
   demonstrate a request, then mute/end the call.
8. **6:30-8:00 - Visit:** select a property, provide a future date/time, and show
   the returned appointment and owned listing. Reschedule or cancel the test visit.
9. **8:00-9:00 - Boundaries:** try an off-topic or prompt-reveal request. Explain
   cookie ownership and the deterministic ranking baseline.
10. **9:00-10:00 - Operations:** show health, dated verification evidence, and
    remaining live-delivery/deployment work.

Only claim Calendar/email delivery if its result is actually verified. Check
appointment status before retrying an interrupted booking. Keep a prerecorded
fallback for unavailable providers and identify it as recorded. Website chat does
not expose the full Day 3 FAQ/RAG/comparison surface; demonstrate only supported flows.
