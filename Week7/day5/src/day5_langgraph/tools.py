"""Tool definitions for the LangGraph agent."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base class for tool inputs."""

    pass


class SearchPropertiesInput(ToolInput):
    """Input for property search tool."""

    location: str = Field(description="Location (city or area)")
    min_price: int = Field(default=0, description="Minimum price")
    max_price: int = Field(default=1000000000, description="Maximum price")
    bedrooms: int | None = Field(default=None, description="Number of bedrooms")
    purpose: str = Field(default="all", description="Purpose: buy, rent, invest, commercial")
    limit: int = Field(default=5, description="Number of results to return")


class GetPropertyDetailsInput(ToolInput):
    """Input for getting property details."""

    property_id: str | int = Field(description="Property ID")


class BookAppointmentInput(ToolInput):
    """Input for booking appointment."""

    client_name: str = Field(description="Client name")
    client_phone: str = Field(description="Client phone number")
    employee_name: str = Field(description="Employee name")
    employee_email: str = Field(description="Employee email")
    property_id: str | int = Field(description="Property ID")
    property_name: str = Field(description="Property name")
    starts_at: str = Field(description="ISO format datetime with timezone")
    duration_minutes: int = Field(default=60, description="Duration in minutes")
    meeting_notes: str = Field(default="", description="Meeting notes")


class RescheduleAppointmentInput(ToolInput):
    """Input for rescheduling appointment."""

    appointment_id: str = Field(description="Appointment ID (UUID)")
    starts_at: str = Field(description="New ISO format datetime with timezone")


class CancelAppointmentInput(ToolInput):
    """Input for canceling appointment."""

    appointment_id: str = Field(description="Appointment ID (UUID)")


class GetCustomerHistoryInput(ToolInput):
    """Input for retrieving customer history."""

    phone: str = Field(description="Customer phone number")
    limit: int = Field(default=10, description="Number of records to return")


class RAGSearchInput(ToolInput):
    """Input for verified semantic document retrieval."""

    question: str = Field(min_length=1, description="Property or company question")


# Tool definitions for LangGraph
TOOLS_DEFINITION = [
    {
        "name": "search_properties",
        "description": "Search for properties based on location, price, and preferences",
        "input_type": SearchPropertiesInput,
    },
    {
        "name": "get_property_details",
        "description": "Get detailed information about a specific property",
        "input_type": GetPropertyDetailsInput,
    },
    {
        "name": "book_appointment",
        "description": "Book a property visit appointment",
        "input_type": BookAppointmentInput,
    },
    {
        "name": "reschedule_appointment",
        "description": "Reschedule an existing appointment to a new time",
        "input_type": RescheduleAppointmentInput,
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment",
        "input_type": CancelAppointmentInput,
    },
    {
        "name": "get_customer_history",
        "description": "Retrieve customer's appointment and interaction history",
        "input_type": GetCustomerHistoryInput,
    },
    {
        "name": "search_rag",
        "description": "Answer FAQs and brochure questions from verified documents",
        "input_type": RAGSearchInput,
    },
]


class ToolExecutor:
    """Executes tools by calling appropriate APIs."""

    def __init__(
        self,
        day4_api_url: str,
        day4_timeout: float = 10.0,
        *,
        property_repository: Any = None,
        rag_pipeline: Any = None,
    ):
        self.day4_api_url = day4_api_url.rstrip("/")
        self.day4_timeout = day4_timeout
        self._property_repository = property_repository
        self._rag_pipeline = rag_pipeline

    def _repository(self) -> Any:
        """Load the finalized Day 2 PostgreSQL repository lazily."""
        if self._property_repository is None:
            day2_dir = Path(
                os.getenv("DAY2_ROOT", Path(__file__).resolve().parents[3] / "day2")
            )
            structured_dir = str(day2_dir / "03_structured_retrieval")
            if structured_dir not in sys.path:
                sys.path.insert(0, structured_dir)
            from postgres_repository import PostgresPropertyRepository

            self._property_repository = PostgresPropertyRepository()
        return self._property_repository

    def _rag(self) -> Any:
        """Load the finalized Day 2 RAG pipeline lazily."""
        if self._rag_pipeline is None:
            day2_dir = Path(
                os.getenv("DAY2_ROOT", Path(__file__).resolve().parents[3] / "day2")
            )
            rag_dir = str(day2_dir / "02_rag")
            if rag_dir not in sys.path:
                sys.path.insert(0, rag_dir)
            from rag_pipeline import RAGPipeline

            self._rag_pipeline = RAGPipeline()
        return self._rag_pipeline

    async def search_properties(self, **kwargs) -> dict[str, Any]:
        """Search for properties."""
        input_data = SearchPropertiesInput(**kwargs)
        location = input_data.location.strip()
        city = location if location.lower() not in {"", "all"} else None
        properties = await asyncio.to_thread(
            self._repository().search,
            budget=input_data.max_price,
            city=city,
            area=None,
            bedrooms=input_data.bedrooms,
            purpose=None if input_data.purpose == "all" else input_data.purpose,
            limit=input_data.limit,
        )
        return {
            "properties": properties,
            "count": len(properties),
            "filters_applied": {
                "location": input_data.location,
                "min_price": input_data.min_price,
                "max_price": input_data.max_price,
            },
        }

    async def get_property_details(self, **kwargs) -> dict[str, Any]:
        """Get property details."""
        input_data = GetPropertyDetailsInput(**kwargs)
        result = await asyncio.to_thread(
            self._repository().get_property, str(input_data.property_id)
        )
        return result or {"error": "Property not found", "status": "not_found"}

    async def search_rag(self, question: str) -> dict[str, Any]:
        """Answer a semantic property question from verified Day 2 documents."""
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question is required")
        return await asyncio.to_thread(self._rag().answer, question.strip())

    async def book_appointment(self, **kwargs) -> dict[str, Any]:
        """Book appointment via Day 4 API."""
        input_data = BookAppointmentInput(**kwargs)

        async with httpx.AsyncClient(timeout=self.day4_timeout) as client:
            try:
                response = await client.post(
                    f"{self.day4_api_url}/appointments",
                    json=input_data.model_dump(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {"error": str(e), "status": "failed"}

    async def reschedule_appointment(self, **kwargs) -> dict[str, Any]:
        """Reschedule appointment via Day 4 API."""
        input_data = RescheduleAppointmentInput(**kwargs)

        async with httpx.AsyncClient(timeout=self.day4_timeout) as client:
            try:
                response = await client.patch(
                    f"{self.day4_api_url}/appointments/{input_data.appointment_id}/reschedule",
                    json={"starts_at": input_data.starts_at},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {"error": str(e), "status": "failed"}

    async def cancel_appointment(self, **kwargs) -> dict[str, Any]:
        """Cancel appointment via Day 4 API."""
        input_data = CancelAppointmentInput(**kwargs)

        async with httpx.AsyncClient(timeout=self.day4_timeout) as client:
            try:
                response = await client.delete(
                    f"{self.day4_api_url}/appointments/{input_data.appointment_id}"
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {"error": str(e), "status": "failed"}

    async def get_customer_history(self, **kwargs) -> dict[str, Any]:
        """Get customer history."""
        input_data = GetCustomerHistoryInput(**kwargs)
        async with httpx.AsyncClient(timeout=self.day4_timeout) as client:
            try:
                response = await client.get(
                    f"{self.day4_api_url}/customers/history",
                    params={"phone": input_data.phone, "limit": input_data.limit},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                return {"error": str(exc), "status": "failed"}

    async def execute(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool by name."""
        if tool_name == "search_properties":
            return await self.search_properties(**kwargs)
        elif tool_name == "get_property_details":
            return await self.get_property_details(**kwargs)
        elif tool_name == "book_appointment":
            return await self.book_appointment(**kwargs)
        elif tool_name == "reschedule_appointment":
            return await self.reschedule_appointment(**kwargs)
        elif tool_name == "cancel_appointment":
            return await self.cancel_appointment(**kwargs)
        elif tool_name == "get_customer_history":
            return await self.get_customer_history(**kwargs)
        elif tool_name == "search_rag":
            return await self.search_rag(**kwargs)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
