"""
Day 4, Task 1: CUAD clause classification - LLM (zero-shot) vs fine-tuned Legal-BERT-small.

Both label the same passages from the 51 test contracts (data/cuad_labels/clauses_test_sample.jsonl:
up to 15 marked passages per type plus 150 sentences no lawyer marked). Each passage gets a set of
clause types, possibly empty.

* LLM: gemini-3.5-flash-lite, zero-shot, given CUAD's own one-line description of each of the 28 types,
  15 passages per request (about 33 requests).
* Fine-tuned: src/contracts/finetune.py (trained on 407 other contracts).

Scores: precision / recall / F1 per clause type, micro and macro averages, plus false alarms on the
unmarked sentences, cost (requests, tokens) and time per passage.

Run:  python -m evaluations.clause_classification            (LLM run + report)
      python -m evaluations.clause_classification --no-llm   (fine-tuned only)
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from src.contracts.cuad_data import DIR, load, load_types

REPORT = Path("evaluations/clause_classification_report.md")
BATCH = 15


class PassageLabels(BaseModel):
    n: int
    types: List[str]


class BatchLabels(BaseModel):
    passages: List[PassageLabels]


def _system(types: Dict[str, str]) -> str:
    lines = "\n".join(f"- {name}: {desc}" for name, desc in types.items())
    return f"""You label passages from commercial contracts with CUAD clause types.
A passage can have several types or none. Give a type only if the passage itself is that kind of clause.
Use exactly these type names:
{lines}
Return every passage number, with an empty list when no type applies."""


def llm_predict(rows: List[Dict], types: Dict[str, str]) -> Dict:
    from src.llm.gemini_client import GeminiClient

    llm, system = GeminiClient(), _system(types)
    labels, start, requests, chars = {}, time.time(), 0, 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        prompt = "Label each passage.\n\n" + "\n\n".join(f"{n}. {r['text'][:1500]}" for n, r in enumerate(batch, 1))
        result = llm.generate_json(prompt, BatchLabels, system=system, temperature=0.0)
        requests, chars = requests + 1, chars + len(prompt) + len(system)
        by_n = {p.n: [t for t in p.types if t in types] for p in result.passages}
        for n, row in enumerate(batch, 1):
            labels[row["id"]] = by_n.get(n, [])
        print(f"  {min(i + BATCH, len(rows))}/{len(rows)} passages", flush=True)
    return {"labels": labels, "requests": requests, "input_tokens_est": chars // 4, "seconds": time.time() - start}


def score(rows: List[Dict], predicted: Dict[str, List[str]], types: List[str]) -> Dict:
    per_type = {}
    TP = FP = FN = 0
    for t in types:
        tp = sum(1 for r in rows if t in r["labels"] and t in predicted.get(r["id"], []))
        fp = sum(1 for r in rows if t not in r["labels"] and t in predicted.get(r["id"], []))
        fn = sum(1 for r in rows if t in r["labels"] and t not in predicted.get(r["id"], []))
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        per_type[t] = {"support": tp + fn, "precision": p, "recall": rc, "f1": 2 * p * rc / (p + rc) if p + rc else 0.0}
        TP, FP, FN = TP + tp, FP + fp, FN + fn
    unmarked = [r for r in rows if not r["labels"]]
    return {"per_type": per_type,
            "micro_f1": 2 * TP / (2 * TP + FP + FN) if TP else 0.0,
            "macro_f1": sum(v["f1"] for v in per_type.values()) / len(types),
            "false_alarm_rate": sum(1 for r in unmarked if predicted.get(r["id"])) / len(unmarked) if unmarked else 0.0}


def _load_preds(path: Path) -> Optional[Dict[str, List[str]]]:
    if not path.exists():
        return None
    return {r["id"]: r["labels"] for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def main(use_llm: bool) -> None:
    types = load_types()
    rows = load("test_sample")
    finetuned = _load_preds(DIR / "pred_finetuned_test_sample.jsonl")
    llm_path, llm_meta = DIR / "pred_llm_test_sample.jsonl", DIR / "pred_llm_meta.json"
    if use_llm:
        run = llm_predict(rows, types)
        with llm_path.open("w", encoding="utf-8") as handle:
            for rid, labels in run["labels"].items():
                handle.write(json.dumps({"id": rid, "labels": labels}) + "\n")
        llm_meta.write_text(json.dumps({k: v for k, v in run.items() if k != "labels"}), encoding="utf-8")
    llm = _load_preds(llm_path)
    meta = json.loads(llm_meta.read_text(encoding="utf-8")) if llm_meta.exists() else {}

    # every fine-tuned model: the CPU run (3 epochs) and the Colab runs (colab/clause_finetune_colab.ipynb)
    systems = [("LLM (Gemini, zero-shot)", llm, {"cost": f"{meta['requests']} requests, ~{meta['input_tokens_est']:,} input tokens"
                                                 if meta else "", "speed": f"{1000 * meta['seconds'] / len(rows):.0f} ms (API)" if meta else ""})]
    cpu_meta_path = Path("models/clause_legalbert_3ep/config_extra.json")
    cpu_meta = json.loads(cpu_meta_path.read_text(encoding="utf-8")) if cpu_meta_path.exists() else {}
    systems.append(("Legal-BERT-small, 3 epochs (laptop CPU)", _load_preds(DIR / "pred_finetuned_3ep_test_sample.jsonl"),
                    {"cost": f"free; {cpu_meta.get('train_minutes', '?')} min training on CPU", "speed": "50 ms (CPU)"}))
    for meta_path in sorted(DIR.glob("meta_ft_*.json")):
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        systems.append((f"{m['model'].split('/')[-1]}, best of {m['epochs_run']} epochs (Colab {m['gpu'].split()[-1]})",
                        _load_preds(DIR / f"pred_ft_{m['name']}_test_sample.jsonl"),
                        {"cost": f"free; {m['train_minutes']} min training on GPU", "speed": f"{m['ms_per_passage_test_sample']} ms (GPU)"}))
    systems = [(name, preds, info) for name, preds, info in systems if preds]
    results = {name: score(rows, preds, list(types)) for name, preds, _ in systems}
    info = {name: i for name, _, i in systems}
    support = Counter(t for r in rows for t in r["labels"])
    lines = ["# Clause classification: LLM vs fine-tuned model (Day 4, Task 1)", "",
             f"Test passages: {len(rows)} from the 51 CUAD test contracts ({sum(1 for r in rows if not r['labels'])} "
             "sentences no lawyer marked, the rest marked with one or more of 28 clause types). The fine-tuned model "
             "never saw these contracts. `support` = marked test passages of that type: types with few passages "
             "have unreliable scores.", ""]
    if results:
        names = list(results)
        lines += ["| | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
        for label, key in (("Micro F1", "micro_f1"), ("Macro F1 (28 types)", "macro_f1"), ("False alarms on unmarked sentences", "false_alarm_rate")):
            fmt = (lambda v: f"{v:.0%}") if key == "false_alarm_rate" else (lambda v: f"{v:.2f}")
            lines.append(f"| {label} | " + " | ".join(fmt(results[n][key]) for n in names) + " |")
        lines.append("| Cost | " + " | ".join(info[n]["cost"] or "-" for n in names) + " |")
        lines.append("| Time per passage | " + " | ".join(info[n]["speed"] or "-" for n in names) + " |")
        lines += ["", "F1 per clause type:", "", "| Clause type | Support | " + " | ".join(names) + " |",
                  "|---|---:|" + "---:|" * len(names)]
        for t in types:
            lines.append(f"| {t} | {support[t]} | " + " | ".join(f"{results[n]['per_type'][t]['f1']:.2f}" for n in names) + " |")
    REPORT.write_text("\n".join(l for l in lines if l is not None) + "\n", encoding="utf-8")
    for name, r in results.items():
        print(f"{name:10} micro F1 {r['micro_f1']:.3f}  macro F1 {r['macro_f1']:.3f}  false alarms {r['false_alarm_rate']:.0%}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true")
    main(not parser.parse_args().no_llm)
