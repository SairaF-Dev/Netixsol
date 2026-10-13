# 🗄️ FHIR-Inspired Database Schema & ER Diagram

This document details the database architecture for City Care Clinics, modeled after HL7 FHIR (Fast Healthcare Interoperability Resources) standards adapted for relational storage.

---

## 📐 Entity Relationship Diagram

```mermaid
erDiagram
    BRANCHES ||--o{ PRACTITIONERS : "hosts"
    PRACTITIONERS ||--o{ APPOINTMENTS : "conducts"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    PATIENTS ||--o{ ALLERGIES : "has"
    PATIENTS ||--o{ CONDITIONS : "diagnosed_with"
    PATIENTS ||--o{ OBSERVATIONS : "has_results"
    APPOINTMENTS ||--o{ OBSERVATIONS : "generates"
    PATIENTS ||--o{ MEDICATION_REQUESTS : "prescribed"
    APPOINTMENTS ||--o{ MEDICATION_REQUESTS : "originates_from"

    BRANCHES {
        string id PK
        string name
        string city
        string address
        string phone
    }

    PRACTITIONERS {
        string id PK
        string branch_id FK
        string name
        string specialty
        int fee_pkr
        string days_available
        string timing
        string languages
    }

    PATIENTS {
        string id PK
        string cnic
        string name
        int age
        string gender
        string phone
        string city
        string address
        string blood_group
        string emergency_contact
    }

    ALLERGIES {
        string id PK
        string patient_id FK
        string allergen
        string severity
        string reaction
    }

    CONDITIONS {
        string id PK
        string patient_id FK
        string condition_name
        string status
        string onset_date
    }

    APPOINTMENTS {
        string id PK
        string patient_id FK
        string doctor_id FK
        string branch_id FK
        string appointment_date
        string time_slot
        string status
        string urgency_level
        string chief_complaint
    }

    OBSERVATIONS {
        string id PK
        string patient_id FK
        string appointment_id FK
        string test_name
        string test_category
        float value
        string unit
        string reference_range
        boolean is_abnormal
        string test_date
    }

    MEDICATION_REQUESTS {
        string id PK
        string patient_id FK
        string doctor_id FK
        string appointment_id FK
        string drug_name
        string generic_name
        string dosage
        string frequency
        string duration
        string status
    }
```

---

## 📑 Schema Field Mapping (FHIR Standard)

| Relational Table | Corresponding FHIR Resource | Description |
|------------------|-----------------------------|-------------|
| `BRANCHES` | `Location` | Physical clinic locations in Lahore and Islamabad |
| `PRACTITIONERS` | `Practitioner` | Doctor profile, specialty, fees, and schedule |
| `PATIENTS` | `Patient` | Patient demographic info (Pakistani format) |
| `ALLERGIES` | `AllergyIntolerance` | Adverse drug reactions and environmental allergies |
| `CONDITIONS` | `Condition` | Active and past medical history |
| `APPOINTMENTS` | `Appointment` | Scheduled, completed, or cancelled visit records |
| `OBSERVATIONS` | `Observation` | Diagnostic test results and vital signs |
| `MEDICATION_REQUESTS` | `MedicationRequest` | Prescriptions issued by doctors |

