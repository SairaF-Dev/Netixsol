"""Shared customer identity and preference hydration service."""

from __future__ import annotations

from dataclasses import dataclass

from vapi_integration.customer_identity import normalize_phone
from vapi_integration.customer_repository import Customer, CustomerRepository
from vapi_integration.preference_repository import CustomerPreferences, PreferenceRepository


@dataclass
class CustomerContext:
    customer: Customer | None = None
    preferences: CustomerPreferences | None = None


class CustomerService:
    """Resolve an identity and load its persisted preferences."""

    def __init__(self, customer_repository: CustomerRepository | None = None,
                 preference_repository: PreferenceRepository | None = None) -> None:
        self.customers = customer_repository or CustomerRepository()
        self.preferences = preference_repository or PreferenceRepository()

    def resolve_for_phone(self, phone: str | None) -> CustomerContext:
        normalized = normalize_phone(phone)
        if not normalized:
            return CustomerContext()
        customer = self.customers.get_or_create_by_phone(normalized)
        return CustomerContext(customer, self.preferences.get(customer.customer_id))

    def resolve_for_customer_id(self, customer_id: str | None) -> CustomerContext:
        if not customer_id:
            return CustomerContext()
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            return CustomerContext()
        return CustomerContext(customer, self.preferences.get(customer.customer_id))

    def list_customers(self, limit: int = 100) -> list[Customer]:
        return self.customers.list_customers(limit)

    def create_or_get_test_customer(
        self,
        *,
        full_name: str | None,
        email: str | None,
        phone: str,
    ) -> CustomerContext:
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError("A valid Pakistani mobile phone is required")
        normalized_email = email.strip().lower() if email and email.strip() else None
        customer = self.customers.get_by_phone(normalized)
        if customer is None and normalized_email:
            customer = self.customers.get_by_email(normalized_email)
        if customer is None:
            customer = self.customers.create(
                full_name=full_name.strip() if full_name and full_name.strip() else None,
                email=normalized_email,
                phone_normalized=normalized,
            )
        elif full_name and full_name.strip() and customer.full_name != full_name.strip():
            customer = self.customers.update_name(customer.customer_id, full_name.strip())
        return CustomerContext(customer, self.preferences.get(customer.customer_id))

    def create_web_customer(self, *, full_name: str | None, email: str, phone: str) -> CustomerContext:
        """Create a fresh web identity; never link on unverified contact strings."""
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError("A valid Pakistani mobile phone is required")
        normalized_email = email.strip().casefold()
        if self.customers.get_by_phone(normalized) or self.customers.get_by_email(normalized_email):
            raise ValueError("Existing customer identity requires verified account recovery")
        customer = self.customers.create(
            full_name=full_name.strip() if full_name and full_name.strip() else None,
            email=normalized_email, phone_normalized=normalized,
        )
        return CustomerContext(customer, self.preferences.get(customer.customer_id))

    def update_preferences(self, customer_id: str, updates: dict[str, object]) -> CustomerPreferences:
        return self.preferences.update_partial(customer_id, updates)

    def update_name(self, customer_id: str, full_name: str) -> Customer:
        return self.customers.update_name(customer_id, full_name)
