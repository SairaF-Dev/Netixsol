# ShopKaro — Data Directory Guide & Governance

This directory manages all raw datasets, processed feature stores, and synthetic records used across the ShopKaro AI Commerce Intelligence Platform.

---

## Directory Organization

```
data/
├── raw/
│   ├── retailrocket/       # Unmodified raw CSV files from the RetailRocket dataset
│   └── olist/              # Unmodified raw CSV files from the Olist Brazilian E-Commerce dataset
├── processed/              # Cleaned, transformed, and feature-engineered datasets (Parquet/DuckDB)
├── synthetic/              # Clearly labeled synthetic records (Pakistani catalog, festival spikes)
└── README.md               # Data governance and ingestion documentation (this file)
```

---

## Data Placement & Rules

### 1. Raw Datasets (`data/raw/`)
- **Immutability Principle:** Original raw datasets must remain strictly unmodified in `data/raw/`. No in-place editing, manual filtering, or overwriting is permitted.
- **RetailRocket Files:** Place all RetailRocket CSV files (`category_tree.csv`, `events.csv`, `item_properties_part1.csv`, `item_properties_part2.csv`) inside:
  ```
  data/raw/retailrocket/
  ```
- **Olist Files:** Place all Brazilian E-Commerce CSV files (`olist_customers_dataset.csv`, `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_products_dataset.csv`, etc.) inside:
  ```
  data/raw/olist/
  ```

### 2. Processed Datasets (`data/processed/`)
- Contains datasets produced by reproducible data cleaning, normalization, deduplication, and feature engineering pipelines.
- Formats preferred: Compressed columnar files (e.g., Apache Parquet, DuckDB database files).
- Cleaned files should be generated solely via automated scripts in `scripts/` or pipeline modules in `src/shopkaro/data/`.

### 3. Synthetic Datasets (`data/synthetic/`)
- Contains generated Pakistani product catalogue records, regional localization data, and Ramadan/Eid festival promotional sales data.
- **Mandatory Labeling:** All synthetic records must be explicitly marked with provenance tags (`is_synthetic = True` or equivalent column indicators).
- **Prohibition on Misrepresentation:** Synthetic data must never be presented as real customer observations.

---

## Critical Data Provenance & Entity Isolation Warning

> [!CAUTION]
> **RetailRocket and Olist Datasets Must NOT Be Merged at the User ID Level**
> RetailRocket and Olist originate from completely distinct e-commerce platforms, geographic regions, and time periods.
> - **RetailRocket:** Clickstream event logs (view, addtocart, transaction) collected from an anonymous real-world e-commerce website.
> - **Olist:** Order fulfillment, logistics, marketplace merchant, and review data collected from Brazilian e-commerce operations.
> 
> User identifiers (`visitorid` from RetailRocket and `customer_id` / `customer_unique_id` from Olist) **do not share identities or entity mappings**. Under no circumstances should models or pipelines join these datasets assuming shared customer journeys or unified user profiles.

---

## Data Governance, Licensing & Version Control

1. **Version Control (`.gitignore`):**
   - Raw, processed, and synthetic data files must **never** be committed to Git.
   - Large binary or tabular datasets are excluded via `.gitignore`.
2. **Licensing & Usage:**
   - **RetailRocket Dataset:** Released for academic and research evaluation. Verify terms before commercial reuse.
   - **Olist Brazilian E-Commerce:** Released under the CC BY-NC-SA 4.0 license.
3. **Data Security & Privacy:**
   - Raw datasets do not contain unencrypted passwords or payment card details.
   - Always ensure adherence to standard data privacy practices during processing.

