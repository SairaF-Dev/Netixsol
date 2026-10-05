from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from src.agent.data_store import PropertyDataStore


class FakeCursor:
    columns = (
        "property_id",
        "property_type",
        "price",
        "location",
        "city",
        "area_marla",
        "bedrooms",
        "baths",
        "purpose",
        "price_per_marla",
        "available",
        "status",
        "page_url",
        "province_name",
        "latitude",
        "longitude",
        "area",
        "agency",
        "agent",
    )

    def __init__(self) -> None:
        self.description = [SimpleNamespace(name=name) for name in self.columns]
        self.query = ""

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str) -> None:
        self.query = query

    def fetchall(self) -> list[tuple[object, ...]]:
        return [
            (
                123,
                "House",
                10_000_000,
                "DHA Phase 5",
                "Lahore",
                10,
                3,
                2,
                "For Sale",
                1_000_000,
                True,
                "Available",
                None,
                "Punjab",
                None,
                None,
                None,
                None,
                None,
            ),
            (
                456,
                "House",
                4_400_000,
                "Malir",
                "Karachi",
                None,
                2,
                2,
                "For Sale",
                None,
                True,
                "Available",
                None,
                "Sindh",
                None,
                None,
                None,
                None,
                None,
            ),
        ]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor


def test_neon_load_uses_only_week8_rows_and_does_not_invent_week7_agents(
    monkeypatch, tmp_path
):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    psycopg = ModuleType("psycopg")
    psycopg.connect = lambda *_args, **_kwargs: connection
    monkeypatch.setitem(sys.modules, "psycopg", psycopg)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    store = PropertyDataStore(data_path=tmp_path / "missing.csv")

    assert "p.property_id LIKE 'W8-%'" in cursor.query
    assert len(store.df) == 2
    assert store.get_property("W8-123") == {
        "property_id": "W8-123",
        "raw_property_id": "123",
        "property_name": "3 Bed House in DHA Phase 5, Lahore",
        "property_type": "House",
        "city": "Lahore",
        "location": "DHA Phase 5",
        "province_name": "Punjab",
        "area": "10 Marla",
        "area_marla": 10.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "baths": 2,
        "price": 10_000_000.0,
        "price_pkr": 10_000_000.0,
        "purpose": "For Sale",
        "latitude": None,
        "longitude": None,
        "agency": "",
        "agent": "",
        "page_url": "",
        "available": True,
        "status": "Available",
    }
    missing_area = store.get_property("W8-456")
    assert missing_area is not None
    assert missing_area["property_id"] == "W8-456"
    assert missing_area["area_marla"] is None
    assert missing_area["price"] == 4_400_000
    search = store.search_properties(city="Karachi", limit=10)
    assert search["total"] == 1
    assert search["properties"][0]["property_id"] == "W8-456"
