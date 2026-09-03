from sara_agent.session_store import SessionStore


class Box:
    def __init__(self):
        self.value = []


def test_sessions_are_isolated_and_reused_by_id():
    store = SessionStore(Box, ttl_seconds=3600, max_sessions=10)

    first_id, first = store.get_or_create()
    second_id, second = store.get_or_create()

    assert first_id != second_id
    assert first is not second

    first.value.append("Lahore")
    assert second.value == []

    same_id, same_first = store.get_or_create(first_id)
    assert same_id == first_id
    assert same_first is first
    assert same_first.value == ["Lahore"]


def test_session_store_is_bounded():
    store = SessionStore(Box, ttl_seconds=3600, max_sessions=2)

    one, _ = store.get_or_create()
    two, _ = store.get_or_create()
    three, _ = store.get_or_create()

    assert len(store) == 2
    assert one not in {two, three}



def test_trivial_client_session_id_is_not_accepted():
    store = SessionStore(
        Box,
        ttl_seconds=3600,
        max_sessions=10,
    )

    resolved, _ = store.get_or_create(
        "customer1"
    )

    assert resolved != "customer1"
    assert len(resolved) >= 20
