"""
Integration Test Suite for all 4 MCP Servers:
1. patient-records
2. scheduling
3. drug-database
4. notifications
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mcp_servers.patient_records_server import PatientRecordsMCPServer
from src.mcp_servers.scheduling_server import SchedulingMCPServer
from src.mcp_servers.drug_database_server import DrugDatabaseMCPServer
from src.mcp_servers.notifications_server import NotificationsMCPServer

def test_all_mcp_servers():
    print("=" * 65)
    print("[TEST] RUNNING INTEGRATION TESTS FOR 4 MCP SERVERS")
    print("=" * 65)

    # 1. Test patient-records MCP
    rec_server = PatientRecordsMCPServer()
    prof = rec_server.get_patient_profile("PAT-0012")
    algs = rec_server.get_patient_allergies("PAT-0012")
    history = rec_server.get_patient_history("PAT-0012")
    labs = rec_server.get_patient_labs("PAT-0012")
    
    assert "name" in prof, "Profile failed"
    print(f"[PASS] MCP 1: patient-records | Name: {prof.get('name')} | Allergies: {len(algs)} | History: {len(history)} | Labs: {len(labs)}")

    # 2. Test scheduling MCP
    sched_server = SchedulingMCPServer()
    docs = sched_server.find_doctors(specialty="Cardiology")
    assert len(docs) > 0, "Find doctors failed"
    doc_id = docs[0]["id"]
    branch_id = docs[0]["branch_id"]
    
    slots = sched_server.check_available_slots(doc_id, "2026-10-15")
    assert len(slots) > 0, "Slots check failed"
    
    booking = sched_server.book_appointment("PAT-0012", doc_id, branch_id, "2026-10-15", slots[0], "Routine", "Chest tightness checkup")
    assert booking["status"] == "Scheduled", "Booking failed"
    print(f"[PASS] MCP 2: scheduling | Found {len(docs)} Cardio doctors | Slot Booked: {booking['appointment_id']} ({slots[0]})")

    # 3. Test drug-database MCP
    drug_server = DrugDatabaseMCPServer()
    drug_info = drug_server.lookup_drug("Amoxicillin")
    conflict = drug_server.check_allergy_conflict([{"allergen": "Penicillin"}], "Amoxicillin")
    interaction = drug_server.check_drug_interaction("Aspirin", "Ibuprofen")
    
    assert drug_info["found"] == True, "Drug lookup failed"
    assert conflict["has_conflict"] == True, "Allergy conflict detection failed"
    assert interaction["has_interaction"] == True, "Interaction detection failed"
    print(f"[PASS] MCP 3: drug-database | Drug: Amoxicillin | Allergy Conflict Caught: {conflict['has_conflict']} | Interaction Caught: {interaction['has_interaction']}")

    # 4. Test notifications MCP
    notif_server = NotificationsMCPServer()
    wa_res = notif_server.send_whatsapp_message("+92-300-1234567", "Your appointment is set.")
    email_res = notif_server.send_email_confirmation("patient@example.com", "Booking", "Details here")
    rem_res = notif_server.schedule_reminder(booking["appointment_id"])
    
    assert wa_res["status"] == "SENT", "WhatsApp failed"
    assert email_res["status"] == "SENT", "Email failed"
    assert rem_res["status"] == "SCHEDULED", "Reminder failed"
    print(f"[PASS] MCP 4: notifications | WhatsApp: SENT | Email: SENT | Reminder: SCHEDULED ({rem_res['task_id']})")

    print("=" * 65)
    print("[SUCCESS] ALL 4 MCP SERVERS PASSED 100% OF INTEGRATION TESTS")
    print("=" * 65)

if __name__ == "__main__":
    test_all_mcp_servers()

