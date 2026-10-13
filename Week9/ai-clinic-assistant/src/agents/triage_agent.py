"""
Triage Agent for City Care Clinics.
Evaluates structured patient intake data to classify urgency level (Emergency, Urgent, Routine)
and map symptoms to the appropriate medical specialty.
Enforces a deterministic Rule-First Red-Flag Filter that CANNOT be overridden.
"""

import re
from typing import Dict, Any, List

# Deterministic Red-Flag Symptoms (Triggers 100% Emergency Escalation)
RED_FLAG_KEYWORDS = [
    # Cardiac
    "chest pain", "seene mein dard", "seene mein", "dil mein dard", "dil mein", "chest tightness", "radiating to arm", "crushing pressure", "crushing pain", "pasina aa raha hai",
    # Respiratory
    "difficulty breathing", "saans mein masla", "saans phool", "unable to breathe", "shortness of breath", "gasping", "asphyxia", "saans nahi aa rahi",
    # Neurological / Stroke (FAST)
    "stroke", "face drooping", "chehra sunn", "arm weakness", "slurred speech", "bolne mein masla", "severe headache", "behoshi", "fainting", "seizure", "fit aana", "fit aaya",
    # Bleeding / Trauma
    "heavy bleeding", "uncontrolled bleeding", "khoon nikal raha hai", "coughing blood", "khoon aa raha", "bleeding ruki nahi", "internal bleeding", "accident",
    # Vision Emergency
    "vision loss", "dikhna mukammal band", "blindness",
    # Paediatric Emergency
    "infant fever", "newborn fever", "3 month fever", "3 mahine bacha", "child seizure", "newborn",
    # Allergic / Anaphylaxis
    "throat swelling", "gala phool", "anaphylaxis", "facial swelling hives",
    # Mental Health Emergency
    "suicidal", "self harm", "khudkushi"
]

URGENT_KEYWORDS = [
    "103", "101", "102", "high fever", "tez bukhar", "severe pain", "sakht dard", "sakht", "kharab", " severe ", "acute pain", "vomiting", "ulti", "ultiyan",
    "stitches", "kat laga", "redness", "moach", "sujan", "jalan", "migraine", "160/100", "high bp"
]

SPECIALTY_KEYWORDS = {
    "Cardiology": ["heart", "chest tightness", "bp", "hypertension", "palpitations"],
    "Paediatrics": ["child", "baby", "infant", "beta", "beti", "bacha", "pediatric"],
    "Obstetrics & Gynaecology": ["pregnancy", "period", "menstrual", "pregnant", "haaml", "pelvic", "morning sickness"],
    "Gynaecology": ["period", "menstrual", "gynaecology"],
    "ENT": ["ear", "nose", "throat", "gala", "kaan", "nasal", "sinus", "tonsil"],
    "Dental": ["dant", "teeth", "tooth", "dental", "gum"],
    "Dermatology": ["skin", "rash", "itching", "acne", "spots", "kharish", "jillad"],
    "Ophthalmology": ["ankh", "eye", "vision", "screen"],
    "Nutrition": ["diet", "nutrition", "weight loss", "nutritionist"],
    "General Medicine": ["fever", "cough", "bukhar", "khansi", "body ache", "weakness", "gastric", "stomach", "pait", "checkup", "gardan", "fatigue"]
}

class TriageAgent:
    def evaluate_triage(self, intake_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates intake data and returns triage classification.
        """
        chief = (intake_data.get("chief_complaint") or "").lower()
        assoc = " ".join(intake_data.get("associated_symptoms") or []).lower()
        patient_type = intake_data.get("patient_type", "self")
        all_text = f"{chief} {assoc}"

        # Stage 1: Deterministic Red-Flag Filter (FIRST)
        red_flags_found = []
        if intake_data.get("urgency_level") == "Emergency" or intake_data.get("is_high_severity"):
            red_flags_found.append("Emergency presentation flagged during intake")

        for kw in RED_FLAG_KEYWORDS:
            if kw in all_text:
                red_flags_found.append(kw)

        # Special Paediatric rule: child under 3mo with fever -> Emergency
        if (patient_type == "child" or "bacha" in all_text) and any(w in all_text for w in ["bukhar", "fever", "103"]) and any(w in all_text for w in ["3 month", "3 mahine", "newborn"]):
            red_flags_found.append("Infant under 3 months with fever")

        # Severity Score 8, 9, or 10 -> Immediate Emergency Trigger
        severity_str = str(intake_data.get("severity") or "").strip().lower()
        if not re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\b\d+:\d\d\b', severity_str):
            sev_match = re.search(r'\b(\d+)(?:\s*/\s*10)?\b', severity_str)
            if sev_match:
                try:
                    score = int(sev_match.group(1))
                    if 8 <= score <= 10:
                        red_flags_found.append(f"High Severity Score ({severity_str})")
                except ValueError:
                    pass
            elif any(w in severity_str for w in ["severe", "extreme", "sakht"]):
                red_flags_found.append(f"High Severity ({severity_str})")

        if red_flags_found:
            return {
                "urgency_level": "Emergency",
                "confidence": 1.0,
                "is_red_flag_triggered": True,
                "red_flags": red_flags_found,
                "recommended_specialty": "Cardiology" if any(w in all_text for w in ["chest", "seene", "dil"]) else "General Medicine",
                "escalation_required": True,
                "escalation_message": "[EMERGENCY ALERT] High symptom severity. Please visit the nearest Emergency Room or call 1122 immediately."
            }

        # Stage 2: Urgency Classification (Urgent vs Routine)
        urgency = "Routine"
        confidence = 0.90
        reason = "Standard non-emergency presentation."

        if any(ind in all_text for ind in URGENT_KEYWORDS) or intake_data.get("severity") in ["8/10", "9/10", "10/10"]:
            urgency = "Urgent"
            reason = "Elevated symptom severity or acute onset."

        # Stage 3: Specialty Mapping
        recommended_specialty = "General Medicine"
        if patient_type == "child":
            recommended_specialty = "Paediatrics"
        else:
            for spec, keywords in SPECIALTY_KEYWORDS.items():
                if any(re.search(r'\b' + re.escape(kw) + r'\b', all_text) for kw in keywords):
                    recommended_specialty = spec
                    break

        return {
            "urgency_level": urgency,
            "confidence": confidence,
            "is_red_flag_triggered": False,
            "red_flags": [],
            "reason": reason,
            "recommended_specialty": recommended_specialty,
            "escalation_required": False,
            "escalation_message": None
        }

if __name__ == "__main__":
    agent = TriageAgent()
    sample_intake = {"chief_complaint": "Seene mein dard aur pasina", "associated_symptoms": [], "patient_type": "self"}
    print("Emergency Test:", agent.evaluate_triage(sample_intake))
