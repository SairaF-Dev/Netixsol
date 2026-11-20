"""
Day 4, Task 1 (small model): fine-tune Legal-BERT-small for CUAD clause classification.

* Model: nlpaueb/legal-bert-small-uncased (35M parameters, pre-trained on legal text), with a
  multi-label head: one yes/no output per clause type (a passage can have several types, or none).
* Training: train split (src/contracts/cuad_data.py), binary cross-entropy, AdamW lr 5e-5, batch 16,
  6 epochs (3 left validation F1 still rising: 0.60 -> 0.68), passages cut to 192 word pieces. Laptop CPU, ~3 hours.
* Threshold: one decision threshold for all types, chosen on the validation split (best micro F1).
* Output: predictions for test and test_sample in data/cuad_labels/pred_finetuned_<split>.jsonl
  and the model in models/clause_legalbert/ (not in git).

Run:  python -m src.contracts.finetune            (train + predict)
      python -m src.contracts.finetune --predict  (predict with the saved model)
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from src.contracts.cuad_data import DIR, load, load_types

MODEL_NAME = "nlpaueb/legal-bert-small-uncased"
OUT = Path("models/clause_legalbert")
MAX_LEN, BATCH, EPOCHS, LR, SEED = 192, 16, 6, 5e-5, 42


def _encode(tokenizer, rows: List[Dict], types: List[str]):
    enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt")
    y = torch.tensor([[1.0 if t in r["labels"] else 0.0 for t in types] for r in rows])
    return enc, y


def _batches(rows: List[Dict], shuffle: bool, rng: np.random.Generator):
    order = rng.permutation(len(rows)) if shuffle else np.arange(len(rows))
    for start in range(0, len(rows), BATCH):
        yield [rows[i] for i in order[start:start + BATCH]]


@torch.no_grad()
def probabilities(model, tokenizer, rows: List[Dict], types: List[str]) -> np.ndarray:
    model.eval()
    out = []
    for batch in _batches(rows, False, np.random.default_rng(0)):
        enc, _ = _encode(tokenizer, batch, types)
        out.append(torch.sigmoid(model(**enc).logits).numpy())
    return np.concatenate(out)


def _micro_f1(probs: np.ndarray, rows: List[Dict], types: List[str], threshold: float) -> float:
    gold = np.array([[t in r["labels"] for t in types] for r in rows])
    pred = probs >= threshold
    tp, fp, fn = (pred & gold).sum(), (pred & ~gold).sum(), (~pred & gold).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def train() -> None:
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    types = list(load_types())
    train_rows, val_rows = load("train"), load("val")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(types), problem_type="multi_label_classification")
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    steps = EPOCHS * ((len(train_rows) + BATCH - 1) // BATCH)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.06 * steps), steps)
    start, step = time.time(), 0
    for epoch in range(EPOCHS):
        model.train()
        for batch in _batches(train_rows, True, rng):
            enc, y = _encode(tokenizer, batch, types)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(**enc).logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step(); scheduler.step(); optimizer.zero_grad()
            step += 1
            if step % 100 == 0:
                print(f"epoch {epoch + 1} step {step}/{steps} loss {loss.item():.4f} ({(time.time() - start) / 60:.1f} min)", flush=True)
        val_probs = probabilities(model, tokenizer, val_rows, types)
        print(f"epoch {epoch + 1}: validation micro F1 at 0.5 = {_micro_f1(val_probs, val_rows, types, 0.5):.3f}", flush=True)
    threshold = max(np.arange(0.1, 0.91, 0.05), key=lambda t: _micro_f1(val_probs, val_rows, types, t))
    print(f"threshold {threshold:.2f}: validation micro F1 {_micro_f1(val_probs, val_rows, types, threshold):.3f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    (OUT / "config_extra.json").write_text(json.dumps({"types": types, "threshold": float(threshold),
                                                      "train_minutes": round((time.time() - start) / 60, 1)}), encoding="utf-8")


def predict() -> None:
    extra = json.loads((OUT / "config_extra.json").read_text(encoding="utf-8"))
    types, threshold = extra["types"], extra["threshold"]
    tokenizer = AutoTokenizer.from_pretrained(OUT)
    model = AutoModelForSequenceClassification.from_pretrained(OUT)
    for split in ("test", "test_sample"):
        rows = load(split)
        start = time.time()
        probs = probabilities(model, tokenizer, rows, types)
        seconds = time.time() - start
        with (DIR / f"pred_finetuned_{split}.jsonl").open("w", encoding="utf-8") as handle:
            for row, p in zip(rows, probs):
                handle.write(json.dumps({"id": row["id"], "labels": [t for t, v in zip(types, p) if v >= threshold]}) + "\n")
        print(f"{split}: {len(rows)} passages in {seconds:.0f}s ({1000 * seconds / len(rows):.0f} ms each, CPU)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predict", action="store_true")
    args = parser.parse_args()
    if not args.predict:
        train()
    predict()
