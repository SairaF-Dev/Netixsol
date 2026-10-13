"""
Integration Test Suite for Scheduling Agent.
Tests options suggestion, booking confirmation, past date prevention, and UrduLish formatting.
"""

import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.scheduling_agent import SchedulingAgent

def test_scheduling_flow():
    agent = SchedulingAgent()
    print("=" * 65)
    print("[TEST] SCHEDULING AGENT INTEGRATION TEST")
    print("=" * 65)

    # 1. Test Option Suggestion
    triage_info = {"recommended_specialty": "Cardiology", "urgency_level": "Routine"}
    opts = agent.suggest_options(triage_info, city="Lahore", patient_id="PAT-0012")

    assert opts["status"] == "OPTIONS_FOUND", "Option suggestion failed"
    print("[PASS] 1. Options Suggestion:")
    print("     Response:", opts["urdulish_response"])

    # 2. Test Booking Confirmation
    doc = opts["doctor"]
    slot = opts["available_slots"][0]
    date_str = opts["proposed_date"]

    confirm = agent.confirm_booking(
        patient_id="PAT-0012",
        doctor_id=doc["id"],
        branch_id=doc["branch_id"],
        date_str=date_str,
        time_slot=slot,
        urgency="Routine",
        chief_complaint="Chest tightness"
    )

    assert confirm["status"] == "CONFIRMED", "Booking failed"
    print("\n[PASS] 2. Booking Confirmation:")
    print("     Response:", confirm["urdulish_response"])

    # 3. Test Past Date Safeguard
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    past_booking = agent.confirm_booking("PAT-0012", doc["id"], doc["branch_id"], yesterday, "10:00 AM")
    assert past_booking["status"] == "ERROR", "Past date safeguard failed"
    print("\n[PASS] 3. Past Date Safeguard: Correctly rejected past date booking.")

    # Cleanup test booking
    if confirm.get("booking_details", {}).get("appointment_id"):
        agent.mcp.cancel_appointment(confirm["booking_details"]["appointment_id"])

    print("=" * 65)
    print("[SUCCESS] SCHEDULING AGENT TEST PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_scheduling_flow()

