"""CRM Admin Dashboard - View all appointments, customers, and workflow history."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
import streamlit as st
from psycopg.rows import dict_row

# ============================================================
# PROJECT SETUP
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DAY3_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

# Load .env from day3 directory (relative to where streamlit is run from)
load_dotenv(".env")
# Fallback to absolute path if not found
if not os.getenv("DATABASE_URL"):
    load_dotenv(DAY3_ROOT / ".env")


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Sara CRM — Appointment Management",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Sara CRM — Appointment Management Dashboard")
st.caption("PostgreSQL Backend • Real-time Appointment Tracking • Customer Management")


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_db_connection():
    """Create PostgreSQL connection."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL not set in .env")
        st.error("Debug: Check day3/.env file exists")
        st.stop()
    
    try:
        conn = psycopg.connect(db_url)
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.error(f"DEBUG: DATABASE_URL = {db_url}")
        st.stop()


# ============================================================
# DATABASE QUERIES
# ============================================================

def get_all_appointments(conn) -> list[dict]:
    """Fetch all appointments from PostgreSQL."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    appointment_id,
                    session_id,
                    status,
                    request_json->>'client_name' as client_name,
                    request_json->>'client_phone' as client_phone,
                    request_json->>'client_email' as client_email,
                    request_json->>'property_name' as property_name,
                    request_json->>'employee_name' as employee_name,
                    (request_json->>'starts_at')::timestamp as starts_at,
                    request_json->>'meeting_notes' as meeting_notes,
                    calendar_event_id,
                    calendar_link,
                    created_at,
                    updated_at
                FROM appointments
                ORDER BY created_at DESC
                LIMIT 1000
            """)
            return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Error fetching appointments: {e}")
        return []


def search_customer_by_phone(conn, phone: str) -> list[dict]:
    """Search customer by phone number."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    appointment_id,
                    session_id,
                    status,
                    request_json->>'client_name' as client_name,
                    request_json->>'client_phone' as client_phone,
                    request_json->>'client_email' as client_email,
                    request_json->>'property_name' as property_name,
                    request_json->>'employee_name' as employee_name,
                    (request_json->>'starts_at')::timestamp as starts_at,
                    request_json->>'meeting_notes' as meeting_notes,
                    calendar_event_id,
                    calendar_link,
                    created_at,
                    updated_at
                FROM appointments
                WHERE request_json->>'client_phone' ILIKE %s
                ORDER BY created_at DESC
            """, (f"%{phone}%",))
            return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Error searching customer: {e}")
        return []


def get_workflow_history(conn, appointment_id: str) -> list[dict]:
    """Fetch workflow events for an appointment."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    id,
                    appointment_id,
                    event_type,
                    payload,
                    created_at
                FROM workflow_events
                WHERE appointment_id = %s
                ORDER BY created_at DESC
            """, (appointment_id,))
            return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Error fetching workflow history: {e}")
        return []


def get_dashboard_stats(conn) -> dict[str, Any]:
    """Get CRM statistics."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            # Total appointments
            cur.execute("SELECT COUNT(*) as total FROM appointments")
            total = cur.fetchone()["total"]
            
            # Confirmed appointments
            cur.execute("SELECT COUNT(*) as confirmed FROM appointments WHERE status = 'confirmed'")
            confirmed = cur.fetchone()["confirmed"]
            
            # Pending appointments
            cur.execute("SELECT COUNT(*) as pending FROM appointments WHERE status = 'pending'")
            pending = cur.fetchone()["pending"]
            
            # Cancelled appointments
            cur.execute("SELECT COUNT(*) as cancelled FROM appointments WHERE status = 'cancelled'")
            cancelled = cur.fetchone()["cancelled"]
            
            # Rescheduled appointments
            cur.execute("SELECT COUNT(*) as rescheduled FROM appointments WHERE status = 'rescheduled'")
            rescheduled = cur.fetchone()["rescheduled"]
            
            # Unique customers
            cur.execute("""
                SELECT COUNT(DISTINCT request_json->>'client_phone') as unique_customers 
                FROM appointments
            """)
            unique_customers = cur.fetchone()["unique_customers"]
            
            # Appointments in next 7 days
            cur.execute("""
                SELECT COUNT(*) as upcoming 
                FROM appointments
                WHERE (request_json->>'starts_at')::timestamp 
                BETWEEN NOW() AND NOW() + INTERVAL '7 days'
                AND status IN ('confirmed', 'pending')
            """)
            upcoming = cur.fetchone()["upcoming"]
            
            return {
                "total": total,
                "confirmed": confirmed,
                "pending": pending,
                "cancelled": cancelled,
                "rescheduled": rescheduled,
                "unique_customers": unique_customers,
                "upcoming": upcoming,
            }
    except Exception as e:
        st.error(f"❌ Error fetching stats: {e}")
        return {}


# ============================================================
# UI COMPONENTS
# ============================================================

def format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt.strftime("%d %b %Y, %H:%M")


def status_badge_color(status: str) -> str:
    """Get color for status badge."""
    colors = {
        "confirmed": "🟢",
        "pending": "🟡",
        "cancelled": "🔴",
        "rescheduled": "🔵",
    }
    return colors.get(status, "⚪")


def render_stats_dashboard(stats: dict):
    """Render statistics dashboard."""
    if not stats:
        st.warning("No data available")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total Appointments", stats.get("total", 0))
    
    with col2:
        st.metric("✅ Confirmed", stats.get("confirmed", 0), help="Confirmed appointments")
    
    with col3:
        st.metric("⏳ Pending", stats.get("pending", 0), help="Pending confirmation")
    
    with col4:
        st.metric("🔄 Rescheduled", stats.get("rescheduled", 0), help="Rescheduled appointments")
    
    with col5:
        st.metric("❌ Cancelled", stats.get("cancelled", 0), help="Cancelled appointments")
    
    st.divider()
    
    col6, col7 = st.columns(2)
    
    with col6:
        st.metric("👥 Unique Customers", stats.get("unique_customers", 0))
    
    with col7:
        st.metric("📅 Upcoming (7 days)", stats.get("upcoming", 0))


def render_appointment_table(appointments: list[dict]):
    """Render appointments in a table."""
    if not appointments:
        st.info("ℹ️ No appointments found")
        return
    
    # Create DataFrame
    df = pd.DataFrame(appointments)
    
    # Format columns
    if "created_at" in df.columns:
        df["created_at"] = df["created_at"].apply(format_datetime)
    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(format_datetime)
    if "starts_at" in df.columns:
        df["starts_at"] = df["starts_at"].apply(format_datetime)
    
    # Select columns to display
    display_cols = [
        "appointment_id",
        "client_name",
        "client_phone",
        "property_name",
        "employee_name",
        "starts_at",
        "status",
        "created_at",
    ]
    
    df_display = df[[col for col in display_cols if col in df.columns]].copy()
    
    # Rename columns
    df_display.columns = [
        "ID",
        "Customer",
        "Phone",
        "Property",
        "Agent",
        "Appointment Date",
        "Status",
        "Created",
    ]
    
    st.dataframe(
        df_display,
        use_container_width=True,
        height=400,
        hide_index=True,
    )


def render_appointment_details(appointment: dict):
    """Render detailed view of an appointment."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Customer Information")
        st.write(f"**Name:** {appointment.get('client_name', '—')}")
        st.write(f"**Phone:** {appointment.get('client_phone', '—')}")
        st.write(f"**Email:** {appointment.get('client_email', '—')}")
    
    with col2:
        st.subheader("🏠 Property & Agent")
        st.write(f"**Property:** {appointment.get('property_name', '—')}")
        st.write(f"**Agent:** {appointment.get('employee_name', '—')}")
        st.write(f"**Status:** {status_badge_color(appointment.get('status', ''))} {appointment.get('status', '—').upper()}")
    
    st.divider()
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("📅 Appointment Details")
        st.write(f"**Date & Time:** {format_datetime(appointment.get('starts_at'))}")
        st.write(f"**Created:** {format_datetime(appointment.get('created_at'))}")
        st.write(f"**Updated:** {format_datetime(appointment.get('updated_at'))}")
    
    with col4:
        st.subheader("🔗 Calendar & Links")
        if appointment.get('calendar_event_id'):
            st.write(f"**Calendar Event ID:** {appointment.get('calendar_event_id')}")
        else:
            st.write("**Calendar Event ID:** —")
        
        if appointment.get('calendar_link'):
            st.write(f"**Calendar Link:** [Open Link]({appointment.get('calendar_link')})")
        else:
            st.write("**Calendar Link:** —")
    
    st.divider()
    
    if appointment.get('meeting_notes'):
        st.subheader("📝 Meeting Notes")
        st.write(appointment.get('meeting_notes'))


def render_workflow_timeline(workflow_events: list[dict]):
    """Render workflow events as timeline."""
    if not workflow_events:
        st.info("ℹ️ No workflow events recorded")
        return
    
    for i, event in enumerate(workflow_events):
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            
            with col1:
                st.write(f"**{i + 1}.**")
            
            with col2:
                event_type = event.get('event_type', 'unknown')
                created_at = format_datetime(event.get('created_at'))
                
                st.write(f"**{event_type.upper()}** — {created_at}")
                
                if event.get('payload'):
                    try:
                        payload = event['payload']
                        if isinstance(payload, str):
                            payload = json.loads(payload)
                        
                        with st.expander("📋 Details"):
                            st.json(payload)
                    except Exception as e:
                        st.write(f"Payload: {event.get('payload')}")


# ============================================================
# MAIN APP
# ============================================================

def main():
    conn = get_db_connection()
    
    # Sidebar
    with st.sidebar:
        st.header("🔍 Search & Filter")
        
        view_mode = st.radio(
            "Select View",
            options=["Dashboard", "All Appointments", "Search Customer", "Appointment Details"],
            index=0,
        )
    
    # ============================================================
    # DASHBOARD VIEW
    # ============================================================
    if view_mode == "Dashboard":
        st.subheader("📊 Statistics & Overview")
        
        stats = get_dashboard_stats(conn)
        render_stats_dashboard(stats)
        
        st.subheader("📅 Recent Appointments")
        appointments = get_all_appointments(conn)
        render_appointment_table(appointments[:20])  # Show last 20
    
    # ============================================================
    # ALL APPOINTMENTS VIEW
    # ============================================================
    elif view_mode == "All Appointments":
        st.subheader("📋 All Appointments")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=["confirmed", "pending", "cancelled", "rescheduled"],
                default=["confirmed", "pending"],
            )
        
        with col2:
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=30), datetime.now()),
                label_visibility="collapsed",
            )
        
        appointments = get_all_appointments(conn)
        
        # Apply filters
        if status_filter:
            appointments = [a for a in appointments if a.get('status') in status_filter]
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            appointments = [
                a for a in appointments
                if start_date <= a.get('created_at', datetime.now()).date() <= end_date
            ]
        
        st.write(f"📊 Showing {len(appointments)} appointments")
        render_appointment_table(appointments)
    
    # ============================================================
    # CUSTOMER SEARCH VIEW
    # ============================================================
    elif view_mode == "Search Customer":
        st.subheader("🔍 Search Customer by Phone")
        
        phone = st.text_input(
            "Customer Phone Number",
            placeholder="e.g., +92-300-1234567 or 03001234567",
        )
        
        if phone:
            appointments = search_customer_by_phone(conn, phone)
            
            if appointments:
                st.success(f"✅ Found {len(appointments)} appointment(s)")
                
                # Display customer info from first appointment
                first_apt = appointments[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Customer", first_apt.get('client_name', '—'))
                with col2:
                    st.metric("Email", first_apt.get('client_email', '—'))
                with col3:
                    st.metric("Total Bookings", len(appointments))
                
                st.divider()
                
                # Show all appointments for this customer
                st.subheader("📅 Customer Appointment History")
                render_appointment_table(appointments)
            else:
                st.warning("❌ No appointments found for this phone number")
    
    # ============================================================
    # APPOINTMENT DETAILS VIEW
    # ============================================================
    elif view_mode == "Appointment Details":
        st.subheader("📋 Appointment Details & Workflow History")
        
        appointments = get_all_appointments(conn)
        
        if appointments:
            # Select appointment
            appointment_options = {
                f"{a.get('client_name')} - {a.get('property_name')} - {format_datetime(a.get('starts_at'))}": a
                for a in appointments
            }
            
            selected = st.selectbox(
                "Select an Appointment",
                options=appointment_options.keys(),
            )
            
            if selected:
                appointment = appointment_options[selected]
                
                # Show appointment details
                render_appointment_details(appointment)
                
                # Show workflow history
                st.subheader("📜 Workflow History")
                workflow_events = get_workflow_history(conn, str(appointment.get('appointment_id')))
                render_workflow_timeline(workflow_events)
        else:
            st.info("ℹ️ No appointments available")


if __name__ == "__main__":
    main()
