# Knowledge Base Schema

The Day 2 knowledge base separates exact business facts from semantic
documents.

## Structured datasets

- `properties.csv` — core property records.
- `prices.csv` — verified prices and transaction types.
- `locations.csv` — normalized areas and cities.
- `amenities.csv` — property-level amenities.
- `schools.csv` — nearby/associated schools.
- `hospitals.csv` — nearby/associated hospitals.
- `payment_plans.csv` — payment-plan information.
- `developers.csv` — developer/project information.
- `faqs.csv` — frequently asked questions.

## Source of truth policy

For production use, prices and availability must come from the
authoritative company database or API. The included records are demo
data for the capstone and should not be presented as live market data.

## Design rule

Structured data is used for exact values such as price, availability,
bedrooms and property identifiers. RAG is used for brochures,
descriptions and semantic FAQ retrieval.
