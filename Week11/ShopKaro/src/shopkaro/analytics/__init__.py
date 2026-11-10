"""
ShopKaro Analytics Module
=========================
Powers exploratory data analysis, funnel analysis, business KPIs, customer lifetime value
estimation, repeat purchase rates, and revenue metric computations.
"""

from shopkaro.analytics.cohorts import CohortReport, run_cohort_and_retention_analysis
from shopkaro.analytics.eda import EDAReport, run_exploratory_analysis

__all__ = [
    "CohortReport",
    "EDAReport",
    "run_cohort_and_retention_analysis",
    "run_exploratory_analysis",
]
