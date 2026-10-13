"""
Human-in-the-Loop (HITL) Manager for City Care Clinics.
Evaluates interrupt conditions (lab explanations, prescription warnings, low triage confidence)
and manages graph pause, doctor approval, doctor edit, and graph resume workflows.
"""

from typing import Dict, Any, List

class HITLManager:
    def should_interrupt_for_doctor(self, state: Dict[str, Any]) -> bool:
        """
        Evaluates whether current state requires doctor approval before proceeding.
        """
        # Condition 1: Low triage confidence (< 0.85)
        triage = state.get("triage_result") or {}
        if triage and triage.get("confidence", 1.0) < 0.85:
            return True

        # Condition 2: Prescriptions needing doctor validation
        safety = state.get("safety_report") or {}
        if safety and safety.get("status") in ["WARNING", "CONTRAINDICATED"]:
            return True

        # Condition 3: Clinical SOAP brief / Lab explanations generated
        if state.get("soap_summary") and state.get("hitl_status") != "APPROVED":
            return True

        return False

    def pause_for_doctor_review(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sets graph state to PAUSED_FOR_DOCTOR_APPROVAL.
        """
        state["hitl_status"] = "PAUSED_FOR_DOCTOR_APPROVAL"
        log_msg = f"[{state['current_node']}] Graph paused for Doctor Dashboard approval."
        if log_msg not in state.get("transition_logs", []):
            state["transition_logs"].append(log_msg)
        return state

    def process_doctor_response(
        self,
        state: Dict[str, Any],
        action: str, # "APPROVE", "EDIT", "REJECT"
        doctor_edits: str = None
    ) -> Dict[str, Any]:
        """
        Processes doctor action from dashboard and prepares state for graph resume.
        """
        action_upper = action.strip().upper()

        if action_upper == "APPROVE":
            state["hitl_status"] = "APPROVED"
            state["transition_logs"].append("Doctor approved summary without edits.")
        elif action_upper == "EDIT":
            state["hitl_status"] = "APPROVED"
            if doctor_edits and state.get("soap_summary"):
                state["soap_summary"]["formatted_text"] = doctor_edits
                state["soap_summary"]["doctor_modified"] = True
            state["transition_logs"].append("Doctor modified summary and approved.")
        elif action_upper == "REJECT":
            state["hitl_status"] = "REJECTED"
            state["transition_logs"].append("Doctor rejected summary. Case routed to manual phone consult.")

        return state

if __name__ == "__main__":
    manager = HITLManager()
    dummy_state = {
        "soap_summary": {"formatted_text": "Draft Summary"},
        "hitl_status": "NONE",
        "current_node": "SUMMARY",
        "transition_logs": []
    }
    print("Should Interrupt:", manager.should_interrupt_for_doctor(dummy_state))

