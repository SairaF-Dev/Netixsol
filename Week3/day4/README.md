# Advanced SQL Business Intelligence Pipeline
### Music Store Database (PostgreSQL)

---

## Project Overview

This project implements an end-to-end **Business Intelligence (BI) SQL pipeline** using the PostgreSQL Music Store database. Designed as a **modular and reusable analytical pipeline**, each stage builds upon previous outputs using **Common Table Expressions (CTEs)** to transform transactional data into executive-level insights.

---


## Technologies & SQL Concepts Used

- PostgreSQL & Analytical SQL Pipeline Design
- Common Table Expressions (CTEs) & Multi-level Query Chaining
- Window Functions (`ROW_NUMBER()`, `RANK()`, `NTILE()`)
- Conditional Logic (`CASE WHEN`), Aggregate Functions, and Joins

---

## Customer Segmentation Logic

### Business Metrics & Weight Distribution
Customer segments are determined by a weighted loyalty score incorporating five key metrics converted into quartiles via **`NTILE(4)`**:

| Metric | Weight |
|---------|-------:|
| Total Spending | 3 |
| Invoice Count | 2 |
| Purchase Frequency | 2 |
| Genre Diversity | 1 |
| Artist Diversity | 1 |

### Loyalty Score Formula & Segments
`Loyalty Score = (Spending * 3) + (Invoice * 2) + (Frequency * 2) + Genre + Artist`

| Loyalty Score | Segment |
|--------------:|----------|
| 24 and above | Platinum |
| 18 – 23 | Gold |
| 11 – 17 | Silver |
| Below 11 | Bronze |

---

## Marketing Recommendation Strategy

Personalized campaigns combine the customer's loyalty segment with their favorite genre (identified via **`ROW_NUMBER()`**):

| Customer Segment | Marketing Strategy |
|------------------|--------------------|
| Platinum | Early access to new releases and exclusive content |
| Gold | Curated album bundles based on favorite genre |
| Silver | 20% discount on tracks from favorite genre |
| Bronze | Welcome coupon to encourage future purchases |

---

## Country Ranking Methodology

To identify expansion opportunities, a **Country Expansion Score** balances market size and customer quality using normalized metrics:

`Expansion Score = (0.30 * Avg Rev/Cust) + (0.25 * Total Rev) + (0.15 * Total Cust) + (0.10 * Avg Invoice) + (0.10 * Genre Breadth) + (0.10 * Cust Diversity)`

Countries are ranked using the **`RANK()`** window function based on this final score.

---

## Executive SQL Dashboard

The final report consolidates pipeline insights into a single view without redundant calculations, featuring:
- Customer Segment Summary & Revenue Contribution
- Top Customers, Genres, Artists, and Albums by Revenue
- Top Employees and Top Three Expansion Countries

---

## Business Recommendations

1. **Prioritize High-Scoring Countries:** Focus investment on top-ranked expansion markets.
2. **Retain Platinum Customers:** Introduce premium loyalty benefits and early access programs.
3. **Expand Targeted Marketing:** Deliver personalized album bundles based on favorite genres.
4. **Engage Bronze Customers:** Utilize welcome coupons to drive repeat purchases.
5. **Promote Top Assets:** Highlight best-selling artists and albums through seasonal campaigns.
6. **Replicate Sales Best Practices:** Apply top-performing support representative strategies team-wide.

---

## Challenges Faced and Solutions

- **Redundant Calculations:** Solved by utilizing modular, chained CTEs across pipeline stages.
- **Accurate Customer Segmentation:** Replaced spending-only metrics with a multi-variable weighted scoring model using **`NTILE()`**.
- **Favorite Genre Identification:** Leveraged **`ROW_NUMBER()`** to rank and isolate top music preferences per customer.
- **Objective Country Ranking:** Developed a normalized 6-variable weighted expansion model.

---

## Conclusion

This project demonstrates the power of advanced SQL for BI, transforming raw transactional data into actionable insights through scalable, maintainable, and modular pipeline design.

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*