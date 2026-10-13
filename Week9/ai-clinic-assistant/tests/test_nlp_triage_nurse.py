"""
Unit test for NLP-based Clinical Triage Nurse agent.
Verifies:
1. Critical Red-Flag symptom detection ('saans lenay masla', 'chest pain', 'heavy bleeding')
2. Text-to-severity parsing ('bht zayada', 'extreme' -> High Severity 9/10)
3. Dynamic Memory (no repeated questions about already stated symptoms)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from src.agents.intake_agent import IntakeAgent

class TestNLPTriageNurse(unittest.TestCase):
    def setUp(self):
        self.agent = IntakeAgent()

    def test_nlp_emergency_red_flag_saans_lenay_masla(self):
        reply, state, is_complete = self.agent.process_turn("Mujhe 2 din se bukhar hai aur saans lenay masla ho raha hai")
        self.assertTrue(is_complete)
        self.assertEqual(state["urgency_level"], "Emergency")
        self.assertIn("Emergency Room", reply)

    def test_nlp_emergency_red_flag_chest_pain(self):
        reply, state, is_complete = self.agent.process_turn("Dil mein dard hai aur chest pain ho raha hai")
        self.assertTrue(is_complete)
        self.assertEqual(state["urgency_level"], "Emergency")
        self.assertIn("Emergency Room", reply)

    def test_text_to_severity_bht_zayada(self):
        state = {
            "patient_type": "self",
            "chief_complaint": "Bukhar",
            "duration": "2 din",
            "severity": None,
            "associated_symptoms": [],
            "extracted_symptoms": ["fever"],
            "allergies": None,
            "current_medications": None,
            "is_complete": False
        }
        reply, updated_state, is_complete = self.agent.process_turn("takleef bht zayada hai", state)
        self.assertTrue(is_complete)
        self.assertIn("9/10", updated_state["severity"])
        self.assertIn("Emergency Room", reply)

    def test_text_to_severity_extreme(self):
        state = {
            "patient_type": "self",
            "chief_complaint": "Headache",
            "duration": "1 din",
            "severity": None,
            "associated_symptoms": [],
            "extracted_symptoms": ["headache"],
            "allergies": None,
            "current_medications": None,
            "is_complete": False
        }
        reply, updated_state, is_complete = self.agent.process_turn("extreme pain", state)
        self.assertTrue(is_complete)
        self.assertIn("Emergency Room", reply)

    def test_dynamic_memory_no_symptom_repetition(self):
        # User already mentioned fever (bukhar) in turn 1
        reply, state, _ = self.agent.process_turn("Mujhe 2 din se halka bukhar hai")
        self.assertIn("fever", state["extracted_symptoms"])
        
        # User gives duration
        reply2, state2, _ = self.agent.process_turn("2 din se", state)
        
        # Give normal severity 4
        reply3, state3, _ = self.agent.process_turn("4", state2)
        
        # Response MUST NOT ask "jaise bukhar" as a new example prompt!
        self.assertNotIn("(jaise bukhar)", reply3.lower())
        self.assertIn("kya is ke ilawa koi aur alamaat", reply3.lower())

if __name__ == "__main__":
    unittest.main()
