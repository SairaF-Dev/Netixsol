"""
feedback_pipeline.py
====================
Week 10 Day 5 - Task 2: Active Learning & DPO Continuous Improvement Flywheel

Transforms:
1. Customer thumbs-down feedback (data/feedback.jsonl)
2. Support-agent escalated complaint tickets (data/zarya_banking.db)
into newly formatted DPO preference pairs (prompt, chosen, rejected)
to feed continuous reinforcement and fine-tuning cycles.
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Workspace Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"
DB_PATH = DATA_DIR / "zarya_banking.db"
OUTPUT_DPO_FILE = DATA_DIR / "dpo" / "flywheel_preference_pairs.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Expert Policy Corrections for Common Problematic Scenarios
EXPERT_CORRECTIONS = {
    "block": (
        "Ji, aap ki card block karne ki darkhwast darj kar li gayi hai. "
        "Hifazat ke pesh-e-nazar, kya aap apne registered mobile number ki tasdeeq kar sakte hain?"
    ),
    "transfer": (
        "Ji, ye sun kar afsos hua. Raast/IBFT transfer inquiry ke liye meharbani farma kar "
        "apna 12-digit Transaction ID ya Reference Number share karein taake hum complaint darj kar sakein."
    ),
    "charges": (
        "Zarya Digital Bank ke Schedule of Charges ke mutabiq, Rs. 25,000 se zayed ke "
        "IBFT transfers par fee Rs. 50 fi transaction hai (tax alag se). Rs. 25,000 tak ke transfers bilkul muft hain."
    ),
    "otp": (
        "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. "
        "Yeh fraud ho sakta hai — kisi ko na batayein aur foran helpline par report karein."
    ),
    "balance": (
        "Aap ka mojooda account balance maloom karne ke liye aap Zarya Mobile App par login kar sakte hain, "
        "ya hamari helpline par biometric verification karwa sakte hain. Kya main mazeed koi madad kar sakta hoon?"
    )
}


def synthesize_expert_chosen(prompt: str, rejected: str) -> str:
    """
    Selects or synthesizes an expert gold standard banking response.
    """
    p_lower = prompt.lower()
    for kw, correction in EXPERT_CORRECTIONS.items():
        if kw in p_lower:
            return correction
            
    # Default courteous banking persona
    return (
        "Assalam-o-Alaikum! Zarya Digital Bank ki policy ke mutabiq aap ki darkhwast par fori "
        "amal kiya ja raha hai. Kya aap mazeed tafseelat share karna chahte hain?"
    )


def extract_flywheel_pairs() -> List[Dict[str, Any]]:
    """
    Parses thumbs-down feedback and escalated tickets into DPO preference pairs.
    """
    pairs = []
    
    # 1. Parse Thumbs-Down Feedback
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("rating") == "down":
                    prompt = item.get("query", "").strip()
                    rejected = item.get("response", "").strip()
                    if prompt and rejected:
                        chosen = synthesize_expert_chosen(prompt, rejected)
                        pairs.append({
                            "source": "customer_feedback_thumbs_down",
                            "prompt": prompt,
                            "chosen": chosen,
                            "rejected": rejected
                        })

    # 2. Parse Escalated Tickets from SQLite
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT summary, details, category FROM complaint_tickets WHERE escalated_to_human = 1")
            for row in cursor.fetchall():
                prompt = row["details"].strip()
                # Simulate the previous un-tuned/flawed response
                rejected = f"Your {row['category']} request has been logged. Please wait for an agent to contact you."
                chosen = synthesize_expert_chosen(prompt, rejected)
                pairs.append({
                    "source": "escalated_complaint_ticket",
                    "prompt": prompt,
                    "chosen": chosen,
                    "rejected": rejected
                })

    return pairs


def run_feedback_flywheel(output_file: Path = OUTPUT_DPO_FILE) -> Dict[str, Any]:
    """
    Executes the active learning pipeline and persists new preference pairs.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    pairs = extract_flywheel_pairs()

    # Deduplicate by prompt
    unique_pairs = {}
    for p in pairs:
        key = p["prompt"].lower().strip()
        if key not in unique_pairs:
            unique_pairs[key] = p

    final_pairs = list(unique_pairs.values())

    with open(output_file, "w", encoding="utf-8") as f:
        for p in final_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    return {
        "total_extracted": len(pairs),
        "total_unique": len(final_pairs),
        "output_path": str(output_file)
    }


def main():
    print("=" * 70)
    print("ZARYA BANK AI: ACTIVE LEARNING & DPO FLYWHEEL PIPELINE")
    print("=" * 70)
    
    stats = run_feedback_flywheel()
    print(f"Extracted Pairs : {stats['total_extracted']}")
    print(f"Unique Pairs    : {stats['total_unique']}")
    print(f"Saved To Disk   : {stats['output_path']}")
    print("\n" + "=" * 70)
    print("FEEDBACK FLYWHEEL PIPELINE EXECUTED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()

