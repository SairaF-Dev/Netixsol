"""
Prescription Safety Agent for City Care Clinics.
Intercepts proposed doctor prescriptions, queries patient records via patient-records MCP server,
runs the deterministic PrescriptionSafetyEngine, and formats clinical alerts for the doctor dashboard.
"""

from typing import Dict, Any, List
from src.tools.prescription_safety_engine import PrescriptionSafetyEngine
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer

class PrescriptionSafetyAgent:
    def __init__(self, engine: PrescriptionSafetyEngine = None, records_mcp: PatientRecordsMCPServer = None):
        self.engine = engine or PrescriptionSafetyEngine()
        self.mcp = records_mcp or PatientRecordsMCPServer()

    def evaluate_doctor_prescription(
        self,
        patient_id: str,
        proposed_medications: List[Dict[str, Any]],
        is_pregnant: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates draft doctor prescription against patient allergies and medical history.
        """
        allergies = self.mcp.get_patient_allergies(patient_id)
        history = self.mcp.get_patient_history(patient_id)
        profile = self.mcp.get_patient_profile(patient_id)

        safety_res = self.engine.check_prescription_safety(
            proposed_medications=proposed_medications,
            patient_allergies=allergies,
            patient_age=profile.get("age", 35),
            is_pregnant=is_pregnant
        )

        status = safety_res["overall_status"]
        patient_name = profile.get("name", "Patient")

        if status == "CLEARED":
            doctor_alert = f"[CLEARED] PRESCRIPTION CLEARED: Draft prescription for {patient_name} passed all safety checks."
            patient_msg = "Doctor sahab ne aap ki dawai confirm kar di hai."
        elif status == "WARNING":
            doctor_alert = f"[WARNING] PRESCRIPTION WARNING for {patient_name}:\n" + safety_res["clinical_explanation"]
            patient_msg = "Doctor sahab ne dawai ki dose adjust kar di hai taake aap ko safe dosage mile."
        else: # CONTRAINDICATED
            doctor_alert = f"[CONTRAINDICATED] CONTRAINDICATION ALERT for {patient_name}:\n" + safety_res["clinical_explanation"]
            patient_msg = "Aap ki allergy record check kar ke doctor sahab ne safe alternative medication select ki hai."

        return {
            "status": status,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "doctor_alert_message": doctor_alert,
            "patient_urdulish_message": patient_msg,
            "safety_report": safety_res
        }

if __name__ == "__main__":
    agent = PrescriptionSafetyAgent()
    draft = [{"drug_name": "Amoxicillin", "dose_mg": 500, "frequency_per_day": 3}]
    print(agent.evaluate_doctor_prescription("PAT-0012", draft))
