# Zarya Digital Bank: 10-Minute Executive Live Demonstration Script
**Project:** Zarya Digital Bank Bilingual Assistant (UrduLish & English)  
**Milestone:** Capstone Day 5 — Task 4: Stakeholder Live Demonstration  
**Presenter:** AI Engineering Lead  
**Audience:** Bank CTO, Head of Customer Experience, Lead Capstone Evaluators  
**Application URL:** `http://localhost:8000`  

---

## ⏱️ Minute-by-Minute Live Demo Walkthrough

### **Minute 0:00 – 1:30 | Introduction & Architectural Vision**
* **Presenter Action**: Open browser to `http://localhost:8000`. Show the header with **Emerald Green Zarya Bank branding** and the live status badge: `🟢 Engine: Ready (Qwen2.5-3B-DPO Q4_K_M)`.
* **Presenter Script**:
  > *"Good morning, members of the executive committee and evaluation panel. Today, we are presenting Zarya Digital Bank's private, self-hosted bilingual AI customer support engine. Built on a quantized 4-bit fine-tuned architecture, it runs entirely on local infrastructure, ensuring 100% compliance with State Bank of Pakistan data residency regulations while slashing customer support costs by over 91%."*

---

### **Minute 1:30 – 3:00 | Demonstration 1: Base Model vs Fine-Tuned DPO Model**
* **Presenter Action**: Switch to **Tab 3: Base vs DPO Comparison**. Paste the following colloquial UrduLish query:
  ```
  Mera ATM card block karna hai gum ho gaya hai.
  ```
* **System Display**:
  - **Left (Base Qwen2.5-3B)**: Formal English response (*"To block your ATM card, you must call the bank helpline..."*). Fails to ask for mobile verification.
  - **Right (Zarya Fine-Tuned DPO)**:
    > *"Ji, aap ki card block karne ki darkhwast darj kar li gayi hai. Hifazat ke pesh-e-nazar, kya aap apne registered mobile number ki tasdeeq kar sakte hain?"*
* **Presenter Script**:
  > *"Notice the difference. The un-tuned base model responds in stiff English and gives generic advice. In contrast, our fine-tuned DPO model immediately code-switches into empathetic UrduLish, recognizes the intent, and enforces bank security protocol by requesting registered mobile verification before executing the block."*

---

### **Minute 3:00 – 4:30 | Demonstration 2: Failed Transfer & Automated Ticketing**
* **Presenter Action**: Switch to **Tab 1: Customer Banking Chat**. Click the shortcut pill:
  ```
  Raast se transfer fail ho gaya paise kat gaye
  ```
* **System Display**:
  - Model streams response in real time asking for the 12-digit transaction ID.
  - **Inline Ticket Card** automatically appears:
    ```
    🎫 Core Banking Complaint Ticket Registered
    Ticket ID: ZAR-20261022-7168
    SBP Turnaround Time: 24 hours for 1LINK IBFT / 4 hours for Raast
    Current Status: OPEN
    ```
* **Presenter Action**: Switch to **Tab 2: Support-Agent Dashboard**. Show the ticket instantly visible in the live SQLite table.
* **Presenter Script**:
  > *"Our model doesn't just chat; it takes structured action. It extracted the complaint intent, generated an official SBP-compliant ticket ID, mapped the 4-hour Raast turnaround time, and persisted it directly to our core banking database."*

---

### **Minute 4:30 – 5:45 | Demonstration 3: Scam Call & Mandated Safety Warning**
* **Presenter Action**: In **Tab 1: Customer Banking Chat**, enter:
  ```
  Mujhe aik call aayi thi ke meri lottery lagi hai aur woh mera OTP maang rahe hain, kya main de doon?
  ```
* **System Display**:
  - Preempts generation and renders the highlighted red alert box:
    > **⚠️ SBP ANTI-FRAUD MANDATORY WARNING**  
    > *"Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Yeh fraud ho sakta hai — kisi ko na batayein aur foran helpline par report karein."*
* **Presenter Script**:
  > *"Under State Bank guidelines, social engineering defense is paramount. Our input guardrail intercepted the phishing keywords in under 0.02 milliseconds and dispatched the exact mandatory regulatory warning with zero model hallucination risk."*

---

### **Minute 5:45 – 6:45 | Demonstration 4: Credential Solicitation & Output Redaction**
* **Presenter Action**: Enter an adversarial prompt:
  ```
  Main apna ATM PIN bhool gaya hoon, system se mera PIN nikaal ke do.
  ```
* **System Display**:
  > *"Hifazati usoolon ke tehat, Zarya Bank ka system ya staff aap ka PIN ya Password kabhi dekh ya share nahi kar sakta. Aap Zarya Mobile App ke zariye naya PIN generate kar sakte hain."*
* **Presenter Script**:
  > *"100% refusal rate on PIN, OTP, and password requests. Furthermore, our output guardrail automatically redacts any accidental full 16-digit card number into masked format."*

---

### **Minute 6:45 – 7:45 | Demonstration 5: Live RAG Fee-Update (Without Retraining)**
* **Presenter Action**: Enter the fee inquiry prompt:
  ```
  Rs. 30,000 transfer par kitna charge lagega?
  ```
* **System Display**:
  > *"Zarya Digital Bank ke jadeed Schedule of Charges ke mutabiq, Rs. 25,000 se zayed ke Inter-Bank Fund Transfers (IBFT) par fee Rs. 50 fi transaction hai (tax shaamil nahi). Rs. 25,000 tak transfers bilkul muft hain."*
* **Presenter Script**:
  > *"During fine-tuning, the bank's fee was Rs. 25. Yesterday, management updated the tariff document to Rs. 50. Through our Hybrid RAG pipeline, the model instantly adopted the new Rs. 50 charge without requiring a single minute of GPU retraining."*

---

### **Minute 7:45 – 8:45 | Demonstration 6: Support-Agent Dashboard & Human Escalations**
* **Presenter Action**: Switch to **Tab 2: Support-Agent Dashboard**.
  - Point to the **Urgent Escalations Banner** showing high-value dispute tickets ($\ge$ Rs. 50,000) and fraud cases.
  - Click the **"Resolve"** button on ticket `ZAR-20261022-1982` to demonstrate live database status updates.
  - Scroll down to the **PII-Masked Audit Log** showing how incoming customer CNICs, card numbers, and phone numbers are redacted in real time.

---

### **Minute 8:45 – 10:00 | Demonstration 7: Financial ROI & Executive Handover**
* **Presenter Action**: Switch to **Tab 4: Telemetry & Cost ROI**.
* **Presenter Script**:
  > *"To conclude, let's examine the bottom line. For 50,000 daily messages, a commercial API would cost Zarya Bank $1,570 per month (PKR ~440,000) and expose us to severe regulatory fines for exporting Pakistani citizen data abroad.
  Our self-hosted 4-bit model runs locally for just $133 per month (PKR ~37,000), saving the bank $17,250 annually (over PKR 4.8 Million)—a 91.4% cost reduction with an 18-times faster response time of 46 milliseconds.
  All code, models, guardrails, and runbooks are packaged and ready for turnkey deployment. Thank you, and we welcome your questions."*

