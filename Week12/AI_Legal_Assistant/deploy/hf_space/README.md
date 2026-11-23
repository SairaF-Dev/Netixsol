---
title: Khan & Associates Legal Assistant
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Cited answers from Pakistani law, contract review, drafting
---

# Khan & Associates: AI Legal Assistant

> Capstone project (Netixsol AI engineering, Week 12). "Khan & Associates" is a fictional firm used for the
> demo; this is not the website of any real law firm, and the contracts and client matters are samples.

A research and contract assistant over a corpus of Pakistani statutes (English and Urdu) and 225 Supreme Court
and Lahore High Court judgments:

* **Research**: answers in English, Urdu or Roman Urdu with citations checked against the source text, and a
  second check that the conclusion follows from the sources; no verified source, no answer.
* **Case law**: a knowledge graph of judgments, provisions and judges (Neo4j).
* **Contract review, comparison and drafting**: firm-playbook review with a Word file of margin comments,
  version redlines with legal impact, and drafts marked "DRAFT - for lawyer review".
* **Security**: sign-in, client-matter access control, prompt-injection screening of uploads, PII-masked
  logs and a tamper-evident audit log.

Sign-in is required; demo accounts are given with the project submission. Every output is research
assistance for a lawyer to check, not legal advice.

This Space runs the app in one container (worker inside the web process, vector search in memory, graph on
Neo4j AuraDB). The full deployment - API, worker, Qdrant and Neo4j as separate services - is the
`docker-compose.yml` in the project repository. Uploads and the audit log live on the Space's temporary disk
and are reset when the Space restarts.

Secrets (Space settings): `LLM_API_KEY`, `APP_SECRET`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.
