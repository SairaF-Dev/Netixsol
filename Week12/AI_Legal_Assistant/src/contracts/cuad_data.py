"""
Day 4, Task 1 (data): a clause-classification dataset from CUAD v1.

CUAD (Atticus Project, CC BY 4.0) has 510 commercial contracts in which lawyers marked the passages that
belong to 41 categories. Here:

* Clause types: the 28 categories with at least 100 marked passages, leaving out 4 that are metadata,
  not clauses (Document Name, Parties, Agreement Date, Effective Date). Rarer types have too few examples
  to train a small model.
* Examples: every marked passage, with all the types it was marked with (a passage can be both "Cap On
  Liability" and "Uncapped Liability"), plus sentences that no lawyer marked, labelled with no type, so a
  model also learns to say "this is not a key clause". Unmarked sentences are 1 per 2 marked passages.
* Split by contract (seed 42): 80% train / 10% validation / 10% test, so no test contract is seen in
  training.
* test_sample: up to 15 passages per type plus 150 unmarked sentences from the test contracts, used for
  the LLM vs fine-tuned comparison (the LLM is too slow and costly for the full test set).

Output: data/cuad_labels/clauses_{train,val,test,test_sample}.jsonl, each row
{"id", "contract", "text", "labels": [...]}, and clause_types.json (type -> CUAD definition).

Run:  python -m src.contracts.cuad_data --download   (fetch CUAD_v1.json + master_clauses.csv, 44 MB)
      python -m src.contracts.cuad_data              (build the dataset)
"""

import argparse
import json
import random
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

DIR = Path("data/cuad_labels")
SOURCE = DIR / "CUAD_v1.json"
URL = "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/CUAD_v1/{name}"
METADATA = {"Document Name", "Parties", "Agreement Date", "Effective Date"}
MIN_SPANS = 100
SEED = 42
PER_TYPE_SAMPLE, NEGATIVE_SAMPLE = 15, 150


def download() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    for name in ("CUAD_v1.json", "master_clauses.csv"):
        subprocess.run(["curl", "-sL", "-o", str(DIR / name), URL.format(name=name)], check=True)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_cuad() -> List[Dict]:
    return json.loads(SOURCE.read_text(encoding="utf-8"))["data"]


def clause_types(contracts: List[Dict]) -> Dict[str, str]:
    """Clause type -> CUAD's own description ('Details: ...' in its question)."""
    counts, details = Counter(), {}
    for contract in contracts:
        for qa in contract["paragraphs"][0]["qas"]:
            cat = qa["id"].split("__")[-1]
            counts[cat] += len({a["text"] for a in qa["answers"]})
            details[cat] = qa["question"].split("Details:", 1)[-1].strip()
    return {cat: details[cat] for cat, n in counts.most_common() if n >= MIN_SPANS and cat not in METADATA}


def contract_examples(contract: Dict, types: Dict[str, str], rng: random.Random) -> List[Dict]:
    context = contract["paragraphs"][0]["context"]
    labels, covered = defaultdict(set), []
    for qa in contract["paragraphs"][0]["qas"]:
        cat = qa["id"].split("__")[-1]
        for answer in qa["answers"]:
            covered.append((answer["answer_start"], answer["answer_start"] + len(answer["text"])))
            text = _norm(answer["text"])
            if cat in types and 3 <= len(text.split()) <= 400:
                labels[text].add(cat)
    title = contract["title"]
    examples = [{"contract": title, "text": text, "labels": sorted(cats)} for text, cats in labels.items()]
    # unmarked sentences: no overlap with any lawyer-marked span (of any category)
    negatives = []
    for match in re.finditer(r"[^.;\n]{40,700}[.;]", context):
        start, end = match.span()
        text = _norm(match.group(0))
        if 8 <= len(text.split()) <= 120 and not any(s < end and start < e for s, e in covered):
            negatives.append({"contract": title, "text": text, "labels": []})
    rng.shuffle(negatives)
    return examples + negatives[: max(1, len(examples) // 2)]


def build() -> None:
    contracts = load_cuad()
    types = clause_types(contracts)
    rng = random.Random(SEED)
    titles = sorted(c["title"] for c in contracts)
    rng.shuffle(titles)
    n = len(titles)
    split_of = {t: "train" for t in titles[: int(n * 0.8)]}
    split_of.update({t: "val" for t in titles[int(n * 0.8): int(n * 0.9)]})
    split_of.update({t: "test" for t in titles[int(n * 0.9):]})
    rows = defaultdict(list)
    for contract in contracts:
        for i, ex in enumerate(contract_examples(contract, types, rng)):
            ex["id"] = f"{contract['title'][:60]}#{i}"
            rows[split_of[contract["title"]]].append(ex)
    # LLM / fine-tuned comparison sample from the test contracts
    test = rows["test"]
    rng.shuffle(test)
    sample, per_type = [], Counter()
    for ex in test:
        if ex["labels"] and any(per_type[t] < PER_TYPE_SAMPLE for t in ex["labels"]):
            sample.append(ex)
            per_type.update(ex["labels"])
    sample += [ex for ex in test if not ex["labels"]][:NEGATIVE_SAMPLE]
    rows["test_sample"] = sample
    for split, data in rows.items():
        with (DIR / f"clauses_{split}.jsonl").open("w", encoding="utf-8") as handle:
            for ex in data:
                handle.write(json.dumps(ex, ensure_ascii=False) + "\n")
    (DIR / "clause_types.json").write_text(json.dumps(types, indent=1, ensure_ascii=False), encoding="utf-8")
    for split, data in rows.items():
        print(f"{split:12} {len(data):6} examples, {sum(1 for e in data if not e['labels']):5} unmarked, "
              f"{len({e['contract'] for e in data})} contracts")
    print(f"{len(types)} clause types; sample per type: {dict(per_type)}")


def load(split: str) -> List[Dict]:
    return [json.loads(line) for line in (DIR / f"clauses_{split}.jsonl").read_text(encoding="utf-8").splitlines()]


def load_types() -> Dict[str, str]:
    return json.loads((DIR / "clause_types.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    download() if args.download else build()
