"""
Writes colab/clause_finetune_colab.ipynb and data/cuad_labels/cuad_clauses_for_colab.zip (the notebook's input).

Run:  python colab/make_clause_notebook.py
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text})


md("""# Day 4, Task 1: fine-tune clause classifiers on CUAD (Colab GPU)

Trains three small models on the CUAD clause dataset built by `python -m src.contracts.cuad_data`
(28 clause types, multi-label, split by contract) and predicts the test set.

1. **Runtime > Change runtime type > T4 GPU**, then run the cells in order.
2. When asked, upload `cuad_clauses_for_colab.zip` (in the project's `data/cuad_labels/`).
3. Download `colab_clause_results.zip` at the end and unzip it into the project's `data/cuad_labels/`.
4. Locally: `python -m evaluations.clause_classification --no-llm` (or without `--no-llm` once the LLM has run)
   compares the LLM with every model.

Each model keeps the epoch with the best validation micro F1, and one decision threshold tuned on validation.
The test contracts are never used for any choice.""")
code("""!nvidia-smi --query-gpu=name,memory.total --format=csv
import torch
print("GPU available:", torch.cuda.is_available())""")
code("""from google.colab import files
import os, zipfile
uploaded = files.upload()          # choose cuad_clauses_for_colab.zip
zipfile.ZipFile(next(iter(uploaded))).extractall("data")
print(sorted(os.listdir("data")))""")
code('''import copy, json, time
import numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

def load(split):
    return [json.loads(line) for line in open(f"data/clauses_{split}.jsonl", encoding="utf-8")]

TYPES = list(json.load(open("data/clause_types.json", encoding="utf-8")))
train_rows, val_rows, test_rows, sample_rows = load("train"), load("val"), load("test"), load("test_sample")
print(len(train_rows), len(val_rows), len(test_rows), len(sample_rows), "examples;", len(TYPES), "clause types")
device = "cuda" if torch.cuda.is_available() else "cpu"
os.makedirs("out", exist_ok=True)


def micro_f1(probs, rows, threshold):
    gold = np.array([[t in r["labels"] for t in TYPES] for r in rows])
    pred = probs >= threshold
    tp, fp, fn = (pred & gold).sum(), (pred & ~gold).sum(), (~pred & gold).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


@torch.no_grad()
def probabilities(model, tok, rows, max_len, batch=64):
    model.eval()
    out = []
    for i in range(0, len(rows), batch):
        enc = tok([r["text"] for r in rows[i:i + batch]], truncation=True, max_length=max_len,
                  padding=True, return_tensors="pt").to(device)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
            out.append(torch.sigmoid(model(**enc).logits.float()).cpu().numpy())
    return np.concatenate(out)


def train(name, model_name, epochs, lr, batch=16, max_len=256, seed=42):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=len(TYPES), problem_type="multi_label_classification",
        id2label=dict(enumerate(TYPES)), label2id={t: i for i, t in enumerate(TYPES)},
        ignore_mismatched_sizes=True, dtype=torch.float32).to(device)   # DeBERTa-v3 is stored in FP16
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * ((len(train_rows) + batch - 1) // batch)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")
    best_f1, best_state, best_epoch, history, start = -1.0, None, 0, [], time.time()
    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(train_rows))
        for i in range(0, len(order), batch):
            rows = [train_rows[j] for j in order[i:i + batch]]
            enc = tok([r["text"] for r in rows], truncation=True, max_length=max_len,
                      padding=True, return_tensors="pt").to(device)
            y = torch.tensor([[1.0 if t in r["labels"] else 0.0 for t in TYPES] for r in rows], device=device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                logits = model(**enc).logits
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits.float(), y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
        val_probs = probabilities(model, tok, val_rows, max_len)
        f1 = max(micro_f1(val_probs, val_rows, t) for t in np.arange(0.1, 0.91, 0.05))
        history.append(round(float(f1), 4))
        print(f"{name} epoch {epoch + 1}: validation micro F1 {f1:.3f} ({(time.time() - start) / 60:.1f} min)")
        if f1 > best_f1:
            best_f1, best_state, best_epoch = f1, copy.deepcopy(model.state_dict()), epoch + 1
    model.load_state_dict(best_state)
    val_probs = probabilities(model, tok, val_rows, max_len)
    threshold = float(max(np.arange(0.1, 0.91, 0.05), key=lambda t: micro_f1(val_probs, val_rows, t)))
    meta = {"name": name, "model": model_name, "epochs_run": epochs, "best_epoch": best_epoch, "lr": lr,
            "max_len": max_len, "threshold": round(threshold, 2),
            "val_micro_f1": round(float(micro_f1(val_probs, val_rows, threshold)), 4), "val_history": history,
            "train_minutes": round((time.time() - start) / 60, 1),
            "gpu": torch.cuda.get_device_name(0) if device == "cuda" else "cpu"}
    for split, rows in (("test", test_rows), ("test_sample", sample_rows)):
        t0 = time.time()
        probs = probabilities(model, tok, rows, max_len)
        meta[f"ms_per_passage_{split}"] = round(1000 * (time.time() - t0) / len(rows), 1)
        with open(f"out/pred_ft_{name}_{split}.jsonl", "w", encoding="utf-8") as f:
            for r, p in zip(rows, probs):
                f.write(json.dumps({"id": r["id"], "labels": [t for t, v in zip(TYPES, p) if v >= threshold]}) + "\\n")
    json.dump(meta, open(f"out/meta_ft_{name}.json", "w"), indent=1)
    print(meta)
    del model
    torch.cuda.empty_cache()''')
md("Three models, about 10-30 minutes in total on a T4. Each cell can be run on its own.")
code('train("legalbert_small", "nlpaueb/legal-bert-small-uncased", epochs=8, lr=5e-5)')
code('train("legalbert_base", "nlpaueb/legal-bert-base-uncased", epochs=5, lr=3e-5)')
code('train("deberta_v3_base", "microsoft/deberta-v3-base", epochs=5, lr=2e-5)')
code("""import shutil
shutil.make_archive("colab_clause_results", "zip", "out")
files.download("colab_clause_results.zip")""")

notebook = {"cells": cells, "nbformat": 4, "nbformat_minor": 0,
            "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                         "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}}
(ROOT / "colab" / "clause_finetune_colab.ipynb").write_text(json.dumps(notebook, indent=1), encoding="utf-8")

data = ROOT / "data" / "cuad_labels"
with zipfile.ZipFile(data / "cuad_clauses_for_colab.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for name in ("clauses_train.jsonl", "clauses_val.jsonl", "clauses_test.jsonl", "clauses_test_sample.jsonl", "clause_types.json"):
        z.write(data / name, name)
print("wrote colab/clause_finetune_colab.ipynb and", data / "cuad_clauses_for_colab.zip",
      (data / "cuad_clauses_for_colab.zip").stat().st_size // 1024, "KB")
