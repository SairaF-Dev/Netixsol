# Dataset B — Lead Scoring Documentation

**Project:** Week 8 Capstone — AI Property Valuation & Lead Scoring Platform for Real Estate  
**Component:** Dataset B (Inbound Lead Scoring Classification)  
**Date:** 2026-09-29  

---

## 1. Overview & Provenance

| Attribute | Specification |
|---|---|
| **Dataset Title** | Real Estate Inbound Lead Scoring Dataset |
| **Generation Engine** | `src/data/generate_leads.py` |
| **Random Seed** | `RANDOM_STATE = 42` (exact reproducibility) |
| **Dataset Volume** | **5,000 records** (exceeds assignment minimum of 3,000) |
| **Target Variable** | `converted` (Binary: 1 = Deal closed / purchased, 0 = Lost) |
| **Class Distribution** | **3,910 negative (78.2%) vs 1,090 positive (21.8%)** |
| **Provenance Nature** | **Synthetic / Augmented** |

---

## 2. Realistic Generation Logic

Conversion probability is computed via a latent logistic model with Gaussian noise:

$$\text{logit} = \beta_0 + \sum \beta_i X_i + \epsilon, \quad \epsilon \sim \mathcal{N}(0, 0.3^2)$$
$$P(\text{converted} = 1) = \sigma(\text{logit}) = \frac{1}{1 + e^{-\text{logit}}}$$
$$\text{converted} \sim \text{Bernoulli}(P)$$

### Latent Coefficients ($\beta$):
- **Base Intercept ($\beta_0 = -6.0$):** Calibrated to yield a realistic baseline conversion rate of ~21.8%.
- **Visit Booked ($\beta = +2.5$):** On-site property inspection represents the highest customer commitment signal.
- **Engagement Calls ($\beta = +0.15$ per call):** Higher interaction frequency indicates serious intent.
- **Budget-to-Market Ratio:**
  - Budget match $> 0.80$: $\beta = +1.5$ (affords standard properties).
  - Budget match $> 1.00$: $\beta = +1.0$ (affords above-average properties).
  - Severe mismatch $< 0.50$: $\beta = -0.5$ (unrealistic budget vs target area).
- **Response Speed ($\beta = -0.003$ per minute):** Slower response times degrade buyer interest.
- **Follow-up Count ($\beta = +0.05$ per follow-up):** Consistent agent persistence improves pipeline velocity.
- **Lead Age Decay ($\beta = -0.008$ per day):** Leads older than 30–60 days exhibit natural pipeline decay.
- **Unresolved Objections ($\beta = -0.5$ if objection $\neq$ "None"):** Unresolved issues hinder closing.
- **Channel Effects:** Call ($+0.3$), WhatsApp ($+0.15$), Facebook ($-0.1$), Website ($+0.0$).
- **Purpose Effects:** Buy ($+0.2$), Invest ($+0.4$), Rent ($0.0$).

---

## 3. Column Schema (22 Columns)

### Base Attributes (15 features + 1 target)
1. `lead_id`: Unique identifier string (`L00001` to `L05000`) — excluded from ML features.
2. `lead_source`: Inbound acquisition source (`Call`, `WhatsApp`, `Facebook`, `Website`).
3. `budget_pkr`: Stated budget in PKR.
4. `preferred_city`: Target city (`Lahore`, `Karachi`, `Islamabad`, `Rawalpindi`, `Faisalabad`).
5. `preferred_location`: Target neighborhood / society (20 prominent localities).
6. `property_type`: Intended property type (`House`, `Flat`, `Upper Portion`, `Lower Portion`, `Penthouse`).
7. `purpose`: Client objective (`Buy`, `Rent`, `Invest`).
8. `number_of_calls`: Total telephone interactions logged (1–15).
9. `total_call_duration_min`: Cumulative duration across calls in minutes.
10. `response_time_minutes`: Speed of first contact in minutes.
11. `visit_booked`: Binary indicator (1 if property visit confirmed, 0 otherwise).
12. `days_since_first_contact`: Pipeline age in days (1–180).
13. `objection_raised`: Primary objection logged (`None`, `Budget`, `Price`, `Location`, `Timing`, `Financing`).
14. `follow_up_count`: Number of agent follow-up attempts.
15. `budget_match_ratio`: Client budget divided by city median market price.
16. `converted`: Target variable (0 = Not converted, 1 = Converted).

### Engineered Features (6 features)
17. `engagement_score`: Composite index (0–12) aggregating calls, duration, follow-ups, and visit status.
18. `avg_call_duration_min`: Total call minutes divided by total call count.
19. `lead_age_bucket`: Categorical lifecycle phase (`<1w`, `1w-1m`, `1m-3m`, `3m-6m`, `6m+`).
20. `lead_age_bucket_num`: Numeric ordinal lifecycle stage (1 to 5).
21. `response_speed_category`: Categorical response speed (`Fast (<30m)`, `Moderate (30m-3h)`, `Slow (>3h)`).
22. `follow_up_intensity`: Follow-up rate per day (`follow_up_count / days_since_first_contact`).

---

## 4. Stratified Splitting (70 / 15 / 15)

Data is split using stratified sampling on `converted`:
- **Train (70%):** 3,500 records (21.8% converted)
- **Validation (15%):** 750 records (21.9% converted)
- **Test (15%):** 750 records (21.7% converted)
