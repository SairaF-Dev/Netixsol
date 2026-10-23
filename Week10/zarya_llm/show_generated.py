import json, sys
sys.stdout.reconfigure(encoding="utf-8")
path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/generated.jsonl"
for r in map(json.loads, open(path, encoding="utf-8")):
    print(r["seed_id"], r["task_type"], r["language"], "| context:", r["context"])
    for m in r["messages"]:
        if m["role"] != "system":
            print("  ", m["role"][0].upper() + ":", m["content"])
    if r.get("ticket"):
        print("   TICKET:", json.dumps(r["ticket"], ensure_ascii=False))
    print()