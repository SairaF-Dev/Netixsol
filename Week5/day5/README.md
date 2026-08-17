
# SRE Incident Investigation Agent

An AI-powered SRE incident investigation system that collects evidence from server logs, infrastructure metrics, and GitHub, analyzes incidents using an LLM, and keeps consequential actions behind a Human-in-the-Loop (HITL) approval checkpoint.

This project was developed for **Week 5 Day 5 CM-IT — Capstone: Production-Ready Agent System, Evaluation & Deployment**.

---

## 1. Project Overview

SRE teams often need to investigate incidents by checking multiple sources:

- Application/server logs
- Infrastructure metrics
- Database connection health
- Recent code changes

Doing this manually can be slow and inconsistent.

This project provides an AI-assisted investigation workflow that:

1. Receives an incident through a FastAPI endpoint.
2. Validates the incident request.
3. Collects evidence from multiple tools.
4. Queries local infrastructure metrics.
5. Reads service-specific server logs.
6. Checks recent GitHub commits.
7. Uses an LLM to analyze the collected evidence.
8. Produces a structured investigation result.
9. Applies safety checks.
10. Requires human approval before consequential remediation.

The system is designed so that the **LLM performs reasoning while application logic controls workflow, safety, and approval**.

---

# 2. Business Goal

The main business goal is to reduce the time required to investigate production incidents while maintaining operational safety.

The system aims to provide:

- Faster incident investigation
- Evidence-based root-cause analysis
- Consistent investigation workflows
- Reduced manual investigation effort
- Human oversight for consequential actions
- Measurable performance, cost, and safety

---

# 3. Architecture

```text
                         User / SRE
                             |
                             v
                    +------------------+
                    |     FastAPI      |
                    |       API        |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |    LangGraph     |
                    |     Workflow     |
                    +--------+---------+
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
       +-----------+   +-----------+   +-----------+
       | Server    |   |  SQLite   |   | GitHub    |
       | Logs      |   | Metrics   |   | API       |
       +-----------+   +-----------+   +-----------+
             |               |               |
             +---------------+---------------+
                             |
                             v
                    +------------------+
                    | Evidence Analysis|
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |   LLM Reasoning  |
                    |      / RCA       |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |   Safety Gate    |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    | Human Approval   |
                    |      HITL        |
                    +--------+---------+
                             |
                       +-----+-----+
                       |           |
                    Reject      Approve
                       |           |
                       v           v
                      End    Controlled Action
````

Architecture diagram:

```text
docs/system_diagram.png
```

---

# 4. Framework Choice

## LangGraph

LangGraph was selected because this problem is a **stateful, control-heavy workflow**.

The investigation requires:

* Multiple sequential investigation steps
* Shared workflow state
* Conditional transitions
* Tool execution
* Safety checks
* Human-in-the-loop approval

LangGraph provides explicit workflow control while allowing the LLM to focus on reasoning.

CrewAI was not selected because the primary requirement is workflow control and safety rather than role-based multi-agent collaboration.

### Design Principle

```text
LLM
 ↓
Reasoning

Application / Workflow Logic
 ↓
Control + Safety + HITL
```

---

# 5. Main Components

## FastAPI

File:

```text
app/main.py
```

Provides API endpoints for:

* Incident investigation
* Human approval

---

## LangGraph Agent

File:

```text
app/agent.py
```

Responsible for the investigation workflow, state management, tool usage, reasoning, and structured output.

---

## Server Log Tool

File:

```text
app/tools.py
```

Tool:

```text
fetch_server_logs
```

Reads:

```text
data/server.log
```

and returns log entries associated with the requested service.

---

## SQLite Metrics Tool

Tool:

```text
get_db_metrics
```

Database:

```text
data/local_metrics.db
```

Metrics include:

* CPU usage
* Memory usage
* Active database connections
* Maximum database connections
* Service status

SQL queries use parameterized inputs to reduce SQL injection risk.

---

## GitHub API Tool

Tool:

```text
check_github_commits
```

The tool calls the GitHub API and retrieves:

* Latest commit
* Commit SHA
* Author
* Commit date
* Commit message
* Changed files
* Additions
* Deletions

Repository format:

```text
owner/repository
```

The API request uses a timeout and handles request/HTTP errors.

---

# 6. Human-in-the-Loop

Consequential actions are not allowed to proceed automatically.

The workflow is:

```text
Incident
   |
   v
Investigation
   |
   v
Evidence Collection
   |
   v
LLM Analysis
   |
   v
Recommendation
   |
   v
Safety Check
   |
   v
Human Approval
   |
   +----------+
   |          |
 Reject     Approve
   |          |
   v          v
  End      Controlled
             Action
```

The approval endpoint is separated from the investigation endpoint.

This provides an explicit human checkpoint before consequential remediation.

---

# 7. Safety Features

The system includes:

* Input validation
* Required field validation
* Repository format validation
* Parameterized SQL queries
* GitHub API timeout handling
* Tool retry/fallback handling
* Safety checks
* Human approval
* Human rejection handling
* Unknown-service handling
* Adversarial-input testing
* Conflicting-evidence testing

---

# 8. Monitoring

Monitoring is implemented in:

```text
app/monitoring.py
```

The system records structured events containing information such as:

* Timestamp
* Event type
* Incident ID
* Tool activity
* Latency
* Errors
* Token usage
* Cost information when available

Monitoring documentation:

```text
docs/monitoring_checklist.pdf
```

Production monitoring should track:

* Error rate
* P95/P99 latency
* Cost per run
* Token usage
* Tool failure rate
* Output quality
* Safety failures
* HITL compliance
* Quality drift
* Cost drift

---

# 9. Cost Tracking

Cost tracking is implemented in:

```text
app/cost.py
```

The system calculates estimated LLM cost from input and output token usage.

Latest evaluation:

```text
Cost-measured tests : 7/13
Total LLM Cost      : $0.068356
Average Cost        : $0.009765/run
Input Tokens        : 157,584
Output Tokens       : 74,531
Total Tokens        : 232,115
```

Cost is only reported when token telemetry is available.

---

# 10. Evaluation

The project includes a formal evaluation framework:

```text
evaluation/evaluation.py
```

Run:

```powershell
python -m evaluation.evaluation
```

Latest evaluation result:

```text
Test Cases       : 13
Overall Score    : 129/130
Percentage       : 99.23%
Rating           : Excellent
Release Gate     : PASS
Safety Failures  : 0
HITL Failures    : 0
Perfect Tests    : 12
Partial Tests   : 1
Failed Tests    : 0
```

---

# 11. Evaluation Criteria

Each test is evaluated against:

1. Task Success
2. Evidence Grounding
3. Safety
4. HITL Compliance
5. Robustness

The evaluation also measures:

* Incident latency
* End-to-end latency
* Token usage
* Estimated LLM cost
* Failure patterns

---

# 12. Test Coverage

The evaluation contains 13 test cases covering:

* Normal incidents
* Unknown services
* Adversarial input
* Invalid input
* HITL rejection
* Large input
* Unicode input
* Unsafe remediation
* Conflicting evidence

Example categories:

```text
INC-001  Normal
INC-002  Normal
INC-003  Normal
INC-004  Unknown Service
INC-005  Adversarial
INC-006  Invalid
INC-007  HITL Rejection
INC-008  Normal
INC-009  Large Input
INC-010  Unicode
INC-011  Unknown Service
INC-012  Unsafe Remediation
INC-013  Conflicting Evidence
```

---

# 13. Performance Results

Latest evaluation:

| Metric                     | Result |
| -------------------------- | -----: |
| Average Incident Latency   | 2.207s |
| Maximum Incident Latency   | 4.312s |
| P95 Incident Latency       | 3.242s |
| P99 Incident Latency       | 4.098s |
| Average End-to-End Latency | 2.403s |
| Maximum End-to-End Latency | 4.507s |
| P95 End-to-End             | 3.462s |
| Latency Threshold          |  30.0s |
| Tests Within Threshold     |  13/13 |

---

# 14. Evaluation Failure Pattern

One partial case was identified:

```text
INC-011 — Unknown Service
Score: 9/10
```

Issue:

```text
The agent did not clearly state that the requested
service could not be verified/found.
```

This was a task-success communication issue.

There were:

```text
Safety failures : 0
HITL failures   : 0
Evidence failures : 0
Robustness failures : 0
```

### Recommended Fix

When no evidence exists for a requested service, the final output should explicitly include:

```text
Service Verification: NOT FOUND / UNVERIFIED
```

This prevents the agent from appearing to have successfully investigated a service when the service could not actually be verified.

---

# 15. Project Structure

```text
capstone_project/
│
├── .gitignore
├── README.md
├── requirements.txt
├── evaluation_results.json
│
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── cost.py
│   ├── database.py
│   ├── main.py
│   ├── monitoring.py
│   └── tools.py
│
├── data/
│   ├── local_metrics.db
│   └── server.log
│
├── docs/
│   ├── executive_report_sre_agent_.pdf
│   ├── monitoring_checklist.pdf
│   ├── SRE_Capstone_Presentation_.pptx
│   ├── system_design_and_framework_choice.pdf
│   └── system_diagram.png
│
├── evaluation/
│   └── evaluation.py
│
└── tests/
    ├── test_agent.py
    ├── test_llm_usage.py
    ├── test_tools.py
    └── test_tool_retry.py
```

---

# 16. Installation

## Clone the repository

```powershell
git clone <YOUR_REPOSITORY_URL>
cd capstone_project
```

## Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

## Install dependencies

```powershell
pip install -r requirements.txt
```

---

# 17. Environment Variables

Create a local `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

Never commit the real `.env` file.

A safe `.env.example` can be:

```env
OPENAI_API_KEY=
```

---

# 18. Initialize the Database

Run:

```powershell
python -m app.database
```

This creates:

```text
data/local_metrics.db
```

with the local server metrics used by the investigation tools.

---

# 19. Start the API

Run from the project root:

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 20. Run Tests

Tool tests:

```powershell
python -m tests.test_tools
```

LLM usage test:

```powershell
python -m tests.test_llm_usage
```

Retry/fallback test:

```powershell
python -m tests.test_tool_retry
```

API integration tests:

```powershell
python -m tests.test_agent
```

---

# 21. Run Formal Evaluation

First start the API:

```powershell
python -m uvicorn app.main:app --reload
```

Then in another terminal:

```powershell
python -m evaluation.evaluation
```

Results are saved to:

```text
evaluation_results.json
```

---

# 22. Deliverables

The `docs/` directory contains the stakeholder-facing deliverables:

### System Design

```text
system_design_and_framework_choice.pdf
system_diagram.png
```

### Monitoring

```text
monitoring_checklist.pdf
```

### Executive Report

```text
executive_report_sre_agent_.pdf
```

### Stakeholder Presentation

```text
SRE_Capstone_Presentation_.pptx
```

---

# 23. Production Improvements

Before production deployment, recommended improvements include:

## Scaling

* Persistent workflow state
* Centralized observability
* Production metrics backend
* Distributed deployment
* Concurrent incident processing

## Security

* API authentication
* Secret management
* Rate limiting
* Tool allowlists
* Stronger authorization
* Audit logging

## Guardrails

* Strict structured-output validation
* Fail-closed safety policies
* Evidence verification
* More adversarial testing
* Regression evaluation

## Human Oversight

* Maintain HITL for consequential actions
* Store approval identity
* Store approval timestamp
* Store proposed action
* Store final outcome

---

# 24. Final Evaluation Status

```text
========================================
SRE AGENT CAPSTONE
========================================

Overall Score      : 129/130
Percentage         : 99.23%
Rating             : Excellent
Release Gate       : PASS

Safety Failures    : 0
HITL Failures      : 0
Failed Tests       : 0
Perfect Tests      : 12/13

Average Latency    : 2.207s
P95 Latency        : 3.242s
========================================
```

---

# 25. Conclusion

This project demonstrates an end-to-end AI-assisted SRE incident investigation system combining:

* **LangGraph** for controlled workflow orchestration
* **LLM reasoning** for evidence analysis
* **SQLite** for infrastructure metrics
* **Server logs** for operational evidence
* **GitHub API** for recent code-change analysis
* **FastAPI** for deployment
* **Monitoring and cost tracking**
* **Formal evaluation**
* **Human-in-the-Loop safety controls**

The latest evaluation achieved **99.23% overall performance with zero safety and HITL failures**, while identifying one concrete improvement for clearer handling of unknown services.


