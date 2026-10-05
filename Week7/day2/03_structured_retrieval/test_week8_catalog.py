from pathlib import Path
from postgres_repository import PostgresPropertyRepository


class FakeColumn:
    def __init__(self, name):
        self.name = name

    def __getitem__(self, index):
        if index == 0:
            return self.name
        raise IndexError(index)


class FakeCursor:
    def __init__(self):
        self.description = [
            FakeColumn(name)
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
                "total_count",
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
            190_731,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params=None):
        self.query = query
        self.params = params
        if "SELECT l.area, MIN(pr.price)" in query:
            self.description = [
                FakeColumn(name)
                for name in ("area", "min_price", "max_price", "match_price")
            ]

    def fetchall(self):
        if "SELECT l.area, MIN(pr.price)" in self.query:
            return [("DHA Phase 5", 1_000_000, 2_000_000, 1_500_000)]
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

    rows = repository.search(city="Faisalabad", limit=20, offset=24)

    assert len(rows) == 1
    assert rows[0]["property_id"] == "W8-1422699"
    assert rows[0]["available"] is True
    assert rows[0]["total_count"] == 190_731
    assert "p.available = TRUE" in cursor.query
    assert "p.property_id LIKE 'W8-%'" in cursor.query
    assert "COUNT(*) OVER () AS total_count" in cursor.query
    assert "OFFSET %(offset)s" in cursor.query
    assert "pr.verification_status = 'Verified'" not in cursor.query
    assert cursor.params["city"] == "Faisalabad"
    assert cursor.params["offset"] == 24


def test_exact_lookup_includes_week8_catalog_records(monkeypatch):
    repository, cursor = make_repository(monkeypatch)

    row = repository.get_property("W8-1422699")

    assert row is not None
    assert row["property_id"] == "W8-1422699"
    assert row["available"] is True
    assert "p.property_id LIKE 'W8-%'" in cursor.query


def test_all_property_queries_exclude_legacy_catalog_rows():
    repository = PostgresPropertyRepository(
        database_url="postgresql://test",
        queries_file=Path(__file__).with_name("property_queries.sql"),
    )
    property_queries = {
        "available_cities",
        "exact_property",
        "property_name_lookup",
        "buyer_search",
        "availability",
        "developer_lookup",
        "cheaper_alternatives",
        "rental_search",
        "property_agents",
    }

    for query_name in property_queries:
        query = repository._get_query(query_name)
        assert "p.property_id LIKE 'W8-%'" in query
        assert "pr.verification_status = 'Verified'" not in query


def test_inline_property_catalog_queries_are_week8_only(monkeypatch):
    repository, cursor = make_repository(monkeypatch)

    repository.list_available_cities(purpose="Purchase")
    assert "p.property_id LIKE 'W8-%'" in cursor.query

    repository.budget_area_options(city="Lahore")
    assert "p.property_id LIKE 'W8-%'" in cursor.query

    repository.get_city_price_summary("Lahore")
    assert "p.property_id LIKE 'W8-%'" in cursor.query

    repository.get_minimum_price("Lahore")
    assert "p.property_id LIKE 'W8-%'" in cursor.query
