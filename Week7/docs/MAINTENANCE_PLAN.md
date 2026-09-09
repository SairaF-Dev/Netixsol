# Monitoring and Maintenance Plan

These are proposed operational targets and procedures, not measured service-level
results or an installed monitoring/backup system.

Targets: 99.5% monthly availability; p95 text turn under 2 seconds excluding
telephony/TTS; booking success above 98% when dependencies are healthy; grounded
answer rate above 95%; critical tool failure below 1%. Measure each channel
separately and establish a provider-inclusive baseline before adopting targets.

- Daily: review API health response bodies, database reachability, chat/voice
  latency, authentication/CSRF failures, tool failures, and booking status.
- Weekly: review privacy-safe structured failures and explicit feedback. Website
  chat does not persist raw transcripts; do not assume transcript logs exist.
- Monthly: refresh changed knowledge documents, rebuild/evaluate the vector
  index, and run conversation, ownership, preference-editing, and voice regressions.
- Quarterly: restore an isolated database backup, review permissions and secrets,
  and run prompt-injection/security evaluation.
- Backups: arrange daily encrypted PostgreSQL backups with a proposed 30-day
  retention and monthly restore drill. Version knowledge documents and workflows.
- Retention: define cleanup for expired auth/chat/voice rows and recommendation
  snapshots. Runtime expiry denies access without physically deleting records.
- Alerts: proposed thresholds are health failure for 5 minutes, p95 above 5
  seconds for 15 minutes, booking failure above 5%, or repeated delivery failures.

Keep `SARA_ML_RANKING_MODE=off` as the deterministic baseline. Review real and
synthetic data separately; model training/promotion is an explicit offline action,
not an automatic consequence of collecting feedback. Follow the
[ML guide](../day7/ml/README.md) for readiness and label policy.

Before a release, verify authenticated website flows, live browser/phone voice,
and test-account Calendar/email delivery. Record dates, environment, provider
latency, and failures. Local fixture timings and historical pass counts are not
production acceptance evidence. See the [admin guide](ADMIN_AND_TROUBLESHOOTING_GUIDE.md).
