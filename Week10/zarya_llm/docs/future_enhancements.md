# Zarya Digital Bank: Strategic Future Enhancements & AI Roadmap
**Project:** Zarya Digital Bank Bilingual Assistant (UrduLish & English)  
**Milestone:** Capstone Day 5 — Task 5: Strategic Product & Technical Roadmap  
**Target Horizon:** 2026 – 2028  

---

## 1. Executive Vision: Universal Banking Inclusion

Having demonstrated production-level accuracy (94.5%), SBP compliance (100%), and a 91.4% cost reduction with the **Zarya-Qwen2.5-3B-DPO** model, this roadmap defines the next strategic horizons to scale AI capabilities across Pakistan's unbanked and underserved populations.

---

## 2. Core Strategic Enhancements

### 2.1 Native Urdu-Script & Speech-to-Speech (Voice IVR)
* **Objective:** Enable semi-literate and rural retail banking customers who cannot read or type Roman Urdu to conduct banking inquiries via voice phone calls.
* **Architecture:**
  - **Speech-to-Text (ASR):** Fine-tuned Whisper-Large-v3 on Pakistani accented English, Roman Urdu, and conversational Urdu speech.
  - **Text-to-Speech (TTS):** Natural, low-latency neural TTS (VITS or FastSpeech2) synthesizing warm, respectful Pakistani Urdu speech (*"Ji, Zarya Bank mein aap ka khushamdeed"*).
  - **IVR Telephony Integration:** SIP/RTP bridge connecting Asterisk/FreeSWITCH PBX directly to the serving engine for automated call center handling.

### 2.2 Model Distillation for Edge & Offline Mobile Deployment
* **Objective:** Run the assistant directly on low-cost Android smartphones without requiring active 4G data or internet connectivity.
* **Architecture:**
  - Knowledge distillation of `Zarya-Qwen2.5-3B` teacher weights into a **0.5B compact student model** (e.g., `Qwen2.5-0.5B-Instruct`).
  - INT4 quantization for mobile ONNX Runtime / MediaPipe / llama.cpp Android NDK bindings, requiring $< 350$ MB RAM.

### 2.3 Core Banking API Function-Calling & Transaction Execution
* **Objective:** Empower the assistant to execute authorized customer actions beyond informational queries.
* **Architecture:**
  - Standard JSON schema tool calling (Function Calling) connecting to Core Banking APIs (e.g., Temenos T24 / Oracle FLEXCUBE):
    * `check_account_balance(account_id, biometric_token)`
    * `temporarily_block_card(card_pan_token, reason)`
    * `initiate_raast_p2p(recipient_iban, amount, otp_auth_token)`
  - Out-of-band 2FA confirmation via Push Notification / SMS OTP before executing any financial ledger mutation.

### 2.4 Regional Language Expansion (Sindhi, Pashto, Punjabi, Balochi)
* **Objective:** Expand financial inclusion across provincial populations by supporting Pakistan's primary regional languages.
* **Architecture:**
  - Tokenizer vocabulary adaptation with regional scripts (Perso-Arabic Sindhi and Pashto).
  - Synthetic corpus generation for regional banking terminology (e.g. Sindhi: *"منهنجو اي ٽي ايم ڪارڊ بلاڪ ڪريو"*).

### 2.5 Active Continuous DPO from Live Customer Feedback
* **Objective:** Fully automate the active learning loop so the model adapts to emerging colloquial slang and query patterns weekly.
* **Architecture:**
  - Automated weekly cronjob parsing `data/feedback.jsonl`.
  - Automated LoRA fine-tuning on new batches of $\ge 250$ preference pairs.
  - Automated canary deployment with regression test gates.

### 2.6 Cross-Conversation Fraud & Social Engineering Pattern Detection
* **Objective:** Detect organized syndicate phishing and SIM-swap fraud rings operating across multiple customer accounts simultaneously.
* **Architecture:**
  - Graph Neural Network (GNN) and embedding cluster analysis over sanitized query embeddings.
  - Detects if 50 different accounts suddenly ask about identical scam transfer beneficiaries within a 2-hour window, automatically triggering bank-wide transaction freezes.

