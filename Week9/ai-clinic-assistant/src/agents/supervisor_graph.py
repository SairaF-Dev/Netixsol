"""
Supervisor & State Graph Router for City Care Clinics.
Implemented with LangGraph StateGraph v0.2.
Orchestrates all 7 specialist agents, manages global ClinicState,
executes parallel node branches, handles errors/fallbacks, and logs node transitions.
"""

from typing import Dict, Any, List, Optional, TypedDict
import datetime
import re

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.intake_agent import IntakeAgent
from src.agents.triage_agent import TriageAgent
from src.agents.scheduling_agent import SchedulingAgent
from src.agents.records_agent import RecordsAgent
from src.agents.clinical_summary_agent import ClinicalSummaryAgent
from src.agents.prescription_safety_agent import PrescriptionSafetyAgent
from src.agents.followup_agent import FollowupAgent


class ClinicState(TypedDict, total=False):
    patient_id: str
    messages: List[Dict[str, str]]
    intake_form: Dict[str, Any]
    triage_result: Optional[Dict[str, Any]]
    records_data: Optional[Dict[str, Any]]
    appointment_data: Optional[Dict[str, Any]]
    soap_summary: Optional[Dict[str, Any]]
    safety_report: Optional[Dict[str, Any]]
    followup_plan: Optional[Dict[str, Any]]
    hitl_status: str
    current_node: str
    transition_logs: List[str]
    error_count: int
    user_message: Optional[str]


class ClinicSupervisorGraph:
    """
    LangGraph-based Supervisor & State Graph for MedCare Clinic.
    Uses StateGraph with MemorySaver checkpointing to execute clinical workflows.
    """
    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.triage_agent = TriageAgent()
        self.scheduling_agent = SchedulingAgent()
        self.records_agent = RecordsAgent()
        self.summary_agent = ClinicalSummaryAgent()
        self.safety_agent = PrescriptionSafetyAgent()
        self.followup_agent = FollowupAgent()

        self.checkpointer = MemorySaver()
        self.builder = self._create_graph_builder()
        self.app = self.builder.compile(checkpointer=self.checkpointer)
        self.graph = self.app

    def create_initial_state(self, patient_id: str = "PAT-0012") -> Dict[str, Any]:
        """
        Creates an initialized ClinicState dictionary.
        """
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
            "error_count": 0,
            "user_message": None
        }

    def _log_transition(self, state: Dict[str, Any], from_node: str, to_node: str, msg: str = ""):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {from_node} -> {to_node} | {msg}".strip()
        state.setdefault("transition_logs", []).append(log_entry)
        state["current_node"] = to_node

    # =========================================================================
    # LangGraph Node Handlers
    # =========================================================================

    def _entry_router(self, state: ClinicState) -> str:
        curr = state.get("current_node", "INTAKE")
        user_msg = state.get("user_message")

        # Automatic recovery from manual override, fallback or paused states
        if curr in ["MANUAL_OVERRIDE", "FALLBACK", "NONE"]:
            if state.get("appointment_data") or (state.get("intake_form") and state["intake_form"].get("is_complete")):
                curr = "SCHEDULING"
            else:
                curr = "INTAKE"
            state["current_node"] = curr

        # Post-intake handling: scheduling queries vs new medical complaints
        if user_msg and (curr in ["HITL_DOCTOR_APPROVAL", "SUMMARY", "SAFETY", "FOLLOWUP", "COMPLETED"] or state.get("appointment_data")):
            msg_lower = user_msg.lower().strip()
            symptoms_found = self.intake_agent.extract_symptoms(user_msg)
            is_clinical_symptom = bool(symptoms_found) or any(w in msg_lower for w in [
                "dard", "pain", "bukhar", "fever", "khansi", "cough", "ulti", "vomit",
                "daant", "dant", "tooth", "teeth", "pait", "stomach", "rash", "khareesh",
                "kharish", "chot", "injury", "blood", "khoon", "saans", "gala", "throat",
                "zukaam", "nazla", "kaan", "ear", "ankh", "eye", "headache", "sar dard"
            ])
            is_explicit_scheduling = any(w in msg_lower for w in [
                "slot", "reschedule", "cancel", "mansookh", "nahi aana", "nai aana",
                "shukriya", "thanks", "theek hai", "allah hafiz", "bye", "okay", "ok",
                "timing", "available", "doosra time", "pehla time"
            ]) or bool(re.search(r'\b\d{1,2}:\d{2}\b|\b10:\d\d|\b11:\d\d|\b05:\d\d|\b06:\d\d|\b10\s*baje|\b11\s*baje|\b05\s*baje', msg_lower))

            is_restart_intent = any(w in msg_lower for w in [
                "restart", "dobara shuru", "shuru se", "naya masla", "nayi appointment",
                "doosra masla", "dusra masla", "new appointment", "new consultation"
            ])

            if (is_clinical_symptom and not is_explicit_scheduling) or is_restart_intent:
                # Reset intake form for new medical consultation
                patient_id = state.get("patient_id", "PAT-7215")
                state["intake_form"] = {
                    "patient_type": "self",
                    "patient_id": patient_id,
                    "chief_complaint": None,
                    "duration": None,
                    "severity": None,
                    "associated_symptoms": [],
                    "allergies": None,
                    "current_medications": None,
                    "is_complete": False
                }
                state["triage_result"] = None
                state["appointment_data"] = None
                state["soap_summary"] = None
                state["safety_report"] = None
                state["hitl_status"] = "NONE"
                state["current_node"] = "INTAKE"
                self._log_transition(state, curr, "INTAKE", f"New complaint presented: {user_msg[:30]}")
                return "intake_node"

            return "scheduling_query"

        node_map = {
            "INTAKE": "intake_node",
            "PARALLEL_TRIAGE_RECORDS": "parallel_triage_records_node",
            "SCHEDULING": "scheduling_node",
            "SUMMARY": "summary_node",
            "HITL_DOCTOR_APPROVAL": "hitl_approval_node",
            "SAFETY": "safety_node",
            "FOLLOWUP": "followup_node",
            "EMERGENCY_ESCALATION": "emergency_escalation_node",
            "COMPLETED": "end_node"
        }
        return node_map.get(curr, "intake_node")

    def _scheduling_query_node(self, state: ClinicState) -> Dict[str, Any]:
        curr = state.get("current_node", "SCHEDULING")
        user_message = state.get("user_message")
        messages = list(state.get("messages", []))
        if user_message:
            messages.append({"sender": "Patient", "text": user_message})
            state["messages"] = messages
            reply, state = self.scheduling_agent.handle_scheduling_query(state, user_message)
            state.setdefault("messages", []).append({"sender": "AI", "text": reply})
            self._log_transition(state, curr, curr, f"Scheduling query handled: {user_message[:30]}")
        state["user_message"] = None
        return state

    def _intake_node(self, state: ClinicState) -> Dict[str, Any]:
        user_message = state.get("user_message")
        messages = list(state.get("messages", []))

        # If intake was previously completed (e.g. starting a new complaint), reset for fresh intake
        if state.get("intake_form", {}).get("is_complete", False):
            patient_id = state.get("patient_id", "PAT-7215")
            state["intake_form"] = {
                "patient_type": "self",
                "patient_id": patient_id,
                "chief_complaint": None,
                "duration": None,
                "severity": None,
                "associated_symptoms": [],
                "allergies": None,
                "current_medications": None,
                "is_complete": False
            }
            state["triage_result"] = None
            state["appointment_data"] = None
            state["soap_summary"] = None
            state["safety_report"] = None
            state["hitl_status"] = "NONE"
            state["current_node"] = "INTAKE"

        if not user_message:
            reply = self.intake_agent.initial_greeting
            messages.append({"sender": "AI", "text": reply})
            state["messages"] = messages
            state["current_node"] = "INTAKE"
            state["user_message"] = None
            return state

        messages.append({"sender": "Patient", "text": user_message})
        reply, updated_intake, is_complete = self.intake_agent.process_turn(user_message, state["intake_form"])
        state["intake_form"] = updated_intake
        messages.append({"sender": "AI", "text": reply})
        state["messages"] = messages
        state["user_message"] = None

        if is_complete:
            self._log_transition(state, "INTAKE", "PARALLEL_TRIAGE_RECORDS", "Intake form complete.")
        return state

    def _route_after_intake(self, state: ClinicState) -> str:
        if state.get("intake_form", {}).get("is_complete", False):
            return "parallel_triage_records_node"
        return "end_node"

    def _parallel_triage_records_node(self, state: ClinicState) -> Dict[str, Any]:
        # Branch A: Triage Agent
        triage_res = self.triage_agent.evaluate_triage(state["intake_form"])
        state["triage_result"] = triage_res

        # Branch B: Records Agent
        records_res = self.records_agent.answer_patient_query(state["patient_id"], state["intake_form"]["chief_complaint"])
        state["records_data"] = records_res

        if triage_res["urgency_level"] == "Emergency":
            self._log_transition(state, "PARALLEL_TRIAGE_RECORDS", "EMERGENCY_ESCALATION", "Red flag triggered!")
            state.setdefault("messages", []).append({"sender": "AI", "text": triage_res["escalation_message"]})
        else:
            self._log_transition(state, "PARALLEL_TRIAGE_RECORDS", "SCHEDULING", f"Priority: {triage_res['urgency_level']}")

        return state

    def _route_after_triage(self, state: ClinicState) -> str:
        triage = state.get("triage_result") or {}
        if triage.get("urgency_level") == "Emergency":
            return "emergency_escalation_node"
        return "scheduling_node"

    def _scheduling_node(self, state: ClinicState) -> Dict[str, Any]:
        rec_spec = (state.get("triage_result") or {}).get("recommended_specialty", "General Medicine")
        patient_id = state.get("patient_id", "")

        # 1. Determine target city from EHR profile or user conversation
        patient_profile = self.records_agent.mcp.get_patient_profile(patient_id)
        registered_city = patient_profile.get("city") if isinstance(patient_profile, dict) else None

        all_text = " ".join([m.get("text", "") for m in state.get("messages", [])]).lower()
        if any(w in all_text for w in ["islamabad", "isb", "f-8", "f-7", "blue area"]):
            target_city = "Islamabad"
        elif any(w in all_text for w in ["lahore", "lhr", "dha", "gulberg", "johar town"]):
            target_city = "Lahore"
        elif registered_city and registered_city in ["Islamabad", "Lahore", "Rawalpindi"]:
            target_city = "Islamabad" if registered_city in ["Islamabad", "Rawalpindi"] else "Lahore"
        else:
            target_city = "Lahore"

        pref_doc = "DOC-101" if target_city == "Lahore" and rec_spec == "General Medicine" else None

        opts = self.scheduling_agent.suggest_options(
            state["triage_result"],
            city=target_city,
            preferred_doctor_id=pref_doc,
            patient_id=patient_id,
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
                state.setdefault("messages", []).append({"sender": "AI", "text": booking["urdulish_response"]})
            else:
                state.setdefault("messages", []).append({"sender": "AI", "text": f"[SCHEDULING NOTICE] {booking.get('message', 'Booking could not be auto-confirmed.')}"})

        self._log_transition(state, "SCHEDULING", "SUMMARY", "Appointment confirmed." if (state.get("appointment_data") or {}).get("status") == "CONFIRMED" else "Scheduling evaluated.")
        return state

    def _summary_node(self, state: ClinicState) -> Dict[str, Any]:
        soap_res = self.summary_agent.generate_soap_summary(state["patient_id"], state["intake_form"])
        state["soap_summary"] = soap_res

        # HITL Checkpoint Status
        state["hitl_status"] = "PAUSED_FOR_DOCTOR_APPROVAL"
        self._log_transition(state, "SUMMARY", "HITL_DOCTOR_APPROVAL", "Paused for doctor sign-off.")
        return state

    def _hitl_approval_node(self, state: ClinicState) -> Dict[str, Any]:
        if state.get("hitl_status") == "APPROVED":
            self._log_transition(state, "HITL_DOCTOR_APPROVAL", "SAFETY", "Doctor approved summary.")
        return state

    def _route_after_hitl(self, state: ClinicState) -> str:
        if state.get("hitl_status") == "APPROVED":
            return "safety_node"
        return "end_node"

    def _safety_node(self, state: ClinicState) -> Dict[str, Any]:
        draft = [{"drug_name": "Panadol", "dose_mg": 500, "frequency_per_day": 3}]
        safety_res = self.safety_agent.evaluate_doctor_prescription(state["patient_id"], draft)
        state["safety_report"] = safety_res
        self._log_transition(state, "SAFETY", "FOLLOWUP", f"Safety Status: {safety_res['status']}")
        return state

    def _followup_node(self, state: ClinicState) -> Dict[str, Any]:
        f_plan = self.followup_agent.create_reminder_plan(
            appointment_id=state["appointment_data"]["booking_details"]["appointment_id"] if state.get("appointment_data") else "APT-001",
            patient_name="Patient",
            medications=[{"drug_name": "Panadol", "frequency_per_day": 2}]
        )
        state["followup_plan"] = f_plan
        self._log_transition(state, "FOLLOWUP", "COMPLETED", "Workflow execution complete.")
        return state

    def _emergency_escalation_node(self, state: ClinicState) -> Dict[str, Any]:
        user_message = state.get("user_message")
        if user_message:
            messages = list(state.get("messages", []))
            messages.append({"sender": "Patient", "text": user_message})
            messages.append({
                "sender": "AI",
                "text": "[EMERGENCY ALERT] Please contact emergency medical services (1122) or visit the nearest ER immediately. Routine booking is suspended for your safety."
            })
            state["messages"] = messages
        state["current_node"] = "EMERGENCY_ESCALATION"
        state["user_message"] = None
        return state

    def _end_node(self, state: ClinicState) -> Dict[str, Any]:
        state["user_message"] = None
        return state

    # =========================================================================
    # StateGraph Builder & Compiler
    # =========================================================================

    def _create_graph_builder(self) -> StateGraph:
        builder = StateGraph(ClinicState)

        # 1. Register Autonomous Specialist Nodes
        builder.add_node("scheduling_query", self._scheduling_query_node)
        builder.add_node("intake_node", self._intake_node)
        builder.add_node("parallel_triage_records_node", self._parallel_triage_records_node)
        builder.add_node("emergency_escalation_node", self._emergency_escalation_node)
        builder.add_node("scheduling_node", self._scheduling_node)
        builder.add_node("summary_node", self._summary_node)
        builder.add_node("hitl_approval_node", self._hitl_approval_node)
        builder.add_node("safety_node", self._safety_node)
        builder.add_node("followup_node", self._followup_node)
        builder.add_node("end_node", self._end_node)

        # 2. Add Conditional Entry Routing
        builder.add_conditional_edges(
            START,
            self._entry_router,
            {
                "scheduling_query": "scheduling_query",
                "intake_node": "intake_node",
                "parallel_triage_records_node": "parallel_triage_records_node",
                "emergency_escalation_node": "emergency_escalation_node",
                "scheduling_node": "scheduling_node",
                "summary_node": "summary_node",
                "hitl_approval_node": "hitl_approval_node",
                "safety_node": "safety_node",
                "followup_node": "followup_node",
                "end_node": "end_node"
            }
        )

        # 3. Add Edges & Conditional Branching
        builder.add_conditional_edges(
            "intake_node",
            self._route_after_intake,
            {
                "parallel_triage_records_node": "parallel_triage_records_node",
                "end_node": "end_node"
            }
        )

        builder.add_conditional_edges(
            "parallel_triage_records_node",
            self._route_after_triage,
            {
                "emergency_escalation_node": "emergency_escalation_node",
                "scheduling_node": "scheduling_node"
            }
        )

        builder.add_edge("scheduling_node", "summary_node")
        builder.add_edge("summary_node", "hitl_approval_node")

        builder.add_conditional_edges(
            "hitl_approval_node",
            self._route_after_hitl,
            {
                "safety_node": "safety_node",
                "end_node": "end_node"
            }
        )

        builder.add_edge("safety_node", "followup_node")
        builder.add_edge("followup_node", "end_node")
        builder.add_edge("scheduling_query", "end_node")
        builder.add_edge("emergency_escalation_node", "end_node")
        builder.add_edge("end_node", END)

        return builder

    # =========================================================================
    # Public Execution Methods
    # =========================================================================

    def step(self, state: Dict[str, Any], user_message: str = None) -> Dict[str, Any]:
        """
        Executes a single turn step through the compiled LangGraph StateGraph.
        """
        state_copy = dict(state)
        state_copy["user_message"] = user_message
        thread_id = state_copy.get("patient_id", "default_thread")
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.app.invoke(state_copy, config=config)
            result["user_message"] = None
            return result
        except Exception as e:
            state_copy["error_count"] = state_copy.get("error_count", 0) + 1
            curr = state_copy.get("current_node", "UNKNOWN")
            log_err = f"ERROR in {curr}: {str(e)}"
            state_copy.setdefault("transition_logs", []).append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {log_err}")
            if state_copy["error_count"] > 3:
                self._log_transition(state_copy, curr, "FALLBACK", "Max errors exceeded. Invoking human fallback.")
                state_copy.setdefault("messages", []).append({"sender": "AI", "text": "System error occurred. Connecting to human front desk..."})
            return state_copy

    def invoke(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Direct LangGraph invoke wrapper."""
        thread_id = state.get("patient_id", "default_thread")
        cfg = config or {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(state, config=cfg)

    def stream(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """Direct LangGraph stream wrapper."""
        thread_id = state.get("patient_id", "default_thread")
        cfg = config or {"configurable": {"thread_id": thread_id}}
        return self.app.stream(state, config=cfg)

    def get_graph(self):
        """Returns the compiled LangGraph topology representation."""
        return self.app.get_graph()


if __name__ == "__main__":
    graph = ClinicSupervisorGraph()
    st = graph.create_initial_state("PAT-0012")
    print("LangGraph initialized successfully.")
    print("Initial Node:", st["current_node"])
    print("Initial Log:", st["transition_logs"][0])
    print("LangGraph Nodes:", list(graph.get_graph().nodes.keys()))
