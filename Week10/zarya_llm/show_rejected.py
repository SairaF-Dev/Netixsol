import json, sys
sys.stdout.reconfigure(encoding="utf-8")
for line in open("data/raw/rejected.jsonl", encoding="utf-8"):
    r = json.loads(line)
    c = r.get("candidate", r)
    print(r.get("seed_id", c.get("seed_id")), r.get("task_type", c.get("task_type")), c.get("language"))
    for k, v in r.items():
        if any(w in k.lower() for w in ("fail", "rule", "reason", "error")):
            print("   RULES:", v)
    for m in c.get("messages", []):
        if m.get("role") != "system":
            print("  ", m["role"][0].upper() + ":", m["content"])
    print()