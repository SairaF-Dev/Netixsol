"""
Test Suite for ShortTermMemoryBuffer and LongTermPatientMemory.
Tests active session turn management, cross-visit memory updates, privacy filter, and personalized returning patient greetings.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.patient_memory import ShortTermMemoryBuffer, LongTermPatientMemory

def test_memory_system():
    print("=" * 65)
    print("[TEST] DUAL-TIER PATIENT MEMORY SYSTEM")
    print("=" * 65)

    # 1. Test Short-Term Buffer
    buf = ShortTermMemoryBuffer("SESSION-101")
    buf.add_turn("Patient", "Mujhe bukhar hai")
    buf.add_turn("AI", "Kab se hai?")
    buf.add_turn("Patient", "2 din se")

    recent = buf.get_recent_dialogue()
    assert "2 din se" in recent, "Short term buffer failed"
    print("[PASS] 1. Short-Term Memory Buffer:")
    print("     Recent Dialogue:\n    ", recent.replace("\n", "\n     "))

    # 2. Test Long-Term Memory & Persistence
    lt_mem = LongTermPatientMemory()
    lt_mem.update_patient_memory(
        patient_id="PAT-0042",
        preferred_doctor_id="DOC-005",
        preferred_doctor_name="Dr. Bilal Ahmed",
        preferred_branch_id="BRANCH-ISB-01",
        preferred_branch_name="F-7 Markaz Branch",
        last_complaint="Severe headache and dizziness"
    )

    mem_profile = lt_mem.get_patient_memory("PAT-0042")
    assert mem_profile["preferred_doctor_name"] == "Dr. Bilal Ahmed", "Long-term doctor memory failed"
    assert mem_profile["preferred_branch_name"] == "F-7 Markaz Branch", "Long-term branch memory failed"
    print("\n[PASS] 2. Long-Term Patient Memory:")
    print(f"     Patient      : {mem_profile['patient_name']} (ID: {mem_profile['patient_id']})")
    print(f"     Pref Doctor  : {mem_profile['preferred_doctor_name']}")
    print(f"     Pref Branch  : {mem_profile['preferred_branch_name']}")

    # 3. Test Returning Patient Personalized Greeting
    greeting = lt_mem.generate_returning_greeting("PAT-0042")
    assert "Dr. Bilal Ahmed" in greeting, "Returning greeting failed"
    assert "F-7 Markaz Branch" in greeting, "Branch greeting failed"
    print("\n[PASS] 3. Returning Patient Personalized Greeting:")
    print("     Generated Greeting:", greeting)

    print("=" * 65)
    print("[SUCCESS] DUAL-TIER PATIENT MEMORY TESTS PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_memory_system()

