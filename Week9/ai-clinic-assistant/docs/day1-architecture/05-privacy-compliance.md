# Privacy & Compliance Design

## 1. Sensitive Data Classification
To ensure patient safety and legal compliance, data processed by the AI Clinic Assistant is categorized into distinct sensitivity levels.

### Personal Identifiable Information (PII)
- Name
- CNIC (Computerized National Identity Card) number
- Phone number
- Address
- Email

### Protected Health Information (PHI)
- Diagnosis
- Medications
- Lab results
- Allergies
- Visit history and clinical notes

### Data Classification Table
| Data Field | Sensitivity Level | Handling Rules |
| :--- | :--- | :--- |
| PII (Name, CNIC, Phone) | High / Critical | Encrypt at rest and in transit. Restrict access. Must be redacted before LLM processing. |
| PHI (Diagnosis, Meds) | High / Critical | Encrypt at rest and in transit. Access restricted to Doctors and specific system processes. |
| Symptoms (De-identified) | Medium | Can be passed to LLMs for triage/summary, provided PII is stripped. |
| Appointments (Time/Date) | Low | Visible to Receptionists, Patients, Doctors. |

## 2. PII Redaction Strategy (Microsoft Presidio)
To protect patient privacy, Microsoft Presidio is used to detect and anonymize PII before data is sent to external LLMs.

### Pipeline Integration
- **Presidio Analyzer** identifies entities like PERSON, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION. We will add custom recognizers for CNIC.
- **Presidio Anonymizer** replaces identified entities with placeholders (e.g., `<PERSON_1>`, `<PHONE_1>`).

### LLM Boundaries
- **Redacted BEFORE LLM:** Names, contact details, exact addresses, CNIC.
- **Preserved:** Symptoms, pain levels, duration, general medical context (essential for triage and summarization).

### Code-level Integration (Middleware)
A middleware layer intercepts outgoing prompts to the LLM and incoming responses.
1. Raw Input -> 2. Presidio Anonymizer -> 3. Redacted Input -> 4. LLM -> 5. Redacted Output -> 6. Re-identifier -> 7. Final Output

*Example:*
- **Raw Input:** "Hi, I am Ali and my phone number is 0300-1234567. I have a severe headache."
- **Redacted Input:** "Hi, I am <PERSON> and my phone number is <PHONE_NUMBER>. I have a severe headache."
- **LLM Processing:** Translates and structures the input.
- **Re-identified Output:** Mapped back if necessary (typically not needed for symptom extraction).

## 3. Role-Based Access Control (RBAC)

### Roles
1. **Patient:** Can see own data only, chat with agents, view appointments.
2. **Receptionist:** Can see patient demographics, appointments. No access to medical records.
3. **Doctor:** Full access to assigned patients, approval dashboard, prescriptions.

### Permission Matrix
| Resource | Patient | Receptionist | Doctor |
| :--- | :--- | :--- | :--- |
| Own Demographics | Read/Write | Read | Read |
| Other Demographics | None | Read | Read |
| Own Appointments | Read/Write | Read/Write | Read |
| Clinical Summaries | None | None | Read/Write/Approve |
| Prescriptions | Read | None | Read/Write/Approve |
| LLM Chat (Intake) | Write | None | None |

## 4. Audit Log Design
Comprehensive logging is required for compliance and security monitoring.

### Logged Events
- Data access (Read) of any PHI/PII.
- Agent actions (Intake complete, Triage assigned, Schedule booked).
- Approvals/Rejections by doctors (e.g., approving a SOAP note).
- System errors and authentication events.

### Log Schema
```json
{
  "timestamp": "2023-11-01T10:15:30Z",
  "user_id": "doc_123",
  "role": "Doctor",
  "action": "APPROVE_SUMMARY",
  "resource": "ClinicalSummary",
  "patient_id": "pat_456",
  "agent_id": "clinical_summary_agent",
  "details": "Approved SOAP note with minor edits.",
  "ip_address": "192.168.1.50"
}
```

### Storage and Retention
- Logs stored in a secure, append-only database table.
- Retained for a minimum of 5 years.
- Easily queryable via secure admin dashboard for compliance reporting.

## 5. Data Retention & Consent

### Patient Consent (UrduLish)
Shown at first interaction:
*"Assalam o Alaikum! City Care Clinic mein khush amdeed. Hum aapki behtar rehnumai ke liye AI assistant ka istemal kar rahe hain. Aapki maloomat mehfooz rakhi jayengi aur sirf doctor ke sath share ki jayengi. Kya hum shuru karein? (Type 'Yes' or 'Haan' to agree)"*

### Retention Policy
- Medical records: Retained indefinitely unless deletion requested (subject to legal requirements).
- Chat transcripts: Retained for 1 year, then summarized and deleted.

### Right to Deletion
Patients can request deletion of their data (excluding legally required records like past prescriptions).

### Data Minimization
Agents will only ask for information strictly necessary for triage and scheduling.

## 6. Agent Persona & System Prompts

### Patient-facing Persona Guidelines
- **Tone:** Warm, respectful, patient, simple UrduLish.
- **Safety:** Never alarming, never casual about symptoms.
- **Professionalism:** Always professional, always empathetic.
- **Cultural Sensitivity:** Use Islamic greetings (Assalam o Alaikum, Allah Hafiz). Use respectful address (Sahib, Sahiba, Bhai, Baji/Sister).

### Master System Prompt Template
```text
You are the AI Assistant for City Care Clinics. You interact with patients to gather symptoms and help them.
You MUST follow these rules:
1. LANGUAGE: Communicate in 'UrduLish' (Roman Urdu mixed with English). Keep it simple and easy to understand.
2. TONE & PERSONA: Be warm, respectful, and patient. Start with "Assalam o Alaikum". Use terms like "Sahib", "Sahiba", "Bhai", or "Baji" when appropriate.
3. SAFETY BOUNDARIES: NEVER diagnose a condition. NEVER prescribe medication. If a user asks for a diagnosis, politely state that only a doctor can diagnose, and you are here to gather information to help the doctor.
4. PRIVACY: Do not ask for unnecessary personal details. Reassure the patient that their data is secure and confidential.
5. EMPATHY: Acknowledge the patient's discomfort but do not cause alarm. Do not be casual about severe symptoms.
```

## 7. Compliance Framework

### Safeguards (HIPAA-inspired)
While HIPAA is not strictly enforced in Pakistan, we adhere to its best practices to ensure global standards of data protection.

### Encryption
- **At Rest:** AES-256 encryption for PostgreSQL and ChromaDB databases.
- **In Transit:** TLS 1.3 for all API and web traffic.

### Minimum Necessary Principle
Agents and staff are only given the minimum data required to perform their specific tasks (enforced via RBAC and Presidio redaction).

### Breach Notification Plan
1. **Identification:** Automated alerts on unauthorized access or mass data export.
2. **Containment:** Immediately revoke access and isolate affected systems.
3. **Assessment:** Security team evaluates the scope of the breach.
4. **Notification:** Affected patients and relevant authorities notified within 72 hours, detailing what data was exposed and steps taken.
