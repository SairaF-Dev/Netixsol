"""
Doctor Dashboard API for City Care Clinics.
Provides REST endpoints for doctors to review pending approvals, edit summaries, and approve/reject cases.
"""

from typing import Dict, Any, List
from src.agents.hitl_manager import HITLManager
from src.mcp_servers.notifications_server import NotificationsMCPServer

# In-memory approval queue (persisted during server runtime)
PENDING_APPROVAL_QUEUE: Dict[str, Dict[str, Any]] = {}

class DoctorDashboardAPI:
    def __init__(self, notifications_mcp: NotificationsMCPServer = None):
        self.hitl_manager = HITLManager()
        self.notifications_mcp = notifications_mcp or NotificationsMCPServer()

    def register_pending_case(self, state: Dict[str, Any]):
        """
        Enqueues a paused graph state for doctor review.
        """
        patient_id = state["patient_id"]
        paused_state = self.hitl_manager.pause_for_doctor_review(state)
        PENDING_APPROVAL_QUEUE[patient_id] = paused_state
        return paused_state

    def get_pending_cases(self) -> List[Dict[str, Any]]:
        """
        Endpoint: GET /api/doctor/pending_approvals
        Returns list of all cases awaiting doctor review.
        """
        cases = []
        for pid, st in PENDING_APPROVAL_QUEUE.items():
            if st.get("hitl_status") == "PAUSED_FOR_DOCTOR_APPROVAL":
                intake = st.get("intake_form", {})
                cases.append({
                    "patient_id": pid,
                    "patient_type": intake.get("patient_type", "self"),
                    "chief_complaint": intake.get("chief_complaint"),
                    "severity": intake.get("severity", "Normal"),
                    "allergies": intake.get("allergies") or [],
                    "current_medications": intake.get("current_medications") or [],
                    "triage_urgency": st.get("triage_result", {}).get("urgency_level"),
                    "draft_soap_summary": st.get("soap_summary", {}).get("formatted_text"),
                    "safety_status": (st.get("safety_report") or {}).get("status", "NOT_CHECKED")
                })
        return cases

    def submit_doctor_action(
        self,
        patient_id: str,
        action: str, # "APPROVE", "EDIT", "REJECT"
        doctor_edits: str = None
    ) -> Dict[str, Any]:
        """
        Endpoint: POST /api/doctor/action
        Submits doctor decision and returns updated state ready for graph resume.
        """
        if patient_id not in PENDING_APPROVAL_QUEUE:
            return {"status": "ERROR", "message": f"No pending approval for patient {patient_id}"}

        st = PENDING_APPROVAL_QUEUE[patient_id]
        updated_st = self.hitl_manager.process_doctor_response(st, action, doctor_edits)
        
        email_status = "NOT_DISPATCHED"
        if updated_st["hitl_status"] in ["APPROVED", "REJECTED"]:
            # Dispatch email notification to patient via HTTPS API (Port 443)
            email_res = self.notifications_mcp.send_email_confirmation(
                email=f"{patient_id.lower()}@patient.clinic.pk",
                subject=f"Doctor Review Status Update - {patient_id}",
                body_text=f"Your clinical review has been processed by your attending doctor. Status: {updated_st['hitl_status']}."
            )
            email_status = email_res.get("status")
            # Remove from active queue
            del PENDING_APPROVAL_QUEUE[patient_id]

        return {
            "status": "SUCCESS",
            "patient_id": patient_id,
            "hitl_status": updated_st["hitl_status"],
            "email_status": email_status,
            "updated_state": updated_st
        }

if __name__ == "__main__":
    api = DoctorDashboardAPI()
    print("Pending Cases:", len(api.get_pending_cases()))
