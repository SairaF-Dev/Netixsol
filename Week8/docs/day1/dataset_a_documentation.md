# Dataset A — Property Valuation Documentation (For Sale & For Rent)

**Project:** Week 8 Capstone — AI Property Valuation & Lead Scoring Platform for Real Estate  
**Component:** Dataset A (Property Valuation Dual-Model Engine)  
**Date:** 2026-09-29  

---

## 1. Dataset Provenance & Overview

| Attribute | Specification |
|---|---|
| **Dataset Title** | Zameen.com Property Data Pakistan |
| **Source Platform** | Kaggle (`huzzefakhan/zameencom-property-data-pakistan`) |
| **Data Nature** | Real-world property listings scraped from Zameen.com |
| **File Location** | `data/raw/Property.csv` (100% immutable raw source) |
| **Raw Dataset Dimensions** | **190,904 rows × 31 columns** |
| **Total Cleaned Dataset** | **190,827 rows × 44 columns** (`data/processed/properties_clean.csv`) |
| **For Sale Subset** | **126,666 rows** (`data/processed/properties_sale_clean.csv`) |
| **For Rent Subset** | **64,161 rows** (`data/processed/properties_rent_clean.csv`) |
| **Assignment Requirement** | Minimum 5,000 rows (exceeded by ~38×) |

---

## 2. Valuation Architecture: Dual-Model Routing

The platform explicitly supports **both Capital Asset Valuation (Sale Price)** and **Rental Yield Valuation (Monthly Rental Rate)**.

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

### Why Pooling Sale and Rent into a Single Model is Scientifically Rejected:
1. **Target Scale Divergence:** Sale prices have a median of PKR 13,500,000 (mean ~PKR 24.7M), while rental prices have a median of PKR 45,000 (mean ~PKR 91.2k) — a ~300× magnitude difference.
2. **Heteroscedasticity:** Residual errors in sale predictions ($\pm \text{PKR } 2\text{M}$) would completely overwhelm the entire dynamic range of rental prices ($10\text{k}\text{--}200\text{k}$ PKR).
3. **Divergent Structural Drivers:** Houses comprise 62% of sales but only 39% of rentals. Upper/Lower Portions and Flats comprise 59% of rental inventory, reflecting fundamentally distinct market demand realities.

---

## 3. Data Cleaning & Validation Rules

1. **Empty Export Columns:** 14 columns (`Unnamed: 17` to `Unnamed: 30`) containing $\le 8$ non-null values across 190k rows were stripped in interim data. Raw file untouched.
2. **Missing Purpose:** 17 records (<0.01%) missing `purpose` were dropped in interim data.
3. **Area Normalization:** Standardized text `area` (`"1 Kanal"`, `"10 Marla"`) into numeric `area_marla` ($1\text{ Kanal} = 20\text{ Marla}$). Original string retained.
4. **Coordinate Validation:** 10 coordinate pairs outside Pakistan bounding box ($20\text{--}38^\circ\text{N}$, $58\text{--}80^\circ\text{E}$) were set to `NaN` and flagged via `coord_valid = False`.
5. **Zero Bedrooms / Bathrooms:** Residential units (House, Flat, Portion, Penthouse) with 0 bedrooms (24,213) or 0 bathrooms (47,817) represent unrecorded data; imputed using median of `(property_type, city)` groups.
6. **Purpose-Specific Price Validation:**
   - **For Sale:** Enforced minimum price floor of **PKR 50,000** (removed 56 corrupt test records: 0, 1, 4, etc.). Upper IQR fence ($Q_3 + 3 \times IQR \approx 81.5\text{M}$ PKR) flagged with `price_outlier_flag` and retained.
   - **For Rent:** Enforced minimum rental floor of **PKR 1,000** (removed 4 corrupt test records: 0, 27, 40, 54 PKR). Legitimate hostel rooms (PKR 3,000–8,000) are fully preserved. Upper IQR fence ($Q_3 + 3 \times IQR \approx 250\text{k}$ PKR) flagged with `price_outlier_flag` and retained.

---

## 4. Column Schema (44 Columns)

### Original (17 columns)
- `property_id`: Integer ID (ID only; excluded from ML).
- `location_id`, `page_url`, `agency`, `agent`: Excluded from ML features.
- `property_type`, `city`, `province_name`: Categoricals (one-hot encoded).
- `location`: High-cardinality locality (frequency / target encoded).
- `latitude`, `longitude`: Validated numeric coordinates.
- `baths`, `bedrooms`: Cleaned & imputed numeric counts.
- `area`: Raw text area (transformed to `area_marla`).
- `purpose`: Router key (`For Sale` vs `For Rent`).
- `price`: Target variable in PKR (capital price or monthly rent).
- `date_added`: Temporal timestamp.

### Derived Features (12 columns)
- `area_marla`: Plot size in Marla.
- `price_per_marla`: Price divided by area (**STRICTLY EDA ONLY — TARGET LEAKAGE**).
- `coord_valid`: Coordinate QA flag.
- `listing_year`, `listing_month`, `listing_quarter`, `listing_season`: Temporal components.
- `price_outlier_flag`: Luxury segment QA flag.
- `property_age_bucket`: Binned age categories (`New`, `0-5yr`, `6-10yr`, `11-20yr`, `20+yr`).
- `bed_bath_ratio`: Accommodation density ratio (`bedrooms / baths`).
- `covered_area_ratio`: Structural density ratio (`covered_sqft / plot_sqft`).
- `society_tier`: Prestige tier (`Premium`, `Mid`, `Budget`).
- `location_frequency`: Neighborhood frequency in training fold (train-only).

### Synthetic / Augmented Features (15 columns)
- `property_age_years`: Gamma-distributed age (0–60 years) conditioned on property type.
- `floors`: Storeys count (1–3 for houses; 1–20 for flats/penthouses).
- `corner`, `park_facing`: Binary orientation indicators.
- `covered_area_sqft`: Realistic constructed footprint conditioned on plot size and coverage ratio.
- `parking`, `security`, `electricity_backup`, `gas`, `water_supply`, `park_nearby`: Binary infrastructure indicators.
- `amenity_score`: Composite integer score (0–6).
- `distance_main_road_km`, `distance_school_km`, `distance_hospital_km`: Exponential transit access distances.

---

## 5. Splitting Strategy (70 / 15 / 15)

Data is split using purpose-stratified sampling:
- **Train (70%):** 133,578 listings (88,665 Sale + 44,913 Rent)
- **Validation (15%):** 28,624 listings (19,000 Sale + 9,624 Rent)
- **Test (15%):** 28,625 listings (19,001 Sale + 9,624 Rent)
- Dedicated purpose split files are also persisted in `data/processed/` for direct training of Day 2 models.
