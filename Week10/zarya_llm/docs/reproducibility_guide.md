# Zarya Digital Bank: End-to-End Training & Evaluation Reproducibility Guide
**Project:** Zarya Digital Bank Bilingual Assistant (UrduLish & English)  
**Milestone:** Capstone Day 5 — Task 5: Engineering Handover & Reproducibility  
**Date:** October 2026  

---

## 1. System Requirements & Environment Setup

### Recommended Hardware
* **Fine-Tuning (SFT & DPO):** NVIDIA GPU with $\ge 8$ GB VRAM (RTX 2080 Ti, RTX 3060, or Google Colab T4).
* **Serving & Inference:** Single CPU (4 cores, 8GB RAM) or any entry-level consumer GPU (2.4 GB VRAM for 4-bit GGUF).

### Environment Installation
```bash
# Clone the repository
git clone https://github.com/sairafatima193/zarya_banking_llm.git
cd zarya_banking_llm

# Create and activate Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install fastapi uvicorn httpx
```

---

## 2. Step-by-Step Pipeline Reproduction

### Day 1: Dataset Generation, Cleaning & Splitting
```bash
# 1. Synthesize raw banking dialogues using Gemini Flash-Lite teacher model
python src/generate.py

# 2. Clean, deduplicate (MinHash LSH) and validate JSON schemas
python src/clean.py

# 3. Create stratified splits (90% Train, 10% Validation, 200 Golden Test)
python src/split.py

# 4. (Optional) Publish dataset to Hugging Face Hub
python src/upload_to_hf.py --repo-id sairafatima193/zarya_banking_dataset --token <HF_TOKEN>
```

### Day 2: Baseline Evaluations & SFT Fine-Tuning
```bash
# 1. Evaluate Zero-Shot & Few-Shot baselines on Golden Test Set
python src/evaluate_baselines.py

# 2. Run LoRA Supervised Fine-Tuning (SFT)
# Can be run via notebook notebooks/train_sft.ipynb or python script:
python src/train_sft.py --model_name Qwen/Qwen2.5-3B-Instruct --epochs 3 --lr 2e-4

# 3. Benchmark SFT adapter checkpoint against baselines
python src/evaluate_sft.py
```

### Day 3: DPO Alignment & Evaluation Harness
```bash
# 1. Generate 600 DPO preference pairs (540 train / 60 val)
python src/create_preference_data.py

# 2. Run Direct Preference Optimization (DPO)
# Can be executed via notebook notebooks/train_dpo.ipynb:
python src/train_dpo.py --beta 0.1 --lr 5e-5

# 3. Run LLM-as-a-Judge and Double-Blind Human Study Evaluation Harness
python src/eval_harness.py
python src/human_eval.py
```

### Day 4: Merge, Quantize, Serving API & Guardrails
```bash
# 1. Merge LoRA weights into base model and benchmark FP16, INT8, and 4-bit GGUF
python src/merge_and_quantize.py --export-format all

# 2. Run Concurrent Serving Load Test (10, 50, 100 concurrent users)
python src/load_test.py

# 3. Execute Live Fee-Change RAG Experiment (Rs. 25 -> Rs. 50 without retraining)
python src/hybrid_rag.py

# 4. Verify 5 Canonical Guardrail Scenarios (<0.02ms overhead)
python src/guardrails.py

# 5. Verify Core Banking Ticketing and Database Operations
python src/ticketing.py
```

### Day 5: Production Deployment & Telemetry
```bash
# 1. Launch Unified Serving API & Interactive Web UI
python src/serve_api.py
# Open browser at: http://localhost:8000

# 2. Test Feedback Flywheel (turns thumbs-down into new DPO pairs)
python src/feedback_pipeline.py

# 3. Stage and Upload Final Production Model to Hugging Face
python src/upload_final_model.py --dry-run
python src/upload_final_model.py --token <HF_TOKEN>
```

