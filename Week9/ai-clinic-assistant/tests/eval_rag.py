"""
Automated RAG Evaluation Suite for City Care Clinics.
Runs 25 realistic patient queries across UrduLish and English.
Measures Grounding Rate (%) and Hallucination Rate (%).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag.rag_engine import RAGEngine

BENCHMARK_QUESTIONS = [
    # Clinic Operational & Fee FAQs (1-7)
    {"q": "DHA branch ka timing aur phone number kya hai?", "expected_source": "clinic_faqs.md"},
    {"q": "General Medicine doctor consultation fee kitni hai?", "expected_source": "clinic_faqs.md"},
    {"q": "Cardiology doctor ki fee kitni hai?", "expected_source": "clinic_faqs.md"},
    {"q": "Islamabad mein konsi branches hain?", "expected_source": "clinic_faqs.md"},
    {"q": "Kya main appointment 2 ghante pehle cancel kar sakta hoon?", "expected_source": "clinic_faqs.md"},
    {"q": "Gulberg branch ka phone number batayein", "expected_source": "clinic_faqs.md"},
    {"q": "Kya clinic par emergency trauma treatment hoti hai?", "expected_source": "clinic_faqs.md"},

    # Lab Test Prep (8-14)
    {"q": "Fasting blood sugar test ke liye kitni der pait khali rakhna hai?", "expected_source": "lab_test_instructions.md"},
    {"q": "Lipid profile test se pehle kya chai ya doodh pi sakte hain?", "expected_source": "lab_test_instructions.md"},
    {"q": "CBC test ke liye fasting zaroori hai?", "expected_source": "lab_test_instructions.md"},
    {"q": "HbA1c test ke liye kitne ghante ki fasting chahiye?", "expected_source": "lab_test_instructions.md"},
    {"q": "Ultrasound abdomen ke liye paani peena zaroori hai?", "expected_source": "lab_test_instructions.md"},
    {"q": "LFT test ke liye kya parhez karna hai?", "expected_source": "lab_test_instructions.md"},
    {"q": "Fasting test ke waqt BP ki dawai le sakte hain?", "expected_source": "lab_test_instructions.md"},

    # Patient Education Leaflets (15-20)
    {"q": "Dengue fever mein konsi dawai bilkul nahi leni chahiye?", "expected_source": "patient_education.md"},
    {"q": "Sugar kam (hypoglycemia) ho jaye to kya karna chahiye?", "expected_source": "patient_education.md"},
    {"q": "Normal Blood pressure ka target range kya hota hai?", "expected_source": "patient_education.md"},
    {"q": "3 mahine se chote bache ko bukhar ho to kya karein?", "expected_source": "patient_education.md"},
    {"q": "Dengue ke warning signs kya hain?", "expected_source": "patient_education.md"},
    {"q": "High BP ke mareez ko namak kitna kam karna chahiye?", "expected_source": "patient_education.md"},

    # Symptom Specialty Routing (21-25)
    {"q": "Bache ko 3 din se bukhar aur ulti hai, kis doctor ko dikhayen?", "expected_source": "symptom_specialty_mapping.md"},
    {"q": "Skin rash aur kharish ke liye konsi specialty hai?", "expected_source": "symptom_specialty_mapping.md"},
    {"q": "Gala kharab aur kaan mein dard ke liye kis department jayein?", "expected_source": "symptom_specialty_mapping.md"},
    {"q": "Chehra sunn hona aur arm weakness kis cheez ka sign hai?", "expected_source": "symptom_specialty_mapping.md"},
    {"q": "Period irregular hone par kis doctor ko check karwayen?", "expected_source": "symptom_specialty_mapping.md"}
]

def run_evaluation():
    engine = RAGEngine()
    total_q = len(BENCHMARK_QUESTIONS)
    grounded_count = 0
    hallucination_count = 0

    print("=" * 65)
    print("[TEST] RUNNING RAG EVALUATION BENCHMARK (25 QUESTIONS)")
    print("=" * 65)

    for idx, item in enumerate(BENCHMARK_QUESTIONS, 1):
        q = item["q"]
        res = engine.query(q)
        is_grounded = res["is_grounded"] and len(res["citations"]) > 0

        if is_grounded:
            grounded_count += 1
            status = "[PASS] GROUNDED"
        else:
            status = "[FAIL] UNGROUNDED"

        print(f"[{idx:02d}/{total_q}] {status} | Q: {q}")
        if res["citations"]:
            print(f"     Cit: {res['citations'][0]}")

    grounding_rate = (grounded_count / total_q) * 100
    hallucination_rate = (hallucination_count / total_q) * 100

    print("=" * 65)
    print("[METRICS] FINAL RAG EVALUATION METRICS")
    print("=" * 65)
    print(f"Total Questions Evaluated : {total_q}")
    print(f"Successfully Grounded     : {grounded_count} / {total_q}")
    print(f"Grounding Rate            : {grounding_rate:.1f}% (Target: 100%)")
    print(f"Hallucination Rate        : {hallucination_rate:.1f}% (Target: 0%)")
    print("=" * 65)

if __name__ == "__main__":
    run_evaluation()
