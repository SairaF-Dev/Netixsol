from __future__ import annotations

import re
from decimal import Decimal


class ObjectionHandler:
    """
    Grounded objection responses.

    The handler may repeat verified fields from the selected property,
    but never invents market claims, trust claims, ROI or negotiation facts.
    """

    def respond(
        self,
        message: str,
        selected: dict | None,
    ) -> str:
        if not selected:
            return (
                "Ji, concern samajh gayi. Pehle relevant property select kar dein; "
                "phir main uske verified facts ke basis par concern address karungi."
            )

        normalized = " ".join(
            message.casefold().split()
        )

        name = (
            selected.get("property_name")
            or selected.get("name")
            or "selected property"
        )

        if self._has(
            normalized,
            (
                "mehngi",
                "mehnga",
                "expensive",
                "price high",
                "bohat zyada",
                "budget se",
            ),
        ):
            price = selected.get(
                "price"
            )

            if isinstance(
                price,
                (int, float, Decimal),
            ):
                return (
                    f"Ji, {name} ki verified listed price "
                    f"{price:,.0f} {selected.get('currency', 'PKR')} hai. "
                    "Agar ye budget se high hai to main same current requirements "
                    "ke andar cheaper verified alternatives check kar sakti hoon."
                )

            return (
                f"{name} ki verified price current selected record mein available "
                "nahi hai. Main price assume nahi karungi; cheaper alternatives "
                "verified retrieval se hi check hongi."
            )

        if self._has(
            normalized,
            (
                "area pasand nahi",
                "location pasand nahi",
                "door hai",
                "far",
            ),
        ):
            area = selected.get(
                "area"
            )
            city = selected.get(
                "city"
            )

            location = ", ".join(
                value
                for value in (
                    area,
                    city,
                )
                if isinstance(value, str)
                and value.strip()
            )

            return (
                f"Ji. Current selected property ki verified location "
                f"{location or 'record mein unavailable'} hai. "
                "Agar location suitable nahi lag rahi to main area constraint "
                "change/relax karke verified alternatives dhoond sakti hoon."
            )

        if self._has(
            normalized,
            (
                "bedroom kam",
                "bedrooms kam",
                "chhota",
                "chota",
                "small",
            ),
        ):
            bedrooms = selected.get(
                "bedrooms"
            )
            covered = selected.get(
                "covered_area"
            )

            facts = []

            if bedrooms is not None:
                facts.append(
                    f"{bedrooms} bedrooms"
                )

            if covered is not None:
                unit = selected.get(
                    "covered_area_unit"
                )
                facts.append(
                    f"covered area {covered}"
                    + (
                        f" {unit}"
                        if unit
                        else ""
                    )
                )

            return (
                f"Ji. {name} ke verified size-related facts: "
                + (
                    ", ".join(facts)
                    if facts
                    else "current record mein size details unavailable"
                )
                + ". Agar ye requirement se kam hai to bedrooms/size filter "
                  "change karke alternatives check ki ja sakti hain."
            )

        if self._has(
            normalized,
            (
                "developer",
                "builder",
                "trustworthy",
                "trust",
            ),
        ):
            developer = (
                selected.get(
                    "developer_name"
                )
                or selected.get(
                    "developer"
                )
            )

            if developer:
                return (
                    f"Verified record mein developer {developer} listed hai. "
                    "Main developer ki trustworthiness ya reputation bina verified "
                    "support ke claim nahi karungi."
                )

            return (
                "Selected property ke current verified record mein developer detail "
                "available nahi hai, isliye main builder ke bare mein guess nahi karungi."
            )

        if self._has(
            normalized,
            (
                "roi",
                "return",
                "profit",
                "guarantee",
                "investment",
            ),
        ):
            return (
                "Investment return future outcome hai, isliye main guaranteed ROI "
                "ya profit claim nahi karungi. Verified price/location/property facts "
                "aur available investment criteria ke basis par options compare kiye "
                "ja sakte hain."
            )

        if self._has(
            normalized,
            (
                "family se",
                "discuss",
                "sochna",
                "decide nahi",
                "abhi decide",
            ),
        ):
            return (
                "Bilkul. Aap araam se discuss/decide kar sakti hain. "
                "Main pressure nahi dungi; jab chahein current verified options "
                "dobara compare ya refine kar sakti hain."
            )

        return (
            f"Ji, {name} ke concern ko facts ke basis par dekhte hain. "
            "Main price, location, developer, maintenance ya investment return "
            "assume nahi karungi. Jo verified data available hai usi se "
            "comparison ya alternative dhoond sakti hoon."
        )

    def _has(
        self,
        text: str,
        markers: tuple[str, ...],
    ) -> bool:
        return any(
            marker in text
            for marker in markers
        )
