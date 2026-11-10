"""
ShopKaro Customer Segmentation Module
=====================================
Implements Recency-Frequency-Monetary (RFM) modeling, behavioral clustering algorithms
(e.g., K-Means), cohort tracking, and customer segment profiling.
"""

from shopkaro.segmentation.rfm import (
    SEGMENT_MARKETING_ACTIONS,
    SegmentationReport,
    run_customer_segmentation,
)

__all__ = [
    "SEGMENT_MARKETING_ACTIONS",
    "SegmentationReport",
    "run_customer_segmentation",
]
