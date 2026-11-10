# ShopKaro — Jupyter Notebooks

This directory contains research notebooks, exploratory data analysis (EDA), iterative prototyping, and experimental evaluations for the ShopKaro platform.

---

## Intended Purpose

Notebooks are designed for exploratory and diagnostic workflows:
- Visualizing distributions, clickstream funnels, and transaction patterns.
- Rapid prototyping of candidate recommendation algorithms and forecasting models.
- Interactive validation of sentiment models and search retrieval quality.

---

## Notebook Conventions & Best Practices

1. **Naming Conventions:**
   - Prefix notebooks with sequential numbers reflecting the lifecycle stage:
     - `01_eda_retailrocket_clickstream.ipynb`
     - `02_eda_olist_orders_reviews.ipynb`
     - `03_customer_rfm_segmentation.ipynb`
     - `04_recommender_prototypes.ipynb`
     - `05_demand_forecasting_experiments.ipynb`
     - `06_hybrid_search_bm25_semantic.ipynb`
     - `07_aspect_review_sentiment.ipynb`
     - `08_ab_testing_simulation.ipynb`

2. **Code Promotion to Modules:**
   - Notebooks are scratchpads. Once logic (data loaders, metric calculators, model wrappers) stabilizes, refactor and migrate it into the appropriate package in `src/shopkaro/`.
   - Notebooks should import reusable functionality directly from `shopkaro`.

3. **Clean Version Control:**
   - Clear outputs or avoid committing massive cell execution outputs before committing notebooks to Git.
   - Do not commit large embedded graphs or raw dataframes.

