"""
Test Suite for Records Agent and Clinical Summary Agent.
Generates and evaluates 10 pre-visit SOAP summaries across diverse patient profiles.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.records_agent import RecordsAgent
from src.agents.clinical_summary_agent import ClinicalSummaryAgent

SAMPLE_CASES = [
    ("PAT-0012", {"chief_complaint": "High fever and cough", "duration": "3 days", "severity": "7/10", "allergies": ["Penicillin"]}),
    ("PAT-0042", {"chief_complaint": "Severe headache and dizziness", "duration": "1 day", "severity": "8/10", "allergies": []}),
    ("PAT-0089", {"chief_complaint": "Stomach pain after meals", "duration": "5 days", "severity": "5/10", "allergies": ["Aspirin"]}),
    ("PAT-0115", {"chief_complaint": "Ear discharge and throat pain", "duration": "2 days", "severity": "6/10", "allergies": []}),
    ("PAT-0164", {"chief_complaint": "Routine blood sugar checkup", "duration": "Ongoing", "severity": "2/10", "allergies": ["Sulfa"]}),
    ("PAT-0201", {"chief_complaint": "Skin rash on arms and itching", "duration": "4 days", "severity": "4/10", "allergies": []}),
    ("PAT-0250", {"chief_complaint": "Joint stiffness and back pain", "duration": "1 week", "severity": "5/10", "allergies": []}),
    ("PAT-0300", {"chief_complaint": "Child fever 101F and vomiting", "duration": "1 day", "severity": "7/10", "allergies": []}),
    ("PAT-0350", {"chief_complaint": "Irregular period and pelvic ache", "duration": "2 weeks", "severity": "4/10", "allergies": []}),
    ("PAT-0400", {"chief_complaint": "Chest tightness on walking", "duration": "3 days", "severity": "6/10", "allergies": ["Penicillin"]}),
]

def test_records_and_summary():
    rec_agent = RecordsAgent()
    summary_agent = ClinicalSummaryAgent()

    print("=" * 65)
    print("[TEST] TESTING RECORDS AGENT QA")
    print("=" * 65)
    qa_res = rec_agent.answer_patient_query("PAT-0012", "Mera pichla lab test kaisa tha?")
    print("Records QA Response:", qa_res["urdulish_response"])
    assert qa_res["status"] == "SUCCESS"

    print("\n" + "=" * 65)
    print(f"[TEST] GENERATING & RATING 10 CLINICAL SOAP SUMMARIES")
    print("=" * 65)

    passed_count = 0
    for idx, (pid, intake) in enumerate(SAMPLE_CASES, 1):
        res = summary_agent.generate_soap_summary(pid, intake)
        soap = res["soap_structure"]["SOAP_NOTE"]

        # Validate SOAP structure integrity
        has_sub = "SUBJECTIVE_PATIENT_REPORTED" in soap
        has_obj = "OBJECTIVE_EMPIRICAL_DATA" in soap
        has_ass = "ASSESSMENT_FOR_DOCTOR_REVIEW_ONLY" in soap
        has_pln = "PLAN_AI_SUGGESTIONS" in soap

        if has_sub and has_obj and has_ass and has_pln:
            passed_count += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"[{idx:02d}/10] {status} Patient: {pid} | Chief: {intake['chief_complaint']}")
        if idx == 1:
            print("\n--- SAMPLE FORMATTED SOAP BRIEF (CASE 1) ---")
            print(res["formatted_text"])
            print("-------------------------------------------\n")

    accuracy_rate = (passed_count / 10) * 100
    print("=" * 65)
    print("[METRICS] CLINICAL SUMMARY AGENT RESULTS")
    print("=" * 65)
    print(f"Summaries Evaluated : 10")
    print(f"Passed Integrity    : {passed_count} / 10")
    print(f"Accuracy Rate       : {accuracy_rate:.1f}% (Target: 100%)")
    print("=" * 65)

if __name__ == "__main__":
    test_records_and_summary()

