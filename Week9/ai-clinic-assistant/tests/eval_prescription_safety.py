"""
Evaluation Benchmark Suite for Prescription Safety Engine.
Verifies 100% recall on allergy contraindications, dosage limits, drug interactions, and special cases.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools.prescription_safety_engine import PrescriptionSafetyEngine

TEST_SCENARIOS = [
    {
        "name": "Allergy Conflict (Penicillin -> Amoxicillin)",
        "proposed": [{"drug_name": "Amoxicillin", "dose_mg": 500, "frequency_per_day": 3}],
        "allergies": [{"allergen": "Penicillin"}],
        "expected_status": "CONTRAINDICATED"
    },
    {
        "name": "Dosage Limit Exceeded (Panadol > 4000mg/day)",
        "proposed": [{"drug_name": "Panadol", "dose_mg": 1500, "frequency_per_day": 4}],
        "allergies": [],
        "expected_status": "WARNING"
    },
    {
        "name": "Drug Interaction (Aspirin + Brufen)",
        "proposed": [{"drug_name": "Aspirin", "dose_mg": 300, "frequency_per_day": 1}, {"drug_name": "Brufen", "dose_mg": 400, "frequency_per_day": 2}],
        "allergies": [],
        "expected_status": "CONTRAINDICATED"
    },
    {
        "name": "Pregnancy Contraindication (Ibuprofen)",
        "proposed": [{"drug_name": "Ibuprofen", "dose_mg": 400, "frequency_per_day": 2}],
        "allergies": [],
        "is_pregnant": True,
        "expected_status": "CONTRAINDICATED"
    },
    {
        "name": "Safe Prescription (Panadol 500mg 3x/day)",
        "proposed": [{"drug_name": "Panadol", "dose_mg": 500, "frequency_per_day": 3}],
        "allergies": [],
        "expected_status": "CLEARED"
    }
]

def run_safety_evaluation():
    engine = PrescriptionSafetyEngine()
    total_scenarios = len(TEST_SCENARIOS)
    passed_count = 0

    print("=" * 65)
    print("[TEST] EVALUATING PRESCRIPTION SAFETY ENGINE (BENCHMARK)")
    print("=" * 65)

    for idx, scenario in enumerate(TEST_SCENARIOS, 1):
        res = engine.check_prescription_safety(
            proposed_medications=scenario["proposed"],
            patient_allergies=scenario.get("allergies", []),
            is_pregnant=scenario.get("is_pregnant", False)
        )

        status = res["overall_status"]
        expected = scenario["expected_status"]

        if status == expected:
            passed_count += 1
            test_result = "[PASS]"
        else:
            test_result = "[FAIL]"

        print(f"[{idx:02d}/{total_scenarios}] {test_result} Scenario: {scenario['name']}")
        print(f"     Status: {status} | Expected: {expected}")
        if res["flags"]:
            print(f"     Flag: {res['flags'][0]['message']}")

    recall_rate = (passed_count / total_scenarios) * 100

    print("=" * 65)
    print("[METRICS] PRESCRIPTION SAFETY EVALUATION METRICS")
    print("=" * 65)
    print(f"Total Scenarios Evaluated: {total_scenarios}")
    print(f"Scenarios Passed          : {passed_count} / {total_scenarios}")
    print(f"Safety Recall Rate        : {recall_rate:.1f}% (Target: 100%)")
    print("=" * 65)

if __name__ == "__main__":
    run_safety_evaluation()

