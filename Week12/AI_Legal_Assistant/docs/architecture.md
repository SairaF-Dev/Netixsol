# Architecture

The AI Legal Assistant answers legal questions from Pakistani statutes and judgments with checked citations,
explores case law as a knowledge graph, and reviews, compares and drafts contracts. This page shows how
the parts fit together. The diagrams are written in Mermaid, which GitHub draws as pictures.

## 1. The system at a glance

```mermaid
flowchart LR
    U["Lawyer's browser<br/>web/static (HTML, CSS, JS)"]

    subgraph API["Web app and API - web/server.py (FastAPI)"]
        AUTH["Sign-in, tokens,<br/>matter access checks"]
        ROUTES["Research, Case law, Review,<br/>Compare, Draft, Upload, Rating"]
        SCAN["Upload screening<br/>(prompt injection, hidden text)"]
    end

    subgraph JOBS["Background jobs"]
        Q[("Job queue<br/>SQLite")]
        W["Worker<br/>review, compare, drafts,<br/>indexing uploads"]
    end

    subgraph SEARCH["Retrieval"]
        BM25["BM25 keyword index"]
        VEC[("Vector index<br/>SQLite in memory, or Qdrant")]
        MODELS["Embedding model + reranker<br/>(ONNX Runtime, on the server)"]
    end

    GEM["Gemini<br/>(answers, reviews, drafts)"]
    NEO[("Neo4j knowledge graph<br/>cases, sections, judges")]
    AUDIT[("Audit log<br/>hash-chained")]

    U -- "HTTPS + sign-in token" --> AUTH
    AUTH --> ROUTES
    ROUTES -- "uploads" --> SCAN
    ROUTES -- "long tasks" --> Q
    Q --> W
    ROUTES -- "questions" --> SEARCH
    W --> SEARCH
    BM25 --- MODELS
    VEC --- MODELS
    ROUTES --> GEM
    W --> GEM
    ROUTES -- "case-law questions" --> NEO
    AUTH -. "every action" .-> AUDIT
    W -. "every action" .-> AUDIT
```

**The rule behind the design:** the language model never decides on its own what the law is. Search finds the
sources, Gemini writes from those sources only, and plain code then checks every citation against the
source text before anything reaches the lawyer.

## 2. What happens when a lawyer asks a question

```mermaid
sequenceDiagram
    autonumber
    actor L as Lawyer
    participant S as web/server.py
    participant R as Router
    participant H as Hybrid search + reranker
    participant G as Gemini
    participant V as Citation verifier (code)
    participant C as Conclusion check (Gemini)

    L->>S: POST /api/ask with the question
    S->>S: check token, log the question (personal data masked)
    S->>R: vector, graph or both?
    R-->>S: "vector"
    S->>H: search, only passages this user may see
    H-->>S: top 5 passages (public law + the user's own matters)
    S->>G: answer ONLY from these 5 passages, with exact quotes
    G-->>S: short answer, explanation, citations
    S->>V: is each quote really in its passage?
    V-->>S: unverified citations removed (none left, so "No sufficient source found")
    S->>C: does the conclusion follow from the sources?
    C-->>S: supported / partly / not supported (one redraft, then withheld)
    S-->>L: answer + verified citations + check result
```

Case-law questions ("which judges...", "which cases cite...") go to the knowledge graph instead: known question
shapes use ready-made queries, and anything else is translated to a Cypher query by Gemini. That query is
refused unless it is read-only and touches only public node types (Case, Section, Act, Judge, Court, Party).

## 3. What happens when a contract is uploaded

```mermaid
flowchart TD
    A["Lawyer uploads a contract<br/>(PDF, Word, text or JSON) to one of their matters"] --> B{"On this matter?"}
    B -- no --> X1["403, logged"]
    B -- yes --> C["Parse into numbered clauses"]
    C -- "damaged file" --> X2["400: could not be read"]
    C --> D{"Scanner: text addressed to an AI?<br/>hidden white / tiny / off-page text?"}
    D -- "instruction found" --> X3["422 blocked, the clause named,<br/>logged as 'blocked'"]
    D -- clean --> E["Filed on the matter"]
    E --> F["Job: embed the clauses,<br/>add to BM25 + vector index"]
    F --> G["Searchable in Research and Review,<br/>only for people on that matter"]
```

If an instruction slips past the scanner, a second defence remains: in every review and comparison prompt the
contract text sits inside `<contract_text>` tags, and the model is told that text there is data to review,
never instructions. The red team switched the scanner off and sent 12 kinds of injection through real
reviews: none changed a rating (`evaluations/red_team_report.md`).

## 4. Who can see what

```mermaid
flowchart LR
    subgraph PUBLIC["Public law (everyone)"]
        ST["53 statutes<br/>(13 English, 40 Urdu)"]
        JU["225 judgments<br/>Supreme Court, Lahore High Court"]
    end
    subgraph M1["MAT-001, MAT-002"]
        C1["Pak Telecom:<br/>20 contracts + version pair"]
    end
    subgraph M3["MAT-003, MAT-004"]
        C3["CUAD clients:<br/>53 contracts"]
    end
    AY["ayesha (associate)"] --> PUBLIC
    AY --> M1
    BI["bilal (associate)"] --> PUBLIC
    BI --> M3
    SA["sana (partner) and admin"] --> PUBLIC
    SA --> M1
    SA --> M3
```

The same check (`src/security/access.py`) is applied everywhere a document can come out: search results,
reviews, comparisons, Word downloads, job results, the contract lists and graph queries. A document on
another matter gives "404 not found", so a user cannot even learn that it exists.

## 5. Two ways to deploy

```mermaid
flowchart LR
    subgraph DOCKER["Docker Compose"]
        direction TB
        D1["api"] --- D2["worker"]
        D1 --- D3[("qdrant")]
        D1 --- D4[("neo4j")]
        D5["bootstrap (runs once):<br/>loads Qdrant, Neo4j, accounts"] -.-> D3
        D5 -.-> D4
    end
    subgraph CS["Codespace (live link)"]
        direction TB
        E1["one process:<br/>web app + worker thread,<br/>vectors in memory"] --- E2[("Neo4j AuraDB<br/>(cloud)")]
    end
```

Both run the same code; switches are environment variables (`WORKER_MODE`, `VECTOR_BACKEND`, `NEO4J_URI`).
Search results are identical on Qdrant and in memory (same top passage on 25/25 test questions). Details:
`docs/deployment.md`.

## 6. Components and where they live

| Part | What it does | Code |
|---|---|---|
| Web app | Pages, sign-in, all endpoints | `web/server.py`, `web/static/` |
| Security | Tokens, passwords, matter access, PII masking, audit log, injection scanner | `src/security/` |
| Jobs | Queue (SQLite), worker, the job handlers | `src/jobs/` |
| Ingestion | Collect PDFs, OCR Urdu scans, parse | `src/ingestion/`, `src/extraction/` |
| Chunking + indexing | Section-level chunks, BM25, vector store, Qdrant sync, ONNX models | `src/chunking/`, `src/indexing/` |
| Research | Retrieval configurations, answer generation, citation verifier, conclusion check, router | `src/rag/` |
| Knowledge graph | Extraction of cases, sections, judges and their links; loading Neo4j; GraphRAG | `src/graph/` |
| Contracts | Clause classification, playbook review, version comparison, drafting | `src/contracts/` |
| Operations | First-start bootstrap, health checks | `src/ops/`, `web/server.py` |
| Evaluation | Every report and the scripts that produce them | `evaluations/` |
| Deployment | Dockerfile, docker-compose.yml, Codespace setup, CI | `Dockerfile`, `deploy/`, `../../.devcontainer/legal-assistant/`, `../../.github/workflows/` |

## 7. Data

| Data | Size | Where |
|---|---|---|
| Statutes, judgments, contracts as structured JSON | 351 files | `data/structured/` (in git) |
| Search index: 11,232 passages, BM25 + 384-number vectors | ~270 MB | `data/indices/` (not in git; built with `python main.py --index`) |
| Knowledge graph: 1,649 cases, sections, judges and links | CSV files | `data/graph/` (in git), loaded into Neo4j |
| Saved Gemini answers (so repeated questions cost nothing) | cache | `data/llm_cache/` (not in git) |
| Accounts (password hashes), matters, audit log, uploads, jobs | small | `data/security/`, `data/web_outputs/`, `data/jobs/` (never in git) |

## 8. Main design decisions

| Decision | Why |
|---|---|
| Section-level chunks (one legal provision per passage) | A citation then points to exactly one section; Day 1 compared three chunking strategies. |
| Hybrid search (BM25 + vectors) + a multilingual reranker | Keyword search finds exact section numbers, vectors find meaning across English, Urdu and Roman Urdu; the reranker puts the best passage first (Day 2 comparison of 8 configurations). |
| Citations checked by code, not by the model | A quote is accepted only if it is really in the cited passage; the answer is refused when nothing survives. |
| A second model call checks the conclusion | A correct quote can still be stretched into a wrong conclusion; the check catches that and redrafts once. |
| Graph for case-law relationships | "Which cases cite X" is a path question that vector search answers poorly (Day 3: vector vs graph vs hybrid). |
| Long tasks as background jobs | A review takes 20-60 s; the page stays responsive and a separate worker container can do the work. |
| ONNX Runtime instead of PyTorch on servers | Same vectors and rankings, 2.68 GB image instead of 4.41 GB, 1.7 GB memory instead of 2.5 GB. |
| Refuse by default | "No sufficient source found" is a correct answer; inventing law is the worst failure for a law firm. |
