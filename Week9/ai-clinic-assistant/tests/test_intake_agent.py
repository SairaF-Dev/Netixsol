"""
Multi-turn Conversation Test for Intake Agent.
Simulates a patient giving answers turn by turn and validates structured JSON generation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.intake_agent import IntakeAgent

def test_intake_conversation():
    agent = IntakeAgent()
    print("=" * 65)
    print("[TEST] INTAKE AGENT MULTI-TURN CONVERSATION SIMULATION")
    print("=" * 65)

    turns = [
        "Mujhe kal raat se bukhar aur khansi hai",
        "2 din se hai",
        "Around 6 out of 10",
        "Jism mein dard aur thakawat hai",
        "Mujhe Penicillin se allergy hai",
        "Ghar mein bas Panadol li hai"
    ]

    state = None
    print(f"AI: {agent.initial_greeting}\n")

    for i, user_msg in enumerate(turns, 1):
        print(f"Patient (Turn {i}): {user_msg}")
        reply, state, is_complete = agent.process_turn(user_msg, state)
        print(f"AI: {reply}\n")

    assert is_complete == True, "Intake did not mark complete"
    assert state["chief_complaint"] == "Mujhe kal raat se bukhar aur khansi hai"
    assert state["duration"] == "2 din se hai"
    assert state["severity"] == "Around 6 out of 10"
    assert len(state["allergies"]) > 0

    print("=" * 65)
    print("[SUCCESS] INTAKE AGENT STRUCTURED JSON OUTPUT:")
    print("=" * 65)
    import json
    print(json.dumps(state, indent=2))
    print("=" * 65)

if __name__ == "__main__":
    test_intake_conversation()

