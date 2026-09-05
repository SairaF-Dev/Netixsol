# Offline Recommendation Training

This package contains the Phase 4 offline pipeline and the Phase 5
development-only runtime scorer. The development
artifact is explicitly named `dev_property_ranker_v1.joblib` and must not be
treated as a production model.

## Data policy

The dataset joins `customer_interactions` to the latest
`customer_preferences` row and verified PostgreSQL property facts. Customer
IDs are used only for grouping and splitting. Names, email addresses, phone
numbers, transcripts, recordings, and customer IDs are not model features.

The binary label policy is:

- `liked` and `shortlisted`: positive (`1`)
- `rejected`: negative (`0`)
- `shown`, `viewed`, `appointment_booked`, and `appointment_cancelled`: ignored

One customer/property history produces one outcome. The conservative outcome
precedence is `rejected > liked > shortlisted`; therefore contradictory
feedback resolves to rejection instead of silently producing duplicate rows.

The current preference table stores only the latest profile. Reconstructing an
older interaction with today's preferences can introduce temporal leakage. The
future fix is now implemented for new events: each interaction carries a
preference and property snapshot. Older rows use the latest-profile fallback
and are marked accordingly.

## Features

Features are deterministic numeric values: exact city and area matches,
budget match, price difference and ratio, bedroom match and difference,
property-type match, purpose match, amenity match ratio, under-budget flag,
and matching-amenity count. Missing numeric values use `0.0`; an empty
requested-amenity set has neutral ratio `0.0`.

## Commands

From `day7`:

```powershell
python -m ml.train_model --artifact ml/models/property_ranker_v1.joblib
python -m ml.dev_generate_synthetic_interactions --output ml/dev_data/synthetic_interactions.json
python -m ml.report_data_quality --synthetic ml/dev_data/synthetic_interactions.json
python -m ml.train_model --input ml/dev_data/synthetic_interactions.json --artifact ml/models/dev_property_ranker_v1.joblib
```

The `--input` command is the only synthetic training path. It requires every
fixture row to contain `synthetic=true` and requires a development artifact
path containing `dev`; it never writes rows to PostgreSQL.

Identified customers accumulate real events through Sara's existing search and
feedback flow. Search records only verified properties actually presented;
explicit feedback records the referenced shown property. The development
generator reads verified property facts but writes only a local fixture and
never inserts synthetic rows into `customer_interactions`.

Training uses `GroupShuffleSplit` by customer with deterministic
`random_state=42`, followed by a balanced `LogisticRegression` in a
scikit-learn pipeline. The artifact contains the model, feature names,
metrics, coefficients, label policy, and split metadata. It is saved only
after both classes, grouped train/test splits, fitting, and evaluation pass.

Readiness defaults to at least 50 resolved outcomes and 10 customers. These
thresholds are configurable through `ml.readiness.readiness()`. Real and
synthetic counts are always reported separately.

The existing deterministic ranker remains the production baseline. Phase 4
does not replace it or perform an apples-to-apples ranking comparison because
the current interaction table has no impression-level candidate set or
ranking metric. That comparison belongs after sufficient reviewed data and a
runtime model interface exist.

## Phase 5 development service

`PropertyPreferenceModelService` supports three explicit modes and defaults to
`off`:

- `off`: deterministic ranking only; the artifact is not loaded
- `shadow`: score candidates and log comparison positions, but preserve deterministic order
- `active_dev`: reorder verified candidates by development-model probability

Use these exact PowerShell commands before starting Sara:

```powershell
# Production-safe baseline (also the default when the variable is missing)
$env:SARA_ML_RANKING_MODE = "off"

# Score and record non-PII comparisons; keep deterministic customer-facing order
$env:SARA_ML_RANKING_MODE = "shadow"

# Explicit synthetic development-model reordering
$env:SARA_ML_RANKING_MODE = "active_dev"

# Remove the override; the service defaults safely to off
Remove-Item Env:SARA_ML_RANKING_MODE -ErrorAction SilentlyContinue
```

The service requires
the synthetic-development metadata contract and falls back to deterministic
ranking on any load, feature, or prediction failure. It never queries
properties and never changes property facts. Shadow comparisons contain only
`property_id`, `deterministic_rank`, `ml_rank`, and `ml_probability`; they are
runtime diagnostics and are not persisted as PostgreSQL property facts or
customer-interaction labels.
