"""
market_stats_tool.py
--------------------
LangGraph tool for Market Statistics.
Computes genuine average price per marla and aggregations from actual property data.

Guarantees:
- Every average, median, count, and range is calculated directly from genuine records.
- LLM is strictly prohibited from computing arithmetic averages.
- Returns available=False if data points are insufficient (< 3 listings).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agent.data_store import PropertyDataStore

logger = logging.getLogger(__name__)


def market_stats_tool(
    city: Optional[str] = None,
    location: Optional[str] = None,
    purpose: str = "For Sale",
) -> Dict[str, Any]:
    """
    Calculate market statistics including average price per marla from actual data.

    Parameters:
    - city: e.g. 'Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad'
    - location: Society/locality e.g. 'DHA', 'Clifton', 'F-7'
    - purpose: 'For Sale' or 'For Rent'

    Returns structured statistics dictionary.
    """
    try:
        store = PropertyDataStore.get_instance()
        res = store.get_market_stats(
            city=city,
            location=location,
            purpose=purpose,
        )
        return res
    except Exception as e:
        logger.error("Market stats tool error: %s", e, exc_info=True)
        return {
            "available": False,
            "reason": f"Calculation failed: {str(e)}",
        }
