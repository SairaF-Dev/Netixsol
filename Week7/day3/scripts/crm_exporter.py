"""CRM Export Utilities - Export appointments to CSV/PDF."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class CRMExporter:
    """Export CRM data to various formats."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
    
    def _get_connection(self):
        """Create database connection."""
        return psycopg.connect(self.database_url)
    
    def get_all_appointments(self) -> list[dict]:
        """Fetch all appointments."""
        with self._get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT 
                        appointment_id,
                        session_id,
                        status,
                        request_json->>'client_name' as client_name,
                        request_json->>'client_phone' as client_phone,
                        request_json->>'client_email' as client_email,
                        request_json->>'property_id' as property_id,
                        request_json->>'property_name' as property_name,
                        request_json->>'employee_name' as employee_name,
                        request_json->>'employee_email' as employee_email,
                        (request_json->>'starts_at')::timestamp as starts_at,
                        request_json->>'duration_minutes' as duration_minutes,
                        request_json->>'meeting_notes' as meeting_notes,
                        calendar_event_id,
                        calendar_link,
                        created_at,
                        updated_at
                    FROM appointments
                    ORDER BY created_at DESC
                """)
                return cur.fetchall()
    
    def get_workflow_events_for_appointment(self, appointment_id: str) -> list[dict]:
        """Fetch workflow events for an appointment."""
        with self._get_connection() as conn:
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
    
    def export_to_csv(self, output_path: str | Path) -> Path:
        """Export all appointments to CSV."""
        appointments = self.get_all_appointments()
        
        # Flatten data
        rows = []
        for apt in appointments:
            row = {
                "Appointment ID": apt.get('appointment_id'),
                "Status": apt.get('status'),
                "Customer Name": apt.get('client_name'),
                "Customer Phone": apt.get('client_phone'),
                "Customer Email": apt.get('client_email'),
                "Property ID": apt.get('property_id'),
                "Property Name": apt.get('property_name'),
                "Agent Name": apt.get('employee_name'),
                "Agent Email": apt.get('employee_email'),
                "Appointment Date": apt.get('starts_at'),
                "Duration (minutes)": apt.get('duration_minutes'),
                "Meeting Notes": apt.get('meeting_notes'),
                "Calendar Event ID": apt.get('calendar_event_id'),
                "Calendar Link": apt.get('calendar_link'),
                "Created At": apt.get('created_at'),
                "Updated At": apt.get('updated_at'),
            }
            rows.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(rows)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        return output_path
    
    def export_to_json(self, output_path: str | Path) -> Path:
        """Export all appointments to JSON."""
        appointments = self.get_all_appointments()
        
        # Ensure all datetime objects are serializable
        data = {
            "export_date": datetime.now().isoformat(),
            "total_appointments": len(appointments),
            "appointments": [
                {
                    k: (str(v) if isinstance(v, datetime) else v)
                    for k, v in apt.items()
                }
                for apt in appointments
            ]
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_customer_appointments_csv(self, phone: str, output_path: str | Path) -> Path:
        """Export appointments for a specific customer to CSV."""
        with self._get_connection() as conn:
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
                        request_json->>'duration_minutes' as duration_minutes,
                        request_json->>'meeting_notes' as meeting_notes,
                        created_at,
                        updated_at
                    FROM appointments
                    WHERE request_json->>'client_phone' ILIKE %s
                    ORDER BY created_at DESC
                """, (f"%{phone}%",))
                appointments = cur.fetchall()
        
        # Create DataFrame and save
        rows = []
        for apt in appointments:
            row = {
                "Appointment ID": apt.get('appointment_id'),
                "Status": apt.get('status'),
                "Property": apt.get('property_name'),
                "Agent": apt.get('employee_name'),
                "Date": apt.get('starts_at'),
                "Duration (mins)": apt.get('duration_minutes'),
                "Notes": apt.get('meeting_notes'),
                "Created": apt.get('created_at'),
                "Updated": apt.get('updated_at'),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        return output_path
    
    def export_workflow_history_csv(self, appointment_id: str, output_path: str | Path) -> Path:
        """Export workflow history for an appointment to CSV."""
        events = self.get_workflow_events_for_appointment(appointment_id)
        
        rows = []
        for event in events:
            payload_str = json.dumps(event.get('payload')) if event.get('payload') else ""
            
            row = {
                "Event Type": event.get('event_type'),
                "Created At": event.get('created_at'),
                "Payload": payload_str,
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        return output_path
    
    def export_daily_report(self, date: datetime, output_path: str | Path) -> Path:
        """Export appointments for a specific date."""
        with self._get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT 
                        appointment_id,
                        status,
                        request_json->>'client_name' as client_name,
                        request_json->>'client_phone' as client_phone,
                        request_json->>'property_name' as property_name,
                        request_json->>'employee_name' as employee_name,
                        (request_json->>'starts_at')::timestamp as starts_at,
                        created_at
                    FROM appointments
                    WHERE DATE((request_json->>'starts_at')::timestamp) = %s
                    ORDER BY (request_json->>'starts_at')::timestamp
                """, (date.date(),))
                appointments = cur.fetchall()
        
        rows = []
        for apt in appointments:
            row = {
                "Customer": apt.get('client_name'),
                "Phone": apt.get('client_phone'),
                "Property": apt.get('property_name'),
                "Agent": apt.get('employee_name'),
                "Appointment Time": apt.get('starts_at'),
                "Status": apt.get('status'),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        return output_path


def main():
    """Example usage."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    exporter = CRMExporter(db_url)
    
    # Export all appointments to CSV
    csv_path = exporter.export_to_csv("crm_export_appointments.csv")
    print(f"✅ Exported appointments to {csv_path}")
    
    # Export to JSON
    json_path = exporter.export_to_json("crm_export_appointments.json")
    print(f"✅ Exported appointments to {json_path}")
    
    # Export today's appointments
    today_path = exporter.export_daily_report(datetime.now(), "crm_export_today.csv")
    print(f"✅ Exported today's appointments to {today_path}")


if __name__ == "__main__":
    main()
