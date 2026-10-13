"""
Supervisor & State Graph Router for City Care Clinics.
Orchestrates all 7 specialist agents, manages global ClinicState,
executes parallel node branches, handles errors/fallbacks, and logs node transitions.
"""

from typing import Dict, Any, List
import datetime

from src.agents.intake_agent import IntakeAgent
from src.agents.triage_agent import TriageAgent
from src.agents.scheduling_agent import SchedulingAgent
from src.agents.records_agent import RecordsAgent
from src.agents.clinical_summary_agent import ClinicalSummaryAgent
from src.agents.prescription_safety_agent import PrescriptionSafetyAgent
from src.agents.followup_agent import FollowupAgent

class ClinicSupervisorGraph:
    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.triage_agent = TriageAgent()
        self.scheduling_agent = SchedulingAgent()
        self.records_agent = RecordsAgent()
        self.summary_agent = ClinicalSummaryAgent()
        self.safety_agent = PrescriptionSafetyAgent()
        self.followup_agent = FollowupAgent()

    def create_initial_state(self, patient_id: str = "PAT-0012") -> Dict[str, Any]:
        return {
            "patient_id": patient_id,
            "messages": [],
            "intake_form": {
                "patient_type": "self",
                "patient_id": patient_id,
                "chief_complaint": None,
                "duration": None,
                "severity": None,
                "associated_symptoms": [],
                "allergies": None,
                "current_medications": None,
                "is_complete": False
            },
            "triage_result": None,
            "records_data": None,
            "appointment_data": None,
            "soap_summary": None,
            "safety_report": None,
            "followup_plan": None,
            "hitl_status": "NONE",
            "current_node": "INTAKE",
            "transition_logs": [f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Graph initialized for {patient_id}"],
            "error_count": 0
        }

    def _log_transition(self, state: Dict[str, Any], from_node: str, to_node: str, msg: str = ""):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {from_node} -> {to_node} | {msg}".strip()
        state["transition_logs"].append(log_entry)
        state["current_node"] = to_node

    def step(self, state: Dict[str, Any], user_message: str = None) -> Dict[str, Any]:
        """
        Executes a single state transition step through the supervisor graph.
        """
        curr = state["current_node"]

        # Automatic recovery from manual override or paused states
        if curr in ["MANUAL_OVERRIDE", "FALLBACK", "NONE"]:
            if state.get("appointment_data") or (state.get("intake_form") and state["intake_form"].get("is_complete")):
                curr = "SCHEDULING"
            else:
                curr = "INTAKE"
            state["current_node"] = curr

        try:
            # Handle post-intake patient messages (e.g. rescheduling, slot query, cancellation)
            if user_message and (curr in ["HITL_DOCTOR_APPROVAL", "SUMMARY", "SAFETY", "FOLLOWUP", "COMPLETED"] or state.get("appointment_data")):
                state["messages"].append({"sender": "Patient", "text": user_message})
                reply, state = self.scheduling_agent.handle_scheduling_query(state, user_message)
                state["messages"].append({"sender": "AI", "text": reply})
                self._log_transition(state, curr, curr, f"Scheduling query handled: {user_message[:30]}")
                return state

            # Node 1: INTAKE
            if curr == "INTAKE":
                if not user_message:
                    reply = self.intake_agent.initial_greeting
                    state["messages"].append({"sender": "AI", "text": reply})
                    return state

                state["messages"].append({"sender": "Patient", "text": user_message})
                reply, updated_intake, is_complete = self.intake_agent.process_turn(user_message, state["intake_form"])
                state["intake_form"] = updated_intake
                state["messages"].append({"sender": "AI", "text": reply})

                if is_complete:
                    self._log_transition(state, "INTAKE", "PARALLEL_TRIAGE_RECORDS", "Intake form complete.")
                    # Automatically trigger parallel node step
                    return self.step(state)
                return state

            # Node 2: PARALLEL_TRIAGE_RECORDS (Executes Triage + Records in parallel)
            elif curr == "PARALLEL_TRIAGE_RECORDS":
                # Branch A: Triage Agent
                triage_res = self.triage_agent.evaluate_triage(state["intake_form"])
                state["triage_result"] = triage_res

                # Branch B: Records Agent
                records_res = self.records_agent.answer_patient_query(state["patient_id"], state["intake_form"]["chief_complaint"])
                state["records_data"] = records_res

                if triage_res["urgency_level"] == "Emergency":
                    self._log_transition(state, "PARALLEL_TRIAGE_RECORDS", "EMERGENCY_ESCALATION", "Red flag triggered!")
                    state["messages"].append({"sender": "AI", "text": triage_res["escalation_message"]})
                    return state

                self._log_transition(state, "PARALLEL_TRIAGE_RECORDS", "SCHEDULING", f"Priority: {triage_res['urgency_level']}")
                return self.step(state)

            # Node 3: SCHEDULING
            elif curr == "SCHEDULING":
                pref_doc = "DOC-101"
                rec_spec = state["triage_result"].get("recommended_specialty", "General Medicine")
                opts = self.scheduling_agent.suggest_options(
                    state["triage_result"], 
                    city="Lahore", 
                    preferred_doctor_id=pref_doc,
                    patient_id=state.get("patient_id"),
                    preferred_specialty=rec_spec
                )
                if opts["status"] == "OPTIONS_FOUND":
                    doc = opts["doctor"]
                    slot = opts["available_slots"][0]
                    date_str = opts["proposed_date"]

                    booking = self.scheduling_agent.confirm_booking(
                        patient_id=state["patient_id"],
                        doctor_id=doc["id"],
                        branch_id=doc["branch_id"],
                        date_str=date_str,
                        time_slot=slot,
                        urgency=state["triage_result"]["urgency_level"],
                        chief_complaint=state["intake_form"]["chief_complaint"]
                    )
                    state["appointment_data"] = booking
                    if booking.get("status") == "CONFIRMED":
                        state["messages"].append({"sender": "AI", "text": booking["urdulish_response"]})
                    else:
                        state["messages"].append({"sender": "AI", "text": f"[SCHEDULING NOTICE] {booking.get('message', 'Booking could not be auto-confirmed.')}"})

                self._log_transition(state, "SCHEDULING", "SUMMARY", "Appointment confirmed." if (state.get("appointment_data") or {}).get("status") == "CONFIRMED" else "Scheduling evaluated.")
                return self.step(state)

            # Node 4: SUMMARY (SOAP Brief Generation)
            elif curr == "SUMMARY":
                soap_res = self.summary_agent.generate_soap_summary(state["patient_id"], state["intake_form"])
                state["soap_summary"] = soap_res
                
                # Set HITL Checkpoint Status
                state["hitl_status"] = "PAUSED_FOR_DOCTOR_APPROVAL"
                self._log_transition(state, "SUMMARY", "HITL_DOCTOR_APPROVAL", "Paused for doctor sign-off.")
                return state

            # Node 5: HITL DOCTOR APPROVAL CHECKPOINT
            elif curr == "HITL_DOCTOR_APPROVAL":
                if state["hitl_status"] == "APPROVED":
                    self._log_transition(state, "HITL_DOCTOR_APPROVAL", "SAFETY", "Doctor approved summary.")
                    return self.step(state)
                # Still paused
                return state

            # Node 6: PRESCRIPTION SAFETY
            elif curr == "SAFETY":
                draft = [{"drug_name": "Panadol", "dose_mg": 500, "frequency_per_day": 3}]
                safety_res = self.safety_agent.evaluate_doctor_prescription(state["patient_id"], draft)
                state["safety_report"] = safety_res
                self._log_transition(state, "SAFETY", "FOLLOWUP", f"Safety Status: {safety_res['status']}")
                return self.step(state)

            # Node 7: FOLLOWUP
            elif curr == "FOLLOWUP":
                f_plan = self.followup_agent.create_reminder_plan(
                    appointment_id=state["appointment_data"]["booking_details"]["appointment_id"] if state["appointment_data"] else "APT-001",
                    patient_name="Patient",
                    medications=[{"drug_name": "Panadol", "frequency_per_day": 2}]
                )
                state["followup_plan"] = f_plan
                self._log_transition(state, "FOLLOWUP", "COMPLETED", "Workflow execution complete.")
                return state

            # Node: EMERGENCY_ESCALATION
            elif curr == "EMERGENCY_ESCALATION":
                if user_message:
                    state["messages"].append({"sender": "Patient", "text": user_message})
                    state["messages"].append({
                        "sender": "AI",
                        "text": "[EMERGENCY ALERT] Please contact emergency medical services (1122) or visit the nearest ER immediately. Routine booking is suspended for your safety."
                    })
                return state

        except Exception as e:
            state["error_count"] += 1
            log_err = f"ERROR in {curr}: {str(e)}"
            state["transition_logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {log_err}")
            if state["error_count"] > 3:
                self._log_transition(state, curr, "FALLBACK", "Max errors exceeded. Invoking human fallback.")
                state["messages"].append({"sender": "AI", "text": "System error occurred. Connecting to human front desk..."})

        return state

if __name__ == "__main__":
    graph = ClinicSupervisorGraph()
    st = graph.create_initial_state("PAT-0012")
    print("Initial Node:", st["current_node"])
    print("Initial Log:", st["transition_logs"][0])

