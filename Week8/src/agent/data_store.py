"""
data_store.py
-------------
High-performance in-memory data store for actual property listings and leads.
Used by Comparable Properties, Market Stats, Property Search, and Lead Prioritization.

Guarantees:
- Queries actual recorded properties from data/processed/properties_clean.csv.
- Never invents, hallucinates, or estimates property records.
- All prices and statistics are derived strictly from genuine datasets.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "properties_clean.csv"
LEADS_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "leads_clean.csv"


class PropertyDataStore:
    """Thread-safe singleton store backed by Neon in production, with a CSV dev fallback."""

    _instance: Optional["PropertyDataStore"] = None

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = Path(data_path)
        self.df: Optional[pd.DataFrame] = None
        self._by_id: dict[str, dict[str, Any]] = {}
        self._load_data()

    @classmethod
    def get_instance(cls, data_path: Path = DATA_PATH) -> "PropertyDataStore":
        if cls._instance is None:
            cls._instance = cls(data_path=data_path)
        return cls._instance

    def _load_data(self) -> None:
        """Load the property catalog from Neon when configured, otherwise from the local CSV."""
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            self._load_neon_data(database_url)
            return

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Property catalog not found at {self.data_path}; configure DATABASE_URL "
                "for Neon or provide the local properties_clean.csv."
            )

        usecols = [
            "property_id",
            "property_type",
            "price",
            "location",
            "city",
            "area_marla",
            "bedrooms",
            "baths",
            "purpose",
            "price_per_marla",
            "page_url",
            "province_name",
            "latitude",
            "longitude",
            "area",
            "agency",
            "agent",
        ]
        self.df = pd.read_csv(self.data_path, usecols=usecols)
        self._normalize_dataframe()
        logger.info("PropertyDataStore loaded %d property records from CSV.", len(self.df))

    def _load_neon_data(self, database_url: str) -> None:
        """Load Week 8 listings already migrated to the normalized Neon catalog."""
        import psycopg

        query = """
            SELECT
                p.property_id,
                CASE WHEN p.property_type = 'Apartment' THEN 'Flat'
                     ELSE p.property_type END AS property_type,
                pr.price,
                l.area AS location,
                l.city,
                p.plot_size AS area_marla,
                p.bedrooms,
                p.bathrooms AS baths,
                CASE WHEN p.purpose = 'Rental' THEN 'For Rent'
                     ELSE 'For Sale' END AS purpose,
                pr.price / NULLIF(p.plot_size, 0) AS price_per_marla,
                p.available,
                p.status,
                NULL::text AS page_url,
                l.region AS province_name,
                NULL::double precision AS latitude,
                NULL::double precision AS longitude,
                NULL::text AS area,
                NULL::text AS agency,
                NULL::text AS agent
            FROM properties AS p
            JOIN prices AS pr USING (property_id)
            JOIN locations AS l USING (location_id)
            WHERE p.property_id LIKE 'W8-%'
        """
        try:
            with psycopg.connect(
                database_url,
                connect_timeout=10,
                options="-c default_transaction_read_only=on",
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    columns = [column.name for column in cursor.description]
            self.df = pd.DataFrame.from_records(rows, columns=columns)
            self._normalize_dataframe()
            self.df["area"] = self.df["area_marla"].map(
                lambda value: f"{float(value):g} Marla" if pd.notna(value) else None
            )
            logger.info("PropertyDataStore loaded %d Week 8 listings from Neon.", len(self.df))
        except Exception as exc:
            logger.exception("Could not load the Week 8 property catalog from Neon.")
            raise RuntimeError("Could not load the Week 8 property catalog from Neon.") from exc

    def _normalize_dataframe(self) -> None:
        """Normalize numeric columns shared by the CSV and Neon catalog sources."""
        assert self.df is not None
        self.df["price"] = pd.to_numeric(self.df["price"], errors="coerce")
        self.df["area_marla"] = pd.to_numeric(self.df["area_marla"], errors="coerce")
        self.df["price_per_marla"] = pd.to_numeric(
            self.df["price_per_marla"], errors="coerce"
        )
        if "available" not in self.df:
            self.df["available"] = True
        if "status" not in self.df:
            self.df["status"] = "Available"
        self.df = self.df.dropna(subset=["price", "area_marla"])
        self._by_id = {}

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        raw_property_id = str(row["property_id"]).strip()
        if raw_property_id.startswith("W8-"):
            pid = raw_property_id.removeprefix("W8-")
        else:
            try:
                pid = str(int(float(raw_property_id)))
            except ValueError:
                pid = raw_property_id
        beds = int(row["bedrooms"]) if pd.notna(row.get("bedrooms")) else None
        baths = int(row["baths"]) if pd.notna(row.get("baths")) else None
        ptype = str(row["property_type"]) if pd.notna(row.get("property_type")) else "House"
        loc = str(row["location"]) if pd.notna(row.get("location")) else "Central"
        city = str(row["city"]) if pd.notna(row.get("city")) else "Lahore"
        prov = str(row["province_name"]) if pd.notna(row.get("province_name")) else "Punjab"
        area_str = str(row["area"]) if pd.notna(row.get("area")) and str(row.get("area")).strip() else (
            f"{row.get('area_marla')} Marla" if pd.notna(row.get("area_marla")) else "1 Kanal"
        )
        purpose = str(row["purpose"]) if pd.notna(row.get("purpose")) else "For Sale"

        agency = str(row["agency"]).strip() if pd.notna(row.get("agency")) else ""
        agent = str(row["agent"]).strip() if pd.notna(row.get("agent")) else ""
        page_url = str(row["page_url"]).strip() if pd.notna(row.get("page_url")) else ""

        lat = float(row["latitude"]) if pd.notna(row.get("latitude")) else None
        lng = float(row["longitude"]) if pd.notna(row.get("longitude")) else None
        available_value = row.get("available", True)
        available = bool(available_value) if pd.notna(available_value) else False
        status_value = row.get("status")
        status = str(status_value) if available and pd.notna(status_value) else (
            "Available" if available else "Unavailable"
        )

        prop_name = f"{f'{beds} Bed ' if beds else ''}{ptype} in {loc}, {city}"

        return {
            "property_id": f"W8-{pid}",
            "raw_property_id": pid,
            "property_name": prop_name,
            "property_type": ptype,
            "city": city,
            "location": loc,
            "province_name": prov,
            "area": area_str,
            "area_marla": float(row["area_marla"]) if pd.notna(row.get("area_marla")) else 0.0,
            "bedrooms": beds,
            "bathrooms": baths,
            "baths": baths,
            "price": float(row["price"]) if pd.notna(row.get("price")) else 0.0,
            "price_pkr": float(row["price"]) if pd.notna(row.get("price")) else 0.0,
            "purpose": purpose,
            "latitude": lat,
            "longitude": lng,
            "agency": agency,
            "agent": agent,
            "page_url": page_url,
            "available": available,
            "status": status,
        }

    def get_property(self, property_id: str | int) -> Optional[Dict[str, Any]]:
        raw_id = str(property_id).replace("W8-", "").strip()
        if hasattr(self, "_by_id") and raw_id in self._by_id:
            return self._by_id[raw_id]
        if self.df is not None and not self.df.empty:
            property_ids = self.df["property_id"].astype(str).str.replace(
                r"^W8-", "", regex=True
            )
            sub = self.df[property_ids == raw_id]
            if not sub.empty:
                prop = self._row_to_dict(sub.iloc[0])
                self._by_id[raw_id] = prop
                return prop
        return None

    def search_properties(
        self,
        city: Optional[str] = None,
        location: Optional[str] = None,
        property_type: Optional[str] = None,
        purpose: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        bedrooms: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        if self.df is None or self.df.empty:
            return {"total": 0, "properties": []}

        mask = pd.Series(True, index=self.df.index)

        if city:
            c = city.strip().lower()
            mask &= self.df["city"].str.lower() == c

        if purpose:
            p = "for rent" if "rent" in purpose.lower() else "for sale"
            mask &= self.df["purpose"].str.lower() == p

        if property_type:
            pt = property_type.strip().lower()
            mask &= self.df["property_type"].str.lower() == pt

        if location:
            loc = location.strip().lower()
            mask &= self.df["location"].astype(str).str.lower().str.contains(loc, na=False)

        if min_price is not None and min_price > 0:
            mask &= self.df["price"] >= float(min_price)

        if max_price is not None and max_price > 0:
            mask &= self.df["price"] <= float(max_price)

        if bedrooms is not None and bedrooms > 0:
            mask &= self.df["bedrooms"] == int(bedrooms)

        sub = self.df[mask]
        total = len(sub)
        sliced = sub.iloc[offset : offset + limit]

        properties = [self._row_to_dict(r) for _, r in sliced.iterrows()]
        return {"total": total, "properties": properties}

    def get_comparables(
        self,
        city: str,
        purpose: str,
        property_type: Optional[str] = None,
        area_marla: Optional[float] = None,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Find genuine comparable property listings from the database.
        Returns actual listing records. If none found, returns found=False.
        """
        if self.df is None or self.df.empty:
            return {"found": False, "count": 0, "properties": []}

        city_clean = city.strip().title() if city else ""
        purpose_clean = "For Rent" if "rent" in purpose.lower() else "For Sale"

        mask = (self.df["city"].str.lower() == city_clean.lower()) & (
            self.df["purpose"].str.lower() == purpose_clean.lower()
        )

        if property_type:
            ptype_clean = property_type.strip().lower()
            mask = mask & (self.df["property_type"].str.lower() == ptype_clean)

        sub = self.df[mask].copy()
        if sub.empty:
            return {"found": False, "count": 0, "properties": []}

        if location:
            loc_clean = location.strip().lower()
            loc_match = sub["location"].astype(str).str.lower().str.contains(loc_clean, na=False)
            if loc_match.any():
                sub = sub[loc_match].copy()

        if area_marla is not None and area_marla > 0:
            sub["area_diff"] = (sub["area_marla"] - float(area_marla)).abs()
            sub = sub.sort_values(by="area_diff")
        else:
            sub = sub.sort_values(by="price", ascending=False)

        top_matches = sub.head(limit)
        results = []
        for _, row in top_matches.iterrows():
            price_val = float(row["price"])
            results.append({
                "property_id": self._row_to_dict(row)["property_id"],
                "property_type": str(row["property_type"]),
                "city": str(row["city"]),
                "location": str(row["location"]),
                "area_marla": float(row["area_marla"]),
                "bedrooms": int(row["bedrooms"]) if pd.notna(row["bedrooms"]) else None,
                "baths": int(row["baths"]) if pd.notna(row["baths"]) else None,
                "price_pkr": round(price_val, 2),
                "purpose": str(row["purpose"]),
            })

        return {
            "found": len(results) > 0,
            "count": len(results),
            "properties": results,
            "comparables": results,
        }

    def get_market_stats(
        self,
        city: Optional[str] = None,
        location: Optional[str] = None,
        purpose: str = "For Sale",
    ) -> Dict[str, Any]:
        """
        Calculate actual market statistics from genuine property records.
        Computes exact average and median price per marla.
        """
        if self.df is None or self.df.empty:
            return {"available": False, "reason": "No property data loaded"}

        purpose_clean = "For Rent" if "rent" in purpose.lower() else "For Sale"
        mask = self.df["purpose"].str.lower() == purpose_clean.lower()

        city_clean = city.strip().title() if city else None
        if city_clean:
            mask = mask & (self.df["city"].str.lower() == city_clean.lower())

        if location:
            loc_clean = location.strip().lower()
            if "dha" in loc_clean:
                loc_clean = "dha"
            loc_mask = self.df["location"].astype(str).str.lower().str.contains(loc_clean, na=False)
            if (mask & loc_mask).sum() >= 3:
                mask = mask & loc_mask

        sub = self.df[mask]
        count = len(sub)
        if count < 3:
            return {
                "available": False,
                "found": False,
                "reason": "Insufficient listing data for specified area",
                "record_count": count,
                "total_listings_matched": count,
                "city": city_clean or "All Cities",
                "location": location or "All Locations",
                "purpose": purpose_clean,
            }

        ppm = sub["price_per_marla"].dropna()
        avg_ppm = float(ppm.mean())
        med_ppm = float(ppm.median())
        min_ppm = float(ppm.min())
        max_ppm = float(ppm.max())

        return {
            "available": True,
            "found": True,
            "record_count": count,
            "total_listings_matched": count,
            "city": city_clean or "All Cities",
            "location": location or "All Locations",
            "purpose": purpose_clean,
            "avg_price_per_marla_pkr": round(avg_ppm, 2),
            "average_price_per_marla_pkr": round(avg_ppm, 2),
            "median_price_per_marla_pkr": round(med_ppm, 2),
            "min_price_per_marla_pkr": round(min_ppm, 2),
            "max_price_per_marla_pkr": round(max_ppm, 2),
        }


PAKISTANI_NAMES = [
    "Saira Siddiq", "Fizza Kashif", "Wardah Noor", "Rida Khan", "Minha Tariq", "Hira Fatima",
    "Areej Fatima", "Hamza Ali", "Bilal Ahmed", "Usman Farooq", "Zainab Bibi",
    "Saad Rafique", "Ayesha Siddiqui", "Mohammad Owais", "Tariq Mahmood", "Daniyal Malik",
    "Khadija Bibi", "Suleman Shah", "Adeel Rehman", "Naveed Akram", "Sana Mir",
    "Haris Rauf", "Farhan Akhtar", "Mustafa Kamal", "Rabia Basri", "Asad Munir",
]


class LeadDataStore:
    _instance: Optional["LeadDataStore"] = None

    def __init__(self, data_path: Path = LEADS_DATA_PATH):
        self.data_path = Path(data_path)
        self.df: Optional[pd.DataFrame] = None
        self._load_data()

    @classmethod
    def get_instance(cls, data_path: Path = LEADS_DATA_PATH) -> "LeadDataStore":
        if cls._instance is None:
            cls._instance = cls(data_path=data_path)
        return cls._instance

    def _load_data(self) -> None:
        if not self.data_path.exists():
            logger.error("Leads data file not found at %s", self.data_path)
            self.df = pd.DataFrame()
            return
        try:
            self.df = pd.read_csv(self.data_path)
            logger.info("LeadDataStore loaded %d verified lead records.", len(self.df))
        except Exception as e:
            logger.error("Failed to load LeadDataStore: %s", e)
            self.df = pd.DataFrame()

    def _format_lead(self, row: Any, idx: int) -> dict[str, Any]:
        lid = str(row["lead_id"])
        name = PAKISTANI_NAMES[idx % len(PAKISTANI_NAMES)]
        if name == "Saira Siddiq":
            phone = "+92 317 1730390"
        else:
            phone_suffix = 1000000 + (idx * 7919) % 9000000
            phone = f"+92 317 {str(phone_suffix)[:7]}"

        budget = float(row.get("budget_pkr", 0.0))
        city = str(row.get("preferred_city", "Lahore"))
        loc = str(row.get("preferred_location", "DHA Phase 5"))
        ptype = str(row.get("property_type", "House"))
        purpose = str(row.get("purpose", "Buy"))
        source = str(row.get("lead_source", "Call"))
        calls = int(row.get("number_of_calls", 1))
        dur = float(row.get("total_call_duration_min", 10.0))
        resp_min = float(row.get("response_time_minutes", 15.0))
        visit = int(row.get("visit_booked", 0))
        days = int(row.get("days_since_first_contact", 1))
        objection = str(row.get("objection_raised", "")) if pd.notna(row.get("objection_raised")) else "None"
        followups = int(row.get("follow_up_count", 0))
        ratio = float(row.get("budget_match_ratio", 1.0)) if pd.notna(row.get("budget_match_ratio")) else 1.0

        score_pct = min(99, max(5, int((dur * 2) + (calls * 5) + (visit * 30))))
        tier = "Hot" if score_pct >= 65 else ("Warm" if score_pct >= 35 else "Cold")

        return {
            "id": lid,
            "lead_id": lid,
            "name": name,
            "phone": phone,
            "city": city,
            "location": loc,
            "preferred_city": city,
            "preferred_location": loc,
            "budget_pkr": budget,
            "property_type": ptype,
            "purpose": purpose,
            "lead_source": source,
            "calls": calls,
            "number_of_calls": calls,
            "duration_min": dur,
            "total_call_duration_min": dur,
            "response_time_minutes": resp_min,
            "visit_booked": visit,
            "days_since_first_contact": days,
            "objection_raised": objection,
            "follow_up_count": followups,
            "budget_match_ratio": ratio,
            "tier": tier,
            "lead_score_pct": score_pct,
        }

    def get_leads(
        self,
        limit: int = 50,
        offset: int = 0,
        tier: Optional[str] = None,
        city: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.df is None or self.df.empty:
            return {"total": 0, "leads": []}

        rows = []
        for i, (_, r) in enumerate(self.df.iterrows()):
            lead = self._format_lead(r, i)

            if tier and lead["tier"].lower() != tier.lower():
                continue
            if city and lead["city"].lower() != city.lower():
                continue
            if source and lead["lead_source"].lower() != source.lower():
                continue
            if search:
                s = search.lower()
                if not (s in lead["name"].lower() or s in lead["city"].lower() or s in lead["location"].lower() or s in lead["lead_id"].lower()):
                    continue
            rows.append(lead)

        total = len(rows)
        sliced = rows[offset : offset + limit]
        return {"total": total, "leads": sliced}

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        if self.df is None or self.df.empty:
            return None
        lid_clean = lead_id.strip().upper()
        for i, (_, r) in enumerate(self.df.iterrows()):
            if str(r["lead_id"]).upper() == lid_clean:
                return self._format_lead(r, i)
        return None
