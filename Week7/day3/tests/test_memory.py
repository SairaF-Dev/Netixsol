from sara_agent.memory import ConversationState

def test_required_and_relax():
    s=ConversationState()
    s.apply(required={"city":"Lahore","area":"X","bedrooms":2})
    s.apply(relax=["area"])
    assert s.required=={"city":"Lahore","bedrooms":2}

def test_exclusion_supersedes_same_positive_field():
    s=ConversationState(required={"city":"Lahore","area":"X"})
    s.apply(excluded={"area":["X","Y"]})
    assert "area" not in s.required
    assert s.excluded["area"]==["X","Y"]
