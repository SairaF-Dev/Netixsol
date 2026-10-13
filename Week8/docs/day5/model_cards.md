# Model cards

## Sale valuation — Huber LightGBM

- **Purpose:** Estimate asking-price reference values for supported For Sale listings.
- **Target / output:** `log1p(price)` during fitting; API output is PKR.
- **Training source:** Cleaned Zameen property listings. The active model uses observed listing fields and excludes the dataset's simulated property-condition and amenity features.
- **Locked test:** MAPE 17.17%, MdAPE 10.75%, MAE PKR 3,980,731, RMSE PKR 12,541,322, R² 0.8839 (18,989 listings; observed-feature model).
- **Limitations:** Overall MAPE exceeds the project target (<15%); low-priced listings and some property types show higher relative error. This is an estimate, not a formal appraisal. OOD inputs are rejected.
- **Explanation:** TreeSHAP local contributions are in log-price units. They describe direction and relative model contribution, not PKR adjustments or causal effects.
- **Intended use:** Agent decision support in the five supported cities; review comparables and property condition before quoting.

## Rental valuation — Huber LightGBM

- **Purpose:** Estimate monthly rent for supported For Rent listings.
- **Target / output:** `log1p(price)` during fitting; API output is monthly PKR.
- **Training source:** Cleaned Zameen property listings. The active model uses observed listing fields and excludes the dataset's simulated property-condition and amenity features.
- **Locked test:** MAPE 16.96%, MdAPE 11.25%, MAE PKR 18,525, RMSE PKR 64,653, R² 0.7979 (9,621 listings; observed-feature model).
- **Limitations:** Overall MAPE exceeds the project target (<15%); some market segments have higher error. Estimate only; OOD inputs are rejected.
- **Explanation:** TreeSHAP local contributions are in log-price units, not rent-value changes in PKR.
- **Intended use:** Agent decision support in the five supported cities, with human review.

## Lead scoring — Optuna-tuned LightGBM

- **Purpose:** Rank inbound inquiries and recommend Hot/Warm/Cold follow-up.
- **Target:** Binary `converted` class.
- **Training source:** 5,000 generated synthetic leads; no real CRM sale/rent outcome labels were present in Week 7 or Week 8. Week 7 stores interaction actions and appointment lifecycle statuses, not closed-transaction outcomes.
- **API provenance:** Responses include `training_label_provenance="synthetic"` and `crm_validated=false`.
- **Locked test:** PR-AUC 0.6055, ROC-AUC 0.8671, Precision@Top-20% 58.0%, Top-20% lift 2.67×, Brier score 0.1263.
- **Limitations:** Synthetic labels and simulated behaviors do not establish performance on actual Week 7 customers. Tiers are operational suggestions, not guarantees. Monitor by lead source, city and budget segment.
- **Explanation:** TreeSHAP plus UrduLish rationale; subgroup results are descriptive and do not prove absence of bias.
- **Intended use:** Demonstrations and agent prioritization only until calibrated against consented, quality-checked CRM outcomes.

## Promotion and rollback policy

Candidates must be compared with the active model on the same purpose-specific validation data. A candidate is promoted only when its validation MAPE is strictly lower; the pre-promotion model and preprocessor pair are backed up together. A lower MAPE does not automatically make the model production-ready: the test target, domain review and data provenance requirements still apply.
