"""
Deterministic Prescription Safety Engine for City Care Clinics.
Implements 5-stage rule-based validation for:
1. Allergy & Cross-Reactivity
2. Drug-Drug Interactions
3. Maximum Daily Dosage Limits
4. Duplicate Therapy Detection
5. Special Population Guardrails (Pregnancy, Age limits)
"""

from typing import Dict, Any, List

# Standard Drug Database Rules
DRUG_RULES = {
    "amoxicillin": {"generic": "Amoxicillin", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 3000, "pregnancy_safe": True},
    "augmentin": {"generic": "Amoxicillin + Clavulanic Acid", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 2000, "pregnancy_safe": True},
    "penicillin": {"generic": "Penicillin V", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 2000, "pregnancy_safe": True},
    "panadol": {"generic": "Paracetamol", "class": "Analgesic", "max_daily_dose_mg": 4000, "pregnancy_safe": True},
    "paracetamol": {"generic": "Paracetamol", "class": "Analgesic", "max_daily_dose_mg": 4000, "pregnancy_safe": True},
    "aspirin": {"generic": "Acetylsalicylic Acid", "class": "NSAID", "max_daily_dose_mg": 3000, "pregnancy_safe": False},
    "brufen": {"generic": "Ibuprofen", "class": "NSAID", "max_daily_dose_mg": 2400, "pregnancy_safe": False},
    "ibuprofen": {"generic": "Ibuprofen", "class": "NSAID", "max_daily_dose_mg": 2400, "pregnancy_safe": False},
    "azithromycin": {"generic": "Azithromycin", "class": "Macrolide Antibiotic", "max_daily_dose_mg": 500, "pregnancy_safe": True},
    "flagyl": {"generic": "Metronidazole", "class": "Nitroimidazole", "max_daily_dose_mg": 1500, "pregnancy_safe": False},
}

INTERACTION_MATRIX = [
    ({"aspirin", "brufen"}, "Increased risk of severe gastrointestinal bleeding and ulceration.", "HIGH"),
    ({"aspirin", "ibuprofen"}, "Increased risk of severe gastrointestinal bleeding and ulceration.", "HIGH"),
    ({"warfarin", "aspirin"}, "Severe bleeding risk interaction when Warfarin is combined with Aspirin.", "HIGH"),
]

class PrescriptionSafetyEngine:
    def check_prescription_safety(
        self,
        proposed_medications: List[Dict[str, Any]],
        patient_allergies: List[Dict[str, Any]] = None,
        current_medications: List[Dict[str, Any]] = None,
        patient_age: int = 35,
        is_pregnant: bool = False
    ) -> Dict[str, Any]:
        
        patient_allergies = patient_allergies or []
        current_medications = current_medications or []
        
        flags = []
        overall_status = "CLEARED"

        proposed_generics = []
        proposed_names = []

        for med in proposed_medications:
            drug_name = med.get("drug_name", "").strip()
            drug_key = drug_name.lower()
            dose_mg = med.get("dose_mg", 0)
            freq = med.get("frequency_per_day", 1)
            daily_total = dose_mg * freq

            # Extract base drug name without dosage (e.g. "amoxicillin 500mg" -> "amoxicillin")
            base_key = drug_key
            for token in drug_key.replace("+", " ").split():
                if token in DRUG_RULES:
                    base_key = token
                    break

            rule = DRUG_RULES.get(base_key, DRUG_RULES.get(drug_key, {"generic": drug_name, "class": "Unknown", "max_daily_dose_mg": 99999, "pregnancy_safe": True}))
            generic = rule["generic"].lower()
            drug_class = rule["class"].lower()

            proposed_names.append(base_key)
            proposed_generics.append(generic)

            # Stage 1: Allergy & Cross-Reactivity Check
            for alg in patient_allergies:
                if isinstance(alg, dict):
                    allergen = alg.get("allergen", "").strip().lower()
                    alg_display = alg.get("allergen", "")
                else:
                    allergen = str(alg).strip().lower()
                    alg_display = str(alg)

                is_allergy_match = (
                    allergen == drug_key or
                    allergen == base_key or
                    allergen == generic or
                    base_key in allergen or
                    (generic != "unknown" and generic in allergen) or
                    (drug_class == "nsaid" and any(k in allergen for k in ["nsaid", "aspirin", "brufen", "ibuprofen"]))
                )

                if is_allergy_match:
                    flags.append({
                        "stage": "Allergy",
                        "severity": "CONTRAINDICATED",
                        "drug": drug_name,
                        "message": f"Direct allergy conflict! Patient is allergic to {alg_display}."
                    })
                    overall_status = "CONTRAINDICATED"
                elif "penicillin" in allergen and "penicillin" in drug_class:
                    flags.append({
                        "stage": "Allergy Cross-Reactivity",
                        "severity": "CONTRAINDICATED",
                        "drug": drug_name,
                        "message": f"Cross-reactivity risk! Patient is allergic to Penicillin. {drug_name} is in the Penicillin class."
                    })
                    overall_status = "CONTRAINDICATED"

            # Stage 3: Maximum Daily Dosage Check
            max_allowed = rule["max_daily_dose_mg"]
            if daily_total > max_allowed:
                flags.append({
                    "stage": "Dosage Limit",
                    "severity": "WARNING",
                    "drug": drug_name,
                    "message": f"Maximum daily dose exceeded! Prescribed {daily_total}mg/day exceeds maximum limit of {max_allowed}mg/day."
                })
                if overall_status != "CONTRAINDICATED":
                    overall_status = "WARNING"

            # Stage 5: Pregnancy Safety Check
            if is_pregnant and not rule.get("pregnancy_safe", True):
                flags.append({
                    "stage": "Pregnancy Safety",
                    "severity": "CONTRAINDICATED",
                    "drug": drug_name,
                    "message": f"{drug_name} is contraindicated in pregnancy."
                })
                overall_status = "CONTRAINDICATED"

        # Stage 2: Drug-Drug Interaction Check (Proposed vs Current & Proposed vs Proposed)
        all_drugs_in_play = proposed_names + [m.get("drug_name", "").lower() for m in current_medications]
        for i in range(len(all_drugs_in_play)):
            for j in range(i + 1, len(all_drugs_in_play)):
                d1, d2 = all_drugs_in_play[i], all_drugs_in_play[j]
                for pair, desc, sev in INTERACTION_MATRIX:
                    if {d1, d2} == pair:
                        flags.append({
                            "stage": "Drug Interaction",
                            "severity": sev,
                            "drug": f"{d1.capitalize()} + {d2.capitalize()}",
                            "message": f"Adverse interaction between {d1.capitalize()} and {d2.capitalize()}: {desc}"
                        })
                        if sev == "HIGH":
                            overall_status = "CONTRAINDICATED"
                        elif overall_status == "CLEARED":
                            overall_status = "WARNING"

        # Stage 4: Duplicate Therapy Check
        if len(proposed_generics) != len(set(proposed_generics)):
            flags.append({
                "stage": "Duplicate Therapy",
                "severity": "WARNING",
                "drug": "Multiple medications",
                "message": "Duplicate active ingredient or therapy class detected in proposed prescription."
            })
            if overall_status == "CLEARED":
                overall_status = "WARNING"

        # LLM Clinical Explanation Generator
        clinical_explanation = self._generate_clinical_explanation(overall_status, flags)

        return {
            "overall_status": overall_status,
            "total_flags": len(flags),
            "flags": flags,
            "clinical_explanation": clinical_explanation
        }

    def _generate_clinical_explanation(self, status: str, flags: List[Dict]) -> str:
        if status == "CLEARED":
            return "Prescription Cleared: No allergy conflicts, drug interactions, or dosage violations detected."
        
        explanations = [f"[{f['severity']}] {f['stage']}: {f['message']}" for f in flags]
        return "Prescription Safety Alert:\n" + "\n".join(explanations)

if __name__ == "__main__":
    engine = PrescriptionSafetyEngine()
    test_res = engine.check_prescription_safety(
        proposed_medications=[{"drug_name": "Amoxicillin", "dose_mg": 500, "frequency_per_day": 3}],
        patient_allergies=[{"allergen": "Penicillin"}]
    )
    print("Status:", test_res["overall_status"])
    print("Explanation:\n", test_res["clinical_explanation"])

