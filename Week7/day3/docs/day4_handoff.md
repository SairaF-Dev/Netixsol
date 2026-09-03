# Day 4 Handoff Contract

Day 3 emits a pending action with `type` and a verified selected `property`.
The implementation now lives in `../../day4`. Day 4 extends the action with
client name, phone, assigned employee, property, timezone-aware date/time and
meeting notes, then executes Calendar, email, CRM and n8n operations.

Use `day4_workflows.day3_adapter.validate_pending_action` at the boundary.
Day 3 must not claim an appointment was booked; only a successful Day 4
workflow response is final confirmation. Never store Google credentials in
this repository.
