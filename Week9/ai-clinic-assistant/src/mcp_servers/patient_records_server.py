"""
MCP Server: patient-records
Provides standardized tools for querying patient demographics, allergies, medical history, and lab results from the database.
"""

import sqlite3
import os
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "clinic.db")

class PatientRecordsMCPServer:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        """Tool: Retrieve patient demographic profile by ID."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"error": f"Patient {patient_id} not found"}

    def get_patient_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Tool: Retrieve patient known allergies."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM allergies WHERE patient_id = ?", (patient_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_patient_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Tool: Retrieve patient chronic conditions and diagnostic history."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM conditions WHERE patient_id = ?", (patient_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_patient_labs(self, patient_id: str) -> List[Dict[str, Any]]:
        """Tool: Retrieve patient diagnostic laboratory observations."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM observations WHERE patient_id = ? ORDER BY test_date DESC", (patient_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_patient_medications(self, patient_id: str, status: str = None) -> List[Dict[str, Any]]:
        """Tool: Retrieve patient medications and active prescriptions."""
        conn = self._get_connection()
        query = "SELECT * FROM medication_requests WHERE patient_id = ?"
        params = [patient_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Tool: Retrieve patient appointments history."""
        conn = self._get_connection()
        query = """
            SELECT a.*, p.name as doctor_name, p.specialty as doctor_specialty, b.name as branch_name, b.city
            FROM appointments a
            LEFT JOIN practitioners p ON a.doctor_id = p.id
            LEFT JOIN branches b ON a.branch_id = b.id
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date DESC, a.time_slot DESC
        """
        rows = conn.execute(query, (patient_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

if __name__ == "__main__":
    server = PatientRecordsMCPServer()
    print("Test Profile PAT-0012:", server.get_patient_profile("PAT-0012"))
    print("Test Allergies PAT-0012:", server.get_patient_allergies("PAT-0012"))
    print("Test Medications PAT-5501:", server.get_patient_medications("PAT-5501"))


