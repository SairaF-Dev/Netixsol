"""
Dual-Tier Patient Memory Store for City Care Clinics.
Manages:
1. ShortTermMemoryBuffer: Transient session-scoped dialogue history and turn state.
2. LongTermPatientMemory: Cross-visit patient preferences, past visit complaints, preferred doctor/branch, and privacy-minimized profiles.
"""

import json
import os
from typing import Dict, Any, List
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "long_term_memory.json")

class ShortTermMemoryBuffer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turns: List[Dict[str, str]] = []

    def add_turn(self, sender: str, text: str):
        self.turns.append({"sender": sender, "text": text})

    def get_recent_dialogue(self, max_turns: int = 6) -> str:
        recent = self.turns[-max_turns:]
        return "\n".join([f"{t['sender']}: {t['text']}" for t in recent])

class LongTermPatientMemory:
    def __init__(self, memory_file: str = MEMORY_FILE, records_mcp: PatientRecordsMCPServer = None):
        self.memory_file = memory_file
        self.records_mcp = records_mcp or PatientRecordsMCPServer()
        self.memory_store: Dict[str, Dict[str, Any]] = self._load_store()

    def _load_store(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_store(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory_store, f, indent=2)

    def update_patient_memory(
        self,
        patient_id: str,
        preferred_doctor_id: str = None,
        preferred_doctor_name: str = None,
        preferred_branch_id: str = None,
        preferred_branch_name: str = None,
        last_complaint: str = None
    ):
        """
        Updates long-term memory for a patient while enforcing privacy data minimization.
        """
        profile = self.records_mcp.get_patient_profile(patient_id)
        history = self.records_mcp.get_patient_history(patient_id)

        patient_mem = self.memory_store.get(patient_id, {
            "patient_id": patient_id,
            "patient_name": profile.get("name", "Patient"),
            "preferred_doctor_id": None,
            "preferred_doctor_name": None,
            "preferred_branch_id": None,
            "preferred_branch_name": None,
            "preferred_language": "UrduLish",
            "past_visit_complaints": [],
            "chronic_conditions": [c["condition_name"] for c in history] if isinstance(history, list) else []
        })

        if preferred_doctor_id:
            patient_mem["preferred_doctor_id"] = preferred_doctor_id
        if preferred_doctor_name:
            patient_mem["preferred_doctor_name"] = preferred_doctor_name
        if preferred_branch_id:
            patient_mem["preferred_branch_id"] = preferred_branch_id
        if preferred_branch_name:
            patient_mem["preferred_branch_name"] = preferred_branch_name
        if last_complaint:
            patient_mem["past_visit_complaints"].append(last_complaint)

        self.memory_store[patient_id] = patient_mem
        self._save_store()

    def get_patient_memory(self, patient_id: str) -> Dict[str, Any]:
        """
        Retrieves long-term memory profile. If not found, initializes from DB.
        """
        if patient_id not in self.memory_store:
            self.update_patient_memory(patient_id)
        return self.memory_store.get(patient_id, {})

    def generate_returning_greeting(self, patient_id: str) -> str:
        """
        Generates a personalized returning-patient greeting using long-term memory.
        """
        mem = self.get_patient_memory(patient_id)
        name = mem.get("patient_name", "Patient")
        doc_name = mem.get("preferred_doctor_name")
        branch_name = mem.get("preferred_branch_name")

        if doc_name and branch_name:
            return (
                f"Assalam-o-Alaikum {name} sahib! MedCare Clinic mein khush aamdeed. "
                f"Pichli dafa aap {doc_name} ko ({branch_name}) dikhaye thay. "
                f"Kya dobara unhi ke paas appointment book karni hai ya koi nayi takleef hai?"
            )
        elif doc_name:
            return (
                f"Assalam-o-Alaikum {name} sahib! Welcome back to MedCare Clinic. "
                f"Pichli dafa aap {doc_name} ke paas aaye thay. Aaj aap ki kya madad kar sakta hoon?"
            )

        return f"Assalam-o-Alaikum {name} sahib! Welcome to MedCare Clinic. Aaj aap ki kya khidmath kar sakta hoon?"

if __name__ == "__main__":
    memory = LongTermPatientMemory()
    memory.update_patient_memory(
        patient_id="PAT-0012",
        preferred_doctor_id="DOC-003",
        preferred_doctor_name="Dr. Prof. Hira Rehman",
        preferred_branch_id="BRANCH-LHR-01",
        preferred_branch_name="DHA Branch",
        last_complaint="High fever and cough"
    )
    print("Greeting:", memory.generate_returning_greeting("PAT-0012"))

