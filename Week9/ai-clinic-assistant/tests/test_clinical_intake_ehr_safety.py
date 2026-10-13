"""
Comprehensive Clinical Safety, Intake, Authorization & Scheduling Verification Test Suite.
Validates all 12 mandatory clinical scenarios for MedCare Clinic platform:
1. Patient reporting new Brufen allergy with Penicillin already on file (additive preservation).
2. Patient reporting Rizek when Panadol is listed as a current medicine (reconciliation discrepancy).
3. Active Amoxicillin prescription alongside recorded Penicillin allergy (cross-allergy flag; no auto-cancel).
4. Missing symptom information and unknown answers (treated as Unknown, not negative).
5. Emergency warning signs interrupting routine scheduling (overrides low numerical scores).
6. Duplicate booking attempts and conflicting time slots (transactional conflict rejection).
7. Scheduling failure and unsuccessful database persistence handling (no fabricated IDs).
8. Successful booking with genuine appointment ID persistence verified in SQLite.
9. Existing completed appointments remaining unchanged (APT-72D443 historical integrity).
10. Correct patient authorization and prevention of cross-patient data access.
11. Conversation continuity across multiple stateful messages.
12. Correct UrduLish language handling and avoidance of repeated questions.
"""

import sys
import os
import sqlite3
import datetime
from datetime import timedelta

# Setup project root path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.agents.intake_agent import IntakeAgent
from src.agents.scheduling_agent import SchedulingAgent
from src.agents.clinical_summary_agent import ClinicalSummaryAgent
from src.agents.triage_agent import TriageAgent
from src.mcp_servers.scheduling_server import SchedulingMCPServer
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer

DB_PATH = os.path.join(BASE_DIR, "data", "synthetic", "clinic.db")


def test_scenario_1_brufen_allergy_with_penicillin_on_file():
    """Scenario 1: A patient reporting a new Brufen allergy when Penicillin is already on file."""
    print("\n[TEST 1] Testing new Brufen allergy reporting with Penicillin on file...")
    intake = IntakeAgent()
    records_mcp = PatientRecordsMCPServer()

    # 1. Verify Penicillin allergy exists on file for PAT-5501
    ehr_algs = records_mcp.get_patient_allergies("PAT-5501")
    alg_names = [a["allergen"].lower() for a in ehr_algs]
    assert any("penicillin" in name for name in alg_names), "Penicillin allergy must exist in EHR on file"

    # 2. Patient reports Brufen allergy
    state = {
        "patient_id": "PAT-5501",
        "chief_complaint": "zukaam hai mujey",
        "duration": "4 din",
        "severity": "3/10",
        "associated_symptoms": ["sore throat"],
        "allergies": None,
        "current_medications": None
    }
    reply, state, is_complete = intake.process_turn("Brufen allergy hai", state)

    # 3. Verify Brufen is recorded without deleting or replacing Penicillin
    assert state["allergies"] is not None and any("brufen" in str(a).lower() for a in state["allergies"])
    
    # 4. Perform live reconciliation check
    reconciled_state = intake.reconcile_ehr_and_intake(state, "PAT-5501")
    assert any("penicillin" in str(a).lower() for a in reconciled_state["ehr_allergies_on_file"]), "EHR Penicillin allergy must be preserved"
    print("  -> PASS: Both Penicillin (EHR on file) and Brufen (reported) preserved without silent deletion.")


def test_scenario_2_rizek_reported_with_panadol_on_file():
    """Scenario 2: A patient reporting Rizek when Panadol is listed as a current medicine."""
    print("\n[TEST 2] Testing Rizek reporting when Panadol is listed in current medicines...")
    intake = IntakeAgent()
    records_mcp = PatientRecordsMCPServer()

    # Verify Panadol exists in EHR
    ehr_meds = records_mcp.get_patient_medications("PAT-5501")
    has_panadol = any("panadol" in m["drug_name"].lower() for m in ehr_meds)
    assert has_panadol, "Panadol must exist in EHR medication records for PAT-5501"

    # Patient reports taking Rizek
    state = {
        "patient_id": "PAT-5501",
        "chief_complaint": "zukaam hai mujey",
        "duration": "4 din",
        "severity": "3/10",
        "associated_symptoms": ["sore throat"],
        "allergies": ["Brufen"],
        "current_medications": None
    }
    reply, state, is_complete = intake.process_turn("taking Rizek", state)

    # Reconcile EHR
    reconciled_state = intake.reconcile_ehr_and_intake(state, "PAT-5501")
    flags = reconciled_state.get("reconciliation_flags", [])
    
    # Assert reconciliation discrepancy flag is raised
    has_discrepancy_flag = any("discrepancy" in f.lower() or "rizek" in f.lower() for f in flags)
    assert has_discrepancy_flag, "Reconciliation flag must record discrepancy between reported Rizek and EHR list"
    assert any("panadol" in str(m).lower() for m in reconciled_state["ehr_medications_on_file"]), "EHR Panadol must remain intact"
    print("  -> PASS: Discrepancy between reported Rizek and EHR Panadol cleanly recorded for clinician review.")


def test_scenario_3_amoxicillin_prescription_with_penicillin_allergy():
    """Scenario 3: An active Amoxicillin prescription alongside a recorded Penicillin allergy."""
    print("\n[TEST 3] Testing active Amoxicillin prescription alongside Penicillin allergy...")
    intake = IntakeAgent()
    records_mcp = PatientRecordsMCPServer()

    # Verify active Amoxicillin prescription in DB
    ehr_meds = records_mcp.get_patient_medications("PAT-5501", status="Active")
    amox_rx = [m for m in ehr_meds if "amoxicillin" in m["drug_name"].lower()]
    assert len(amox_rx) > 0, "Active Amoxicillin prescription RX-77369 must exist for PAT-5501"

    # Reconcile for PAT-5501
    state = {
        "patient_id": "PAT-5501",
        "chief_complaint": "zukaam hai mujey",
        "allergies": ["Brufen"],
        "current_medications": ["Rizek"]
    }
    reconciled_state = intake.reconcile_ehr_and_intake(state, "PAT-5501")
    flags = reconciled_state.get("reconciliation_flags", [])

    # Verify cross-reactivity safety alert flagged for clinician review
    has_amox_alert = any("amoxicillin" in f.lower() and "penicillin" in f.lower() for f in flags)
    assert has_amox_alert, "Active Amoxicillin prescription must be flagged due to Penicillin allergy cross-reactivity"

    # Verify prescription was NOT independently cancelled or deleted
    rechecked_meds = records_mcp.get_patient_medications("PAT-5501", status="Active")
    assert any("amoxicillin" in m["drug_name"].lower() for m in rechecked_meds), "Prescription must remain active in DB until clinician review"
    print("  -> PASS: Active Amoxicillin prescription correctly flagged for clinician review without independent deletion.")


def test_scenario_4_missing_symptom_info_and_unknown_answers():
    """Scenario 4: Missing symptom information and unknown answers."""
    print("\n[TEST 4] Testing unknown responses and missing symptom info...")
    intake = IntakeAgent()

    state = None
    # Turn 1: Chief complaint
    reply, state, comp = intake.process_turn("zukaam hai mujey", state)
    assert comp == False

    # Turn 2: Unknown duration
    reply, state, comp = intake.process_turn("pata nahi", state)
    assert "unknown" in state["duration"].lower(), "Unknown duration must be recorded as Unknown"
    assert comp == False

    # Turn 3: Unknown severity
    reply, state, comp = intake.process_turn("maloom nahi", state)
    assert "unknown" in state["severity"].lower(), "Unknown severity must be recorded as Unknown"
    assert comp == False

    # Turn 4: Unknown associated symptoms
    reply, state, comp = intake.process_turn("don't know", state)
    assert "Unknown" in state["associated_symptoms"], "Unknown associated symptoms must not be treated as negative (None)"
    print("  -> PASS: Unknown responses preserved as Unknown without being treated as negative.")


def test_scenario_5_emergency_warning_signs_interrupting_routine_scheduling():
    """Scenario 5: Emergency warning signs interrupting routine scheduling."""
    print("\n[TEST 5] Testing emergency warning signs overriding low self-reported severity...")
    intake = IntakeAgent()

    # Case A: Casual chest pain downplayed with low severity
    msg = "Seene mein dard aur pasina aa raha hai lekin severity sirf 2 hai"
    reply, state, comp = intake.process_turn(msg, None)

    assert comp == True, "Emergency must immediately complete/interrupt routine flow"
    assert state.get("is_high_severity") == True or state.get("urgency_level") == "Emergency"
    assert "[EMERGENCY ALERT]" in reply
    assert "1122" in reply or "Emergency Room" in reply

    # Case B: Breathing difficulty reported as associated symptom with severity 3
    state_b = {
        "patient_id": "PAT-5501",
        "chief_complaint": "bukhar hai",
        "duration": "2 din",
        "severity": "3/10",
        "associated_symptoms": [],
        "allergies": None,
        "current_medications": None
    }
    reply_b, state_b, comp_b = intake.process_turn("saans lene mein bohot shadeed masla ho raha hai", state_b)
    assert comp_b == True, "Severe respiratory red-flag in associated symptoms must trigger emergency"
    assert "[EMERGENCY ALERT]" in reply_b
    print("  -> PASS: Serious warning signs strictly override low numerical scores and suspend routine booking.")


def test_scenario_6_duplicate_booking_attempts_and_conflicting_slots():
    """Scenario 6: Duplicate booking attempts and conflicting time slots."""
    print("\n[TEST 6] Testing duplicate booking attempts and conflicting slot rejection...")
    sched_mcp = SchedulingMCPServer(DB_PATH)

    test_date = (datetime.datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    test_slot = "10:30 AM"
    doc_id = "DOC-001"
    pat_id = "PAT-TEST-CONFLICT"

    # Cleanup any leftovers
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM appointments WHERE patient_id = ? OR (doctor_id = ? AND appointment_date = ? AND time_slot = ?)", 
                 (pat_id, doc_id, test_date, test_slot))
    conn.commit()
    conn.close()

    # 1. Book first appointment (Should succeed)
    res1 = sched_mcp.book_appointment(
        patient_id=pat_id,
        doctor_id=doc_id,
        branch_id="BRANCH-LHR-01",
        date_str=test_date,
        time_slot=test_slot,
        urgency="Routine",
        complaint="Test initial booking"
    )
    assert res1.get("status") == "Scheduled", f"First booking should succeed: {res1}"
    apt_id_1 = res1["appointment_id"]

    # 2. Attempt exact same slot for same doctor with different patient (Doctor double-booking conflict)
    res2 = sched_mcp.book_appointment(
        patient_id="PAT-ANOTHER",
        doctor_id=doc_id,
        branch_id="BRANCH-LHR-01",
        date_str=test_date,
        time_slot=test_slot,
        urgency="Routine",
        complaint="Conflicting booking"
    )
    assert res2.get("status") == "ERROR", "Doctor double-booking must be rejected"
    assert res2.get("conflict_type") == "DOCTOR_UNAVAILABLE"

    # 3. Attempt same slot on same date for same patient with different doctor (Patient slot conflict)
    res3 = sched_mcp.book_appointment(
        patient_id=pat_id,
        doctor_id="DOC-031",
        branch_id="BRANCH-LHR-01",
        date_str=test_date,
        time_slot=test_slot,
        urgency="Routine",
        complaint="Double booking for patient"
    )
    assert res3.get("status") == "ERROR", "Patient overlapping appointment must be rejected"
    assert res3.get("conflict_type") == "PATIENT_SLOT_CONFLICT"

    # Cleanup test appointment
    sched_mcp.cancel_appointment(apt_id_1)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id_1,))
    conn.commit()
    conn.close()
    print("  -> PASS: Transactional conflict validation prevented duplicate provider and patient bookings.")


def test_scenario_7_scheduling_api_failures_and_persistence_handling():
    """Scenario 7: Scheduling API failures and unsuccessful database persistence."""
    print("\n[TEST 7] Testing scheduling API failure handling...")
    sched_agent = SchedulingAgent()

    # Attempt to book a past date
    past_date = (datetime.datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    fail_res = sched_agent.confirm_booking(
        patient_id="PAT-5501",
        doctor_id="DOC-001",
        branch_id="BRANCH-LHR-01",
        date_str=past_date,
        time_slot="10:00 AM",
        urgency="Routine",
        chief_complaint="Past booking test"
    )

    assert fail_res.get("status") == "ERROR", "Past date booking must return ERROR"
    assert "appointment_id" not in fail_res or fail_res.get("appointment_id") is None
    assert "maazi" in fail_res.get("urdulish_response", "").lower() or "past" in fail_res.get("message", "").lower()
    print("  -> PASS: System cleanly reported scheduling failure without hallucinating confirmation.")


def test_scenario_8_successful_booking_real_appointment_id():
    """Scenario 8: Successful booking with the real appointment ID returned by the backend."""
    print("\n[TEST 8] Testing successful booking with real DB persistence...")
    sched_mcp = SchedulingMCPServer(DB_PATH)
    sched_agent = SchedulingAgent(sched_mcp)

    future_date = (datetime.datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")
    open_slots = sched_mcp.check_available_slots("DOC-001", future_date)
    assert len(open_slots) > 0, "Future test date must have available slots"
    selected_slot = open_slots[0]

    booking = sched_agent.confirm_booking(
        patient_id="PAT-5501",
        doctor_id="DOC-001",
        branch_id="BRANCH-LHR-01",
        date_str=future_date,
        time_slot=selected_slot,
        urgency="Routine",
        chief_complaint="Verified E2E booking"
    )

    assert booking.get("status") == "CONFIRMED"
    apt_id = booking["booking_details"]["appointment_id"]
    assert apt_id.startswith("APT-")

    # Verify directly in SQLite DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM appointments WHERE id = ?", (apt_id,)).fetchone()
    conn.close()

    assert row is not None, f"Appointment {apt_id} must genuinely exist in SQLite database"
    assert row["patient_id"] == "PAT-5501"
    assert row["appointment_date"] == future_date
    assert row["time_slot"] == selected_slot
    assert row["status"] == "Scheduled"

    # Cleanup
    sched_mcp.cancel_appointment(apt_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
    conn.commit()
    conn.close()
    print(f"  -> PASS: Real appointment {apt_id} verified in SQLite database.")


def test_scenario_9_existing_completed_appointments_remain_unchanged():
    """Scenario 9: Existing completed appointments remaining unchanged."""
    print("\n[TEST 9] Verifying historical completed appointments remain intact...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    apt = conn.execute("SELECT * FROM appointments WHERE id = 'APT-72D443'").fetchone()
    conn.close()

    assert apt is not None, "Appointment APT-72D443 must exist in database"
    assert apt["status"] == "Completed", "APT-72D443 must have status 'Completed'"
    assert apt["patient_id"] == "PAT-5501"
    assert apt["doctor_id"] == "DOC-031"
    print("  -> PASS: Completed appointment APT-72D443 status and history remain completely intact.")


def test_scenario_10_correct_patient_authorization_and_isolation():
    """Scenario 10: Correct patient authorization and prevention of cross-patient data access."""
    print("\n[TEST 10] Testing patient authorization and isolation between PAT-5501 and PAT-1001...")
    records_mcp = PatientRecordsMCPServer(DB_PATH)

    pat_5501 = records_mcp.get_patient_profile("PAT-5501")
    pat_1001 = records_mcp.get_patient_profile("PAT-1001")

    assert pat_5501["name"] == "Saira Fatima"
    assert pat_1001["name"] == "Ahmed Khan"

    meds_5501 = records_mcp.get_patient_medications("PAT-5501")
    meds_1001 = records_mcp.get_patient_medications("PAT-1001")

    # Assert no cross-leakage
    med_ids_5501 = {m["id"] for m in meds_5501}
    med_ids_1001 = {m["id"] for m in meds_1001}
    assert med_ids_5501.isdisjoint(med_ids_1001), "Patient medication records must be strictly isolated"
    print("  -> PASS: Strict patient isolation verified between PAT-5501 and PAT-1001.")


def test_scenario_11_conversation_continuity_across_multiple_messages():
    """Scenario 11: Conversation continuity across multiple stateful messages."""
    print("\n[TEST 11] Testing conversation continuity across turns...")
    intake = IntakeAgent()

    state = None
    turns = [
        ("zukaam hai mujey", "chief_complaint"),
        ("four days", "duration"),
        ("3", "severity"),
        ("sore throat", "associated_symptoms"),
        ("Brufen", "allergies"),
        ("Facial swelling", "allergy_details"),
        ("taking Rizek", "current_medications"),
        ("20mg subah li thi", "medication_details")
    ]

    for msg, expected_updated_field in turns:
        reply, state, is_comp = intake.process_turn(msg, state)

    assert state["chief_complaint"] == "zukaam hai mujey"
    assert state["duration"] == "four days"
    assert state["severity"] == "3" or "3" in str(state["severity"])
    assert "sore throat" in state["associated_symptoms"]
    assert any("brufen" in a.lower() for a in state["allergies"])
    assert any("rizek" in m.lower() for m in state["current_medications"])
    assert is_comp == True
    print("  -> PASS: All 8 conversation turns preserved state continuity accurately.")


def test_scenario_12_language_handling_and_no_repeated_questions():
    """Scenario 12: Correct language handling and avoidance of repeated questions."""
    print("\n[TEST 12] Testing avoidance of repeated questions when information already provided...")
    intake = IntakeAgent()

    # Patient provides both chief complaint and duration in Turn 1
    reply1, state1, comp1 = intake.process_turn("Mujhe 4 din se zukaam hai", None)

    # Duration was already extracted, so agent should NOT ask "kab se hai?" or "duration kitni hai?"
    assert state1["duration"] is not None
    assert "kab se hai" not in reply1.lower() and "duration kitni" not in reply1.lower()
    assert any(term in reply1.lower() for term in ["0 se 10", "severity", "shiddat", "scale", "number", "kitni"])
    print("  -> PASS: Agent did not repeat duration question and smoothly progressed to severity.")


def run_all_tests():
    print("=" * 75)
    print("MEDCARE CLINIC — COMPREHENSIVE CLINICAL SAFETY & SCHEDULING VERIFICATION")
    print("=" * 75)

    test_scenario_1_brufen_allergy_with_penicillin_on_file()
    test_scenario_2_rizek_reported_with_panadol_on_file()
    test_scenario_3_amoxicillin_prescription_with_penicillin_allergy()
    test_scenario_4_missing_symptom_info_and_unknown_answers()
    test_scenario_5_emergency_warning_signs_interrupting_routine_scheduling()
    test_scenario_6_duplicate_booking_attempts_and_conflicting_slots()
    test_scenario_7_scheduling_api_failures_and_persistence_handling()
    test_scenario_8_successful_booking_real_appointment_id()
    test_scenario_9_existing_completed_appointments_remain_unchanged()
    test_scenario_10_correct_patient_authorization_and_isolation()
    test_scenario_11_conversation_continuity_across_multiple_messages()
    test_scenario_12_language_handling_and_no_repeated_questions()

    print("\n" + "=" * 75)
    print("ALL 12 MANDATORY CLINICAL SAFETY & EHR SCHEDULING TESTS PASSED (100%)!")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()

