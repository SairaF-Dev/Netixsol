from tools import retrieval_tools as retrieval


def test_known_player_names_resolve_through_metadata():
    """These are dataset assertions, not application-level special cases."""
    assert retrieval.resolve_player_name("Nick Daicos") == {
        "player_id": 43668,
        "player_name": "Nick Daicos",
    }
    assert retrieval.resolve_player_name("Patrick Cripps")["player_id"] == 43642
    assert retrieval.resolve_player_name("Marcus Bontempelli")["player_id"] == 43414


def test_player_name_normalization_and_unknown_player():
    expected = retrieval.resolve_player_name("Nick Daicos")
    assert retrieval.resolve_player_name(" nick daicos ") == expected
    assert retrieval.resolve_player_name("NICK DAICOS") == expected
    assert retrieval.resolve_player_name("Not A Real AFL Player") is None


def test_ambiguous_names_are_not_resolved_arbitrarily():
    metadata = retrieval._player_metadata()
    ids_per_name = metadata.groupby(
        metadata["player_name"].str.casefold()
    )["player_id"].nunique()
    ambiguous_name = ids_per_name[ids_per_name > 1].index[0]

    assert retrieval.resolve_player_name(ambiguous_name) is None


def test_statistics_query_uses_resolved_raw_player_id():
    assert "player_name" not in retrieval._players.columns

    result = retrieval.get_player_statistics("Nick Daicos", year=2024)

    assert result["player_id"] == 43668
    assert result["match_count"] > 0
    assert {match["player_id"] for match in result["matches"]} == {43668}
