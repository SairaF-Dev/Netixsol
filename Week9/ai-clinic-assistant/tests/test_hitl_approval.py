"""
Integration Test Suite for HITL Doctor Approval Workflow.
Tests graph interrupt evaluation, dashboard queue registration, doctor edit/approval, and graph resume.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.supervisor_graph import ClinicSupervisorGraph
from src.api.doctor_dashboard import DoctorDashboardAPI

def test_hitl_approval_workflow():
    graph = ClinicSupervisorGraph()
    dashboard = DoctorDashboardAPI()

    print("=" * 65)
    print("[TEST] HITL DOCTOR APPROVAL & DASHBOARD INTEGRATION TEST")
    print("=" * 65)

    # 1. Run Routine Journey to Summary Node
    st = graph.create_initial_state("PAT-0012")
    st = graph.step(st) # Greeting

    turns = [
        "Fever for 2 days and cough",
        "2 days",
        "6/10",
        "Weakness",
        "Penicillin",
        "Panadol"
    ]
    for t in turns:
        st = graph.step(st, user_message=t)

    # Verify Graph is Paused for Doctor Review
    assert st["hitl_status"] == "PAUSED_FOR_DOCTOR_APPROVAL", "Graph failed to pause for doctor"
    print("[PASS] 1. Graph State Paused at HITL Checkpoint!")
    print("     Current Node :", st["current_node"])
    print("     HITL Status  :", st["hitl_status"])

    # 2. Register with Doctor Dashboard Queue
    dashboard.register_pending_case(st)
    pending = dashboard.get_pending_cases()
    assert len(pending) > 0, "Dashboard failed to register pending case"
    print("\n[PASS] 2. Dashboard Pending Approval Queue:")
    print("     Pending Patient ID :", pending[0]["patient_id"])
    print("     Triage Urgency     :", pending[0]["triage_urgency"])

    # 3. Doctor Edits & Approves Case via Dashboard API
    edited_text = "DOCTOR EDITED SUMMARY: Patient Ahmed has acute cough. Penicillin allergy confirmed. Switch to Azithromycin."
    action_res = dashboard.submit_doctor_action("PAT-0012", action="EDIT", doctor_edits=edited_text)

    assert action_res["status"] == "SUCCESS", "Doctor action submission failed"
    assert action_res["hitl_status"] == "APPROVED", "Status failed to update to APPROVED"
    print("\n[PASS] 3. Doctor Dashboard Action Submitted (EDIT & APPROVE):")
    print("     New HITL Status :", action_res["hitl_status"])
    print("     Edited Text     :", edited_text)

    # 4. Resume Graph Execution Post-Approval
    resumed_st = action_res["updated_state"]
    final_st = graph.step(resumed_st)

    assert final_st["current_node"] == "COMPLETED", "Graph failed to resume and complete"
    print("\n[PASS] 4. Graph Execution Resumed & Completed Successfully!")

    print("=" * 65)
    print("[SUCCESS] HITL DOCTOR APPROVAL TEST PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_hitl_approval_workflow()

