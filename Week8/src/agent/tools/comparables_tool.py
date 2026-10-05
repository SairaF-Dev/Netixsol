"""
comparables_tool.py
-------------------
LangGraph tool for Comparable Properties retrieval.
Queries real, genuine property records from the processed property data store.

Guarantees:
- Never invents listings or creates synthetic properties.
- All prices and attributes come directly from actual database records.
- Returns found=False if no matching records exist.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agent.data_store import PropertyDataStore

logger = logging.getLogger(__name__)


def comparable_properties_tool(
    city: str,
    purpose: str = "For Sale",
    property_type: Optional[str] = "House",
    area_marla: Optional[float] = None,
    location: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Search actual property database for genuine comparable property listings.

    Parameters:
    - city: e.g. 'Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad'
    - purpose: 'For Sale' or 'For Rent'
    - property_type: 'House', 'Flat', etc.
    - area_marla: Plot size in Marla
    - location: Target neighborhood or society (e.g. 'DHA', 'Clifton')
    - limit: Max records to retrieve (default 5)

    Returns structured comparable listings.
    """
    if not city:
        return {
            "found": False,
            "count": 0,
            "properties": [],
            "message": "City parameter is required to find comparable properties.",
        }

    try:
        store = PropertyDataStore.get_instance()
        res = store.get_comparables(
            city=city,
            purpose=purpose,
            property_type=property_type,
            area_marla=area_marla,
            location=location,
            limit=limit,
        )
        return res
    except Exception as e:
        logger.error("Comparable properties tool error: %s", e, exc_info=True)
        return {
            "found": False,
            "count": 0,
            "properties": [],
            "error": f"Database search failed: {str(e)}",
        }
