"""
Test suite for VapiToolHandler property search using PostgreSQL.

Verifies that:
1. The tool handler uses PostgreSQL instead of CSV files
2. Property search returns properly formatted results
3. Appointment tools continue working
4. Error handling is graceful
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

# Add vapi_integration to path
_VAPI_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_VAPI_DIR))

from tool_handler import VapiToolHandler


class TestPropertySearchPostgres:
    """Test property search using PostgreSQL."""

    @pytest.fixture
    def handler(self):
        """Create a VapiToolHandler for testing."""
        # Mock the repository to avoid actual DB connection during tests
        with patch("tool_handler.PostgresPropertyRepository"):
            handler = VapiToolHandler()
            # Create a mock repository
            handler.repository = Mock()
            return handler

    @pytest.mark.asyncio
    async def test_search_properties_with_results(self, handler):
        """Test successful property search with matching results."""
        # Mock the repository search results
        mock_properties = [
            {
                "property_id": "prop_001",
                "property_name": "Skyline Heights",
                "area": "DHA Phase 6",
                "city": "Lahore",
                "bedrooms": 3,
                "bathrooms": 2,
                "property_type": "Apartment",
                "price": 45000000,
                "currency": "PKR",
                "developer_name": "Emaar",
                "status": "Available",
                "amenities": ["Swimming Pool", "Gym", "24/7 Security", "Parking"],
            },
            {
                "property_id": "prop_002",
                "property_name": "Horizon Park",
                "area": "DHA Phase 5",
                "city": "Lahore",
                "bedrooms": 3,
                "bathrooms": 2,
                "property_type": "Apartment",
                "price": 50000000,
                "currency": "PKR",
                "developer_name": "Bahria",
                "status": "Available",
                "amenities": ["Gymnasium", "Community Center", "Covered Parking"],
            },
        ]

        # Mock asyncio.to_thread to return our mock properties
        handler.repository.search = Mock(return_value=mock_properties)

        with patch("tool_handler.asyncio.to_thread") as mock_to_thread:
            # Make to_thread return the search results
            async def mock_search(*args, **kwargs):
                return mock_properties

            mock_to_thread.side_effect = mock_search

            result = await handler._search_properties({
                "location": "Lahore DHA",
                "max_price": 50000000,
                "bedrooms": 3,
                "purpose": "buy",
            })

        # Verify result is formatted properly
        assert "Found" in result
        assert "Skyline Heights" in result
        assert "Horizon Park" in result
        assert "verified properties" in result
        assert "DHA Phase 6" in result
        assert "DHA Phase 5" in result
        assert "4.50 Crore PKR" in result
        assert "5.00 Crore PKR" in result
        
        # Verify NO CSV file access
        assert "01_knowledge_base" not in result
        
        # Verify asyncio.to_thread was called to safely run sync search
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_available_locations_uses_verified_database(self, handler):
        handler.repository.list_available_cities = Mock(
            return_value=["Islamabad", "Lahore"]
        )

        result = await handler.execute(
            "list_available_locations", {}, "call-city-options"
        )

        assert "Islamabad, Lahore" in result
        assert "Karachi" not in result
        handler.repository.list_available_cities.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_list_available_locations_does_not_guess_on_empty_data(self, handler):
        handler.repository.list_available_cities = Mock(return_value=[])

        result = await handler._list_available_locations()

        assert "koi verified available city nahi mili" in result

    @pytest.mark.asyncio
    async def test_search_properties_re_ranks_verified_candidates_with_profile(self, handler):
        """ML may change ordering, but only after PostgreSQL returns candidates."""
        candidates = [
            {"property_id": "p2", "property_name": "Second", "city": "Lahore", "area": "DHA", "price": 40_000_000},
            {"property_id": "p1", "property_name": "First", "city": "Lahore", "area": "DHA Phase 6", "price": 40_000_000},
        ]
        handler.repository.search = Mock(return_value=candidates)
        handler.preference_repository = Mock()
        handler.preference_repository.get = Mock(return_value=__import__(
            "vapi_integration.customer_learning", fromlist=["PreferenceProfile"]
        ).PreferenceProfile(customer_key="c", city="Lahore", area="DHA Phase 6"))

        session = Mock(caller_phone="+923001234567")
        with patch.dict(os.environ, {"SARA_CUSTOMER_HASH_SALT": "test-salt"}), patch("tool_handler.asyncio.to_thread") as mock_to_thread:
            async def mock_thread(function, *args, **kwargs):
                if function == handler.repository.search:
                    return candidates
                return handler.preference_repository.get(*args, **kwargs)

            mock_to_thread.side_effect = mock_thread
            result = await handler._search_properties({"location": "Lahore", "max_price": 50_000_000}, session=session)

        assert "1. First" in result
        assert "2. Second" in result

    @pytest.mark.asyncio
    async def test_search_properties_no_results(self, handler):
        """Test property search with no matching results."""
        handler.repository.search = Mock(return_value=[])

        with patch("tool_handler.asyncio.to_thread") as mock_to_thread:
            async def mock_search(*args, **kwargs):
                return []

            mock_to_thread.side_effect = mock_search

            result = await handler._search_properties({
                "location": "Nowhere",
                "bedrooms": 5,
            })

        assert "Bohot sorri" in result
        assert "available nahi" in result
        # Should suggest adjusting criteria
        assert "requirements" in result or "adjust" in result

    @pytest.mark.asyncio
    async def test_search_properties_missing_location(self, handler):
        """Test property search without required location parameter."""
        result = await handler._search_properties({
            "bedrooms": 3,
            "max_price": 40000000,
        })

        assert "location batayen" in result or "location" in result.lower()

    @pytest.mark.asyncio
    async def test_search_properties_no_repository(self):
        """Test property search when repository is not available."""
        # Create handler without repository
        handler = VapiToolHandler()
        handler.repository = None

        result = await handler._search_properties({
            "location": "Lahore",
        })

        assert "database" in result.lower() or "connection" in result.lower()

    @pytest.mark.asyncio
    async def test_search_properties_database_error(self, handler):
        """Test graceful error handling when database fails."""
        handler.repository.search = Mock(side_effect=Exception("DB Connection failed"))

        with patch("tool_handler.asyncio.to_thread") as mock_to_thread:
            async def mock_search(*args, **kwargs):
                raise Exception("DB Connection failed")

            mock_to_thread.side_effect = mock_search

            result = await handler._search_properties({
                "location": "Lahore",
            })

        # Should return user-friendly error message
        assert "masla" in result.lower() or "error" in result.lower()
        # Should NOT expose technical details
        assert "Exception" not in result
        assert "Connection failed" not in result

    def test_format_property_results_single(self, handler):
        """Test formatting a single property result."""
        properties = [
            {
                "property_id": "prop_001",
                "property_name": "Test Property",
                "area": "DHA",
                "city": "Lahore",
                "bedrooms": 3,
                "bathrooms": 2,
                "property_type": "Apartment",
                "price": 40000000,
                "currency": "PKR",
                "developer_name": "Test Dev",
                "status": "Available",
                "amenities": ["Pool", "Gym", "Security"],
            }
        ]

        result = handler._format_property_results(properties)

        assert "Test Property" in result
        assert "DHA" in result
        assert "Lahore" in result
        assert "3BED 2BATH" in result
        assert "4.00 Crore PKR" in result
        assert "Test Dev" in result
        assert "Pool" in result
        assert "Gym" in result

    def test_format_property_results_multiple(self, handler):
        """Test formatting multiple property results."""
        properties = [
            {
                "property_id": f"prop_{i:03d}",
                "property_name": f"Property {i}",
                "area": f"Area {i}",
                "city": "Lahore",
                "bedrooms": i + 2,
                "bathrooms": i + 1,
                "property_type": "Apartment",
                "price": 30000000 + (i * 5000000),
                "currency": "PKR",
                "developer_name": f"Dev {i}",
                "status": "Available",
                "amenities": [f"Amenity {i}-A", f"Amenity {i}-B"],
            }
            for i in range(3)
        ]

        result = handler._format_property_results(properties)

        # All properties should be formatted
        for i in range(3):
            assert f"Property {i}" in result
            assert f"Area {i}" in result

    def test_format_property_results_empty(self, handler):
        """Test formatting with no properties."""
        result = handler._format_property_results([])
        assert "No properties" in result

    def test_format_property_results_missing_fields(self, handler):
        """Test formatting with incomplete property data."""
        properties = [
            {
                "property_name": "Partial Property",
                # Missing many fields
            }
        ]

        result = handler._format_property_results(properties)

        # Should handle gracefully with defaults
        assert "Partial Property" in result
        assert "?" in result or "Unknown" in result or "N/A" in result


class TestAppointmentTools:
    """Verify appointment tools are not broken by PostgreSQL changes."""

    @pytest.fixture
    def handler(self):
        """Create a handler for appointment tests."""
        return VapiToolHandler()

    @pytest.mark.asyncio
    async def test_book_appointment_still_works(self, handler):
        """Verify book_appointment tool is unaffected."""
        with patch("tool_handler.httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "appointment": {
                    "appointment_id": "apt_123",
                }
            }
            mock_response.content = True

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await handler._book_appointment({
                "client_name": "Ali",
                "client_phone": "+923001234567",
                "property_name": "Skyline",
                "starts_at": "2025-09-05T10:00:00+05:00",
            }, session=None)

            assert "successfully book" in result or "confirm" in result
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_appointment_still_works(self, handler):
        """Verify cancel_appointment tool is unaffected."""
        with patch("tool_handler.httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await handler._cancel_appointment({
                "appointment_id": "apt_123",
            })

            assert "cancel" in result.lower()
            mock_client.delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
