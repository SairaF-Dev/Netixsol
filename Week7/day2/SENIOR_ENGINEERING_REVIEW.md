# Senior Engineering Review — Week 7 Day 2

## Fixed critical issues

- Removed stale RAG project identities that did not match the canonical property database.
- Synchronized developer project names with `properties.csv`.
- Replaced hard-coded RAG metadata with metadata derived from the structured knowledge base.
- RAG document source paths are now portable relative paths.
- Chroma synchronization now deletes stale/removed sources and re-indexes changed metadata/content.
- Exact structured property facts are blocked from standalone RAG and must use PostgreSQL.
- Added policy-first routing so questions such as “What if a property is not available?” correctly route to FAQ/RAG instead of availability SQL.
- Rebuilt evaluation around canonical property names, source routing, refusal behavior, and expected evidence concepts.
- Added RAG document validation and developer-project consistency validation.
- Removed virtual environments, secrets, caches, generated Chroma stores, and stale evaluation output from the deliverable.

## Source-of-truth contract

**PostgreSQL:** price, availability, bedrooms/bathrooms, location, plot/covered area, developer, amenities, payment plans, schools/hospitals, agents, property IDs.

**RAG:** FAQs, semantic project descriptions, brochure summaries, and company/process knowledge.

RAG must fail closed when information is absent or when the question asks for an exact structured business fact.
