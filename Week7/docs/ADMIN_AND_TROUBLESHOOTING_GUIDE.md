# Administration and Troubleshooting

Follow the [root setup](../README.md) for environment variables and commands.
No `.env.example` files are supplied in this checkout. Preserve local secrets;
never paste them into logs or tickets.

## Startup checks

1. Start PostgreSQL and verify the Day 2 property schema and development seed,
   then apply the customer/interaction migrations listed in the root setup.
2. Start Day 4 on 8004 for appointments; configure Calendar, SMTP, and optional
   n8n using the [Day 4 guide](../day4/docs/SETUP.md).
3. Start the website API on 8010. Its startup initializes additive auth, chat,
   and voice tables, so the database role needs schema permissions.
4. Start the VAPI webhook on 8007 for voice, then the website on 3000.
5. Check `/health` on each API. Website health reports database and ML status;
   inspect the JSON `status` and `database`, not only the HTTP status code.
6. Log in, save preferences, and send a chat turn. For browser voice, test
   microphone/audio and webhook delivery separately.

The website API loads `day7/vapi_integration/.env`, `day3/.env`, and `day2/.env`
in that order without overriding already-set values. A root `.env` is not an
automatic website API configuration source. Restart backends after changes.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Website API startup fails | Database reachability, role permissions, and Python dependencies |
| Login succeeds but later requests return 401 | Cookies, `credentials: include`, and consistent `localhost` hostnames |
| Authenticated mutation returns 403 | CSRF token and cookie; the frontend refreshes the token and retries once |
| Chat returns 503 after a 403 retry | API terminal's `Chat turn failed` entry and the LLM provider configuration |
| Webhook returns 403 | Matching `VAPI_WEBHOOK_SECRET` and `X-Vapi-Secret` |
| Voice cannot start | Public browser key, backend assistant ID, microphone permission, and HTTPS/localhost |
| Voice starts but tools fail | Public webhook delivery, shared database/secret, and `SARA_WEB_API_INTERNAL_URL` |
| No property results | Property data, availability, city/area/purpose, budget, and saved preferences |
| Recommendation session expired | Load a fresh recommendation before submitting feedback |
| Appointment conflict | Choose another slot and inspect the Day 4 response |
| Booking response was interrupted | Check owned appointments before retrying; external effects are not atomic with chat state |
| Email warning or Calendar failure | Day 4 provider configuration, service-account access, and delivery logs |

From the repository root, `python day7/diagnose_chat.py` probes the configured
LLM using the API environment. It makes a provider request; success verifies that
connection at that moment, not the whole authenticated chat flow.

VAPI `/metrics` is protected with the webhook credential. See
[API security](API_SECURITY.md) for separate service and website authentication.
The [browser voice audit](BROWSER_VOICE_REPORT.md) lists live checks that were
not performed during that implementation audit.

## Deployment and retention

The root Compose stack does not run Next.js or the website API. Its Calendar
backend defaults to memory. Configure the full service topology, real delivery
providers, HTTPS, and `SARA_AUTH_SECURE_COOKIE=1` before a deployment acceptance
check. Keep Day 4, the internal voice callback, PostgreSQL, and n8n restricted.
The VAPI webhook itself must be reachable by VAPI over HTTPS.

Back up PostgreSQL and review retention for expired auth/chat/voice sessions and
recommendation snapshots. Expiry prevents access but does not delete rows.
Review [maintenance](MAINTENANCE_PLAN.md) for proposed operational targets.
