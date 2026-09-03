# Sara Real Estate Voice Agent

Sara is a production-oriented AI voice agent for real-estate conversations. It
speaks natural UrduLish, remembers customer requirements, retrieves verified
property information, recommends suitable listings, handles objections, and
manages property-visit appointments through business workflows.

> Core rule: the language model interprets the customer; verified company data
> determines property facts and availability.

## Capabilities

- Incoming phone-call handling through VAPI
- Deepgram speech recognition and configurable voice synthesis
- Natural UrduLish conversation and multi-turn memory
- Buyer, renter, seller, commercial, and investor intent handling
- PostgreSQL retrieval for prices, availability, and structured property facts
- Vector RAG for FAQs, brochures, and project descriptions
- Requirement-based property recommendations
- Objection handling without unsupported claims or guaranteed returns
- Booking, rescheduling, and cancellation of property visits
- Calendar, email, CRM, and n8n workflow integration
- FastAPI services, health checks, structured validation, and logging
- Runtime off-topic, prompt-injection, private-data, and fake-action guardrails

## Architecture

```text
Caller
  │
  ▼
VAPI telephony
  ├── Speech-to-text
  └── Text-to-speech
  │
  ▼
Day 7 FastAPI webhook
  │
  ├── Runtime guardrails
  ├── Per-call session management
  └── Tool-call validation
  │
  ▼
Day 3 conversational agent / Day 5 LangGraph design
  ├── Intent and constraint extraction
  ├── Context memory
  ├── RAG and structured retrieval
  ├── Recommendation and objection handling
  └── Appointment routing
  │
  ├── Day 2 PostgreSQL + vector knowledge layer
  └── Day 4 calendar, email, CRM, and n8n workflows
```

## Repository layout

| Path | Purpose |
|---|---|
| `day1/` | Architecture, conversation flows, UrduLish persona, voice evaluation, and system prompt |
| `day2/` | Knowledge base, RAG, PostgreSQL retrieval, recommendation engine, and grounding evaluation |
| `day3/` | Conversational agent, memory, voice pipeline, APIs, UI, and human/latency evaluation |
| `day4/` | Appointment API, Calendar/email/CRM services, and n8n automation |
| `day5/` | LangGraph state, nodes, tools, validation, and orchestration design |
| `day7/vapi_integration/` | VAPI webhook, live-call sessions, runtime tools, guardrails, and deployment integration |

Day 6 security and evaluation work is represented by tests and evaluation
artifacts across the modules rather than a separate `day6/` directory.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL
- A VAPI account and phone number for live calls
- API credentials for the selected LLM, STT, TTS, Calendar, and email providers
- n8n for the optional workflow automation path
- Docker for containerized deployment

Do not commit populated `.env` files, API keys, OAuth credentials, recordings,
or customer data.

## Configuration

Each service owns its environment configuration. Start from the corresponding
`.env.example` where available:

```powershell
Copy-Item day2/.env.example day2/.env
Copy-Item day3/.env.example day3/.env
```

For Day 7, create `day7/vapi_integration/.env` and configure the values required
by your selected providers. Common settings include:

```env
VAPI_API_KEY=
VAPI_WEBHOOK_SECRET=
VAPI_SERVER_URL=
DAY4_API_URL=http://localhost:8004
DATABASE_URL=
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
FISH_AUDIO_API_KEY=
N8N_WEBHOOK_URL=
```

`VAPI_WEBHOOK_SECRET` should always be configured outside local development.
When it is set, webhook requests must provide the matching `x-vapi-secret`
header.

## Installation

Install each independently deployable Python service in its own virtual
environment. For example:

```powershell
cd day7/vapi_integration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Day-specific installation and database initialization details are available in:

- [Day 2 knowledge layer](day2/README.md)
- [Day 3 conversational agent](day3/README.md)
- [Day 4 business workflows](day4/README.md)
- [Day 5 orchestration](day5/README.md)
- [Day 7 VAPI integration](day7/vapi_integration/README.md)

## Running locally

Start the required infrastructure first, then run the application services in
separate terminals.

### 1. Appointment and workflow API

```powershell
cd day4
python -m uvicorn api.main:app --host 127.0.0.1 --port 8004
```

### 2. VAPI webhook server

From the `day7` directory so the `vapi_integration` package is importable:

```powershell
cd day7
python -m uvicorn vapi_integration.webhook_server:app --host 0.0.0.0 --port 8007
```

Check service health:

```powershell
Invoke-RestMethod http://localhost:8007/health
```

For live VAPI calls, expose port `8007` through an HTTPS endpoint, set
`VAPI_SERVER_URL`, and register or update the assistant using the scripts under
`day7/vapi_integration/scripts/`.

## Runtime guardrails

Every caller transcript is checked before intent classification, the LLM, RAG,
or business tools. The guardrail:

- redirects unrelated requests back to real estate;
- rejects attempts to override instructions or reveal prompts and secrets;
- refuses internal company, CRM, employee, and other-customer data requests;
- refuses fake or unauthorized appointment actions;
- checks security before domain relevance to catch mixed attacks;
- allows greetings and explicit context-dependent replies such as prices,
  selected options, dates, and times;
- fails closed for unknown substantive requests.

See the [guardrail evaluation](day7/vapi_integration/GUARDRAIL_EVALUATION.md)
for cases, results, performance, and limitations.

## Testing

Run module tests from the directory that contains the relevant Python package.
For the complete Day 7 runtime regression suite:

```powershell
cd day7
python -m pytest vapi_integration/tests -q
```

The focused guardrail, webhook, and PostgreSQL tool regression currently passes
77 tests. The guardrail evaluation contains 40 primary conversations covering
valid real-estate requests, off-topic requests, prompt injection, private-data
extraction, and fake actions.

Additional suites:

```powershell
cd day3
python -m pytest tests -q

cd ../day4
python -m pytest tests -q

cd ../day5
python -m pytest tests -q
```

Some integration tests require configured databases, provider credentials, or
running dependent services. Never use production customer records in tests.

## API entry points

| Service | Default URL | Purpose |
|---|---|---|
| Day 3 API | `http://localhost:8000` | Conversational and voice-agent interfaces |
| Day 4 API | `http://localhost:8004` | Appointment and workflow operations |
| Day 7 webhook | `http://localhost:8007/vapi/webhook` | VAPI events, transcripts, and tool calls |
| Day 7 health | `http://localhost:8007/health` | Liveness and active-session summary |

FastAPI-generated OpenAPI documentation is normally available at `/docs` for a
running service.

## Deployment notes

- Use HTTPS for all public endpoints.
- Store credentials in the deployment platform's secret manager.
- Restrict database and n8n access to trusted networks.
- Configure webhook authentication and rotate secrets regularly.
- Persist PostgreSQL and vector-store data outside disposable containers.
- Send structured logs and failure metrics to a monitoring service.
- Back up databases and test restoration periodically.
- Review guardrail false positives and false negatives using privacy-safe logs.

Deployment manifests still need environment-specific values and infrastructure
validation before this repository is used for a real client. The root
`docker-compose.yml` is currently only a placeholder; use the working Day 4
container configuration as a reference until an end-to-end root deployment is
defined.

## Documentation and reports

- [Executive report](EXECUTIVE_REPORT.md)
- [10-minute demo script](DEMO_SCRIPT.md)
- [Conversation evaluation](day6/CONVERSATION_EVALUATION.md)
- [Performance and integration report](day6/PERFORMANCE_AND_INTEGRATION_REPORT.md)
- [Client user guide](docs/CLIENT_USER_GUIDE.md)
- [Admin and troubleshooting guide](docs/ADMIN_AND_TROUBLESHOOTING_GUIDE.md)
- [Monitoring and maintenance plan](docs/MAINTENANCE_PLAN.md)
- [Audit summary](AUDIT_SUMMARY.md)
- [Action items](ACTION_ITEMS_DAYS_4-7.md)
- [VAPI retrieval audit](AUDIT_REPORT_VAPI_PROPERTY_RETRIEVAL.md)
- [Quick-start code snippets](QUICK_START_CODE_SNIPPETS.md)
- [System prompt](day1/05_system_prompt/system_prompt.md)
- [Day 3 architecture](day3/docs/architecture.md)
- [Day 4 API documentation](day4/docs/API_DOCUMENTATION.md)

## Known limitations

- Regex guardrails are a fast first layer, not a substitute for ongoing
  adversarial evaluation and least-privilege tool authorization.
- Live voice quality and latency depend on provider configuration and network
  conditions.
- Calendar, email, CRM, and n8n behavior must be validated with the target
  client's accounts before production launch.
- The root end-to-end Docker deployment, CI/CD pipeline, and production
  monitoring backend require environment-specific completion.
