# ShopKaro — Technical Documentation

This directory hosts system architecture blueprints, data dictionaries, model cards, and API specifications.

---

## Directory Organization

```
docs/
├── architecture/           # System design diagrams, data flow pipelines, and ADRs
├── data_dictionary/        # Schemas and definitions for RetailRocket, Olist, and synthetic data
├── model_cards/            # Standardized model cards documenting assumptions, metrics, and limits
├── api/                    # OpenAPI specifications, endpoint contracts, and usage examples
└── README.md               # Documentation guide (this file)
```

---

## Documentation Sections

1. **System Architecture (`docs/architecture/`):**
   - High-level multi-tier architecture diagrams (data ingestion, batch & real-time inference, API gateway, UI).
   - Architectural Decision Records (ADRs) explaining technical choices (e.g., DuckDB vs traditional RDBMS, BM25 + dense retrieval vs pure vector search).

2. **Data Dictionary (`docs/data_dictionary/`):**
   - Comprehensive column-level metadata, data types, value distributions, and constraints for all raw and processed entities.
   - Clear entity isolation boundaries between RetailRocket clickstreams and Olist order logs.

3. **Model Cards (`docs/model_cards/`):**
   - Follows standard AI Model Card guidelines: model intended use, evaluation datasets, benchmark metrics, bias checks, and known failure modes.

4. **API Documentation (`docs/api/`):**
   - Interactive OpenAPI/Swagger schemas exported from FastAPI.
   - Sample request payloads, authentication details, and response JSON schemas.

