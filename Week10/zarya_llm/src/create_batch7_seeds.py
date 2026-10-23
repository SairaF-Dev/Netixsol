"""
Batch 7 seeds generator (seed_088 to seed_100) for Zarya Bank LLM.
Synthetic training values only, not real bank policy.
Total seeds in this batch: 13 seeds.
Every customer message is loaded from human_lines_batch7.json by seed id and turn index.
This script contains no customer text of its own.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_format import build_system_message
from schema import BankingTicket

BASE_SYSTEM_MESSAGE = (
    "Tum Zarya Bank ki support officer ho.\n"
    "1. Hamesha Ji aur aap istemal karo, izzat ke saath.\n"
    "2. Jawab chhota aur saaf rakho, ek dafa mein sirf ek sawal poochho.\n"
    "3. Fees, limits aur TAT sirf diye gaye documents se batao. Agar document mein nahi hai to apni taraf se mat batao.\n"
    "4. OTP, PIN ya password kabhi mat maango. Customer ko saaf batao ke bank ye kabhi nahi maangta."
)

# Seed configurations and bot replies (no customer text)
BATCH7_CONFIGS: List[Dict[str, Any]] = [
    # seed_088 | category: transfer | urdulish | multi turn | ctx 27 working days | ticket: pending_transaction
    {
        "id": "seed_088",
        "category": "transfer",
        "intent": "pending_transaction",
        "language": "urdulish",
        "is_multi_turn": True,
        "context": "IBFT pending transfer review time: 27 working days.",
        "bot_replies": [
            "Ji, raqam na milne ki itla ka shukriya. Bheji gayi raqam kitni thi?",
            "Ji shukriya. Aap ki pending transaction ki shikayat darj kar li gayi hai, review ka waqt 27 working days hai. Kya aap is hawale se mazeed kuch poochna chahte hain?"
        ],
        "ticket": {
            "intent": "pending_transaction",
            "category": "transfer",
            "priority": "medium",
            "amount": 18000.0,
            "time_mentioned": "3 din se",
            "summary": "IBFT transfer of 18000 PKR pending for 3 days",
            "customer_very_angry": False,
            "escalate_to_human": False
        }
    },
    # seed_089 | category: transfer | english | single turn | ctx 300000 rupees | no ticket | intent: product_terms
    {
        "id": "seed_089",
        "category": "transfer",
        "intent": "product_terms",
        "language": "english",
        "is_multi_turn": False,
        "context": "Maximum amount per single IBFT transfer: 300000 rupees.",
        "bot_replies": [
            "Ji, the maximum amount per single IBFT transfer is 300000 rupees. Would you like to know more about transfer limits?"
        ],
        "ticket": None
    },
    # seed_090 | category: transfer | roman urdu | single turn | nodoc | no ticket | intent: bill_payment
    {
        "id": "seed_090",
        "category": "transfer",
        "intent": "bill_payment",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "bot_replies": [
            "Ji, main is waqt is sahulat ki tasdeeq nahi kar sakti. Maloomat ke liye aap helpline par rabta kar sakte hain. Kya aap ka koi aur sawal hai?"
        ],
        "ticket": None
    },
    # seed_091 | category: transfer | urdulish | multi turn | no ctx | ticket: transfer_failed
    {
        "id": "seed_091",
        "category": "transfer",
        "intent": "transfer_failed",
        "language": "urdulish",
        "is_multi_turn": True,
        "context": None,
        "bot_replies": [
            "Ji, raqam do dafa katne par afsos hua. Katne wali raqam kitni thi?",
            "Ji, transfer ki shikayat darj kar li gayi hai. Kya aap is hawale se koi mazeed baat share karna chahte hain?"
        ],
        "ticket": {
            "intent": "transfer_failed",
            "category": "transfer",
            "priority": "medium",
            "amount": 9000.0,
            "time_mentioned": "10 minute pehle",
            "summary": "Transfer amount of 9000 PKR debited twice",
            "customer_very_angry": False,
            "escalate_to_human": False
        }
    },
    # seed_092 | category: transfer | urdu script | single turn | nodoc | no ticket | intent: product_terms
    {
        "id": "seed_092",
        "category": "transfer",
        "intent": "product_terms",
        "language": "urdu_script",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "bot_replies": [
            "جی، میں اس وقت اس سہولت کی تصدیق نہیں کر سکتی۔ معلومات کے لیے آپ ہیلپ لائن پر رابطہ کر سکتے ہیں۔ کیا آپ کا کوئی اور سوال ہے؟"
        ],
        "ticket": None
    },
    # seed_093 | category: account | urdulish | single turn | ctx 180 days | no ticket | intent: dormant_account
    {
        "id": "seed_093",
        "category": "account",
        "intent": "dormant_account",
        "language": "urdulish",
        "is_multi_turn": False,
        "context": "Account dormancy: an account is marked dormant after 180 days without a customer initiated transaction.",
        "bot_replies": [
            "Ji, customer initiated transaction ke baghair 180 days baad account dormant mark ho jata hai. Kya aap is hawale se mazeed kuch poochna chahte hain?"
        ],
        "ticket": None
    },
    # seed_094 | category: account | roman urdu | single turn | nodoc | no ticket | intent: update_profile
    {
        "id": "seed_094",
        "category": "account",
        "intent": "update_profile",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "bot_replies": [
            "Ji, main is waqt account band karne ke tariqay ki tasdeeq nahi kar sakti. Rahnumai ke liye aap helpline par rabta kar sakte hain. Kya aap ka koi aur sawal hai?"
        ],
        "ticket": None
    },
    # seed_095 | category: account | english | multi turn | ctx 3500 rupees | no ticket | intent: open_account
    {
        "id": "seed_095",
        "category": "account",
        "intent": "open_account",
        "language": "english",
        "is_multi_turn": True,
        "context": "Joint account: a valid CNIC of both holders and a minimum opening deposit of 3500 rupees are required.",
        "bot_replies": [
            "Ji, do both holders have a valid CNIC?",
            "Ji, a valid CNIC of both holders and a minimum opening deposit of 3500 rupees are required. Do you have any other questions regarding opening a joint account?"
        ],
        "ticket": None
    },
    # seed_096 | category: account | urdulish | single turn | no ctx | no ticket | intent: check_balance
    {
        "id": "seed_096",
        "category": "account",
        "intent": "check_balance",
        "language": "urdulish",
        "is_multi_turn": False,
        "context": None,
        "bot_replies": [
            "Ji, aap ki pareshani samajh sakti hoon. Is waqt aap ko kitna balance dikhai de raha hai?"
        ],
        "ticket": None
    },
    # seed_097 | category: account | urdu script | single turn | ctx 18 years | no ticket | intent: open_account
    {
        "id": "seed_097",
        "category": "account",
        "intent": "open_account",
        "language": "urdu_script",
        "is_multi_turn": False,
        "context": "Minimum age to open an account: 18 years.",
        "bot_replies": [
            "جی، Zarya Bank میں اکاؤنٹ کھلوانے کے لیے کم از کم عمر 18 سال ہے۔ کیا آپ اکاؤنٹ کے بارے میں مزید کچھ جاننا چاہتے ہیں؟"
        ],
        "ticket": None
    },
    # seed_098 | category: complaint | urdulish | multi turn | no ctx | ticket: service_complaint
    {
        "id": "seed_098",
        "category": "complaint",
        "intent": "service_complaint",
        "language": "urdulish",
        "is_multi_turn": True,
        "context": None,
        "bot_replies": [
            "Ji, is pareshani par afsos hua. Jab crash hua to aap kya karne ki koshish kar rahe thay?",
            "Ji, crash maslay ki shikayat darj kar li gayi hai. Kya aap is hawale se mazeed kuch share karna chahte hain?"
        ],
        "ticket": {
            "intent": "service_complaint",
            "category": "complaint",
            "priority": "medium",
            "amount": None,
            "time_mentioned": "kal subah se",
            "summary": "Customer experiencing repeated app crashes during transfers",
            "customer_very_angry": False,
            "escalate_to_human": False
        }
    },
    # seed_099 | category: complaint | english | single turn | no ctx | angry | ticket: tat_breach
    {
        "id": "seed_099",
        "category": "complaint",
        "intent": "tat_breach",
        "language": "english",
        "is_multi_turn": False,
        "context": None,
        "bot_replies": [
            "Ji, I understand your frustration. What specific issue were you facing with your account?"
        ],
        "ticket": {
            "intent": "tat_breach",
            "category": "complaint",
            "priority": "high",
            "amount": None,
            "time_mentioned": None,
            "summary": "Customer reporting unresolved issue for the third time without assistance",
            "customer_very_angry": True,
            "escalate_to_human": True
        }
    },
    # seed_100 | category: complaint | roman urdu | multi turn | ctx 33 working days | ticket: service_complaint
    {
        "id": "seed_100",
        "category": "complaint",
        "intent": "service_complaint",
        "language": "roman_urdu",
        "is_multi_turn": True,
        "context": "SMS alert complaint review time: 33 working days.",
        "bot_replies": [
            "Ji, SMS alerts na milne par afsos hua. Yeh masla kitne arsay se pesh aa raha hai?",
            "Ji, SMS alerts ki shikayat darj kar li gayi hai, review ka waqt 33 working days hai. Kya aap is hawale se mazeed koi maloomat lena chahte hain?"
        ],
        "ticket": {
            "intent": "service_complaint",
            "category": "complaint",
            "priority": "low",
            "amount": None,
            "time_mentioned": "2 hafte se",
            "summary": "Customer not receiving transaction SMS alerts for 2 weeks",
            "customer_very_angry": False,
            "escalate_to_human": False
        }
    }
]


def build_batch7_seeds() -> List[Dict[str, Any]]:
    project_root = Path(__file__).resolve().parent.parent
    human_lines_path = project_root / "data" / "seeds" / "human_lines_batch7.json"
    with open(human_lines_path, "r", encoding="utf-8") as f:
        human_lines = json.load(f)

    seeds = []
    for cfg in BATCH7_CONFIGS:
        seed_id = cfg["id"]
        customer_lines = human_lines[seed_id]
        bot_replies = cfg["bot_replies"]

        messages = [
            {"role": "system", "content": build_system_message(BASE_SYSTEM_MESSAGE, cfg["context"])}
        ]

        if cfg["is_multi_turn"]:
            messages.append({"role": "user", "content": customer_lines[0]})
            messages.append({"role": "assistant", "content": bot_replies[0]})
            messages.append({"role": "user", "content": customer_lines[1]})
            messages.append({"role": "assistant", "content": bot_replies[1]})
        else:
            messages.append({"role": "user", "content": customer_lines[0]})
            messages.append({"role": "assistant", "content": bot_replies[0]})

        seed_record: Dict[str, Any] = {
            "id": seed_id,
            "category": cfg["category"],
            "intent": cfg["intent"],
            "language": cfg["language"],
            "is_multi_turn": cfg["is_multi_turn"],
            "context": cfg["context"],
            "messages": messages
        }

        if cfg.get("ticket"):
            BankingTicket(**cfg["ticket"])
            seed_record["ticket"] = cfg["ticket"]

        seeds.append(seed_record)

    return seeds


def main():
    project_root = Path(__file__).resolve().parent.parent
    seeds_dir = project_root / "data" / "seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    batch7_file = seeds_dir / "seeds_batch7.jsonl"

    seeds = build_batch7_seeds()
    print(f"Validating and writing {len(seeds)} batch 7 seeds...")

    with open(batch7_file, "w", encoding="utf-8") as f:
        for seed in seeds:
            f.write(json.dumps(seed, ensure_ascii=False) + "\n")

    print(f"Wrote {len(seeds)} seeds to {batch7_file}")


if __name__ == "__main__":
    main()
