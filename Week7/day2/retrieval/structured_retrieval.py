"""
Structured Retrieval — Task 3 (structured half)

Use SQL for anything that is a discrete, exact, frequently-changing
fact: price, availability status, plot/size, agent name/contact. These
have ONE correct value at query time — vector search would only return
"similar sounding" text, not the current true number. See
docs/structured_vs_semantic.md for the full justification.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "real_estate.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_price(property_id):
    conn = _connect()
    row = conn.execute(
        "SELECT p.title, pr.list_price_pkr, pr.monthly_rent_pkr, pr.negotiable "
        "FROM properties p JOIN prices pr ON p.property_id = pr.property_id "
        "WHERE p.property_id = ?", (property_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def check_availability(property_id):
    conn = _connect()
    row = conn.execute(
        "SELECT title, status, possession_status FROM properties WHERE property_id = ?",
        (property_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_plot_size(property_id):
    conn = _connect()
    row = conn.execute(
        "SELECT title, size_marla, bedrooms, bathrooms FROM properties WHERE property_id = ?",
        (property_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_agent(property_id):
    conn = _connect()
    row = conn.execute(
        "SELECT title, agent_name, agent_phone FROM properties WHERE property_id = ?",
        (property_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search_properties(city=None, purpose=None, min_price=None, max_price=None,
                       bedrooms=None, status="Available"):
    """Filtered structured search — used by the recommendation engine."""
    conn = _connect()
    query = "SELECT * FROM properties WHERE 1=1"
    params = []
    if city:
        query += " AND city = ?"
        params.append(city)
    if purpose:
        query += " AND purpose = ?"
        params.append(purpose)
    if min_price:
        query += " AND price_pkr >= ?"
        params.append(min_price)
    if max_price:
        query += " AND price_pkr <= ?"
        params.append(max_price)
    if bedrooms:
        query += " AND bedrooms = ?"
        params.append(bedrooms)
    if status:
        query += " AND status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    print(get_price("P001"))
    print(check_availability("P007"))
    print(search_properties(city="Lahore", purpose="Buy", max_price=35000000))
