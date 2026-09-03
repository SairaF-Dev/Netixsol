from __future__ import annotations

from decimal import Decimal
import re
from typing import Any


class VerifiedComparisonPolicy:
    """
    Compare only fields already present in verified property result rows.

    The policy does not decide a winner unless the user supplies a
    comparison criterion. Missing fields are shown as unavailable.
    """

    FIELD_SPECS = (
        ("price", "Price"),
        ("area", "Area"),
        ("city", "City"),
        ("property_type", "Property type"),
        ("bedrooms", "Bedrooms"),
        ("bathrooms", "Bathrooms"),
        ("plot_size", "Plot size"),
        ("covered_area", "Covered area"),
        ("developer_name", "Developer"),
        ("amenities", "Amenities"),
        ("available", "Availability"),
        ("status", "Status"),
    )

    def parse_pair(
        self,
        text: str,
        result_count: int,
    ) -> tuple[int, int] | None:
        if result_count < 2:
            return None

        normalized = " ".join(
            text.casefold().split()
        )

        if not self._looks_like_compare(
            normalized
        ):
            return None

        numbers = [
            int(value) - 1
            for value in re.findall(
                r"(?<!\d)(\d{1,2})(?!\d)",
                normalized,
            )
            if int(value) >= 1
        ]

        if len(numbers) >= 2:
            left, right = numbers[:2]

            if (
                0 <= left < result_count
                and 0 <= right < result_count
                and left != right
            ):
                return (
                    left,
                    right,
                )

        ordinal_map = {
            "first": 0,
            "pehla": 0,
            "pehli": 0,
            "second": 1,
            "dusra": 1,
            "dusri": 1,
            "doosra": 1,
            "doosri": 1,
            "third": 2,
            "teesra": 2,
            "teesri": 2,
            "fourth": 3,
            "chautha": 3,
            "chauthi": 3,
            "fifth": 4,
            "panchwa": 4,
            "panchwi": 4,
        }

        found = []

        for word, index in ordinal_map.items():
            if re.search(
                rf"\b{re.escape(word)}\b",
                normalized,
            ):
                if index not in found:
                    found.append(index)

        if len(found) >= 2:
            left, right = found[:2]

            if (
                left < result_count
                and right < result_count
            ):
                return (
                    left,
                    right,
                )

        return None

    def asks_better_without_basis(
        self,
        text: str,
        result_count: int,
    ) -> bool:
        if result_count < 2:
            return False

        normalized = " ".join(
            text.casefold().split()
        )

        if not re.search(
            r"\b(?:best|better|behtar|acha|achha|sab se acha)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return False

        explicit_basis = (
            "price",
            "sasta",
            "cheap",
            "budget",
            "bedroom",
            "size",
            "amenity",
            "gym",
            "parking",
            "location",
            "area",
            "developer",
            "payment",
            "rent",
            "investment",
        )

        return not any(
            basis in normalized
            for basis in explicit_basis
        )

    def format_comparison(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        *,
        left_label: str = "Option 1",
        right_label: str = "Option 2",
    ) -> str:
        left_name = (
            left.get("property_name")
            or left.get("name")
            or left_label
        )
        right_name = (
            right.get("property_name")
            or right.get("name")
            or right_label
        )

        lines = [
            f"Ji. {left_name} aur {right_name} ka verified comparison:",
        ]

        compared = 0

        for field, label in self.FIELD_SPECS:
            left_value = self._format_value(
                field,
                left.get(field),
                left,
            )
            right_value = self._format_value(
                field,
                right.get(field),
                right,
            )

            if (
                left_value is None
                and right_value is None
            ):
                continue

            compared += 1

            lines.append(
                f"- {label}: {left_name} = "
                f"{left_value or 'verified value unavailable'}; "
                f"{right_name} = "
                f"{right_value or 'verified value unavailable'}"
            )

        if compared == 0:
            return (
                "In dono options ke comparison ke liye shared verified fields "
                "current result data mein available nahi hain."
            )

        lines.append(
            "Main winner assume nahi karungi. Agar aap price, location, "
            "bedrooms ya amenities ko priority batayein to us basis par "
            "verified comparison explain kar sakti hoon."
        )

        return "\n".join(lines)

    def _looks_like_compare(
        self,
        text: str,
    ) -> bool:
        return bool(
            re.search(
                r"\b(?:compare|comparison|vs|versus|muqabla)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _format_value(
        self,
        field: str,
        value: Any,
        row: dict[str, Any],
    ) -> str | None:
        if value is None:
            return None

        if field == "price":
            if isinstance(
                value,
                (int, float, Decimal),
            ):
                return (
                    f"{value:,.0f} "
                    f"{row.get('currency', 'PKR')}"
                )

        if field == "available":
            if value is True:
                return "Available"
            if value is False:
                return "Not available"

        if isinstance(
            value,
            list,
        ):
            return ", ".join(
                str(item)
                for item in value
            )

        return str(value)
