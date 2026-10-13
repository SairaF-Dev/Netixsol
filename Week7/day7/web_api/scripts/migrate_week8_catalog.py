"""
Import the Week 8 catalog into PostgreSQL as historical, non-public data.

Existing user accounts, sessions, CRM records, appointments, and historical
property references are preserved. Existing Week 7 properties are archived.

Usage:
    python migrate_week8_catalog.py
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import os
from pathlib import Path
import re
import time

import pandas as pd
import psycopg

# Paths
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_WEEK8_CSV_PATH = REPOSITORY_ROOT / "Week8" / "data" / "processed" / "properties_clean.csv"
WEEK8_CSV_PATH = Path(os.getenv("WEEK8_CSV_PATH", str(DEFAULT_WEEK8_CSV_PATH)))

# City prefixes for generated location IDs
CITY_PREFIXES = {
    "Lahore": "LHR",
    "Karachi": "KHI",
    "Islamabad": "ISB",
    "Rawalpindi": "RWP",
    "Faisalabad": "FSD",
}

def make_clean_slug(text: str) -> str:
    """Creates an uppercase alphanumeric slug with dashes."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", str(text).strip()).strip("-").upper()
    return cleaned or "AREA"


def run_migration():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL must be configured before running the catalog migration")
    print("=" * 70)
    print("IMPORTING WEEK 8 HISTORICAL PROPERTY CATALOG")
    print("=" * 70)
    print("Target Database: configured PostgreSQL connection")
    print(f"Source Dataset:  {WEEK8_CSV_PATH}")

    if not WEEK8_CSV_PATH.is_file():
        raise FileNotFoundError(f"Week 8 CSV dataset not found at {WEEK8_CSV_PATH}")

    conn = psycopg.connect(db_url, autocommit=False)

    try:
        with conn.cursor() as cur:
            # ---------------------------------------------------------
            # 0. BASELINE AUDIT
            # ---------------------------------------------------------
            print("\n[Step 0] Recording baseline table counts...")
            cur.execute("SELECT count(*) FROM auth_users;")
            initial_users = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM customers;")
            initial_customers = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM customer_preferences;")
            initial_prefs = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM properties WHERE property_id NOT LIKE 'W8-%';")
            initial_w7_props = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM prices WHERE property_id NOT LIKE 'W8-%';")
            initial_w7_prices = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM properties WHERE property_id LIKE 'W8-%';")
            if cur.fetchone()[0]:
                raise RuntimeError(
                    "Week 8 properties already exist. Refusing to replace rows with "
                    "possible customer-history references."
                )

            print(f"  auth_users:           {initial_users}")
            print(f"  customers:            {initial_customers}")
            print(f"  customer_preferences: {initial_prefs}")
            print(f"  Existing properties to archive: {initial_w7_props}")

            # ---------------------------------------------------------
            # 2. READ CSV AND MAP LOCATIONS
            # ---------------------------------------------------------
            print("\n[Step 2] Reading Week 8 property dataset...")
            t0 = time.time()
            df = pd.read_csv(WEEK8_CSV_PATH)
            read_duration = time.time() - t0
            print(f"  Loaded {len(df):,} listings in {read_duration:.2f}s.")

            # Load existing locations
            cur.execute("SELECT location_id, area, city FROM locations;")
            existing_loc_pairs = {}
            used_loc_ids = set()
            for loc_id, area, city in cur.fetchall():
                existing_loc_pairs[(city.strip().lower(), area.strip().lower())] = loc_id
                used_loc_ids.add(loc_id)

            print(f"  Existing DB locations: {len(existing_loc_pairs)}")

            # Identify unique locations in Week 8
            w8_loc_pairs = df[["city", "location", "province_name"]].drop_duplicates()
            print(f"  Unique (city, location) pairs in Week 8: {len(w8_loc_pairs)}")

            loc_id_map: dict[tuple[str, str], str] = {}
            new_locations_to_insert = []

            for _, row in w8_loc_pairs.iterrows():
                city = str(row["city"]).strip()
                loc = str(row["location"]).strip()
                prov = str(row["province_name"]).strip() if pd.notna(row["province_name"]) else "Pakistan"
                pair_key = (city.lower(), loc.lower())

                if pair_key in existing_loc_pairs:
                    loc_id_map[(city, loc)] = existing_loc_pairs[pair_key]
                else:
                    c_pfx = CITY_PREFIXES.get(city, city[:3].upper())
                    slug = make_clean_slug(loc)[:30]
                    cand_id = f"LOC-{c_pfx}-{slug}"

                    if cand_id in used_loc_ids:
                        h = hashlib.md5(f"{city}:{loc}".encode()).hexdigest()[:6].upper()
                        cand_id = f"LOC-{c_pfx}-{slug[:23]}-{h}"

                    used_loc_ids.add(cand_id)
                    loc_id_map[(city, loc)] = cand_id
                    new_locations_to_insert.append(
                        (cand_id, loc, city, loc, "Residential", prov)
                    )

            if new_locations_to_insert:
                print(f"  Inserting {len(new_locations_to_insert)} new locations...")
                cur.executemany(
                    """
                    INSERT INTO locations (location_id, area, city, zone, classification, region)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (location_id) DO NOTHING;
                    """,
                    new_locations_to_insert,
                )
                print(f"  [OK] New locations inserted.")

            # ---------------------------------------------------------
            # 3. CLEAN PRIOR W8 RECORDS (IDEMPOTENCY)
            # ---------------------------------------------------------
            print("\n[Step 3] Archiving previous catalog records...")
            cur.execute(
                """
                UPDATE properties
                SET available = FALSE, status = 'Archived'
                WHERE property_id NOT LIKE 'W8-%';
                """
            )
            cur.execute(
                """
                UPDATE prices
                SET verification_status = 'Historical'
                WHERE property_id NOT LIKE 'W8-%';
                """
            )
            print("  [OK] Old listings archived; historical records remain intact.")

            # ---------------------------------------------------------
            # 4. PREPARE STREAMING DATA
            # ---------------------------------------------------------
            print("\n[Step 4] Transforming Week 8 dataset rows into relational entities...")
            t_transform = time.time()

            prop_rows = []
            price_rows = []
            amenity_rows = []
            agent_prop_rows = []

            for _, r in df.iterrows():
                p_num = int(r["property_id"])
                p_id = f"W8-{p_num}"
                city = str(r["city"]).strip()
                loc = str(r["location"]).strip()
                loc_id = loc_id_map[(city, loc)]

                raw_type = str(r["property_type"]).strip()
                prop_type = "Apartment" if raw_type == "Flat" else raw_type

                purpose_val = "Purchase" if str(r["purpose"]).strip() == "For Sale" else "Rental"
                price_period = "One-time" if purpose_val == "Purchase" else "Monthly"

                beds = int(r["bedrooms"])
                baths = int(r["baths"])

                # Name formatting
                if beds > 0:
                    name = f"{beds} Bed {prop_type} in {loc}, {city}"
                else:
                    area_label = str(r["area"]).strip() if pd.notna(r["area"]) else "Prime"
                    name = f"{area_label} {prop_type} in {loc}, {city}"

                plot_size = round(float(r["area_marla"]), 2) if pd.notna(r["area_marla"]) else None
                plot_unit = "Marla" if plot_size is not None else None

                covered_area = float(r["covered_area_sqft"])
                covered_area_unit = "sqft"

                # Properties row
                prop_rows.append((
                    p_id,
                    name,
                    loc_id,
                    prop_type,
                    beds,
                    baths,
                    plot_size,
                    plot_unit,
                    covered_area,
                    covered_area_unit,
                    False,           # historical listings are not current inventory
                    "Historical",    # status
                    None,            # developer_id
                    purpose_val,     # purpose
                ))

                # Prices row
                price_val = Decimal(str(int(r["price"])))
                price_rows.append((
                    p_id,
                    price_val,
                    "PKR",
                    purpose_val,
                    price_period,
                    None,
                    "Historical",
                ))

                # Amenities rows
                if r.get("parking") == 1:
                    amenity_rows.append((p_id, "Parking", None))
                if r.get("security") == 1:
                    amenity_rows.append((p_id, "Security", None))
                if r.get("electricity_backup") == 1:
                    amenity_rows.append((p_id, "Backup Power", None))
                if r.get("park_nearby") == 1 or r.get("park_facing") == 1:
                    amenity_rows.append((p_id, "Community Park", None))
                if r.get("is_furnished") == 1:
                    amenity_rows.append((p_id, "Furnished", None))

            print(f"  Transform complete in {time.time() - t_transform:.2f}s:")
            print(f"    - Properties:       {len(prop_rows):,}")
            print(f"    - Prices:           {len(price_rows):,}")
            print(f"    - Amenities:        {len(amenity_rows):,}")
            print(f"    - Agent properties: {len(agent_prop_rows):,}")

            # ---------------------------------------------------------
            # 5. STREAMING COPY TO POSTGRESQL
            # ---------------------------------------------------------
            print("\n[Step 5] Streaming bulk data into PostgreSQL using COPY...")

            # 5a. Properties
            t_copy = time.time()
            with cur.copy(
                """
                COPY properties (
                    property_id, name, location_id, property_type,
                    bedrooms, bathrooms, plot_size, plot_unit,
                    covered_area, covered_area_unit, available,
                    status, developer_id, purpose
                ) FROM STDIN
                """
            ) as copy:
                for row in prop_rows:
                    copy.write_row(row)
            print(f"  [OK] Streamed {len(prop_rows):,} properties in {time.time() - t_copy:.2f}s.")

            # 5b. Prices
            t_copy = time.time()
            with cur.copy(
                """
                COPY prices (
                    property_id, price, currency, transaction_type,
                    price_period, verified_on, verification_status
                ) FROM STDIN
                """
            ) as copy:
                for row in price_rows:
                    copy.write_row(row)
            print(f"  [OK] Streamed {len(price_rows):,} prices in {time.time() - t_copy:.2f}s.")

            # 5c. Amenities
            t_copy = time.time()
            with cur.copy(
                """
                COPY amenities (
                    property_id, amenity, details
                ) FROM STDIN
                """
            ) as copy:
                for row in amenity_rows:
                    copy.write_row(row)
            print(f"  [OK] Streamed {len(amenity_rows):,} amenities in {time.time() - t_copy:.2f}s.")

            # 5d. Agent properties
            t_copy = time.time()
            with cur.copy(
                """
                COPY agent_properties (
                    agent_id, property_id, assignment_type, assigned_on
                ) FROM STDIN
                """
            ) as copy:
                for row in agent_prop_rows:
                    copy.write_row(row)
            print(f"  [OK] Streamed {len(agent_prop_rows):,} agent assignments in {time.time() - t_copy:.2f}s.")

            # ---------------------------------------------------------
            # 6. OPTIMIZE INDEXES
            # ---------------------------------------------------------
            print("\n[Step 6] Verifying indexes for rapid lookup...")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_properties_property ON agent_properties (property_id);"
            )
            print("  [OK] Index idx_agent_properties_property verified.")

            # ---------------------------------------------------------
            # 7. VERIFY BEFORE COMMITTING
            # ---------------------------------------------------------
            print("\n[Step 7] Running post-migration verification...")
            cur.execute("SELECT count(*) FROM properties;")
            final_props = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM prices;")
            final_prices = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM properties WHERE property_id LIKE 'W8-%';")
            final_w8_props = cur.fetchone()[0]
            cur.execute(
                """
                SELECT count(*)
                FROM properties
                WHERE available = TRUE;
                """
            )
            available_props = cur.fetchone()[0]
            cur.execute(
                """
                SELECT count(*)
                FROM prices
                WHERE property_id LIKE 'W8-%' AND verification_status = 'Historical';
                """
            )
            historical_w8_prices = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM amenities;")
            final_amenities = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM agent_properties;")
            final_agent_props = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM auth_users;")
            final_users = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM customers;")
            final_customers = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM customer_preferences;")
            final_prefs = cur.fetchone()[0]

            print(f"  Historical Week 8 properties: {final_w8_props:,}")
            print(f"  Historical Week 8 prices:     {historical_w8_prices:,}")
            print(f"  Available properties:         {available_props:,}")
            print(f"  Total amenities in DB:  {final_amenities:,}")
            print(f"  Total agent properties: {final_agent_props:,}")

            assert final_props == len(df) + initial_w7_props, "Property count mismatch!"
            assert final_prices == len(df) + initial_w7_prices, "Price count mismatch!"
            assert final_w8_props == len(df), "Week 8 property count mismatch!"
            assert historical_w8_prices == len(df), "Week 8 historical price count mismatch!"
            assert available_props == 0, "Historical properties remain marked available!"
            assert final_users == initial_users, "auth_users altered!"
            assert final_customers == initial_customers, "customers altered!"
            assert final_prefs == initial_prefs, "customer_preferences altered!"

            print("  [OK] CRM and user data preserved; imported listings remain historical.")

            conn.commit()
            print("\n[COMMIT] Transaction successfully committed to PostgreSQL!")

    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("HISTORICAL CATALOG IMPORT COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    run_migration()
