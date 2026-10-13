"""
MCP Server: drug-database
Provides standardized tools for drug information lookups, allergy conflict checks, and drug-drug interaction validation.
"""

from typing import Dict, Any, List

DRUG_CATALOG = {
    "penicillin": {"generic": "Penicillin V", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 2000},
    "amoxicillin": {"generic": "Amoxicillin", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 3000},
    "augmentin": {"generic": "Amoxicillin + Clavulanic Acid", "class": "Penicillin Antibiotic", "max_daily_dose_mg": 2000},
    "panadol": {"generic": "Paracetamol", "class": "Analgesic / Antipyretic", "max_daily_dose_mg": 4000},
    "paracetamol": {"generic": "Paracetamol", "class": "Analgesic / Antipyretic", "max_daily_dose_mg": 4000},
    "aspirin": {"generic": "Acetylsalicylic Acid", "class": "NSAID / Antiplatelet", "max_daily_dose_mg": 3000},
    "brufen": {"generic": "Ibuprofen", "class": "NSAID", "max_daily_dose_mg": 2400},
    "ibuprofen": {"generic": "Ibuprofen", "class": "NSAID", "max_daily_dose_mg": 2400},
    "azithromycin": {"generic": "Azithromycin", "class": "Macrolide Antibiotic", "max_daily_dose_mg": 500},
    "flagyl": {"generic": "Metronidazole", "class": "Nitroimidazole Antibacterial", "max_daily_dose_mg": 1500},
    "rizek": {"generic": "Omeprazole", "class": "Proton Pump Inhibitor", "max_daily_dose_mg": 40},
    "risek": {"generic": "Omeprazole", "class": "Proton Pump Inhibitor", "max_daily_dose_mg": 40},
    "omeprazole": {"generic": "Omeprazole", "class": "Proton Pump Inhibitor", "max_daily_dose_mg": 40},
}

KNOWN_INTERACTIONS = [
    ({"aspirin", "ibuprofen"}, "Increased risk of gastrointestinal ulceration and bleeding.", "HIGH"),
    ({"amoxicillin", "penicillin"}, "Duplicate therapy in same antibiotic class.", "MODERATE"),
    ({"aspirin", "heparin"}, "Severe hemorrhage risk due to combined antiplatelet/anticoagulant effect.", "HIGH"),
]

class DrugDatabaseMCPServer:
    def lookup_drug(self, drug_name: str) -> Dict[str, Any]:
        """Tool: Lookup drug generic name, drug class, and max dose limits."""
        key = drug_name.strip().lower()
        if key in DRUG_CATALOG:
            return {"drug_name": drug_name, "found": True, "info": DRUG_CATALOG[key]}
        return {"drug_name": drug_name, "found": False, "info": None}

    def check_allergy_conflict(self, patient_allergies: List[Dict[str, Any]], drug_name: str) -> Dict[str, Any]:
        """Tool: Check if a proposed drug conflicts with patient recorded allergies."""
        drug_key = drug_name.strip().lower()
        drug_info = DRUG_CATALOG.get(drug_key, {"class": drug_name, "generic": drug_name})
        drug_class = drug_info.get("class", "").lower()

        conflicts = []
        for alg in patient_allergies:
            allergen = alg.get("allergen", "").strip().lower()
            
            # Direct match or cross-reactivity match (e.g. Penicillin allergy vs Amoxicillin)
            if allergen == drug_key or allergen in drug_info.get("generic", "").lower():
                conflicts.append(f"Direct allergy match: Patient is allergic to {alg['allergen']}")
            elif "penicillin" in allergen and "penicillin" in drug_class:
                conflicts.append(f"Cross-reactivity warning: Patient allergic to Penicillin. {drug_name} is in Penicillin class.")
            elif ("nsaid" in drug_class or drug_key in ["aspirin", "brufen", "ibuprofen"]) and any(k in allergen for k in ["nsaid", "aspirin", "brufen", "ibuprofen"]):
                conflicts.append(f"Cross-reactivity warning: Patient allergic to NSAIDs/Aspirin. {drug_name} is in NSAID class.")

        return {
            "drug_name": drug_name,
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "severity": "HIGH" if conflicts else "NONE"
        }

    def check_drug_interaction(self, drug_a: str, drug_b: str) -> Dict[str, Any]:
        """Tool: Check if two drugs have a known adverse interaction."""
        set_pair = {drug_a.strip().lower(), drug_b.strip().lower()}
        for pair, desc, severity in KNOWN_INTERACTIONS:
            if set_pair == pair or set_pair.issubset(pair):
                return {
                    "has_interaction": True,
                    "drug_a": drug_a,
                    "drug_b": drug_b,
                    "description": desc,
                    "severity": severity
                }
        return {"has_interaction": False, "drug_a": drug_a, "drug_b": drug_b, "severity": "NONE"}

if __name__ == "__main__":
    server = DrugDatabaseMCPServer()
    print("Allergy Check Amoxicillin vs Penicillin Allergy:", server.check_allergy_conflict([{"allergen": "Penicillin"}], "Amoxicillin"))

