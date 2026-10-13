# MedCare Clinic — Role-Based User Guides & Operations Manuals

Welcome to the comprehensive user guide collection for **MedCare Clinic (City Care Clinics Ambulatory EHR)**. This documentation provides step-by-step operating manuals for each user persona interacting with the multi-agent AI clinic platform.

---

## 👥 Personas & Quick Jump Directory

| Guide | Target Persona | Primary Route | Mission & Key Features |
| :--- | :--- | :--- | :--- |
| **[1. Patient Portal Guide](01-patient-portal-guide.md)** | Patients & Family Members | `/#/assistant`<br>`/#/portal` | Bilingual conversational UrduLish AI intake, 5-stage progress indicator, red-flag emergency bypass (1122), appointment booking, and lab report explanations. |
| **[2. Doctor Workspace Guide](02-doctor-clinical-workspace-guide.md)** | Attending Physicians & Specialists | `/#/doctor`<br>`/#/doctor/approvals` | Split-screen queue, allergy contraindication banners, automated SOAP consultation notes, and Human-in-the-Loop (HITL) approvals for prescriptions and lab reports. |
| **[3. Receptionist Command Center Guide](03-receptionist-command-center-guide.md)** | Front Desk Lead & Clinic Coordinators | `/#/receptionist` | High-density real-time patient live feed, triage urgency tags, walk-in registration, and live **Manual Chat Takeover / Intercept** override. |
| **[4. Care Coordinator Hub Guide](04-care-coordinator-hub-guide.md)** | Care Reminders Lead & Community Outreach | `/#/reminders` | Medication adherence tracking (Panadol, Augmentin), pre-draw lab fasting alerts, omnichannel batch dispatch (Resend Email API + WhatsApp), and Early Warning Safety Net escalations. |

---

## 🔑 Fast Access Credentials & Workstations

All accounts are pre-configured in the platform's SQLite database for immediate demonstration:

| Role | Username | Password | Full Name / Profile | Clinic Branch |
| :--- | :--- | :--- | :--- | :--- |
| **Patient** | `ahmed` | `password123` | **Ahmed Khan** (MRN: `PAT-1001`, Age 38, Hypertension, Penicillin Allergy) | DHA Phase 5, Lahore |
| **Doctor** | `dr.bilal` | `password123` | **Dr. Bilal Ahmed**, MBBS, FCPS (ID: `DOC-101`, General Medicine) | DHA Phase 5, Lahore |
| **Receptionist** | `receptionist` | `password123` | **Sana Front Desk** (ID: `REC-001`, Front Desk Operations Lead) | DHA Phase 5, Lahore |
| **Care Lead** | `coordinator` | `password123` | **Farhan Ali** (ID: `FLD-001`, Care Reminder Coordinator) | DHA Phase 5, Lahore |
| **Clinic Admin** | `admin` | `password123` | **Clinic Administrator** (Observability, LangGraph Topology, Audit Trail) | Enterprise Central |

---

## 🛡️ Core Clinical Principles

Across all user guides, MedCare Clinic strictly maintains two foundational axioms:

1. **AI Handles Administrative Friction, Doctors Make Clinical Decisions:**
   - The AI Assistant never diagnoses or autonomously prescribes medications.
   - All prescription orders and patient-facing lab explanations pass through mandatory Human-in-the-Loop (HITL) checkpoints.
2. **Rule-First Safety & Emergency Escalation:**
   - Critical red flags (acute chest pain, sudden dyspnea post-breakfast, stroke signs) bypass language models and trigger immediate emergency alerts with helpline numbers (1122).

