from __future__ import annotations

from types import SimpleNamespace

import streamlit as st

from dev_data_collection_app import record_shown, shown_signature


class RecordingRepository:
    def __init__(self):
        self.events = []

    def record_interaction(self, **event):
        self.events.append(event)


def test_shown_signature_is_order_sensitive_and_stable():
    results = [{"property_id": "p1"}, {"property_id": "p2"}]
    assert shown_signature(results) == shown_signature(results)
    assert shown_signature(results) != shown_signature(list(reversed(results)))


def test_shown_events_are_not_duplicated_on_rerun_and_reuse_snapshots():
    st.session_state.clear()
    st.session_state.shown_signature = None
    st.session_state.shown_snapshots = {}
    st.session_state.interaction_session_id = "dev-ui-test"
    repository = RecordingRepository()
    preferences = SimpleNamespace(
        city="Lahore", area="DHA", budget_min=None, budget_max=30_000_000,
        bedrooms=3, property_type="Apartment", purpose="buy", amenities=["parking"],
    )
    results = [{
        "property_id": "p1", "city": "Lahore", "area": "DHA", "price": 20_000_000,
        "bedrooms": 3, "property_type": "Apartment", "purpose": "buy", "amenities": ["parking"],
    }]
    record_shown("customer-1", preferences, results, repository)
    record_shown("customer-1", preferences, results, repository)

    assert len(repository.events) == 1
    assert repository.events[0]["action"] == "shown"
    assert repository.events[0]["preference_snapshot"]["budget_max"] == 30_000_000
    assert repository.events[0]["property_snapshot"]["property_id"] == "p1"