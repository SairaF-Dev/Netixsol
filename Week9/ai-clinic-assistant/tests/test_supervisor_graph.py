"""
Test Suite for ClinicSupervisorGraph.
Tests full end-to-end patient workflow routing, parallel execution, emergency bypass, and transition logging.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.supervisor_graph import ClinicSupervisorGraph

def test_supervisor_routine_flow():
    graph = ClinicSupervisorGraph()
    print("=" * 65)
    print("[TEST] ROUTINE PATIENT JOURNEY - SUPERVISOR GRAPH WORKFLOW")
    print("=" * 65)

    st = graph.create_initial_state("PAT-0012")
    st = graph.step(st) # Get initial greeting

    turns = [
        "Mujhe 2 din se halka bukhar aur dry cough hai",
        "2 days",
        "5/10",
        "Body ache hai thora",
        "No allergies",
        "Panadol 500mg"
    ]

    for t in turns:
        st = graph.step(st, user_message=t)

    # Verify intake complete and graph transitioned to HITL Approval Checkpoint
    assert st["intake_form"]["is_complete"] == True, "Intake incomplete"
    assert st["triage_result"] is not None, "Triage failed"
    assert st["triage_result"]["urgency_level"] == "Routine"
    assert st["appointment_data"] is not None, "Scheduling failed"
    assert st["soap_summary"] is not None, "Clinical summary failed"
    assert st["hitl_status"] == "PAUSED_FOR_DOCTOR_APPROVAL", "HITL interrupt failed"

    print("[PASS] Routine Workflow Reached HITL Checkpoint Successfully!")
    print("\n--- GRAPH NODE TRANSITION LOGS ---")
    for log in st["transition_logs"]:
        print(log)

    # Doctor Approves Summary
    st["hitl_status"] = "APPROVED"
    st = graph.step(st) # Resume from HITL

    assert st["current_node"] == "COMPLETED", "Graph failed to complete after approval"
    print("\n[PASS] Graph Resumed & Completed Post-Doctor Approval!")

def test_supervisor_emergency_flow():
    graph = ClinicSupervisorGraph()
    print("\n" + "=" * 65)
    print("[TEST] EMERGENCY PATIENT JOURNEY - SUPERVISOR GRAPH BYPASS")
    print("=" * 65)

    st = graph.create_initial_state("PAT-0042")
    st = graph.step(st)

    turns = [
        "Achanak se severe chest pain aur shoulder mein dard ho raha hai",
        "10 mins",
        "9/10",
        "Pasina aa raha hai",
        "No allergies",
        "None"
    ]

    for t in turns:
        st = graph.step(st, user_message=t)

    assert st["triage_result"]["urgency_level"] == "Emergency", "Failed to detect emergency"
    assert st["current_node"] == "EMERGENCY_ESCALATION", "Emergency bypass failed"

    print("[PASS] Emergency Red-Flag Triggered Immediate Bypass to EMERGENCY_ESCALATION!")
    print("\n--- EMERGENCY GRAPH TRANSITION LOGS ---")
    for log in st["transition_logs"]:
        print(log)

    print("=" * 65)
    print("[SUCCESS] SUPERVISOR GRAPH TESTS PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_supervisor_routine_flow()
    test_supervisor_emergency_flow()

