"""
Integration Test Suite for Prescription Safety Agent and Follow-up Agent.
Tests doctor prescription warnings, reminder plan generation, check-in messages, and recovery escalations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.prescription_safety_agent import PrescriptionSafetyAgent
from src.agents.followup_agent import FollowupAgent

def test_safety_and_followup_flow():
    safety_agent = PrescriptionSafetyAgent()
    followup_agent = FollowupAgent()

    print("=" * 65)
    print("[TEST] PRESCRIPTION SAFETY AGENT & FOLLOW-UP AGENT SUITE")
    print("=" * 65)

    # 1. Test Prescription Safety Flagging (PAT-0017 has Amoxicillin Allergy in DB)
    draft_meds = [{"drug_name": "Amoxicillin", "dose_mg": 500, "frequency_per_day": 3}]
    eval_res = safety_agent.evaluate_doctor_prescription("PAT-0017", draft_meds)

    assert eval_res["status"] == "CONTRAINDICATED", "Prescription safety failed to catch allergy"
    print("[PASS] 1. Prescription Safety Agent:")
    print("     Status:", eval_res["status"])
    print("     Doctor Alert:\n    ", eval_res["doctor_alert_message"].replace("\n", "\n     "))

    # 2. Test Reminder Plan Generation
    rem_plan = followup_agent.create_reminder_plan(
        appointment_id="APT-99201",
        patient_name="Tariq Mahmood",
        medications=[{"drug_name": "Panadol 500mg", "frequency_per_day": 2}],
        follow_up_days=14
    )
    assert rem_plan["total_reminders_enqueued"] > 0, "Reminder plan failed"
    print("\n[PASS] 2. Follow-up Agent (Reminder Plan):")
    print(f"     Enqueued {rem_plan['total_reminders_enqueued']} reminders for APT-99201")

    # 3. Test Check-in Message & Recovery Evaluation
    checkin_msg = followup_agent.generate_checkin_message("Tariq Mahmood", "Dr. Ahmed")
    assert "City Care Clinics" in checkin_msg

    # Test Worsening Response Escalation
    worsening_reply = "Dawai se vomiting ho rahi hai aur tabiyat ziada kharab hai"
    fb_eval = followup_agent.evaluate_patient_feedback(worsening_reply)

    assert fb_eval["needs_escalation"] == True, "Escalation failed on worsening symptoms"
    assert fb_eval["status"] == "WORSENING"
    print("\n[PASS] 3. Follow-up Agent (Recovery Check-in & Escalation):")
    print("     Patient Reply :", worsening_reply)
    print("     Needs Esc     :", fb_eval["needs_escalation"])
    print("     UrduLish Reply:", fb_eval["urdulish_reply"])

    print("=" * 65)
    print("[SUCCESS] PRESCRIPTION SAFETY & FOLLOW-UP AGENT TESTS PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_safety_and_followup_flow()
