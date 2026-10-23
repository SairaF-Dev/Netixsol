import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import BankingTicket

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEEDS_FILES = [
    PROJECT_ROOT / "data" / "seeds" / "seeds.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch2.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch3.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch4.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch5.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch6.jsonl",
    PROJECT_ROOT / "data" / "seeds" / "seeds_batch7.jsonl",
]
OUTPUT_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_json_tasks.jsonl"

TICKET_EXTRACTOR_SYSTEM_PROMPT = (
    "You are a ticket extractor for Zarya Bank. Read the conversation and output ONLY one JSON object following the schema, no extra text."
)


def format_transcript(messages: List[Dict[str, str]]) -> str:
    transcript_lines = []
    for msg in messages:
        if msg.get("role") == "system":
            continue
        role_label = "User" if msg.get("role") == "user" else "Assistant"
        transcript_lines.append(f"{role_label}: {msg.get('content', '')}")
    return "\n".join(transcript_lines)


def build_ticket_extraction_example(seed: Dict[str, Any]) -> Dict[str, Any]:
    raw_ticket = seed.get("ticket")
    if not raw_ticket:
        raise ValueError(f"Seed {seed.get('id')} does not contain a ticket")

    # Validate with Pydantic model
    validated_ticket = BankingTicket(**raw_ticket)

    # Clean payload matching the 8 exact fields
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

    transcript = format_transcript(seed.get("messages", []))
    assistant_json_str = json.dumps(ticket_payload, ensure_ascii=False)

    # Sanity check: must be directly parseable by json.loads
    parsed = json.loads(assistant_json_str)
    assert parsed == ticket_payload, "JSON serialization round-trip failed"

    return {
        "id": f"{seed.get('id')}_extraction",
        "seed_id": seed.get("id"),
        "example_type": "ticket_extraction",
        "category": seed.get("category"),
        "intent": seed.get("intent"),
        "language": seed.get("language"),
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


def main():
    print("=" * 65)
    print("BUILDING TYPE B (TICKET EXTRACTION) EXAMPLES")
    print("=" * 65)

    all_seeds = []
    for seeds_path in SEEDS_FILES:
        if not seeds_path.exists():
            print(f"[WARN] Seed file not found: {seeds_path}")
            continue
        file_seeds = []
        with open(seeds_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    file_seeds.append(json.loads(line))
        print(f"Read {len(file_seeds)} seeds from {seeds_path.name}")
        all_seeds.extend(file_seeds)

    json_tasks = []
    for s in all_seeds:
        if s.get("ticket"):
            task = build_ticket_extraction_example(s)
            json_tasks.append(task)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for task in json_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    print(f"Total seeds read: {len(all_seeds)}")
    print(f"Extracted {len(json_tasks)} Type B ticket extraction examples")
    print(f"Saved to: {OUTPUT_FILE}")

    # Comprehensive verification check on saved file
    print("\n--- Verifying Type B Saved File ---")
    verified_count = 0
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            record = json.loads(line.strip())
            assistant_msg = record["messages"][2]["content"]

            # Must be pure parseable JSON without code fences or surrounding text
            assert not assistant_msg.startswith("```"), f"Line {line_num} starts with code fence"
            assert not assistant_msg.endswith("```"), f"Line {line_num} ends with code fence"

            parsed_ticket = json.loads(assistant_msg)
            # Must pass Pydantic validation
            BankingTicket(**parsed_ticket)
            verified_count += 1

    print(f"[SUCCESS] All {verified_count} Type B assistant messages are pure, valid, parseable JSON tickets.")
    print("=" * 65)


if __name__ == "__main__":
    main()
