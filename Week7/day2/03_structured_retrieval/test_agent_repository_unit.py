from postgres_repository import PostgresPropertyRepository


class Description:
    def __init__(self, name):
        self.name = name


class Cursor:
    def __init__(self, rows, columns):
        self.rows = rows
        self.description = [Description(name) for name in columns]
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.executed = (query, params)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor


def make_repo(cursor):
    repo = object.__new__(PostgresPropertyRepository)
    repo.queries = {
        "agent_lookup": "SELECT agent",
        "property_agents": "SELECT property agents",
    }
    repo._connect = lambda: Connection(cursor)
    return repo


def test_get_agent_returns_verified_sql_row():
    cursor = Cursor(
        [("AGT-001", "Ali Raza")],
        ["agent_id", "agent_name"],
    )
    repo = make_repo(cursor)

    result = repo.get_agent("AGT-001")

    assert result == {
        "agent_id": "AGT-001",
        "agent_name": "Ali Raza",
    }
    assert cursor.executed[1] == {"agent_id": "AGT-001"}


def test_get_agents_for_property_returns_assignments():
    cursor = Cursor(
        [("P1", "Home", "AGT-001", "Ali Raza")],
        ["property_id", "property_name", "agent_id", "agent_name"],
    )
    repo = make_repo(cursor)

    result = repo.get_agents_for_property("P1")

    assert result[0]["agent_name"] == "Ali Raza"
    assert cursor.executed[1] == {"property_id": "P1"}
