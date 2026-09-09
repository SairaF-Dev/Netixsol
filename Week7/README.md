# Sara Real Estate Assistant

Sara is a development real-estate assistant with an authenticated website,
UrduLish text chat, browser voice, and VAPI phone integration. It saves customer
preferences, retrieves verified properties, ranks recommendations, records
feedback, and routes visits through the Day 4 appointment service.

The model interprets requests; PostgreSQL and business services supply property
facts and appointment results. Live provider delivery and production readiness
require separate validation.

## Current capabilities

- Website registration/login, saved preferences, and customer-owned appointments.
- Property search, deterministic recommendations, and like/reject/shortlist feedback.
- Shared chat with structured continuity and returning-customer preference editing.
- Browser voice using the existing VAPI assistant and authenticated voice sessions.
- Phone sessions with guardrails and customer preference persistence.
- Day 2 structured retrieval and RAG. The website adapter exposes a narrower
  surface than the full Day 3 FAQ/RAG and comparison flows.
- Booking, rescheduling, and cancellation through Day 4 workflows.
- Offline ML training and optional development scoring; ML defaults to `off`.

## Architecture and repository

```text
Website (3000) --> Website API (8010) --> Shared Sara services
   |                    ^                     |
   +--> VAPI voice --> Webhook (8007)          +--> Day 3 understanding/policies
Phone --> VAPI ------> Webhook (8007)          +--> Day 2 PostgreSQL retrieval
                                              +--> Deterministic/optional ML ranking
                                              +--> Day 4 appointments (8004)
```

Browser events are forwarded to the website API, which validates the voice
capability and account ownership. Phone calls retain their own identity path.
Day 7 adapters reuse Day 3 policies directly; Day 5 is a separate graph implementation.

| Path | Purpose |
| --- | --- |
| `day1/` | Architecture, persona, conversation flows, and prompt specifications |
| `day2/` | Knowledge documents, PostgreSQL schema/seed, RAG, and retrieval |
| `day3/` | Conversational agent, understanding, memory, and standalone interfaces |
| `day4/` | Appointment API, Calendar/email/CRM, and n8n workflows |
| `day5/` | LangGraph orchestration and tests |
| `day6/` | Conversation and performance reports |
| `day7/web_frontend/` | Next.js website |
| `day7/web_api/` | Authentication, chat, browser voice, and owned API routes |
| `day7/shared/` | Shared conversation service |
| `day7/vapi_integration/` | Webhook, phone sessions, guardrails, and persistence |
| `day7/ml/` | Dataset preparation, training, and development scorer |
| `day7/tests/` | API, security, conversation, voice, and ML regression suites |
| `docs/` | User/admin guides and dated implementation reports |

## Local setup

Use Python 3.11+, PostgreSQL, and Node.js/npm compatible with the frontend's
Next.js dependency. Voice needs a configured VAPI assistant, public browser key,
HTTPS webhook, and provider credentials. External Calendar/email delivery needs
Day 4 integration configuration.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r day3/requirements.txt -r day7/vapi_integration/requirements.txt
```

Run Day 4 in its own environment using [its setup guide](day4/docs/SETUP.md).
Initialize a development database with the Day 2
[schema](day2/03_structured_retrieval/schema.sql) and
[seed](day2/03_structured_retrieval/seed.sql), following the
[knowledge-layer guide](day2/README.md). Seed listings are demonstration data.
Before the first website startup, apply the customer and interaction migrations
to that development database. With `DATABASE_URL` set in the terminal, run from
the repository root:

```powershell
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f day7/vapi_integration/customer_schema.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f day7/vapi_integration/interaction_schema.sql
```

Website startup then initializes additive auth, chat, and voice tables; its
database role needs the corresponding schema permissions. PowerShell does not
automatically load `.env` values into `$env:DATABASE_URL` for `psql`.

Create service environment files manually; `.env.example` files are not supplied
in the current tree. Preserve existing local configuration. The website API loads
`day7/vapi_integration/.env`, then `day3/.env`, then `day2/.env`, without overriding
values already set in the process or an earlier file.

Backend configuration names (supply your own values and keep secrets out of Git):

```env
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/DATABASE
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
SARA_LLM_MODEL=
DAY4_API_URL=http://localhost:8004
DAY4_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_WEBHOOK_SECRET=
SARA_WEB_API_INTERNAL_URL=http://localhost:8010
SARA_WEB_CORS_ORIGINS=http://localhost:3000
SARA_AUTH_SECURE_COOKIE=0
SARA_ML_RANKING_MODE=off
```

Set the LLM model to one supported by your provider. Assistant management scripts
also use `VAPI_API_KEY` and `VAPI_SERVER_URL`; the standalone Day 3 API uses
`SARA_API_KEY`. Generate independent random service secrets. Website users sign
in with cookies rather than the Day 3 shared key.

Create or update `day7/web_frontend/.env.local`:

```env
NEXT_PUBLIC_SARA_API_URL=http://localhost:8010
NEXT_PUBLIC_VAPI_PUBLIC_KEY=
```

Only the VAPI public key belongs in frontend configuration. Use `localhost`
consistently in browser URLs so development cookies remain same-site.

## Start the services

Start PostgreSQL first. In separate terminals, activate the relevant environment
and run these commands from the repository root:

| Service | Command | URL |
| --- | --- | --- |
| Appointments | `python -m uvicorn api.main:app --app-dir day4 --host 127.0.0.1 --port 8004` | `http://localhost:8004` |
| Website API | `python -m uvicorn web_api.app:app --app-dir day7 --host 127.0.0.1 --port 8010 --reload` | `http://localhost:8010/docs` |
| VAPI webhook | `python -m uvicorn vapi_integration.webhook_server:app --app-dir day7 --host 0.0.0.0 --port 8007` | `http://localhost:8007/health` |

Frontend:

```powershell
cd day7/web_frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://localhost:3000/start`, register or log in, save preferences, and
open `/sara` for chat. For voice, expose port 8007 through HTTPS and configure
the existing assistant's webhook URL and secret. Both Day 7 backends must share
`DATABASE_URL` and `VAPI_WEBHOOK_SECRET`. Select **Start voice call** and allow
microphone access.

The root [Docker Compose file](docker-compose.yml) includes PostgreSQL, Day 4,
the VAPI webhook, and n8n. It does not include the website API or Next.js.
Its default Calendar backend is in memory. A successful booking does not by
itself prove email or external Calendar delivery.

## Verification

From the repository root with the Day 7 environment activated:

```powershell
python -m pytest day7/tests day7/vapi_integration/tests -q
```

From `day7/web_frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Some tests/evaluators need PostgreSQL, providers, or additional dependencies.
The [website API guide](day7/web_api/README.md) describes its isolated live verifier.
For LLM diagnosis, run `python day7/diagnose_chat.py` from the root. Health checks
do not verify a full chat turn or paid voice call. Counts and latency figures in
dated reports describe those runs, not a fresh result for the current checkout.

## Security and limitations

Website sessions use HttpOnly cookies, CSRF validation on authenticated mutations,
and account ownership checks. Day 3, Day 4, and VAPI use separate credentials.
See [API security](docs/API_SECURITY.md) for route-specific boundaries and legacy
endpoints. Use HTTPS and Secure cookies in production and restrict internal services.

Chat retains compact structured state rather than raw transcripts. Expiration
denies reuse but does not delete database rows. External appointment side effects
and local state are not atomic; check appointment status before retrying an
interrupted booking. Synthetic development ML is not a production model.

## Documentation

- [Documentation index](docs/README.md)
- [Client guide](docs/CLIENT_USER_GUIDE.md)
- [Administration and troubleshooting](docs/ADMIN_AND_TROUBLESHOOTING_GUIDE.md)
- [Monitoring and maintenance](docs/MAINTENANCE_PLAN.md)
- [Executive report](EXECUTIVE_REPORT.md) and [demo script](DEMO_SCRIPT.md)
- [Website API](day7/web_api/README.md) and [frontend](day7/web_frontend/README.md)
- [VAPI integration](day7/vapi_integration/README.md) and [offline ML](day7/ml/README.md)
- [Day 3 agent](day3/README.md), [Day 4 workflows](day4/README.md), and [Day 5 graph](day5/README.md)
