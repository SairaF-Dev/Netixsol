from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ComparisonRequest:
    field: str | None = None
    operator: str | None = None
    reference: str | None = None
    value: int | float | None = None


@dataclass
class UserUnderstanding:
    intent: str = "unknown"
    required: dict[str, Any] = field(default_factory=dict)
    preferred: dict[str, Any] = field(default_factory=dict)
    excluded: dict[str, list[Any]] = field(default_factory=dict)
    relax: list[str] = field(default_factory=list)
    reference_type: str | None = None
    selected_index: int | None = None
    comparison: ComparisonRequest = field(default_factory=ComparisonRequest)
    needs_clarification: bool = False
    clarification_reason: str | None = None
    raw_message: str = ""


@dataclass
class QueryPlan:
    required: dict[str, Any] = field(default_factory=dict)
    preferred: dict[str, Any] = field(default_factory=dict)
    excluded: dict[str, list[Any]] = field(default_factory=dict)
    comparison_field: str | None = None
    comparison_operator: str | None = None
    comparison_value: int | float | Decimal | None = None
    selected_property: dict[str, Any] | None = None
    needs_clarification: bool = False
    clarification_reason: str | None = None
