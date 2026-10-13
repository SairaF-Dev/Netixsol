# Week 8 Capstone: AI Property Valuation & Lead Scoring Platform for Real Estate

**Client:** Real Estate Agency (UrduLish Voice Agent Integration)  
**Objective:** A production-ready Machine Learning platform that predicts fair market prices for real estate properties across **BOTH Capital Sale and Rental Yield** valuations (Dual Regression Models), and scores inbound sales leads by conversion probability (Classification), with explainable AI and UrduLish voice/chat integration.

---

## 1. Valuation Engine Architecture (Sale & Rent)

The property valuation platform explicitly supports both purchase and rental queries through a dedicated dual-model routing architecture:

```
                         Incoming Property Valuation Query
                                         │
                                         ▼
                                  Check `purpose`
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
          `purpose = For Sale`                           `purpose = For Rent`
                 │                                               │
                 ▼                                               ▼
     Sale Preprocessing Pipeline                    Rent Preprocessing Pipeline
                 │                                               │
                 ▼                                               ▼
      Sale Valuation Regressor                       Rent Valuation Regressor
     (Predicts Capital Value PKR)                  (Predicts Monthly Rent PKR)
                 │                                               │
                 ▼                                               ▼
      Fair Market Purchase Price                     Fair Market Monthly Rent
      (Point Estimate + Range)                       (Point Estimate + Range)
```

### Why a Single Pooled Model is Scientifically Rejected:
1. **Target Magnitude Divergence:** Sale prices have a median of PKR 13,500,000 (mean ~PKR 24.7M), whereas rental prices have a median of PKR 45,000 (mean ~PKR 91.2k) — a ~300× scale difference.
2. **Heteroscedasticity:** Pooling both targets into a single regression model with a dummy variable would cause residual errors in sale prices ($\pm \text{PKR } 2\text{M}$) to completely overwhelm the entire dynamic range of rental prices ($10\text{k}\text{--}200\text{k}$ PKR).
3. **Distinct Structural Demand:** Houses comprise 62% of sales but only 39% of rentals. Upper/Lower Portions and Flats comprise 59% of rental inventory, reflecting fundamentally distinct market drivers.

---

## 2. Datasets & Provenance

### Dataset A — Property Listings (Dual Regression)
- **Source:** Zameen.com Property Data Pakistan (Kaggle: `huzzefakhan/zameencom-property-data-pakistan`).
- **Raw Volume:** **190,904 listings × 31 columns** (includes 14 empty Kaggle export columns). Immutable in `data/raw/Property.csv`.
- **Total Cleaned Dataset:** **190,827 listings × 44 columns** (`data/processed/properties_clean.csv`).
  - **For Sale Subset:** **126,666 listings** (`data/processed/properties_sale_clean.csv`, price floor: PKR 50,000).
  - **For Rent Subset:** **64,161 listings** (`data/processed/properties_rent_clean.csv`, price floor: PKR 1,000).
- **Features:** Plot size (`area_marla`), 15 synthetic domain features (age, floors, corner, amenities, transit distances), temporal quarters/seasons, structural ratios, and locality tiers.

### Dataset B — Inbound Lead Scoring (Classification)
- **Source:** Calibrated behavioral simulator (`src/data/generate_leads.py`, `RANDOM_STATE = 42`).
- **Volume:** **5,000 records × 22 columns** (`data/processed/leads_clean.csv`).
- **Target Variable:** `converted` (Binary: 1 = Deal closed, 0 = Lost).
- **Class Balance:** **21.8% converted (1,090) vs 78.2% lost (3,910)**.
- **Conversion Formulation:** Latent logistic model conditioned on on-site visit confirmations, call volume, budget-to-market affordability ratios, and sales agent response times.

---

## 3. Repository Directory Structure

```text
week8-real-estate-ml/
│
├── data/
│   ├── raw/
│   │   ├── Property.csv                        # Raw Zameen.com listings (190,904 rows)
│   │   ├── leads_raw.csv                       # Raw synthetic leads (5,000 rows)
│   │   └── archive/                            # Benchmark archives
│   ├── interim/
│   │   ├── properties_interim.csv              # 190,887 rows (Sale + Rent preserved)
│   │   └── leads_interim.csv                   # 5,000 rows
│   ├── processed/
│   │   ├── properties_clean.csv                # 190,827 rows (Sale + Rent cleaned)
│   │   ├── properties_sale_clean.csv           # 126,666 For Sale listings (>= 50k PKR)
│   │   ├── properties_rent_clean.csv           # 64,161 For Rent listings (>= 1k PKR)
│   │   ├── leads_clean.csv                     # 5,000 cleaned leads (21.8% conversion)
│   │   ├── prop_train.csv / val / test         # Unified 70/15/15 property splits
│   │   ├── prop_sale_train.csv / val / test    # Dedicated For Sale 70/15/15 splits
│   │   ├── prop_rent_train.csv / val / test    # Dedicated For Rent 70/15/15 splits
│   │   └── lead_train.csv / val / test         # Stratified 70/15/15 lead splits
│   └── dictionaries/
│       ├── dataset_a_data_dictionary.csv       # 44 columns documented
│       └── dataset_b_data_dictionary.csv       # 22 columns documented
│
├── notebooks/
│   └── day1/
│       ├── 01_data_understanding.ipynb         # Profiling & target divergence
│       ├── 02_data_cleaning.ipynb              # Purpose-specific cleaning & hygiene
│       ├── 03_eda.ipynb                        # 17 interactive visualizations & insights
│       ├── 04_feature_engineering.ipynb        # Synthetic augmentation & derived ratios
│       └── 05_preprocessing_split.ipynb        # Leakage-free pipelines & encodings
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── load_data.py                        # Raw data loading & checks
│   │   ├── clean_properties.py                 # Purpose-aware property cleaning
│   │   ├── clean_leads.py                      # Leads cleaning pipeline
│   │   └── generate_leads.py                   # Calibrated leads generator
│   ├── features/
│   │   ├── __init__.py
│   │   ├── property_features.py                # Dual property pipelines & ColumnTransformer
│   │   └── lead_features.py                    # Lead features & ColumnTransformer
│   └── utils/
│       ├── __init__.py
│       └── validation.py                       # Automated verification assertions
│
├── reports/
│   ├── figures/
│   │   └── day1/                               # 17 PNG figures (A1-A10, B1-B7)
│   └── day1/
│       ├── cleaning_report.md                  # Detailed cleaning audit (Sale & Rent)
│       ├── eda_insights.md                     # 17 chart business insights
│       ├── feature_engineering_report.md       # Formulas, justifications & leakage
│       └── leakage_report.md                   # Strict target leakage audit
│
├── docs/
│   └── day1/
│       ├── current_work_audit.md               # Re-audit establishing dual-model scope
│       ├── dataset_a_documentation.md          # Dataset A specification (Sale & Rent)
│       ├── dataset_b_documentation.md          # Dataset B specification
│       ├── dataset_a_column_plan.csv           # 44-column action plan
│       └── day1_completion_report.md           # Master completion report
│
├── tests/
│   └── test_day1_pipeline.py               # Automated pytest suite (25 unit tests)
│
├── run_day1_pipeline.py                        # Master pipeline execution script
├── run_eda.py                                  # Master EDA visualization runner
├── requirements.txt                            # Pinned dependencies
├── README.md                                   # Production README
└── .gitignore                                  # Git exclusions
```

---

## 4. How to Reproduce Day 1

```bash
# Clone and navigate to workspace
cd e:/Netixsol/Week8

# Install dependencies
pip install -r requirements.txt

# Run the master pipeline (cleaning, feature engineering, splitting, pipeline fitting)
python run_day1_pipeline.py

# Generate all 17 EDA figures and Markdown report
python run_eda.py

# Run the automated pytest suite (25 unit tests)
pytest tests/test_day1_pipeline.py -v
```

---

## 5. Key Day 1 Findings & Insights

1. **Sale vs Rent Divergence:** Rent and Sale follow distinct price dynamics (median PKR 45k vs PKR 13.5M). They require dedicated models.
2. **Log-Normality:** Both Sale and Rental prices transform into symmetric bell curves under $\log_{10}$ scaling, making log-scale regression mandatory.
3. **Site Visits Drive Conversions:** Leads who complete an on-site visit convert at 51.4%, compared to 3.6% for those who do not (+47.8pp lift).
4. **Strict Leakage Prevention:** `price_per_marla` is strictly quarantined for EDA; high-cardinality locality encoders are fitted **strictly on the training fold**.

---

## 6. Current Completion Status

- **Day 1 (Data Understanding, Cleaning, EDA, Feature Engineering & Preprocessing):** **100% COMPLETE & VERIFIED**
- **Day 2 (Dual Sale/Rent Valuation):** Implemented and tested; after removing simulated listing features, locked-test MAPE is 17.17% for Sale and 16.96% for Rent. Both remain above the PDF target of <15%.
- **Day 3 (Lead Scoring, Personas & Lead SHAP):** Implemented and tested; test PR-AUC is 0.6055 and Precision@Top-20% is 58.0%. Training leads are synthetic.
- **Day 4 (API, Assistant, Week 7 Integration & Explainability):** Implemented and tested; price and lead explanations return TreeSHAP attributions. Valuation reports include global summary plots and local waterfalls; price contributions are explicitly described on log-price scale. Week 7 labels generated Week 8 leads as simulated.
- **Day 5 (Monitoring, Retraining & Deployment):** Monitoring, validation-gated promotion, rollback, Docker configuration and handover documentation are implemented. The Docker image has not been built in this environment because no container engine is installed. Operations must provide refreshed, labeled data before scheduled retraining.

Run the focused suites from the Week 8 project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_day1_pipeline.py tests\test_day2_valuation.py tests\test_day3_lead_scoring.py tests\test_day4_agent.py tests\test_day4_api.py tests\test_day5_guardrails.py tests\test_day5_mlops.py -q
```

Day 5 operations and deployment instructions are in [`docs/day5/operations.md`](docs/day5/operations.md), with a dedicated [Railway Free guide](docs/day5/railway_free_deployment.md); model limitations and metrics are in [`docs/day5/model_cards.md`](docs/day5/model_cards.md). The system diagram and sales-agent guide are in [`docs/day5/architecture.md`](docs/day5/architecture.md) and [`docs/day5/sales_agent_guide.md`](docs/day5/sales_agent_guide.md). Validation-only valuation tuning results are recorded in [`reports/day5/valuation_accuracy_experiments.md`](reports/day5/valuation_accuracy_experiments.md).

The serving Docker image installs only inference dependencies from `requirements-api.txt`; the full `requirements.txt` remains available for development, testing, and model training.


