"""Development-only human interaction data collection UI.

This app is intentionally separate from the customer-facing website and does
not train or load an ML model. All properties come from verified PostgreSQL.
"""

from __future__ import annotations

import hashlib
import os
import sys
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "vapi_integration" / ".env")
if str(ROOT / "vapi_integration") not in sys.path:
    sys.path.insert(0, str(ROOT / "vapi_integration"))
DAY2_ROOT = ROOT.parent / "day2" / "03_structured_retrieval"
if str(DAY2_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY2_ROOT))

from customer_service import CustomerService
from interaction_repository import InteractionRepository
from preference_repository import CustomerPreferences
from tool_handler import VapiToolHandler
from postgres_repository import PostgresPropertyRepository
from ml.build_dataset import build_dataset, fetch_interaction_rows
from ml.readiness import readiness, summarize_rows


st.set_page_config(page_title="Sara Human Test Data", page_icon="H", layout="wide")
st.title("Development / Human Test Data Collection")
st.caption("Internal tool only. Explicit buttons create real interaction events; no ML or synthetic rows are written here.")


@st.cache_resource
def services():
    return CustomerService(), InteractionRepository(), PostgresPropertyRepository()


def ensure_state() -> None:
    defaults = {
        "selected_customer_id": None,
        "interaction_session_id": f"dev-ui-{uuid.uuid4()}",
        "search_results": [],
        "shown_signature": None,
        "shown_snapshots": {},
        "feedback_events": set(),
        "flash": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def preference_snapshot(preferences: CustomerPreferences | None) -> dict:
    return {
        "city": preferences.city if preferences else None,
        "area": preferences.area if preferences else None,
        "budget_min": preferences.budget_min if preferences else None,
        "budget_max": preferences.budget_max if preferences else None,
        "bedrooms": preferences.bedrooms if preferences else None,
        "property_type": preferences.property_type if preferences else None,
        "purpose": preferences.purpose if preferences else None,
        "amenities": list(preferences.amenities if preferences else []),
    }


def shown_signature(results: list[dict]) -> str:
    ids = [str(item.get("property_id")) for item in results if item.get("property_id")]
    return hashlib.sha256("|".join(ids).encode()).hexdigest()


def normalize_search_property_type(value: str) -> str | None:
    aliases = {
        "appartment": "Apartment",
        "apartment": "Apartment",
        "flat": "Apartment",
        "house": "House",
        "villa": "House",
        "plot": "Plot",
        "office": "Office",
        "shop": "Shop",
    }
    cleaned = value.strip().casefold()
    return aliases.get(cleaned, value.strip() or None)


def normalize_search_purpose(value: str) -> str | None:
    aliases = {
        "buy": "Purchase",
        "purchase": "Purchase",
        "rent": "Rental",
        "rental": "Rental",
        "invest": "Investment",
        "investment": "Investment",
    }
    cleaned = value.strip().casefold()
    return aliases.get(cleaned, value.strip() or None)


def select_customer(service: CustomerService):
    customers = service.list_customers()
    labels = [
        f"{customer.full_name or 'Unnamed'} | {customer.phone_normalized or customer.email or customer.customer_id[:8]}"
        for customer in customers
    ]
    selected_label = st.sidebar.selectbox("Existing test customer", ["Create new customer", *labels])
    if selected_label != "Create new customer":
        customer = customers[labels.index(selected_label)]
        st.session_state.selected_customer_id = customer.customer_id
        return service.resolve_for_customer_id(customer.customer_id)

    with st.sidebar.form("create_customer"):
        st.subheader("Create or reuse test customer")
        name = st.text_input("Full name")
        email = st.text_input("Email")
        phone = st.text_input("Phone", placeholder="03001234567")
        submitted = st.form_submit_button("Create / Load Customer")
    if submitted:
        try:
            context = service.create_or_get_test_customer(full_name=name, email=email, phone=phone)
            st.session_state.selected_customer_id = context.customer.customer_id
            st.session_state.interaction_session_id = f"dev-ui-{uuid.uuid4()}"
            st.session_state.search_results = []
            st.session_state.shown_signature = None
            st.session_state.shown_snapshots = {}
            st.rerun()
        except Exception as exc:
            st.sidebar.error(str(exc))
    return service.resolve_for_customer_id(st.session_state.selected_customer_id)


def save_preferences(service: CustomerService, customer_id: str, current: CustomerPreferences | None) -> None:
    current = current or CustomerPreferences(customer_id=customer_id)
    with st.form("preferences"):
        st.subheader("Customer preferences")
        city = st.text_input("City", value=current.city if current and current.city else "")
        area = st.text_input("Area", value=current.area if current and current.area else "")
        budget = st.number_input("Budget max (PKR)", min_value=0, value=current.budget_max or 0, step=100000)
        bedrooms = st.number_input("Bedrooms", min_value=0, value=current.bedrooms or 0, step=1)
        property_type = st.text_input("Property type", value=current.property_type if current and current.property_type else "")
        purpose = st.text_input("Purpose", value=current.purpose if current and current.purpose else "")
        amenities = st.text_input("Preferred amenities (comma separated)", value=", ".join(current.amenities))
        if st.form_submit_button("Save preferences"):
            updates = {
                "city": city.strip() or None, "area": area.strip() or None,
                "budget_max": int(budget) if budget else None,
                "bedrooms": int(bedrooms) if bedrooms else None,
                "property_type": property_type.strip() or None,
                "purpose": purpose.strip() or None,
                "amenities": list(dict.fromkeys(item.strip() for item in amenities.split(",") if item.strip())),
            }
            updates = {key: value for key, value in updates.items() if value is not None and value != []}
            try:
                service.update_preferences(customer_id, updates)
                st.success("Preferences saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save preferences: {type(exc).__name__}")


def record_shown(customer_id: str, preferences: CustomerPreferences | None, results: list[dict], repository: InteractionRepository) -> None:
    signature = shown_signature(results)
    if signature == st.session_state.shown_signature:
        return
    pref_snapshot = preference_snapshot(preferences)
    for item in results:
        property_id = str(item.get("property_id"))
        snapshot = VapiToolHandler._property_snapshot(item)
        st.session_state.shown_snapshots[property_id] = (pref_snapshot, snapshot)
        try:
            repository.record_interaction(
                customer_id=customer_id,
                conversation_id=st.session_state.interaction_session_id,
                property_id=property_id,
                action="shown",
                preference_snapshot=pref_snapshot,
                property_snapshot=snapshot,
            )
        except Exception as exc:
            st.warning(f"Shown event could not be stored for {property_id}: {type(exc).__name__}")
    st.session_state.shown_signature = signature


def render_results(customer_id: str, repository: InteractionRepository) -> None:
    results = st.session_state.search_results
    if not results:
        return
    st.subheader("Verified properties presented to tester")
    for index, item in enumerate(results):
        property_id = str(item.get("property_id"))
        with st.container(border=True):
            st.markdown(f"**{index + 1}. {item.get('property_name', 'Property')}**")
            st.write(f"ID: `{property_id}` | {item.get('city', '')} / {item.get('area', '')}")
            st.write(f"Price: {item.get('price', 'N/A')} {item.get('currency', 'PKR')} | Bedrooms: {item.get('bedrooms', 'N/A')} | Type: {item.get('property_type', 'N/A')} | Purpose: {item.get('purpose', 'N/A')}")
            st.write("Amenities: " + ", ".join(item.get("amenities") or []) if item.get("amenities") else "Amenities: not listed")
            pref_snapshot, prop_snapshot = st.session_state.shown_snapshots.get(property_id, ({}, {}))
            for action, label in (("liked", "Like"), ("rejected", "Reject"), ("shortlisted", "Shortlist")):
                if st.button(label, key=f"{st.session_state.interaction_session_id}-{property_id}-{action}"):
                    event_key = f"{property_id}:{action}"
                    if event_key not in st.session_state.feedback_events:
                        try:
                            repository.record_interaction(
                                customer_id=customer_id,
                                conversation_id=st.session_state.interaction_session_id,
                                property_id=property_id,
                                action=action,
                                preference_snapshot=pref_snapshot,
                                property_snapshot=prop_snapshot,
                            )
                            st.session_state.feedback_events.add(event_key)
                            st.success(f"Recorded {action} for {property_id}.")
                        except Exception as exc:
                            st.error(f"Could not record {action}: {type(exc).__name__}")


def main() -> None:
    ensure_state()
    try:
        customer_service, interaction_repository, property_repository = services()
    except Exception as exc:
        st.error(f"Database services unavailable: {type(exc).__name__}")
        st.stop()
    context = select_customer(customer_service)
    if not context.customer:
        st.info("Create or select an identified development customer in the sidebar.")
        st.stop()
    current_preferences = context.preferences or CustomerPreferences(
        customer_id=context.customer.customer_id
    )
    st.sidebar.success(f"Selected customer: {context.customer.full_name or 'Unnamed'}")
    st.sidebar.caption(f"Interaction session: {st.session_state.interaction_session_id}")
    if st.sidebar.button("Start new customer scenario"):
        st.session_state.interaction_session_id = f"dev-ui-{uuid.uuid4()}"
        st.session_state.search_results = []
        st.session_state.shown_signature = None
        st.session_state.shown_snapshots = {}
        st.session_state.feedback_events = set()
        st.rerun()
    save_preferences(customer_service, context.customer.customer_id, current_preferences)

    st.subheader("Verified property search")
    with st.form("search"):
        default_location = " ".join(
            value for value in (current_preferences.area, current_preferences.city)
            if value
        )
        location = st.text_input("Location", value=default_location)
        max_price = st.number_input("Maximum price (PKR)", min_value=0, value=current_preferences.budget_max or 0, step=100000)
        bedrooms = st.number_input("Bedrooms filter", min_value=0, value=current_preferences.bedrooms or 0, step=1)
        property_type = st.text_input("Property type filter", value=current_preferences.property_type or "")
        purpose = st.text_input("Purpose filter", value=current_preferences.purpose or "")
        if st.form_submit_button("Search Properties"):
            city = None
            area = location.strip() or None
            for known_city in ("Lahore", "Karachi", "Islamabad", "Rawalpindi"):
                if known_city.casefold() in location.casefold():
                    city = known_city
                    area = location.replace(known_city, "").strip(" ,-") or None
                    break
            st.session_state.search_results = property_repository.search(
                budget=int(max_price) if max_price else None,
                city=city, area=area, bedrooms=int(bedrooms) if bedrooms else None,
                property_type=normalize_search_property_type(property_type),
                purpose=normalize_search_purpose(purpose),
                amenities=None, limit=3,
            )
            st.session_state.shown_signature = None
            st.session_state.shown_snapshots = {}
            st.session_state.feedback_events = set()
            if st.session_state.search_results:
                st.rerun()
            else:
                st.warning("No verified available properties matched these filters. Try a broader location, budget, or property type.")

    if st.session_state.search_results:
        record_shown(context.customer.customer_id, current_preferences, st.session_state.search_results, interaction_repository)
        render_results(context.customer.customer_id, interaction_repository)

    st.subheader("Recent interactions")
    for event in interaction_repository.list_customer_interactions(context.customer.customer_id)[-20:][::-1]:
        st.write(f"{event.property_id} | {event.action} | {event.created_at}")

    st.subheader("Real ML readiness")
    try:
        real_rows = fetch_interaction_rows()
        real_summary = summarize_rows(real_rows)
        st.json(real_summary)
        try:
            real_dataset = build_dataset(real_rows)
            st.json(readiness(real_dataset))
        except Exception:
            st.json({"training_ready": False, "reason": "insufficient resolved real outcomes"})
    except Exception as exc:
        st.warning(f"Readiness unavailable: {type(exc).__name__}")


if __name__ == "__main__":
    main()