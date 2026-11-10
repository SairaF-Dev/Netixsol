"""
ShopKaro Data Engineering & Ingestion Module
=============================================
Manages raw dataset loading (RetailRocket, Olist, synthetic catalogues), data cleaning,
schema validation, pipeline transformation, and DuckDB storage integration.
"""

from shopkaro.data.pipeline import PipelineSummary, run_day1_data_pipeline
from shopkaro.data.splits import SplitSummary, build_features_and_time_splits
from shopkaro.data.synthesizer import (
    generate_daily_sales_history,
    generate_festival_calendar,
    generate_pakistani_reviews,
    generate_product_catalogue,
)

__all__ = [
    "PipelineSummary",
    "SplitSummary",
    "build_features_and_time_splits",
    "generate_daily_sales_history",
    "generate_festival_calendar",
    "generate_pakistani_reviews",
    "generate_product_catalogue",
    "run_day1_data_pipeline",
]
