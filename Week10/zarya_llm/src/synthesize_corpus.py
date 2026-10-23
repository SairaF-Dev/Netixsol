import os
import sys
import json
import random
import copy
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import Counter, defaultdict

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

import generate
from schema import BankingTicket, TicketCategory, TicketPriority, BankingIntent, get_large_amount_threshold
from prompt_format import build_system_message

PROJECT_ROOT = SRC_DIR.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_RAW_PATH = RAW_DIR / "raw_conversations.jsonl"
SEEDS_DIR = PROJECT_ROOT / "data" / "seeds"

BASE_SYSTEM_MESSAGE = generate.BASE_SYSTEM_MESSAGE
TICKET_EXTRACTOR_SYSTEM_PROMPT = (
    "You are a ticket extractor for Zarya Bank. Read the conversation and output ONLY one JSON object following the schema, no extra text."
)

AMOUNTS_POOL = [
    1200, 1850, 2400, 3200, 4500, 5200, 6800, 8500, 9500, 12000,
    14500, 18000, 22500, 28000, 34000, 42000, 48500, 55000, 65000, 78000, 95000, 120000
]

TIMES_POOL = {
    "urdulish": ["kal sham", "aaj subah", "do ghante pehle", "kal raat", "aaj dopahar", "parso subah", "aik ghanta pehle", "kal subah 10 baje"],
    "roman_urdu": ["kal sham", "aaj subah", "do ghante pehle", "kal raat", "aaj dopahar", "parso sham", "aik ghanta pehle", "subah sawere"],
    "english": ["yesterday evening", "this morning", "two hours ago", "last night", "today afternoon", "one hour ago", "yesterday at 10 AM"],
    "urdu_script": ["کل شام", "آج صبح", "دو گھنٹے پہلے", "کل رات", "آج دوپہر", "ایک گھنٹہ پہلے"]
}

TXN_REFS = [
    "TXN-4921", "RS88219", "R-10924", "FT77201", "PK99412", "TRX-3301",
    "IBFT-5510", "REF-8842", "RAAST-2144", "ZAR-7711", "TX-9901", "PY-5542"
]

PREFIXES_ROMAN = ["Salam, ", "Hello, ", "Assalam o alaikum, ", "Bhai jan, ", "Guzarish hai ke ", "Janab, ", "Dear support, "]
SUFFIXES_ROMAN = ["", " please guide karein.", " rehnumai chahiye.", " fori hal darkar hai.", " is ka hal bata dein.", " shukriya."]

PREFIXES_ENG = ["Hello, ", "Dear support team, ", "Good morning, ", "Hi, ", "Assalam o alaikum, ", "Please help, "]
SUFFIXES_ENG = ["", " please guide me.", " need urgent resolution.", " kindly assist.", " thank you."]

PREFIXES_UR = ["سلام، ", "السلام علیکم، ", "جناب، ", "محترم، ", "رہنمائی فرمائیں، "]
SUFFIXES_UR = ["", " رہنمائی درکار ہے۔", " فوری حل درکار ہے۔", " شکریہ۔"]

MOCK_CNICS = ["42101-1234567-1", "35201-9876543-2", "61101-1122334-5", "37405-5566778-9"]
MOCK_CARDS = ["4532 1234 5678 9012", "5123 4567 8901 2345", "4111 2222 3333 4444"]
MOCK_ACCOUNTS = ["PK36SCBL0000001123456702", "PK29HABB0001234567890123", "0123456789012345"]


def load_all_existing_seeds() -> List[Dict[str, Any]]:
    return generate.load_seeds(SEEDS_DIR)


def build_ticket_extraction_example(seed: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    raw_ticket = seed.get("ticket")
    if not raw_ticket:
        raise ValueError(f"Record {seed.get('id')} does not contain a ticket")

    validated_ticket = BankingTicket(**raw_ticket)

    ticket_payload = {
        "intent": validated_ticket.intent.value,
        "category": validated_ticket.category.value,
        "priority": validated_ticket.priority.value,
        "amount": validated_ticket.amount,
        "time_mentioned": validated_ticket.time_mentioned,
        "summary": validated_ticket.summary,
        "customer_very_angry": validated_ticket.customer_very_angry,
        "escalate_to_human": validated_ticket.escalate_to_human,
    }

    transcript_lines = []
    for msg in seed.get("messages", []):
        if msg.get("role") == "system":
            continue
        role_label = "User" if msg.get("role") == "user" else "Assistant"
        transcript_lines.append(f"{role_label}: {msg.get('content', '')}")
    transcript = "\n".join(transcript_lines)

    assistant_json_str = json.dumps(ticket_payload, ensure_ascii=False)

    return {
        "id": task_id,
        "seed_id": seed.get("id"),
        "example_type": "ticket_extraction",
        "category": seed.get("category"),
        "intent": seed.get("intent"),
        "language": seed.get("language"),
        "is_multi_turn": seed.get("is_multi_turn", True),
        "messages": [
            {
                "role": "system",
                "content": TICKET_EXTRACTOR_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": transcript
            },
            {
                "role": "assistant",
                "content": assistant_json_str
            }
        ],
        "ticket": ticket_payload
    }


def create_seed_variation(
    base_seed: Dict[str, Any],
    new_id: str,
    target: Dict[str, Any],
    rng: random.Random
) -> Dict[str, Any]:
    cand = copy.deepcopy(base_seed)
    cand["id"] = new_id
    cand["seed_id"] = base_seed.get("id")
    cand["variation"] = {"source": "seed_selftest"}

    target_lang = target.get("language", base_seed.get("language", "urdulish"))
    cand["language"] = target_lang

    # 1. Disputed amount variation
    t = cand.get("ticket")
    if t and t.get("amount"):
        old_amt_int = int(t["amount"])
        old_amt_str = str(old_amt_int)
        new_amt_int = rng.choice(AMOUNTS_POOL)
        new_amt_str = str(new_amt_int)
        t["amount"] = float(new_amt_int)

        # Update human escalation rules
        is_fraud = (cand.get("category") == "fraud")
        is_large = (t["amount"] >= 50000.0)
        is_angry = bool(target.get("mood") == "very_angry" or t.get("customer_very_angry", False))
        t["customer_very_angry"] = is_angry
        t["escalate_to_human"] = bool(is_fraud or is_large or is_angry)

        # Update all messages citing the old amount
        for m in cand.get("messages", []):
            if old_amt_str in m.get("content", ""):
                m["content"] = m["content"].replace(old_amt_str, new_amt_str)

    # 2. Time mentioned variation if present in ticket
    if t and t.get("time_mentioned"):
        old_time = t["time_mentioned"]
        new_time = rng.choice(TIMES_POOL.get(target_lang, TIMES_POOL["urdulish"]))
        t["time_mentioned"] = new_time
        for m in cand.get("messages", []):
            if old_time in m.get("content", ""):
                m["content"] = m["content"].replace(old_time, new_time)

    # 3. Add greeting prefix, natural customer qualifier, and polite suffix to first customer turn
    QUALIFIERS_ROMAN = [
        "", " actually ", " barah e karam ", " urgent hai, ", " inquiry karni thi, ",
        " masla ye hai ke ", " zaroori maloomat chahiye, ", " kindly check karein, ",
        " meherbani hogi agar bata dein, ", " details confirm kar dein, ", " please check, ",
        " guidance darkar hai, ", " support chahiye, ", " inquiry ke silsilay mein, "
    ]
    QUALIFIERS_ENG = [
        "", " actually, ", " urgently, ", " please note that ", " regarding my account, ",
        " kindly advise on this, ", " could you please check, ", " I need confirmation on this, ",
        " for your information, ", " seeking support regarding, "
    ]
    QUALIFIERS_UR = [
        "", " دراصل ", " برائے مہربانی ", " فوری مسئلہ ہے، ", " معلومات درکار ہیں، ", " توجہ فرمائیں، ", " رہنمائی چاہیے، "
    ]

    for m in cand.get("messages", []):
        if m.get("role") == "user":
            orig = m["content"]
            if target_lang == "urdu_script":
                p = rng.choice(PREFIXES_UR)
                q = rng.choice(QUALIFIERS_UR)
                s = rng.choice(SUFFIXES_UR)
            elif target_lang == "english":
                p = rng.choice(PREFIXES_ENG)
                q = rng.choice(QUALIFIERS_ENG)
                s = rng.choice(SUFFIXES_ENG)
            else:
                p = rng.choice(PREFIXES_ROMAN)
                q = rng.choice(QUALIFIERS_ROMAN)
                s = rng.choice(SUFFIXES_ROMAN)

            # Prevent double greetings or duplicate punctuation
            if not any(orig.startswith(g.strip()) for g in ["Salam", "AOA", "Hello", "Assalam", "Bhai", "سلام"]):
                m["content"] = f"{p}{q}{orig}{s}".strip()
            else:
                m["content"] = f"{orig}{q}{s}".strip()

            # Clean extra spaces
            m["content"] = re.sub(r"\s+", " ", m["content"]).strip()

            # Randomly inject mock PII into ~3% of messages to test Stage D PII sanitization
            if rng.random() < 0.03:
                pii_addon = f" CNIC: {rng.choice(MOCK_CNICS)} Card: {rng.choice(MOCK_CARDS)}"
                m["content"] += pii_addon
            break

    # 4. Reference number variation
    new_ref = rng.choice(TXN_REFS)
    for m in cand.get("messages", []):
        for ref_prefix in ["RS", "TXN", "REF", "FT", "TRX", "PK", "R-"]:
            if ref_prefix in m.get("content", ""):
                m["content"] = re.sub(rf"\b{ref_prefix}\d+\b", new_ref, m["content"])

    return cand


def synthesize_full_dataset(target_type_a: int = 2250, target_type_b: int = 750) -> List[Dict[str, Any]]:
    print("=" * 70)
    print("TASK 3: SYNTHETIC DATASET GENERATION (3,000 EXAMPLES)")
    print(f"Dual Architecture Target: {target_type_a} Type A Chat + {target_type_b} Type B JSON Tasks")
    print("=" * 70)

    config = generate.load_config()
    seeds = load_all_existing_seeds()
    print(f"[INFO] Loaded {len(seeds)} verified golden seeds.")

    # Target planning from generation_plan.yaml
    targets = generate.build_plan_targets("full", config, seeds, override_seed=42)
    print(f"[INFO] Sampled {len(targets)} planned targets.")

    type_a_records: List[Dict[str, Any]] = []
    rng = random.Random(42)

    # Index seeds by task_type and language for fast targeted sampling
    seeds_by_criteria: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for s in seeds:
        tt = generate.derive_task_type(s)
        lg = s.get("language", "urdulish")
        seeds_by_criteria[(tt, lg)].append(s)
        seeds_by_criteria[(tt, "any")].append(s)

    # 1. Synthesize 2,250 Type A Conversations
    print(f"[INFO] Generating {target_type_a} Type A conversations...")
    seen_sigs = set()
    exact_dup_injected = 0

    for idx, target in enumerate(targets[:target_type_a], start=1):
        tt = target.get("task_type")
        lang = target.get("language")

        # Pick matching seed
        candidates = seeds_by_criteria.get((tt, lang), [])
        if not candidates:
            candidates = seeds_by_criteria.get((tt, "any"), seeds)
        base_seed = rng.choice(candidates)

        cand = create_seed_variation(base_seed, f"zarya_conv_{idx:04d}", target, rng)

        # Inject realistic ~1% duplicate overlap to test Stage A deduplication
        if idx % 120 == 0 and type_a_records and exact_dup_injected < 15:
            dup_target = copy.deepcopy(type_a_records[-1])
            dup_target["id"] = f"zarya_conv_{idx:04d}"
            cand = dup_target
            exact_dup_injected += 1

        # Validate with validator engine
        fails = generate.validate_candidate(cand)
        if fails:
            # Revert to clean base seed variation
            clean_seed = copy.deepcopy(base_seed)
            clean_seed["id"] = f"zarya_conv_{idx:04d}"
            clean_seed["variation"] = {"source": "seed_selftest"}
            cand = clean_seed

        type_a_records.append(cand)

    print(f"[INFO] Successfully created {len(type_a_records)} Type A chat dialogues.")

    # 2. Build 750 Type B Ticket Extraction Tasks
    print(f"\n[INFO] Constructing {target_type_b} Type B Ticket Extraction tasks...")
    # Gather Type A conversations that have tickets (complaint and fraud)
    ticketed_conversations = [r for r in type_a_records if r.get("ticket") is not None]
    print(f"[INFO] Found {len(ticketed_conversations)} source dialogues with valid tickets.")

    type_b_records: List[Dict[str, Any]] = []
    ticket_pool = ticketed_conversations[:]
    rng.shuffle(ticket_pool)

    for i in range(target_type_b):
        src_dialogue = ticket_pool[i % len(ticket_pool)]
        task_id = f"zarya_type_b_{i+1:04d}"
        type_b_item = build_ticket_extraction_example(src_dialogue, task_id)
        type_b_records.append(type_b_item)

    print(f"[INFO] Successfully constructed {len(type_b_records)} Type B ticket extraction tasks.")

    # 3. Concatenate and save to data/raw/raw_conversations.jsonl
    full_corpus = type_a_records + type_b_records
    print(f"\n[INFO] Total combined dataset size: {len(full_corpus)}")

    OUTPUT_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_RAW_PATH, "w", encoding="utf-8") as f:
        for r in full_corpus:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[SUCCESS] Dataset saved to: {OUTPUT_RAW_PATH}")

    # Summary Statistics Verification
    verify_dataset_statistics(full_corpus)

    return full_corpus


def verify_dataset_statistics(records: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 55)
    print("DATASET COMPOSITION & SPECIFICATION COMPLIANCE")
    print("=" * 55)
    print(f"Total Records: {len(records)}")

    # Example Types
    type_counts = Counter(r.get("example_type", "type_a_chat") for r in records)
    print("\nExample Types (Dual Architecture):")
    for k, v in type_counts.items():
        print(f"  * {k}: {v} ({v / len(records) * 100:.1f}%)")

    # Categories
    cat_counts = Counter(r.get("category", "unknown") for r in records)
    print("\nOperational Categories:")
    for k, v in cat_counts.items():
        print(f"  * {k}: {v} ({v / len(records) * 100:.1f}%)")

    # Languages
    lang_counts = Counter(r.get("language", "unknown") for r in records)
    print("\nLinguistic Distribution:")
    for k, v in lang_counts.items():
        print(f"  * {k}: {v} ({v / len(records) * 100:.1f}%)")

    # Multi-turn
    multi_count = sum(1 for r in records if r.get("is_multi_turn", False))
    print(f"\nMulti-Turn Conversations: {multi_count} ({multi_count / len(records) * 100:.1f}%)")

    # Schema validity for Type B
    type_b = [r for r in records if r.get("example_type") == "ticket_extraction"]
    valid_b_count = 0
    for r in type_b:
        assistant_json = r["messages"][2]["content"]
        data = json.loads(assistant_json)
        BankingTicket(**data)
        valid_b_count += 1
    print(f"Type B JSON Validity: {valid_b_count}/{len(type_b)} (100% valid BankingTicket schema)")
    print("=" * 55)


if __name__ == "__main__":
    synthesize_full_dataset(target_type_a=2250, target_type_b=750)
