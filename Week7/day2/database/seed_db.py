"""
Builds real_estate.db (SQLite) from the CSVs in data/ using schema.sql.

Run:  python database/seed_db.py
Produces: database/real_estate.db
"""
import sqlite3
import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "database", "real_estate.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())

    # Order matters due to foreign keys
    developers = load_csv(os.path.join(DATA_DIR, "developers.csv"))
    cur.executemany(
        "INSERT INTO developers VALUES (:developer_id, :developer_name, :years_in_business, "
        ":projects_completed, :reputation_rating, :contact_email)",
        developers,
    )

    locations = load_csv(os.path.join(DATA_DIR, "locations.csv"))
    cur.executemany(
        "INSERT INTO locations VALUES (:area_id, :area_name, :city, :latitude, :longitude, "
        ":category, :distance_to_airport_km, :distance_to_city_center_km, :security_rating)",
        locations,
    )

    properties = load_csv(os.path.join(DATA_DIR, "properties.csv"))
    cur.executemany(
        "INSERT INTO properties VALUES (:property_id, :title, :type, :purpose, :city, :area, "
        ":bedrooms, :bathrooms, :size_marla, :price_pkr, :developer_id, :status, :agent_name, "
        ":agent_phone, :possession_status)",
        properties,
    )

    prices = load_csv(os.path.join(DATA_DIR, "prices.csv"))
    for row in prices:
        for k in ("list_price_pkr", "price_per_marla_or_sqft", "advance_percent", "monthly_rent_pkr"):
            row[k] = row[k] if row[k] not in ("", None) else None
    cur.executemany(
        "INSERT INTO prices VALUES (:property_id, :list_price_pkr, :price_per_marla_or_sqft, "
        ":last_price_update, :negotiable, :advance_percent, :monthly_rent_pkr)",
        prices,
    )

    amenities = load_csv(os.path.join(DATA_DIR, "amenities.csv"))
    cur.executemany(
        "INSERT INTO amenities VALUES (:property_id, :gated_community, :parking, :gym, "
        ":swimming_pool, :park_nearby, :mosque_nearby, :generator_backup, :solar_panels, "
        ":servant_quarter, :lift)",
        amenities,
    )

    plans = load_csv(os.path.join(DATA_DIR, "payment_plans.csv"))
    cur.executemany(
        "INSERT INTO payment_plans (property_id, plan_name, advance_percent, installment_count, "
        "installment_frequency, installment_amount_pkr, possession_percent, duration_months) "
        "VALUES (:property_id, :plan_name, :advance_percent, :installment_count, "
        ":installment_frequency, :installment_amount_pkr, :possession_percent, :duration_months)",
        plans,
    )

    conn.commit()
    conn.close()
    print(f"Database built at {DB_PATH}")


if __name__ == "__main__":
    build_database()
