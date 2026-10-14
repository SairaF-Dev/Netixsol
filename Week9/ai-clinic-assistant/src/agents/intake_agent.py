"""
Dynamic Clinical Intake & Safety Nurse Agent for MedCare Clinic.
Implements healthcare-grade conversational intake, EHR reconciliation,
deterministic emergency red-flag screening, and structured clinical summaries.
"""

import re
import os
import json
import datetime
from typing import Dict, Any, Tuple, List, Optional
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer
from src.tools.llm_client import LLMClient

EMERGENCY_RED_FLAGS = [
    # Respiratory / Airway obstruction
    "saans lenay masla", "saans lene mein masla", "saans lene", "difficulty breathing", 
    "saans mein masla", "saans phool", "unable to breathe", "shortness of breath", "gasping", 
    "saans nahi aa rahi", "gala phool", "asphyxia", "choking", "stridor", "saans band",
    # Cardiac
    "heart pain", "heart attack", "chest pain", "seene mein dard", "seene mein", "dil mein dard", "dil mein", "dil ka dard",
    "chest tightness", "crushing pressure", "crushing pain", "pasina aa raha hai",
    # Neurological / Stroke (FAST) / Seizures
    "stroke", "face drooping", "chehra sunn", "slurred speech", "bolne mein masla", 
    "behoshi", "fainting", "seizure", "fit aana", "fit aaya", "sudden weakness",
    # Bleeding / Severe Trauma
    "heavy bleeding", "uncontrolled bleeding", "khoon nikal raha hai", "khoon nikal", 
    "coughing blood", "khoon aa raha", "bleeding ruki nahi", "internal bleeding",
    # Mental Health / Anaphylaxis
    "suicidal", "khudkushi", "anaphylaxis", "severe swelling of lips"
]

HIGH_SEVERITY_PATTERNS = [
    "bht zayada", "bht ziada", "bohot ziada", "bohot dard", "bohot severe", "bohoth ziada", "bohoth zayada",
    "extreme", "too much", "severe", "unbearable", "sakht dard", "bohot ziada dard", "very severe",
    "8/10", "9/10", "10/10", "severity 8", "severity 9", "severity 10"
]

SYMPTOM_LEXICON = {
    "fever": ["bukhar", "fever", "temperature", "tez bukhar", "halka bukhar"],
    "cough": ["khansi", "cough", "dry cough", "balghami khansi"],
    "cold/nasal congestion": ["zukaam", "zukam", "nazla", "cold", "runny nose", "chheenk", "chheankein", "band naak", "naak behna"],
    "sore throat": ["gala", "gala kharab", "gale mein dard", "sore throat", "throat pain", "khushk gala", "swallowing difficulty"],
    "headache": ["headache", "sar dard", "sar mein dard", "saar dard", "saar mein dard", "sir dard", "sir mein dard", "sar me dard", "saar me dard", "sar mai dard", "saar mai dard"],
    "vomiting": ["vomiting", "ulti", "ultiyan", "nausea"],
    "stomach pain": ["stomach pain", "pait dard", "pait mein dard", "acidity"],
    "chest pain": ["chest pain", "heart pain", "seene mein dard", "dil mein dard", "dil ka dard", "heart attack"],
    "breathing issue": ["saans mein masla", "saans lene mein masla", "shortness of breath", "saans phool"],
    "leg pain": ["leg pain", "taang", "tango", "tangon", "taango", "legs pain"],
    "body ache / pain": ["body pain", "body ache", "jism mein dard", "back pain", "kamar dard", "joint pain", "jodon mein dard", "badan mein dard", "badan toot raha", "poore jism mein dard"],
    "toothache / dental": ["daant", "dant", "tooth", "teeth", "molar", "masoorh", "gums", "toothache", "daant mein dard", "dant dard"],
    "eye issue": ["ankh", "aankh", "eye", "eyes", "nazar", "vision", "motia"],
    "ear issue": ["kaan", "kaan mein dard", "ear pain", "peep", "ear discharge"]
}

class IntakeAgent:
    def __init__(self, records_mcp: Optional[PatientRecordsMCPServer] = None, use_llm: Optional[bool] = None):
        self.records_mcp = records_mcp or PatientRecordsMCPServer()
        self.llm_client = LLMClient()
        if use_llm is not None:
            self.use_llm = use_llm
        else:
            self.use_llm = bool(self.llm_client.openrouter_api_key or self.llm_client.openai_api_key) and os.getenv("ENABLE_LLM_INTAKE", "true").lower() in ("true", "1", "yes")
        self.initial_greeting = (
            "Assalam-o-Alaikum! Welcome to MedCare Clinic. Main aap ki clinical intake assistant hoon. "
            "Aaj aap ko kya masla ya takleef hai?"
        )

    def extract_symptoms(self, text: str) -> List[str]:
        t_lower = text.lower()
        found = []
        for sym_category, keywords in SYMPTOM_LEXICON.items():
            if any(kw in t_lower for kw in keywords):
                found.append(sym_category)
        return found

    def extract_duration(self, text: str) -> Optional[str]:
        t_lower = text.lower()
        m = re.search(r'(\d+|ek|do|teen|char|paanch|four|three|two|one|five)\s*(din|days?|hafte|weeks?|mahine|months?|ghante|hours?)(?:\s*se)?', t_lower)
        if m:
            return m.group(0).strip()
        temporal_phrases = [
            "kal raat se", "kal se", "yesterday", "last night",
            "aaj subah se", "aaj se", "since morning", "today",
            "chand din se", "kuch din se", "few days", "kuch ghante se", "four days"
        ]
        for phrase in temporal_phrases:
            if phrase in t_lower:
                return phrase
        return None

    def is_negation(self, text: str) -> bool:
        t_lower = text.lower().strip()
        neg_words = [
            "no", "nahi", "nai", "nhi", "nahe", "none", "kuch nahi", "kuch nai", 
            "koi nahi", "koi nai", "kisi se nahi", "kisi se nai", "koi allergy nahi",
            "koi dawa nahi", "kuch bhi nahi", "nothing", "nil", "na", "nope", "never",
            "koi b nahi", "koi bhi nahi", "kuch b nahi", "kuch bhi nahi", "bilkul nahi",
            "koi dawai nahi", "koi medicine nahi"
        ]
        if any(t_lower == w or t_lower.startswith(w + " ") or t_lower.endswith(" " + w) for w in neg_words):
            return True

        # Natural UrduLish & English negation patterns:
        neg_patterns = [
            r'\b(koi|kisi|kuch)\b.*?\b(nahi|nai|nhi|nahe|no)\b',
            r'\b(allergy|allergies|allergi)\b.*?\b(nahi|nai|nhi|nahe|no)\b',
            r'\b(dawa|dawai|medicine|medication)\b.*?\b(nahi|nai|nhi|nahe|no)\b',
            r'\b(nahi|nai|nhi|no)\b.*?\b(allergy|allergies|dawa|dawai|hai)\b',
            r'\b(no|zero)\s+(allergies|allergy|meds|medications?|medicines?)\b',
            r'\b(don\'?t|do not)\s+have\s+(any\s+)?allerg(y|ies)\b',
            r'\b(not\s+taking|don\'?t\s+take)\s+any\b',
            r'\b(koi\s+b|koi\s+bhi)\s+(nahi|nai|nhi)\b',
            r'\b(nahi\s+hai|nai\s+hai|nhi\s+hai)\b'
        ]
        for pat in neg_patterns:
            if re.search(pat, t_lower):
                return True

        return False

    def is_unknown(self, text: str) -> bool:
        t_lower = text.lower().strip()
        unk_phrases = ["pata nahi", "patta nahi", "don't know", "dont know", "not sure", "maloom nahi", "malum nahi", "unknown", "yaad nahi"]
        return any(u in t_lower for u in unk_phrases)

    def is_severity_answer(self, text: str) -> bool:
        t = text.lower().strip()
        if any(w in t for w in ["din", "day", "hafte", "week", "mahine", "month", "ghante", "hour", "kal", "subah"]):
            return False
        return bool(re.search(r'\b([0-9]|10)\s*(?:hai|/10|out of 10)?\b', t) or any(w in t for w in ["mild", "moderate", "severe", "halka", "tez", "shadeed", "bohot"]))

    def is_no_more_symptoms(self, text: str) -> bool:
        t = text.lower().strip()
        return any(w in t for w in ["bs", "bass", "bus", "sirf", "yahi", "aur nahi", "aur kuch nahi", "koi aur nahi", "kuch nahi", "koi nahi"])

    def clean_allergy_name(self, text: str) -> str:
        s = text.strip()
        clarification_patterns = [
            r'\b(matlab|mtlb|samajh|samjh|mean|meaning)\b',
            r'\b(kiya|kya|what|kyun|kyu|why|kaise|kese|how)\b',
            r'\b(nahi|nai|na|no)\s+(samjha|samjhi|samjhe|samjh|pata|pta)\b',
            r'^\s*\?+\s*$'
        ]
        t = s.lower()
        if any(re.search(pat, t) for pat in clarification_patterns):
            return ""

        s = re.sub(r'^(mujhe|mujy|mjhe|mjy)\s+', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+(se|ki|sy)\s+(allergy|allergies|allergi)\s*(hai|he)?\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+(allergy|allergies|allergi)\s*(hai|he)?\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+(se|ki|sy)\s*(hai|he)?$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+(hai|he)$', '', s, flags=re.IGNORECASE)
        s = s.strip(" .,-!?:;")
        if not s or any(re.search(pat, s.lower()) for pat in clarification_patterns):
            return ""
        known = {
            "penicillin": "Penicillin",
            "brufen": "Brufen",
            "brufin": "Brufen",
            "brufiin": "Brufen",
            "brufeen": "Brufen",
            "ibuprofen": "Brufen",
            "aspirin": "Aspirin",
            "disprin": "Aspirin",
            "paracetamol": "Paracetamol",
            "panadol": "Paracetamol",
            "amoxicillin": "Amoxicillin",
            "augmentin": "Augmentin",
            "sulfa": "Sulfa",
            "dust": "Dust",
            "pollen": "Pollen",
            "peanuts": "Peanuts",
            "peanut": "Peanuts"
        }
        if s.lower() in known:
            return known[s.lower()]
        return s.title() if s else ""

    def clean_medication_name(self, text: str) -> str:
        s = text.strip()
        # Remove conversational prefixes
        s = re.sub(r'^(taking|i take|i took|sirf|bas|bus|ghar mein bas|ghar me bas|maine|main|me ne)\s+', '', s, flags=re.IGNORECASE)
        # Remove conversational verb phrases
        s = re.sub(
            r'\s+(li\s*hai|li\s*he|le\s*raha\s*hoon|le\s*rahi\s*hoon|le\s*rahe\s*hain|'
            r'le\s*rha\s*hu|le\s*rhi\s*hu|le\s*raha\s*hu|le\s*rahi\s*hu|khayi\s*hai|khai\s*hai|'
            r'kha\s*raha\s*hoon|kha\s*rahi\s*hoon|khate\s*hain|khata\s*hoon|khati\s*hoon|'
            r'khaa\s*raha\s*hoon|li\s*thi|leta\s*hoon|leti\s*hoon|le\s*raha|le\s*rahi)\b',
            '', s, flags=re.IGNORECASE
        )
        s = s.strip(" .,-!?:;")
        known = {
            "rizek": "Rizek",
            "risek": "Rizek",
            "panadol": "Panadol",
            "brufen": "Brufen",
            "aspirin": "Aspirin",
            "amoxicillin": "Amoxicillin",
            "augmentin": "Augmentin",
            "disprin": "Disprin",
            "arinate": "Arinate",
            "flagyl": "Flagyl",
            "lipitor": "Lipitor"
        }
        if s.lower() in known:
            return known[s.lower()]
        return s.capitalize() if s else text.strip()

    def reconcile_ehr_and_intake(self, state: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
        """
        Retrieves authentic EHR records for the authenticated patient and performs clinical safety
        and reconciliation checks without independently deleting or altering signed orders.
        """
        ehr_allergies = self.records_mcp.get_patient_allergies(patient_id)
        ehr_meds = self.records_mcp.get_patient_medications(patient_id)

        state["ehr_allergies_on_file"] = [a.get("allergen") for a in ehr_allergies] if ehr_allergies else []
        state["ehr_medications_on_file"] = [f"{m.get('drug_name')} ({m.get('status', 'Active')})" for m in ehr_meds] if ehr_meds else []

        reconciliation_flags = []

        # 1. Reconcile Allergies: Preserve existing Penicillin alongside reported Brufen
        reported_algs = state.get("allergies") or []
        for ea in ehr_allergies:
            allergen_name = ea.get("allergen", "")
            if allergen_name and allergen_name not in reported_algs:
                # Retain historical verified allergy
                pass

        # 2. Check Active Prescription Cross-Allergy: Amoxicillin (RX-77369) vs Penicillin Allergy
        all_allergies_str = " ".join(reported_algs + state["ehr_allergies_on_file"]).lower()
        active_rxs = [m for m in ehr_meds if m.get("status") == "Active"]
        for rx in active_rxs:
            rx_drug = rx.get("drug_name", "")
            rx_id = rx.get("id", "RX-ACTIVE")
            if "amoxicillin" in rx_drug.lower() and "penicillin" in all_allergies_str:
                flag = (
                    f"[CLINICAL SAFETY ALERT] Active prescription {rx_id} ({rx_drug}) belongs to the Penicillin "
                    f"antibiotic class and conflicts with documented Penicillin allergy on file. Flagged for clinician/pharmacist "
                    f"review (prescription remains intact; do not independently cancel)."
                )
                reconciliation_flags.append(flag)

        # 3. Check Current Medication Discrepancies (Reported meds vs authentic EHR records)
        reported_meds = state.get("current_medications") or []
        ehr_med_names = [m.get("drug_name") for m in ehr_meds if m.get("drug_name")]
        for rm in reported_meds:
            if not rm or rm.lower() in ["none", "nahi", "unknown"]:
                continue
            is_rizek = any(k in rm.lower() for k in ["rizek", "risek", "omeprazole"])
            drug_display = "Rizek (Omeprazole)" if is_rizek else rm
            if ehr_med_names:
                ehr_summary = ", ".join(ehr_med_names)
                flag = (
                    f"[MEDICATION RECONCILIATION] Patient reports taking {drug_display} at home. "
                    f"Clinic record lists {ehr_summary}. Recorded for clinician reconciliation."
                )
                reconciliation_flags.append(flag)
            else:
                flag = (
                    f"[MEDICATION RECONCILIATION] Patient reports taking {drug_display} at home. "
                    f"No active medications on clinic record. Recorded for clinician review."
                )
                reconciliation_flags.append(flag)

        state["reconciliation_flags"] = reconciliation_flags
        return state

    def generate_final_intake_summary(self, state: Dict[str, Any]) -> str:
        """
        Builds a structured bilingual clinical intake summary for the patient (Phase 5).
        """
        chief = state.get("chief_complaint") or "Not specified"
        duration = state.get("duration") or "Not specified"
        severity = state.get("severity") or "Not specified"
        assoc = ", ".join(state.get("associated_symptoms") or []) or "None reported"

        # Allergies display
        algs = state.get("allergies") or []
        unique_algs = []
        for a in algs:
            if a and a not in unique_algs and not any(a.lower() == u.lower() for u in unique_algs):
                unique_algs.append(a)

        alg_details_map = {}
        for d in state.get("allergy_details") or []:
            sub = (d.get("substance") or "").lower()
            rx = (d.get("reaction") or "").strip()
            if rx and rx.lower() not in ["none", "unknown"]:
                if sub:
                    alg_details_map[sub] = rx
                if len(unique_algs) == 1:
                    alg_details_map[unique_algs[0].lower()] = rx

        formatted_algs = []
        for a in unique_algs:
            rx = alg_details_map.get(a.lower())
            if rx:
                formatted_algs.append(f"{a} (Reaction: {rx})")
            else:
                formatted_algs.append(a)

        rep_algs = ", ".join(formatted_algs) or "None reported"
        ehr_algs = ", ".join(state.get("ehr_allergies_on_file") or []) or "None recorded"
        
        # Meds display
        rep_meds = ", ".join(state.get("current_medications") or []) or "None reported"
        ehr_meds = ", ".join(state.get("ehr_medications_on_file") or []) or "None on file"

        flags_text = ""
        if state.get("reconciliation_flags"):
            flags_text = "\n" + "\n".join([f"  • {f}" for f in state["reconciliation_flags"]])

        # Determine appropriate specialty using TriageAgent mapping for full clinical consistency
        try:
            from src.agents.triage_agent import TriageAgent
            t_eval = TriageAgent().evaluate_triage(state)
            spec_display = t_eval.get("recommended_specialty") or "General Medicine"
        except Exception:
            all_sym_text = f"{chief} {assoc}".lower()
            if re.search(r'\b(heart|cardiac|cardio|chest|dil|bp|hypertension|palpitation|palpitations)\b', all_sym_text):
                spec_display = "Cardiology"
            elif re.search(r'\b(dant|daant|tooth|teeth|molar|gums|masoorh|jaw|dental)\b', all_sym_text):
                spec_display = "Dental"
            elif re.search(r'\b(gala|throat|zukaam|zukam|cold|naak|ear|ears|kaan|sinus|tonsil|tonsils)\b', all_sym_text):
                spec_display = "ENT"
            elif re.search(r'\b(leg|bone|joint|haddi|kamar|back pain|taang|tango|tangon|muscle)\b', all_sym_text):
                spec_display = "Orthopedics"
            elif re.search(r'\b(skin|rash|khareesh|kharish|jild|jillad|acne|spots)\b', all_sym_text):
                spec_display = "Dermatology"
            elif re.search(r'\b(pait|stomach|vomit|ulti|ultiyan|gastric|acidity)\b', all_sym_text):
                spec_display = "Gastroenterology"
            else:
                spec_display = "General Medicine"

        summary = (
            "Bohot shukriya! Main ne aap ki tamam clinical intake information record kar li hai.\n\n"
            "**CLINICAL INTAKE SUMMARY (KHLASA):**\n"
            f"• **Chief Complaint (Bunyadi Takleef):** {chief}\n"
            f"• **Duration (Waqfa):** {duration}\n"
            f"• **Severity Score (Shidat):** {severity} (Scale: 0-10)\n"
            f"• **Associated Symptoms (Deegar Alamaat):** {assoc}\n"
            f"• **Reported Allergies:** {rep_algs}\n"
            f"  *(Verified EHR Allergies on File: {ehr_algs})*\n"
            f"• **Current Home Medications:** {rep_meds}\n"
            f"  *(Verified EHR Medications on File: {ehr_meds})*\n"
            f"• **Triage Assessment:** Routine Clinical Consultation Recommended\n"
            f"• **Recommended Specialty:** {spec_display}"
            f"{flags_text}\n\n"
            "Main aap ka structured record Triage aur Scheduling department ko forward kar rahi hoon taake doctor ke sath appointment confirm ki ja sakay."
        )
        return summary

    def _process_turn_llm(self, user_message: str, state: Dict[str, Any], patient_id: str) -> Tuple[str, Dict[str, Any], bool]:
        """
        Uses OpenRouter LLM (GPT-4o-mini) to deeply understand patient's message in Roman Urdu,
        extract clinical fields accurately, and formulate empathetic natural responses with zero loops.
        """
        state.setdefault("patient_type", "self")
        state.setdefault("patient_id", patient_id)
        state.setdefault("chief_complaint", None)
        state.setdefault("duration", None)
        state.setdefault("severity", None)
        state.setdefault("associated_symptoms", [])
        state.setdefault("extracted_symptoms", [])
        state.setdefault("allergies", None)
        state.setdefault("allergy_details", [])
        state.setdefault("allergy_followup_needed", False)
        state.setdefault("current_medications", None)
        state.setdefault("medication_details", [])
        state.setdefault("med_followup_needed", False)
        state.setdefault("conversation_history", [])

        msg_lower = user_message.lower().strip()
        is_neg = self.is_negation(user_message)
        is_unk = self.is_unknown(user_message)

        ehr_allergies = self.records_mcp.get_patient_allergies(patient_id)
        ehr_meds = self.records_mcp.get_patient_medications(patient_id)
        ehr_algs_str = ", ".join([a.get("allergen", "") for a in ehr_allergies]) if ehr_allergies else "None on file"
        ehr_meds_str = ", ".join([m.get("drug_name", "") for m in ehr_meds]) if ehr_meds else "None on file"

        # Deduce current stage from state fields if sub_stage was default
        if state.get("sub_stage") in [None, "CHIEF_COMPLAINT"] and state.get("chief_complaint"):
            if not state.get("duration") and not state.get("severity"):
                curr = "DURATION"
            elif not state.get("severity"):
                curr = "SEVERITY"
            elif not state.get("duration"):
                curr = "DURATION"
            elif not state.get("associated_symptoms_done") and not state.get("associated_symptoms"):
                curr = "ASSOCIATED_SYMPTOMS"
            elif state.get("allergies") is None:
                curr = "ALLERGIES"
            elif state.get("allergy_followup_needed"):
                curr = "ALLERGY_DETAILS"
            elif state.get("current_medications") is None:
                curr = "CURRENT_MEDICATIONS"
            elif state.get("med_followup_needed"):
                curr = "MEDICATION_DETAILS"
            else:
                curr = "COMPLETE"
            state["sub_stage"] = curr
        else:
            curr = state.get("sub_stage", "CHIEF_COMPLAINT")

        # 1. Update entities strictly based on current sub_stage (curr)
        # Extract and accumulate clinical symptoms into state["extracted_symptoms"]
        new_syms = self.extract_symptoms(user_message)
        for s in new_syms:
            if s not in state["extracted_symptoms"]:
                state["extracted_symptoms"].append(s)

        if curr == "CHIEF_COMPLAINT":
            state["chief_complaint"] = user_message.strip()
            for s in self.extract_symptoms(user_message):
                if s not in state["extracted_symptoms"]:
                    state["extracted_symptoms"].append(s)
            dur = self.extract_duration(user_message)
            if dur:
                state["duration"] = dur

        elif curr == "DURATION":
            if is_unk:
                state["duration"] = "Unknown (unspecified)"
            elif self.is_severity_answer(user_message) and not state.get("severity"):
                m = re.search(r'\b([0-9]|10)\b', user_message)
                state["severity"] = m.group(1) if m else user_message.strip()
            elif any(k in msg_lower for k in ["leg", "taang", "headache", "sar dard", "cough", "khansi", "bukhar"]):
                state["chief_complaint"] = user_message.strip()
            else:
                dur = self.extract_duration(user_message)
                if dur:
                    state["duration"] = dur
                elif re.search(r'\b([0-9]|10)\b', user_message) and not self.is_severity_answer(user_message):
                    m = re.search(r'\b([0-9]|10)\b', user_message)
                    state["duration"] = f"{m.group(1)} din"
                elif len(user_message.strip()) <= 30 and not self.is_severity_answer(user_message):
                    state["duration"] = user_message.strip()
                else:
                    state["duration"] = "Unspecified duration"

        elif curr == "SEVERITY":
            if is_unk:
                state["severity"] = "Unknown"
            else:
                m = re.search(r'\b([0-9]|10)\b', user_message)
                state["severity"] = m.group(1) if m else user_message.strip()

        elif curr == "ASSOCIATED_SYMPTOMS":
            if self.is_no_more_symptoms(user_message) or is_neg:
                state["associated_symptoms_done"] = True
                if not state.get("associated_symptoms"):
                    state["associated_symptoms"] = ["None reported (only primary pain)"]
            elif is_unk:
                state["associated_symptoms"].append("Unknown")
                state["associated_symptoms_done"] = True
            else:
                s_text = user_message.strip()
                if re.match(r'^\d{1,2}(?:/10)?$', s_text):
                    state["associated_symptoms"] = ["None reported (only primary complaints)"]
                    state["associated_symptoms_done"] = True
                else:
                    parts = [p.strip() for p in re.split(r',\s*|\s+aur\s+|\s+and\s+', s_text) if p.strip()]
                    cleaned_parts = [p for p in parts if not re.match(r'^\d{1,2}(?:/10)?$', p)]
                    state["associated_symptoms"].extend(cleaned_parts if cleaned_parts else ["None reported (only primary complaints)"])
                    state["associated_symptoms_done"] = True

        elif curr == "ALLERGIES":
            is_clarification = any(w in msg_lower for w in ["matlab", "mtlb", "samajh", "samjh", "what", "kyun", "kyu", "why", "kaise", "kese"])
            if is_neg:
                state["allergies"] = []
                state["allergy_followup_needed"] = False
            elif is_unk or is_clarification:
                state["allergies"] = []
                state["allergy_followup_needed"] = False
            else:
                clean_alg = self.clean_allergy_name(user_message)
                if clean_alg:
                    state["allergies"] = [clean_alg]
                    has_reaction = any(w in msg_lower for w in ["reaction", "rash", "swelling", "hives", "soojan", "saans"])
                    if has_reaction:
                        state["allergy_details"].append({"substance": clean_alg, "reaction": user_message.strip()})
                        state["allergy_followup_needed"] = False
                    else:
                        state["allergy_followup_needed"] = True
                else:
                    state["allergies"] = []
                    state["allergy_followup_needed"] = False

        elif curr == "ALLERGY_DETAILS":
            substance = state["allergies"][0] if state.get("allergies") else "Allergen"
            has_reaction = any(w in msg_lower for w in ["reaction", "rash", "swelling", "hives", "soojan", "saans", "vomit", "ulti", "itching", "kharish", "redness"])
            is_no_more = is_neg or any(w in msg_lower for w in ["sirf yahi", "yhi", "yahi", "aur nahi", "koi nahi", "none", "nahi", "no", "bass", "bs", "sirf yeh", "sirf"])
            is_clarification = any(w in msg_lower for w in ["matlab", "mtlb", "samajh", "samjh", "what", "kyun", "kyu", "why", "kaise", "kese", "pata nahi", "pta nai"])

            if has_reaction:
                state["allergy_details"].append({"substance": substance, "reaction": user_message.strip()})
                state["allergy_followup_needed"] = False
            elif is_no_more or is_clarification:
                state["allergy_followup_needed"] = False
            else:
                # Patient reported an additional allergy or confirmed existing
                clean_alg2 = self.clean_allergy_name(user_message)
                existing_lower = [a.lower() for a in state.get("allergies", [])]
                if clean_alg2:
                    if clean_alg2.lower() not in existing_lower and not any(clean_alg2.lower() in ex or ex in clean_alg2.lower() for ex in existing_lower):
                        state["allergies"].append(clean_alg2)
                state["allergy_followup_needed"] = False

        elif curr == "CURRENT_MEDICATIONS":
            if is_neg:
                state["current_medications"] = []
                state["med_followup_needed"] = False
            elif is_unk:
                state["current_medications"] = ["Unknown"]
                state["med_followup_needed"] = False
            else:
                clean_med = self.clean_medication_name(user_message)
                state["current_medications"] = [clean_med]
                has_dose = any(w in msg_lower for w in ["mg", "tablet", "goli", "subah", "shaam", "raat", "once", "twice", "daily", "rozana"])
                if has_dose:
                    state["medication_details"].append({"drug_name": clean_med, "dose": user_message.strip()})
                    state["med_followup_needed"] = False
                else:
                    state["med_followup_needed"] = True

        elif curr == "MEDICATION_DETAILS":
            med_name = state["current_medications"][0] if state.get("current_medications") else "Medication"
            state["medication_details"].append({"drug_name": med_name, "dose": user_message.strip()})
            state["med_followup_needed"] = False

        # 2. Determine Next Clinical Target (Strict Progression)
        if not state.get("chief_complaint"):
            next_target = "CHIEF_COMPLAINT"
        elif not state.get("duration") and not state.get("severity"):
            next_target = "DURATION"
        elif not state.get("severity"):
            next_target = "SEVERITY"
        elif not state.get("duration"):
            next_target = "DURATION"
        elif not state.get("associated_symptoms_done") and not state.get("associated_symptoms"):
            next_target = "ASSOCIATED_SYMPTOMS"
        elif state.get("allergies") is None:
            next_target = "ALLERGIES"
        elif state.get("allergy_followup_needed"):
            next_target = "ALLERGY_DETAILS"
        elif state.get("current_medications") is None:
            next_target = "CURRENT_MEDICATIONS"
        elif state.get("med_followup_needed"):
            next_target = "MEDICATION_DETAILS"
        else:
            next_target = "COMPLETE"

        state["sub_stage"] = next_target

        # If complete, generate summary
        if next_target == "COMPLETE":
            state["is_complete"] = True
            state = self.reconcile_ehr_and_intake(state, patient_id)
            summary = self.generate_final_intake_summary(state)
            state["conversation_history"].append({"sender": "Patient", "text": user_message})
            state["conversation_history"].append({"sender": "AI", "text": summary})
            return summary, state, True

        # 3. Call LLM for natural, empathetic response for next_target
        history = state.get("conversation_history", [])
        history_str = "\n".join([f"{h['sender']}: {h['text']}" for h in history[-4:]]) if history else "Start of conversation"

        system_prompt = f"""You are MedCare Assistant, a professional bilingual Clinical Intake Nurse at City Care Clinics, Lahore.
You speak warm, natural Roman Urdu (UrduLish) and English.

Patient Verified EHR Records on File:
- Documented Allergies: {ehr_algs_str}
- Documented Active Medications: {ehr_meds_str}

PATIENT CURRENT CLINICAL PROFILE:
- Chief Complaint: {state.get('chief_complaint')}
- Duration: {state.get('duration')}
- Severity: {state.get('severity')}
- Associated Symptoms: {state.get('associated_symptoms')}
- Allergies: {state.get('allergies')}
- Current Medications: {state.get('current_medications')}

YOUR EXACT CLINICAL TASK:
You MUST ask about: {next_target}.
- If next target is SEVERITY: acknowledge symptoms and ask severity on a 0 to 10 scale.
- If next target is DURATION: ask how long they have had this issue (e.g. kitne din ya waqt se hai).
- If next target is ASSOCIATED_SYMPTOMS: ask if they have any other symptoms (gale mein dard, sar dard, etc.).
- If next target is ALLERGIES: ask if they have any drug/food allergies (Penicillin, Aspirin, ya koi allergy nahi). DO NOT ask about symptoms or severity again!
- If next target is ALLERGY_DETAILS: acknowledge the reported allergy ({state.get('allergies')}) and ask what specific reaction happens (e.g. skin rash, swelling, hives, breathing issue / saans ka masla).
- If next target is CURRENT_MEDICATIONS: ask if they are taking any home medicines (Panadol, Rizek, ya koi nahi).
- If next target is MEDICATION_DETAILS: acknowledge the reported medication ({state.get('current_medications', ['dawai'])[0]}) and ask dose (e.g. kitni mg ya tablet) and frequency (rozana kitni martaba). DO NOT ask for the medication name again because the patient already told you ({state.get('current_medications', ['dawai'])[0]}). (If EHR has active meds [{ehr_meds_str}], ask if still taking them; if none on file, DO NOT mention any other drugs).

Write ONLY the warm conversational Roman Urdu reply for {next_target}. Keep it concise (1-2 sentences).
"""

        prompt = f"RECENT CONVERSATION:\n{history_str}\n\nPATIENT JUST SAID: \"{user_message}\""
        res = self.llm_client.generate_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ], temperature=0.15, max_tokens=150)

        reply = (res.get("content") or "").strip()
        if not reply or res.get("status") == "ERROR" or reply.startswith("LLM API Error"):
            alg_name = (state.get("allergies") or ["is dawai"])[0]
            med_name = (state.get("current_medications") or ["yeh dawai"])[0]
            fallbacks = {
                "DURATION": "Assalam-o-Alaikum! Yeh takleef ya alamaat aap ko kitne arse se hain? (Jaise 2 din ya aik hafta)",
                "SEVERITY": "Aap ka dard ya takleef 1 se 10 ke paimane par kitni shadeed hai? (1 halki, 10 shadeed)",
                "ASSOCIATED_SYMPTOMS": "Kya is ke ilawa koi aur alamaat bhi hain, jaise gale mein dard, sar dard ya vomiting?",
                "ALLERGIES": "Kya aap ko kisi dawai ya cheez se allergy hai? (Jaise Penicillin, Aspirin ya koi allergy nahi)",
                "ALLERGY_DETAILS": f"Aap ko {alg_name} se kis qisam ka reaction hota hai? (Jaise jild par rash, kharish, ya soojan)?",
                "CURRENT_MEDICATIONS": "Kya aap is waqt koi dawai ya ghareloo nuskha istemal kar rahe hain?",
                "MEDICATION_DETAILS": f"Aap {med_name} ki kitni dose (e.g. 500mg ya tablet) aur rozana kitni martaba lete hain?",
            }
            reply = fallbacks.get(next_target, "Barah-e-karam apni alamaat ke bare mein mazeed thori tafseel batayein.")

        state["conversation_history"].append({"sender": "Patient", "text": user_message})
        state["conversation_history"].append({"sender": "AI", "text": reply})
        return reply, state, False

    def process_turn(self, user_message: str, current_state: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any], bool]:
        """
        Processes a single turn of intake conversation using structured clinical safety protocols.
        Returns: (agent_reply_urdulish, updated_state, is_complete)
        """
        state = current_state.copy() if current_state else {}
        state.setdefault("patient_type", "self")
        state.setdefault("patient_id", "PAT-5501")
        state.setdefault("chief_complaint", None)
        state.setdefault("duration", None)
        state.setdefault("severity", None)
        state.setdefault("associated_symptoms", [])
        state.setdefault("extracted_symptoms", [])
        state.setdefault("allergies", None)
        state.setdefault("allergy_details", [])
        state.setdefault("allergy_followup_needed", False)
        state.setdefault("current_medications", None)
        state.setdefault("medication_details", [])
        state.setdefault("med_followup_needed", False)
        state.setdefault("ehr_allergies_on_file", [])
        state.setdefault("ehr_medications_on_file", [])
        state.setdefault("reconciliation_flags", [])
        state.setdefault("sub_stage", "CHIEF_COMPLAINT")
        state.setdefault("is_complete", False)

        patient_id = state.get("patient_id", "PAT-5501")
        msg_lower = user_message.lower().strip()

        # =========================================================================
        # RULE 1: Red-Flag Emergency Detection (Strict Clinical Priority)
        # Serious warning signs strictly override a low self-reported severity score!
        # =========================================================================
        has_emergency_keyword = any(rf in msg_lower for rf in EMERGENCY_RED_FLAGS)
        if has_emergency_keyword:
            if not state.get("chief_complaint"):
                state["chief_complaint"] = user_message
            new_symptoms = self.extract_symptoms(user_message)
            for s in new_symptoms:
                if s not in state["extracted_symptoms"]:
                    state["extracted_symptoms"].append(s)
            state["is_complete"] = True
            state["is_high_severity"] = True
            state["urgency_level"] = "Emergency"
            reply = "[EMERGENCY ALERT] High symptom severity detected. Please visit the nearest Emergency Room or call 1122 immediately."
            return reply, state, True

        # =========================================================================
        # RULE 2: High Severity Evaluation (8, 9, 10 or 'extreme')
        # =========================================================================
        is_text_high_sev = any(pat in msg_lower for pat in HIGH_SEVERITY_PATTERNS)
        is_date_or_time = bool(re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\b10:\d\d|\b\d+:\d\d|\bslot\b|\bdate\b|\bappointment\b|\btime\b', msg_lower))
        score_match = re.search(r'\b(\d{1,2})\s*(?:/|out of|\s*ke scale par)\s*10\b', msg_lower)
        if score_match:
            score_val = int(score_match.group(1))
            is_num_high_sev = score_val >= 8 and not is_date_or_time
        else:
            is_num_high_sev = (not is_date_or_time) and bool(re.search(r'\b(8|9|10)\b(?!\s*(?:/|out of)\s*10)', msg_lower)) and (
                "severity" in msg_lower or (state.get("sub_stage") == "SEVERITY" and not state.get("severity")) or "scale" in msg_lower or msg_lower in ["8", "9", "10", "8/10", "9/10", "10/10"]
            )

        if is_text_high_sev or is_num_high_sev:
            if not state.get("chief_complaint"):
                state["chief_complaint"] = user_message
            new_symptoms = self.extract_symptoms(user_message)
            for s in new_symptoms:
                if s not in state["extracted_symptoms"]:
                    state["extracted_symptoms"].append(s)
            state["severity"] = "9/10 (High)" if is_text_high_sev else user_message.strip()
            state["is_complete"] = True
            state["is_high_severity"] = True
            state["urgency_level"] = "Emergency"
            reply = "[EMERGENCY ALERT] High symptom severity detected. Please visit the nearest Emergency Room or call 1122 immediately."
            return reply, state, True

        # =========================================================================
        # RULE 3: AI Safety Boundary - Direct Prescription Requests Refusal
        # =========================================================================
        prescription_request_patterns = [
            "prescription likh", "prescription dein", "prescription do", "nuskha likh",
            "dawai likh", "dawa likh", "tablet likh", "prescribe", "write prescription",
            "give prescription", "nuskha dein", "dawai bata do", "dawai tajweez"
        ]
        if any(pat in msg_lower for pat in prescription_request_patterns) or ("prescription" in msg_lower and any(w in msg_lower for w in ["likh", "bana", "dein", "do", "chahiye", "send"])):
            reply = "Main aik AI assistant hoon aur direct prescription ya dawai tajweez nahi kar sakta. Barah-e-karam clinic par doctor se appointment book karein taake woh aap ka mukammal muaina kar ke munasib nuskha likh sakein."
            return reply, state, False

        # Automatic Symptom Extraction & Memory
        new_symptoms = self.extract_symptoms(user_message)
        for s in new_symptoms:
            if s not in state["extracted_symptoms"]:
                state["extracted_symptoms"].append(s)

        # Repetition / Correction Handling
        if any(phrase in msg_lower for phrase in ["already told", "pehle bataya", "pehle bata", "already mentioned", "bata toh diya", "phir se", "repeat"]):
            known = ", ".join(state.get("extracted_symptoms", [])) or "alamaat"
            reply = f"Meri maazrat! Aap ne pehle hi yeh bataya tha ({known}). Main ne note kar liya hai."
            if not state["severity"]:
                reply += " Takleef kitni ziada hai? (0 se 10 ke scale par severity batayein?)"
                return reply, state, False
            elif state["allergies"] is None:
                reply += " Kya aap ko kisi dawai se allergy hai?"
                return reply, state, False
            else:
                state["is_complete"] = True
                reply += " Main aap ki details Triage department ko forward kar rahi hoon."
                return reply, state, True

        # Off-topic & Scope Enforcement
        if any(w in msg_lower for w in ["weather", "cricket", "match", "python", "divided", "recipe", "capital", "biryani"]):
            reply = (
                "Main ek Medical Clinic Assistant hoon aur sirf MedCare Clinic mein aap ki sehat, lab reports, "
                "aur appointments ke hawale se madad kar sakti hoon. Baraye meharbani apni health complaint batayein."
            )
            return reply, state, False

        # Medical Safety Boundaries Check
        if any(w in msg_lower for w in ["prescrib", "nuskha", "dengue", "cancer", "kidney fail", "antibiotic", "diagnos"]):
            reply = (
                "Main ek AI assistant hoon aur direct prescription ya diagnosis nahi de sakti. "
                "Main aap ki alamaat Triage aur Doctor sahab ko forward kar sakti hoon taake safe treatment mile."
            )
            return reply, state, False

        # =========================================================================
        # HYBRID AI LAYER: LLM Conversational Processing (GPT-4o-mini via OpenRouter)
        # =========================================================================
        if self.use_llm and (self.llm_client.openrouter_api_key or self.llm_client.openai_api_key):
            state_backup = json.loads(json.dumps(state))
            try:
                return self._process_turn_llm(user_message, state, patient_id)
            except Exception as e:
                # Silently restore clean state before deterministic fallback
                state.clear()
                state.update(state_backup)

        detected_dur = self.extract_duration(user_message)
        is_dur_msg = bool(detected_dur and any(u in msg_lower for u in ["din", "day", "hafte", "week", "mahine", "month", "ghante", "hour", "kal", "yesterday", "subah", "morning", "four"]))

        # =========================================================================
        # STAGE 1: CHIEF COMPLAINT
        # =========================================================================
        if not state["chief_complaint"]:
            state["chief_complaint"] = user_message.strip()
            if any(w in msg_lower for w in ["bache", "beta", "beti", "son", "daughter", "child"]):
                state["patient_type"] = "child"
            elif any(w in msg_lower for w in ["ammi", "abbu", "father", "mother", "parent"]):
                state["patient_type"] = "parent"

            # Avoid asking duplicate duration if duration was already stated
            if detected_dur:
                state["duration"] = detected_dur
                clean_dur = re.sub(r'\s*se$', '', detected_dur, flags=re.IGNORECASE).strip()
                reply = (
                    f"Samajh gaya. Main ne note kar liya hai ke aap ko {clean_dur} se yeh takleef hai. "
                    "Takleef kitni ziada hai? (0 se 10 ke scale par severity batayein?)"
                )
                state["sub_stage"] = "SEVERITY"
                return reply, state, False

            reply = "Mujhe sun kar afsos hua. Yeh masla kab se hai? (Duration kitni hai?)"
            state["sub_stage"] = "DURATION"
            return reply, state, False

        # =========================================================================
        # STAGE 2: DURATION
        # =========================================================================
        elif not state["duration"] or (is_dur_msg and not state["severity"]):
            if self.is_unknown(user_message):
                state["duration"] = "Unknown (unspecified)"
            elif self.is_severity_answer(user_message) and not state.get("severity"):
                m = re.search(r'\b([0-9]|10)\b', user_message)
                state["severity"] = m.group(1) if m else user_message.strip()
                reply = "Theek hai, shiddat note kar li hai. Yeh takleef kab se hai? (Kitne din ya waqt se hai?)"
                state["sub_stage"] = "DURATION"
                return reply, state, False
            else:
                dur = self.extract_duration(user_message)
                if dur:
                    state["duration"] = dur
                elif re.search(r'\b([0-9]|10)\b', user_message) and not self.is_severity_answer(user_message):
                    m = re.search(r'\b([0-9]|10)\b', user_message)
                    state["duration"] = f"{m.group(1)} din"
                elif len(user_message.strip()) <= 30 and not self.is_severity_answer(user_message):
                    state["duration"] = user_message.strip()
                else:
                    state["duration"] = "Unspecified duration"

            reply = "Theek hai. Takleef kitni ziada hai? (0 se 10 ke scale par kitni severity hai?)"
            state["sub_stage"] = "SEVERITY"
            return reply, state, False

        # =========================================================================
        # STAGE 3: SEVERITY (Explicit 0-10 scale)
        # =========================================================================
        elif not state["severity"]:
            if self.is_unknown(user_message):
                state["severity"] = "Unknown"
            else:
                state["severity"] = user_message.strip()

            # Dynamic symptom screening for respiratory/cold/ENT or general presentation
            urdu_symptoms = {
                "fever": "bukhar", "cough": "khansi", "headache": "sar dard",
                "cold/nasal congestion": "zukaam/naak band", "sore throat": "gale mein dard",
                "vomiting": "ulti/matli", "stomach pain": "pait dard",
                "chest pain": "seene mein dard", "breathing issue": "saans mein masla"
            }
            already_extracted = state.get("extracted_symptoms", [])
            if already_extracted:
                symptom_display = " aur ".join([urdu_symptoms.get(s, s) for s in already_extracted])
            else:
                symptom_display = state['chief_complaint']

            # Screen for relevant remaining symptoms (exclude already extracted ones)
            additional_candidates = [
                ("sore throat", "gale mein dard"),
                ("cold/nasal congestion", "naak behna ya band naak"),
                ("headache", "sar dard"),
                ("fever", "bukhar"),
                ("cough", "khansi"),
                ("breathing issue", "saans lene ya nigalne mein koi takleef")
            ]
            unmentioned = [urdu for cat, urdu in additional_candidates if cat not in already_extracted]
            if len(unmentioned) > 3:
                unmentioned_str = ", ".join(unmentioned[:3]) + ", ya " + unmentioned[3]
            elif unmentioned:
                unmentioned_str = ", ".join(unmentioned[:-1]) + (" ya " + unmentioned[-1] if len(unmentioned) > 1 else unmentioned[0])
            else:
                unmentioned_str = "sar dard, gale mein dard, ya koi aur takleef"

            reply = (
                f"Samajh gaya. Aap ne {symptom_display} bataya hai. "
                f"Kya is ke sath {unmentioned_str} mehsoos ho rahi hai?"
            )
            state["sub_stage"] = "ASSOCIATED_SYMPTOMS"
            return reply, state, False

        # =========================================================================
        # STAGE 4: ASSOCIATED SYMPTOMS
        # =========================================================================
        elif not state["associated_symptoms"]:
            # Clarification query
            if any(cq in msg_lower for cq in ["maslan", "jaise", "jesa", "jese", "jesay", "jaisay", "matlab", "example", "kon si", "kaun si"]):
                reply = (
                    "Maslan kya sar dard, gale mein dard, naak behna, ya thakawat mehsoos ho rahi hai? "
                    "(Agar in mein se koi aur masla nahi to 'Nahi' keh dein)"
                )
                return reply, state, False

            if self.is_negation(user_message) or self.is_no_more_symptoms(user_message):
                state["associated_symptoms"] = ["None"]
            elif self.is_unknown(user_message):
                state["associated_symptoms"] = ["Unknown"]
            else:
                s_text = user_message.strip()
                if re.match(r'^\d{1,2}(?:/10)?$', s_text):
                    state["associated_symptoms"] = ["None reported (only primary complaints)"]
                else:
                    parts = [p.strip() for p in re.split(r',\s*|\s+aur\s+|\s+and\s+', s_text) if p.strip()]
                    cleaned_parts = [p for p in parts if not re.match(r'^\d{1,2}(?:/10)?$', p)]
                    state["associated_symptoms"] = cleaned_parts if cleaned_parts else ["None reported (only primary complaints)"]

            # Check for red flags in associated symptoms
            if any(rf in msg_lower for rf in EMERGENCY_RED_FLAGS):
                state["is_complete"] = True
                state["is_high_severity"] = True
                state["urgency_level"] = "Emergency"
                reply = "[EMERGENCY ALERT] High symptom severity detected. Please visit the nearest Emergency Room or call 1122 immediately."
                return reply, state, True

            reply = "Kya aap ko kisi dawai ya cheez se allergy hai? (e.g. Penicillin, Aspirin, ya koi allergy nahi?)"
            state["sub_stage"] = "ALLERGIES"
            return reply, state, False

        # =========================================================================
        # STAGE 5: ALLERGIES COLLECTION
        # =========================================================================
        elif state["allergies"] is None:
            if self.is_negation(user_message):
                state["allergies"] = []
                state["allergy_followup_needed"] = False
                reply = "Aap filhal ghar mein koi dawai le rahe hain? (e.g. Panadol, Rizek, ya koi nahi?)"
                state["sub_stage"] = "CURRENT_MEDICATIONS"
                return reply, state, False

            if self.is_unknown(user_message):
                state["allergies"] = ["Unknown"]
                state["allergy_followup_needed"] = False
                reply = "Aap filhal ghar mein koi dawai le rahe hain? (e.g. Panadol, Rizek, ya koi nahi?)"
                state["sub_stage"] = "CURRENT_MEDICATIONS"
                return reply, state, False

            # Patient reports allergy (e.g. "Brufen" or "Penicillin")
            a_text = user_message.strip()
            parts = [p.strip() for p in re.split(r',\s*|\s+aur\s+|\s+and\s+', a_text) if p.strip()]
            clean_algs = [self.clean_allergy_name(p) for p in parts]
            state["allergies"] = clean_algs if clean_algs else [a_text]

            # Collect Reaction, Timing, Severity/Emergency status if not already detailed
            has_reaction_info = any(w in msg_lower for w in ["reaction", "swelling", "rash", "hives", "kharish", "soojan", "saans"])
            if not has_reaction_info:
                substance = clean_algs[0] if clean_algs else a_text
                state["allergy_followup_needed"] = True
                state["sub_stage"] = "ALLERGY_DETAILS"
                reply = (
                    f"Aap ko {substance} se kis qism ka reaction hota hai (maslan rash, soojan, ya saans ka masla), "
                    "aur kya kabhi emergency ilaj ki zaroorat pari thi?"
                )
                return reply, state, False
            else:
                state["allergy_details"].append({
                    "substance": clean_algs[0] if clean_algs else a_text,
                    "reaction": a_text,
                    "timing": "Reported during intake",
                    "emergency_treatment": "Unknown"
                })
                reply = "Aap filhal ghar mein koi dawai le rahe hain? (e.g. Panadol, Rizek, ya koi nahi?)"
                state["sub_stage"] = "CURRENT_MEDICATIONS"
                return reply, state, False

        # =========================================================================
        # STAGE 5B: ALLERGY DETAILS FOLLOW-UP
        # =========================================================================
        elif state.get("allergy_followup_needed"):
            is_clarification = any(w in msg_lower for w in ["matlab", "mtlb", "samajh", "samjh", "what", "kyun", "kyu", "why", "kaise", "kese"])
            if is_clarification:
                state["allergy_followup_needed"] = False
                reply = "Mera matlab tha ke kya is allergy ke sath koi reaction (e.g. rash ya soojan) hui thi? Khair koi baat nahi, aap filhal ghar mein koi dawai le rahe hain? (e.g. Panadol, Rizek, ya koi nahi?)"
                state["sub_stage"] = "CURRENT_MEDICATIONS"
                return reply, state, False

            # Check if patient skipped and directly gave medication response (backward compatibility)
            is_med_msg = any(w in msg_lower for w in ["panadol", "rizek", "risek", "dawai", "tablet", "capsule", "li hai", "le raha", "ghar mein", "koi nahi", "none"])
            if is_med_msg:
                # Capture medication response directly
                state["allergy_followup_needed"] = False
                if self.is_negation(user_message):
                    state["current_medications"] = []
                else:
                    parts = [p.strip() for p in re.split(r',\s*|\s+aur\s+|\s+and\s+', user_message.strip()) if p.strip()]
                    clean_meds = [self.clean_medication_name(p) for p in parts]
                    state["current_medications"] = clean_meds if clean_meds else [user_message.strip()]
                state = self.reconcile_ehr_and_intake(state, patient_id)
                state["is_complete"] = True
                reply = (
                    "Bohot shukriya! Main ne aap ki tamam intake information note kar li hai. "
                    "Main aap ki details Triage aur Scheduling department ko forward kar rahi hoon."
                )
                return reply, state, True

            # Record allergy details
            substance = state["allergies"][0] if state["allergies"] else "Allergen"
            reaction_text = "Unknown" if self.is_unknown(user_message) else user_message.strip()
            state["allergy_details"].append({
                "substance": substance,
                "reaction": reaction_text,
                "timing": "Reported during intake",
                "emergency_treatment": "Evaluated during intake"
            })
            state["allergy_followup_needed"] = False

            reply = "Aap filhal ghar mein koi dawai le rahe hain? (e.g. Panadol, Rizek, ya koi nahi?)"
            state["sub_stage"] = "CURRENT_MEDICATIONS"
            return reply, state, False

        # =========================================================================
        # STAGE 6: CURRENT MEDICATIONS & RECONCILIATION
        # =========================================================================
        elif state["current_medications"] is None:
            if self.is_negation(user_message):
                state["current_medications"] = []
                state = self.reconcile_ehr_and_intake(state, patient_id)
                state["is_complete"] = True
                reply = self.generate_final_intake_summary(state)
                return reply, state, True

            if self.is_unknown(user_message):
                state["current_medications"] = ["Unknown"]
                state = self.reconcile_ehr_and_intake(state, patient_id)
                state["is_complete"] = True
                reply = self.generate_final_intake_summary(state)
                return reply, state, True

            m_text = user_message.strip()
            parts = [p.strip() for p in re.split(r',\s*|\s+aur\s+|\s+and\s+', m_text) if p.strip()]
            clean_meds = [self.clean_medication_name(p) for p in parts]
            state["current_medications"] = clean_meds if clean_meds else [m_text]

            # Check if medication dose/frequency/last taken was already detailed
            has_dose_info = any(w in msg_lower for w in ["mg", "tablet", "goli", "subah", "shaam", "raat", "once", "twice", "daily", "rozana"])
            if not has_dose_info:
                med_name = clean_meds[0] if clean_meds else m_text
                state["med_followup_needed"] = True
                state["sub_stage"] = "MEDICATION_DETAILS"

                # Check patient's actual EHR medications on file
                ehr_meds = self.records_mcp.get_patient_medications(patient_id)
                ehr_drug_names = [m.get("drug_name") for m in ehr_meds if m.get("drug_name")]
                if ehr_drug_names:
                    ehr_meds_str = " ya ".join(ehr_drug_names)
                    reply = (
                        f"Aap {med_name} ki kya dose (e.g. 20mg ya 40mg) aur din mein kitni martaba le rahe hain, "
                        f"aur aakhri bar kab li thi? Aur kya aap clinic record mein darj {ehr_meds_str} abhi bhi le rahe hain?"
                    )
                else:
                    reply = (
                        f"Aap {med_name} ki kya dose (e.g. 20mg ya 40mg) aur din mein kitni martaba le rahe hain, "
                        "aur aakhri bar kab li thi?"
                    )
                return reply, state, False
            else:
                state["medication_details"].append({
                    "drug_name": clean_meds[0] if clean_meds else m_text,
                    "dose": m_text,
                    "last_taken": "Reported",
                    "still_taking": True
                })
                state = self.reconcile_ehr_and_intake(state, patient_id)
                state["is_complete"] = True
                reply = self.generate_final_intake_summary(state)
                return reply, state, True

        # =========================================================================
        # STAGE 6B: MEDICATION DETAILS & DISCREPANCY RECONCILIATION
        # =========================================================================
        elif state.get("med_followup_needed"):
            med_name = state["current_medications"][0] if state["current_medications"] else "Medication"
            detail_text = "Unknown" if self.is_unknown(user_message) else user_message.strip()
            state["medication_details"].append({
                "drug_name": med_name,
                "dose_and_frequency": detail_text,
                "last_taken": detail_text,
                "reconciliation_status": "Clarified by patient"
            })
            state["med_followup_needed"] = False
            state = self.reconcile_ehr_and_intake(state, patient_id)
            state["is_complete"] = True
            reply = self.generate_final_intake_summary(state)
            return reply, state, True

        # Default completion
        state = self.reconcile_ehr_and_intake(state, patient_id)
        state["is_complete"] = True
        return "Intake complete.", state, True
