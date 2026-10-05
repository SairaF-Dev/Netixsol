from pathlib import Path
from types import SimpleNamespace

from postgres_repository import PostgresPropertyRepository


class FakeCursor:
    def __init__(self):
        self.description = [
            SimpleNamespace(name=name)
            for name in (
                "property_id",
                "property_name",
                "area",
                "city",
                "property_type",
                "bedrooms",
                "bathrooms",
                "price",
                "currency",
                "available",
                "status",
                "purpose",
                "amenities",
                "verification_status",
            )
        ]
        self.query = ""
        self.params = None
        self.row = (
            "W8-1422699",
            "4 Bed House in Muslim Town, Faisalabad",
            "Muslim Town",
            "Faisalabad",
            "House",
            4,
            5,
            8_500_000,
            "PKR",
            True,
            "Available",
            "Purchase",
            [],
            "Imported",
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return [self.row]

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self):
        return self._cursor


def make_repository(monkeypatch):
    query_file = Path(__file__).with_name("property_queries.sql")
    repository = PostgresPropertyRepository(
        database_url="postgresql://test",
        queries_file=query_file,
    )
    cursor = FakeCursor()
    monkeypatch.setattr(repository, "_connect", lambda: FakeConnection(cursor))
    return repository, cursor


def test_search_includes_available_week8_catalog_records(monkeypatch):
    repository, cursor = make_repository(monkeypatch)

    rows = repository.search(city="Faisalabad", limit=20)

    assert len(rows) == 1
    assert rows[0]["property_id"] == "W8-1422699"
    assert rows[0]["available"] is True
    assert rows[0]["verification_status"] == "Imported"
    assert "p.available = TRUE" in cursor.query
    assert "LEFT(p.property_id, 3) = 'W8-'" in cursor.query
    assert cursor.params["city"] == "Faisalabad"


def test_exact_lookup_includes_week8_catalog_records(monkeypatch):
    repository, cursor = make_repository(monkeypatch)

    row = repository.get_property("W8-1422699")

    assert row is not None
    assert row["property_id"] == "W8-1422699"
    assert row["available"] is True
    assert "LEFT(p.property_id, 3) = 'W8-'" in cursor.query
