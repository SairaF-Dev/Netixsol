"""
Evaluation Benchmark Suite for Triage Agent.
Evaluates 50 clinical symptom scenarios covering:
- 15 Emergency cases
- 15 Urgent cases
- 20 Routine cases
Measures Emergency Recall Rate (target 100%), Under-Triage Rate, and Over-Triage Rate.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.triage_agent import TriageAgent

SCENARIOS = [
    # EMERGENCY SCENARIOS (1-15)
    {"q": "Achanak se severe chest pain aur shoulder mein dard ho raha hai", "expected": "Emergency"},
    {"q": "Saans lene mein sakht masla ho raha hai, unable to breathe", "expected": "Emergency"},
    {"q": "Chehra aik taraf jhuk gaya hai aur bolne mein masla hai (stroke)", "expected": "Emergency"},
    {"q": "Khoon bohot ziada nikal raha hai, heavy bleeding stops not", "expected": "Emergency"},
    {"q": "3 mahine bacha ko 103 degree bukhar hai", "expected": "Emergency"},
    {"q": "Gala phool raha hai aur saans band ho rahi hai (anaphylaxis)", "expected": "Emergency"},
    {"q": "Seene mein crushing pressure aur pasinay aa rahe hain", "expected": "Emergency"},
    {"q": "Achanak severe headache aur behoshi ho gayi thi", "expected": "Emergency"},
    {"q": "Dil mein tez dard aur left arm mein pain", "expected": "Emergency"},
    {"q": "Khansi mein khoon aa raha hai (coughing blood)", "expected": "Emergency"},
    {"q": "Bache ko seizure / fit aaya hai", "expected": "Emergency"},
    {"q": "Khudkushi karne ka khayal aa raha hai", "expected": "Emergency"},
    {"q": "Newborn baby ko 102 bukhar hai", "expected": "Emergency"},
    {"q": "Seene mein tez dard", "expected": "Emergency"},
    {"q": "Saans phool rahi hai aur behoshi ho rahi hai", "expected": "Emergency"},

    # URGENT SCENARIOS (16-30)
    {"q": "Tez bukhar 103 aur baar baar ulti ho rahi hai", "expected": "Urgent"},
    {"q": "Kaan mein sakht dard aur peep / discharge nikal raha hai", "expected": "Urgent"},
    {"q": "Pait mein severe acute pain hai khane ke baad", "expected": "Urgent"},
    {"q": "Bache ko kal se ultiyan aur loose motions hain", "expected": "Urgent"},
    {"q": "Haat par gehra kat laga hai stitches chahiye", "expected": "Urgent"},
    {"q": "Ankh mein redness aur bohot dard hai", "expected": "Urgent"},
    {"q": "Tez bukhar aur jism mein dard", "expected": "Urgent"},
    {"q": "Paon mein moach aagayi hai aur sujan hai", "expected": "Urgent"},
    {"q": "Gala sakht kharab hai aur khana nigalna mushkil hai", "expected": "Urgent"},
    {"q": "Pait ke daayein taraf sakht dard hai", "expected": "Urgent"},
    {"q": "Peshab mein jalan aur bukhar hai", "expected": "Urgent"},
    {"q": "Severe migraine headache kal se", "expected": "Urgent"},
    {"q": "Bache ko 101 bukhar aur khansi hai", "expected": "Urgent"},
    {"q": "Dant mein sakht dard hai", "expected": "Urgent"},
    {"q": "High BP reading 160/100 aayi hai", "expected": "Urgent"},

    # ROUTINE SCENARIOS (31-50)
    {"q": "Halka bukhar aur dry cough 2 din se hai", "expected": "Routine"},
    {"q": "Chehre par acne aur daane nikal rahe hain", "expected": "Routine"},
    {"q": "Routine sugar level checkup karwana hai", "expected": "Routine"},
    {"q": "Kharish aur halka skin rash hai", "expected": "Routine"},
    {"q": "Baal girne ka masla hai", "expected": "Routine"},
    {"q": "Regular BP checkup ke liye doctor ko dikhana hai", "expected": "Routine"},
    {"q": "Halki khansi aur naak beh rahi hai", "expected": "Routine"},
    {"q": "Dawai ki prescription renew karwani hai", "expected": "Routine"},
    {"q": "Weight loss diet plan ke liye consultation", "expected": "Routine"},
    {"q": "Kaan mein aawazein aati hain halki", "expected": "Routine"},
    {"q": "Period dates irregular hain", "expected": "Routine"},
    {"q": "Gardan mein thora sa khichao hai", "expected": "Routine"},
    {"q": "Halka pait kharab hai acidity se", "expected": "Routine"},
    {"q": "Routine health checkup overall", "expected": "Routine"},
    {"q": "Palkon par halki sujan hai", "expected": "Routine"},
    {"q": "Thakawat rehti hai din mein", "expected": "Routine"},
    {"q": "Skin allergy checkup", "expected": "Routine"},
    {"q": "Lab reports doctor ko dikhani hain", "expected": "Routine"},
    {"q": "Halka sar dard fatigue se", "expected": "Routine"},
    {"q": "Pregnancy routine monthly checkup", "expected": "Routine"},
]

def run_triage_benchmark():
    agent = TriageAgent()
    total = len(SCENARIOS)
    
    emergency_expected = 0
    emergency_caught = 0
    under_triage_count = 0
    over_triage_count = 0
    passed_exact = 0

    print("=" * 65)
    print(f"[TEST] EVALUATING TRIAGE AGENT (50 SCENARIOS)")
    print("=" * 65)

    for idx, sc in enumerate(SCENARIOS, 1):
        q = sc["q"]
        expected = sc["expected"]
        
        # Build mock intake payload
        intake_payload = {
            "chief_complaint": q,
            "associated_symptoms": [],
            "patient_type": "child" if "bache" in q or "baby" in q or "newborn" in q else "self"
        }
        
        res = agent.evaluate_triage(intake_payload)
        actual = res["urgency_level"]

        if expected == "Emergency":
            emergency_expected += 1
            if actual == "Emergency":
                emergency_caught += 1

        if actual == expected:
            passed_exact += 1
            status = "[PASS]"
        elif expected in ["Emergency", "Urgent"] and actual == "Routine":
            under_triage_count += 1
            status = "[UNDER-TRIAGE FAIL]"
        else:
            over_triage_count += 1
            status = "[OVER-TRIAGE WARN]"

        print(f"[{idx:02d}/{total}] {status} Actual: {actual:<10} | Expected: {expected:<10} | Query: {q}")

    emergency_recall = (emergency_caught / emergency_expected) * 100 if emergency_expected else 100.0
    under_triage_rate = (under_triage_count / total) * 100
    over_triage_rate = (over_triage_count / total) * 100

    print("=" * 65)
    print("[METRICS] TRIAGE BENCHMARK EVALUATION RESULTS")
    print("=" * 65)
    print(f"Total Scenarios Evaluated  : {total}")
    print(f"Emergency Scenarios        : {emergency_expected}")
    print(f"Emergency Caught (Recall)  : {emergency_caught} / {emergency_expected}")
    print(f"Emergency Recall Rate      : {emergency_recall:.1f}% (Target: 100.0%)")
    print(f"Under-Triage Rate          : {under_triage_rate:.1f}% (Target: 0.0%)")
    print(f"Over-Triage Rate           : {over_triage_rate:.1f}%")
    print("=" * 65)

if __name__ == "__main__":
    run_triage_benchmark()

