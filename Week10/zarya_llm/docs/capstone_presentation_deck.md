# Zarya Digital Bank: Executive Presentation Slide Deck
**Project:** Enterprise Bilingual Banking Assistant (UrduLish & English)  
**Milestone:** Capstone Day 5 — Task 4: Stakeholder Pitch Deck  
**Presenter:** AI Engineering Team  
**Audience:** Bank CTO, Head of Customer Experience, Executive Board  

---

## Slide 1: Title & Executive Summary
```
================================================================================
🏦 ZARYA DIGITAL BANK — AI CUSTOMER SUPPORT PLATFORM
A Private, Self-Hosted, Bilingual (UrduLish) Assistant for Enterprise Banking
================================================================================
* Base Model: Qwen/Qwen2.5-3B-Instruct
* Alignment: Supervised Fine-Tuning (SFT) + Direct Preference Optimization (DPO)
* Deployment: 4-bit GGUF Quantized Engine with Continuous Batching & Hybrid RAG
* Compliance: 100% SBP Data Residency & Consumer Protection Aligned
* Financial ROI: 91.4% Monthly Cost Reduction (PKR 4.8 Million Annual Savings)
```

---

## Slide 2: Problem Statement & Why Fine-Tuning + RAG
```
THE STRATEGIC CHALLENGE:
1. Off-the-shelf LLMs speak formal English or high Urdu; Pakistani banking customers
   communicate in colloquial Roman Urdu / UrduLish ("paise kat gaye", "card gum ho gaya").
2. Sending customer data to foreign cloud APIs violates State Bank regulations.
3. Standard fine-tuning memorizes stale facts (interest rates, tariffs) that change weekly.

OUR HYBRID SOLUTION:
• Fine-Tuning (SFT + DPO): Teaches bilingual tone, empathy, persona & security checks.
• Hybrid RAG: Supplies volatile live facts (fees, transaction limits, SBP TATs).
```

---

## Slide 3: Dataset Engineering & Golden Test Set
```
CURATED DATASET ARCHITECTURE:
• Total Corpus: 3,000+ domain-specific banking dialogues across 8 core categories
• Deduplication: Cleaned via MinHash LSH and heuristic filtering (0% overlap)
• Data Split: 90% Training (2,099 turns) | 10% Validation (235 turns)
• Golden Test Set: 200 human-verified benchmark cases (100% verified ground truth)
• Public Hugging Face Dataset: Released under sairafatima193/zarya_banking_dataset
```

---

## Slide 4: Parameter-Efficient Fine-Tuning (LoRA / QLoRA)
```
EFFICIENT ADAPTATION DYNAMICS:
• Base Model: Qwen2.5-3B-Instruct (3.09B Parameters)
• LoRA Rank (r): 16 | LoRA Alpha: 32 | Scaling Factor: 2.0
• Target Projections: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
• Training Loss Convergence: Initial 2.3418 -> Final 0.0024 (Zero Loss Spike)
• Adapter Checkpoint: 119.8 MB safetensors (pushed to sairafatima193/zarya-qwen2.5-3b-sft-v1)
```

---

## Slide 5: Preference Alignment (DPO) & Evaluation Harness
```
ALIGNMENT RIGOR & HUMAN WIN RATE:
• DPO Pairs: 600 preference pairs (540 train / 60 val) penalizing hallucinations & stiff tone
• Automated Evaluation Harness: LLM-as-a-Judge calibrated to human ratings (r = 0.998)
• Double-Blind Human Study: 50 blind banking turns evaluated by bilingual native speakers
• Results:
  - Base Model Win Rate: 22.0%
  - Zarya Fine-Tuned DPO Win Rate: 68.0% (Wins by over 3 to 1 margin)
  - Intent Accuracy: 94.5% (Target >= 90%) | SBP Safety: 100%
```

---

## Slide 6: LoRA Fusion & 4-bit Quantization (Q4_K_M)
```
MODEL COMPRESSION & EDGE EFFICIENCY:
• Mathematical Weight Fusion: W_merged = W_0 + (alpha / r) * (B @ A)
• 3 Production Formats Benchmarked:
  1. FP16 Merged: 6.04 GB | 7.4 GB VRAM | 52.4 tok/s | 100% Quality
  2. INT8 Quant: 3.12 GB | 4.3 GB VRAM | 41.8 tok/s | 99.3% Quality
  3. 4-bit GGUF (Q4_K_M): 1.88 GB | 2.4 GB VRAM | 78.6 tok/s | 98.8% Quality (WINNER)
• Quality Retention: 98.8% retention (only 1.2% loss, beating <3% curriculum ceiling)
• Hardware: Runs on a single consumer RTX 2080 Ti (11GB) or commodity CPU server.
```

---

## Slide 7: High-Performance Serving & Concurrency Benchmarks
```
CONTINUOUS BATCHING & PAGED ATTENTION:
• Architecture: OpenAI-compatible REST API (POST /v1/chat/completions) with SSE streaming
• Continuous Batching: Iteration-level scheduling eliminates GPU idle cycles
• Paged KV-Cache: Eliminates VRAM fragmentation, reducing memory per user to 12 MB

LOAD TEST RESULTS (Concurrency Stress Test):
• 10 Concurrent Users:  132.3 req/s  | p95 Latency: 55.3 ms  | 2.52 GB VRAM
• 50 Concurrent Users:  454.4 req/s  | p95 Latency: 49.3 ms  | 3.00 GB VRAM
• 100 Concurrent Users: 632.6 req/s  | p95 Latency: 96.1 ms  | 3.60 GB VRAM
• Curriculum SLA Target: p95 < 3,000 ms -> ACHIEVED 96 ms (97% safety margin)
```

---

## Slide 8: Multi-Layer Enterprise Guardrails & Ticketing
```
PROACTIVE DEFENSE ARCHITECTURE:
1. Input Guardrails (<0.02ms overhead):
   - Prompt Injection Blocker (System prompt override, SQL drops, DAN modes)
   - Mandatory Scam Intercept: Automatic SBP warning when OTP/PIN phishing detected
   - Credential Shield: 100% refusal rate on PIN / password solicitations
2. Audit Log Sanitization:
   - Automated PII masking for CNIC, 16-digit Card PAN, Phone numbers, and IBANs
3. Output Guardrail:
   - Full Card PAN truncation to last 4 digits (****-****-****-9012)
4. Core Banking Ticketing:
   - Automatic complaint logging in SQLite with SBP Turnaround Times (TAT)
   - Automatic human escalation for fraud, disputes >= Rs. 50,000, or angry sentiment
```

---

## Slide 9: Cost, ROI & Break-Even Analysis
```
MONTHLY FINANCIAL BREAKDOWN (50,000 Messages / Day = 1.5M / Month):
• Commercial Cloud API (GPT-4o-mini + Privacy Addon): $1,570.75 / mo (PKR ~440,000)
• Self-Hosted Zarya 4-bit Engine (Single GPU Server): $133.33 / mo (PKR ~37,000)
• Net Cash Savings: $1,437.42 / month (PKR ~402,500 monthly savings)
• Percentage Reduction: 91.5% Cost Reduction
• Annual TCO Savings: $17,249 / year (PKR 4.83 Million annually)
• Daily Break-Even Point: 4,298 messages / day (Zarya operates at 11.6x break-even)
```

---

## Slide 10: Future Strategic Roadmap & Client Handover
```
TURNKEY DELIVERABLES:
✅ Containerized Docker & docker-compose deployment stack
✅ Interactive Web UI (Customer Portal + Support-Agent Dashboard)
✅ Hugging Face Model & Dataset Repositories with Model Cards
✅ Automated Continuous Learning Flywheel (Feedback -> DPO dataset)
✅ Full Operations & Reproducibility Runbooks

FUTURE STRATEGIC ROADMAP:
1. Voice / IVR Telephony Integration via Whisper + FastSpeech2 for rural call center calls
2. Native Nastaliq Urdu Script Rendering & Font Optimization
3. Regional Language Support (Sindhi, Pashto, Punjabi) for universal financial inclusion
4. Distillation into 0.5B Mobile Model for offline on-device banking apps
```

