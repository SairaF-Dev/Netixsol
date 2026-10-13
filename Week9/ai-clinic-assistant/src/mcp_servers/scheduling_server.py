"""
MCP Server: scheduling
Provides standardized tools for finding doctors, checking availability, booking, rescheduling, and cancelling appointments.
"""

import sqlite3
import os
import uuid
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "clinic.db")

class SchedulingMCPServer:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def find_doctors(self, specialty: str = None, city: str = None) -> List[Dict[str, Any]]:
        """Tool: Search for doctors by specialty and/or city."""
        conn = self._get_connection()
        query = "SELECT p.*, b.name as branch_name, b.city FROM practitioners p JOIN branches b ON p.branch_id = b.id WHERE 1=1"
        params = []
        if specialty:
            query += " AND p.specialty = ?"
            params.append(specialty)
        if city:
            query += " AND b.city = ?"
            params.append(city)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def check_available_slots(self, doctor_id: str, date_str: str) -> List[str]:
        """Tool: Retrieve open consultation time slots for a doctor on a specific date."""
        all_slots = ["09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM"]
        conn = self._get_connection()
        booked = conn.execute("SELECT time_slot FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled'", (doctor_id, date_str)).fetchall()
        conn.close()
        booked_slots = {r['time_slot'] for r in booked}
        return [s for s in all_slots if s not in booked_slots]

    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Tool: Retrieve existing appointments for a specific patient."""
        conn = self._get_connection()
        rows = conn.execute("""
            SELECT a.*, p.name as doctor_name, p.specialty as doctor_specialty, b.name as branch_name, b.city
            FROM appointments a
            LEFT JOIN practitioners p ON a.doctor_id = p.id
            LEFT JOIN branches b ON a.branch_id = b.id
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date DESC, a.time_slot DESC
        """, (patient_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def book_appointment(self, patient_id: str, doctor_id: str, branch_id: str, date_str: str, time_slot: str, urgency: str = "Routine", complaint: str = None) -> Dict[str, Any]:
        """Tool: Book a new appointment with real transaction & conflict validation."""
        import datetime
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        if date_str < today_str:
            return {"status": "ERROR", "message": "Cannot book appointments in past dates."}

        conn = self._get_connection()
        try:
            # 1. Check if doctor is already booked for this slot
            existing_doc = conn.execute(
                "SELECT id FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'",
                (doctor_id, date_str, time_slot)
            ).fetchone()
            if existing_doc:
                return {
                    "status": "ERROR",
                    "conflict_type": "DOCTOR_UNAVAILABLE",
                    "message": f"Time slot {time_slot} on {date_str} is already booked for this doctor."
                }

            # 2. Check if patient already has a booking at the same date and time slot
            existing_pat = conn.execute(
                "SELECT id FROM appointments WHERE patient_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'",
                (patient_id, date_str, time_slot)
            ).fetchone()
            if existing_pat:
                return {
                    "status": "ERROR",
                    "conflict_type": "PATIENT_SLOT_CONFLICT",
                    "message": f"Patient already has an active appointment ({existing_pat['id']}) on {date_str} at {time_slot}."
                }

            apt_id = f"APT-{uuid.uuid4().hex[:6].upper()}"
            conn.execute(
                "INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (apt_id, patient_id, doctor_id, branch_id, date_str, time_slot, "Scheduled", urgency, complaint)
            )
            conn.commit()
            return {
                "appointment_id": apt_id,
                "status": "Scheduled",
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "branch_id": branch_id,
                "appointment_date": date_str,
                "time_slot": time_slot,
                "urgency": urgency
            }
        except Exception as e:
            conn.rollback()
            return {
                "status": "ERROR",
                "message": f"Database persistence failure: {str(e)}"
            }
        finally:
            conn.close()

    def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Tool: Cancel an existing appointment."""
        conn = self._get_connection()
        conn.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
        return {"appointment_id": appointment_id, "status": "Cancelled"}

if __name__ == "__main__":
    server = SchedulingMCPServer()
    print("Found General Med Doctors:", len(server.find_doctors(specialty="General Medicine")))


