"""
MedCare Clinic - Database Migrations & Production Seeder.
Creates missing tables and seeds the demo personas:
- Ahmed Khan (Returning Patient, Urdu, Dr. Bilal Ahmed preference)
- Dr. Bilal Ahmed (General Physician, DHA Branch)
- User logins for Patient, Doctor, Receptionist, Admin
- Pending Doctor Approvals, Lab Reports, Prescriptions, Follow-ups, Traces, Audit Logs.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json
import sqlite3
import datetime
from sqlalchemy import create_engine
from src.db.models import Base

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "clinic.db"))

def seed_medcare_database():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    # Create any missing tables defined in Base
    Base.metadata.create_all(engine)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Ensure Dr. Bilal Ahmed exists
    cursor.execute("SELECT id FROM practitioners WHERE id = 'DOC-101'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO practitioners (id, branch_id, name, specialty, fee_pkr, days_available, timing, languages)
            VALUES ('DOC-101', 'BRANCH-LHR-01', 'Dr. Bilal Ahmed', 'General Medicine', 2000, 'Mon, Tue, Wed, Thu, Fri', '09:00 - 17:00', 'English, Urdu, Punjabi')
        """)
        print("[SEED] Created Dr. Bilal Ahmed (DOC-101)")

    # 2. Ensure Ahmed Khan exists
    cursor.execute("SELECT id FROM patients WHERE id = 'PAT-1001'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO patients (id, cnic, name, age, gender, phone, city, address, blood_group, emergency_contact)
            VALUES ('PAT-1001', '35201-1234567-1', 'Ahmed Khan', 38, 'Male', '+92-300-1234567', 'Lahore', 'House 42, Sector Y, Phase 3, DHA, Lahore', 'B+', '+92-321-9876543')
        """)
        print("[SEED] Created Ahmed Khan (PAT-1001)")

    # 3. Allergies for Ahmed Khan
    cursor.execute("SELECT id FROM allergies WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO allergies (id, patient_id, allergen, severity, reaction)
            VALUES ('ALG-1001-1', 'PAT-1001', 'Penicillin', 'High', 'Skin rash, facial urticaria, difficulty breathing')
        """)
        cursor.execute("""
            INSERT INTO allergies (id, patient_id, allergen, severity, reaction)
            VALUES ('ALG-1001-2', 'PAT-1001', 'Dust & Pollen', 'Low', 'Mild allergic rhinitis, morning sneezing')
        """)

    # 4. Conditions for Ahmed Khan
    cursor.execute("SELECT id FROM conditions WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO conditions (id, patient_id, condition_name, status, onset_date)
            VALUES ('CND-1001-1', 'PAT-1001', 'Essential Hypertension', 'Active', '2023-04-12')
        """)
        cursor.execute("""
            INSERT INTO conditions (id, patient_id, condition_name, status, onset_date)
            VALUES ('CND-1001-2', 'PAT-1001', 'Mild Bronchial Asthma', 'Chronic', '2021-11-05')
        """)

    # 5. Preferences & Memory for Ahmed Khan
    cursor.execute("SELECT id FROM patient_preferences WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO patient_preferences (id, patient_id, preferred_language, preferred_doctor_id, communication_channel, appointment_preference)
            VALUES ('PREF-1001', 'PAT-1001', 'Urdu', 'DOC-101', 'WhatsApp', 'Morning')
        """)

    cursor.execute("SELECT id FROM patient_memories WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO patient_memories (id, patient_id, memory_type, key, value, created_at)
            VALUES ('MEM-1001-1', 'PAT-1001', 'PREFERENCE', 'preferred_doctor', 'Dr. Bilal Ahmed (General Medicine)', datetime('now', '-30 days'))
        """)
        cursor.execute("""
            INSERT INTO patient_memories (id, patient_id, memory_type, key, value, created_at)
            VALUES ('MEM-1001-2', 'PAT-1001', 'CLINICAL_CONTEXT', 'previous_complaint', 'Previous consult for persistent seasonal dry cough; responded well to inhaler and antihistamines.', datetime('now', '-21 days'))
        """)

    # 6. Appointments for Ahmed Khan
    cursor.execute("SELECT id FROM appointments WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        # Past completed appointment
        past_date = (datetime.datetime.now() - datetime.timedelta(days=21)).strftime('%Y-%m-%d')
        cursor.execute(f"""
            INSERT INTO appointments (id, patient_id, doctor_id, branch_id, appointment_date, time_slot, status, urgency_level, chief_complaint)
            VALUES ('APT-1001-PAST', 'PAT-1001', 'DOC-101', 'BRANCH-LHR-01', '{past_date}', '10:30 AM', 'Completed', 'Routine', 'Dry cough, chest congestion and routine BP check')
        """)
        # Upcoming appointment
        next_date = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        cursor.execute(f"""
            INSERT INTO appointments (id, patient_id, doctor_id, branch_id, appointment_date, time_slot, status, urgency_level, chief_complaint)
            VALUES ('APT-1001-UPCOMING', 'PAT-1001', 'DOC-101', 'BRANCH-LHR-01', '{next_date}', '11:00 AM', 'Scheduled', 'Routine', 'Quarterly hypertension review & lab discussion')
        """)

    # 7. Active Prescriptions for Ahmed Khan
    cursor.execute("SELECT id FROM medication_requests WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO medication_requests (id, patient_id, doctor_id, appointment_id, drug_name, generic_name, dosage, frequency, duration, status)
            VALUES ('RX-1001-1', 'PAT-1001', 'DOC-101', 'APT-1001-PAST', 'Lipitor', 'Atorvastatin', '10mg', 'Once daily (Night)', '90 days', 'Active')
        """)
        cursor.execute("""
            INSERT INTO medication_requests (id, patient_id, doctor_id, appointment_id, drug_name, generic_name, dosage, frequency, duration, status)
            VALUES ('RX-1001-2', 'PAT-1001', 'DOC-101', 'APT-1001-PAST', 'Ventolin Inhaler', 'Salbutamol', '100mcg', '2 puffs PRN (As needed)', '30 days', 'Active')
        """)

    # 8. Lab Reports for Ahmed Khan
    cursor.execute("SELECT id FROM lab_reports WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO lab_reports (id, patient_id, test_name, file_name, raw_text, structured_data, status, ai_explanation, doctor_notes, doctor_approved_by, created_at, approved_at)
            VALUES (
                'REP-1001-1',
                'PAT-1001',
                'Complete Blood Count (CBC) & ESR',
                'cbc_ahmed_khan_oct2026.pdf',
                'Hemoglobin: 14.1 g/dL (Normal: 13.0-17.0)\nWBC: 6,800 /mcL (Normal: 4,000-11,000)\nPlatelets: 245,000 /mcL (Normal: 150,000-450,000)\nESR: 12 mm/hr (Normal: 0-15)',
                '{"hemoglobin": 14.1, "wbc": 6800, "platelets": 245000, "esr": 12}',
                'Doctor Approved',
                'Aap ke blood test reports bilkul normal hain. Hemoglobin aur white cell count theek limits mein hain. Koi infection ya anemia ki alamaat nahi hain.',
                'Reviewed. All baseline hematology parameters within normal range.',
                'DOC-101',
                datetime('now', '-20 days'),
                datetime('now', '-19 days')
            )
        """)
        cursor.execute("""
            INSERT INTO lab_reports (id, patient_id, test_name, file_name, raw_text, structured_data, status, ai_explanation, doctor_notes, doctor_approved_by, created_at)
            VALUES (
                'REP-1001-2',
                'PAT-1001',
                'Fasting Blood Sugar & Lipid Profile',
                'lipid_fbs_ahmed_khan_recent.pdf',
                'Fasting Blood Glucose: 98 mg/dL (Normal: 70-100)\nTotal Cholesterol: 192 mg/dL (Normal: <200)\nTriglycerides: 145 mg/dL (Normal: <150)\nHDL: 48 mg/dL (Normal: >40)\nLDL: 115 mg/dL (Optimal: <100)',
                '{"fasting_glucose": 98, "cholesterol": 192, "triglycerides": 145, "hdl": 48, "ldl": 115}',
                'Awaiting Doctor Review',
                'Glucose normal hai (98 mg/dL). Cholesterol total 192 mg/dL control mein hai, albata LDL thora sa elevated hai (115 mg/dL). Dr. Bilal Ahmed review kar ke rehnumai farmayenge.',
                NULL,
                NULL,
                datetime('now', '-1 days')
            )
        """)

    # 9. Doctor HITL Approvals Queue
    cursor.execute("SELECT id FROM doctor_approvals WHERE status = 'PENDING'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO doctor_approvals (id, approval_type, patient_id, doctor_id, original_payload, proposed_text, doctor_edits, status, created_at)
            VALUES (
                'APP-001',
                'LAB_EXPLANATION',
                'PAT-1001',
                'DOC-101',
                '{"report_id": "REP-1001-2", "tests": {"fbs": 98, "ldl": 115, "cholesterol": 192}}',
                'Glucose normal hai (98 mg/dL). Cholesterol 192 control mein hai, albata LDL 115 mg/dL borderline hai. Kal ki consultation mein doctor dietary lifestyle aur statin dosage review karenge.',
                NULL,
                'PENDING',
                datetime('now', '-2 hours')
            )
        """)
        cursor.execute("""
            INSERT INTO doctor_approvals (id, approval_type, patient_id, doctor_id, original_payload, proposed_text, doctor_edits, status, created_at)
            VALUES (
                'APP-002',
                'PRESCRIPTION',
                'PAT-1001',
                'DOC-101',
                '{"drug": "Augmentin 625mg", "indication": "Suspected bacterial sinusitis"}',
                'SAFETY WARNING: Patient has documented severe PENICILLIN ALLERGY. Proposed Augmentin (Amoxicillin/Clavulanate) is CONTRAINDICATED. Recommend alternative non-beta-lactam: Azithromycin 500mg or Levofloxacin.',
                NULL,
                'PENDING',
                datetime('now', '-4 hours')
            )
        """)
        cursor.execute("""
            INSERT INTO doctor_approvals (id, approval_type, patient_id, doctor_id, original_payload, proposed_text, doctor_edits, status, created_at)
            VALUES (
                'APP-003',
                'LOW_CONFIDENCE_TRIAGE',
                'PAT-0004',
                'DOC-101',
                '{"complaint": "Persistent fatigue, intermittent abdominal cramps, and slight feverish feeling for 10 days", "confidence": 0.62}',
                'Confidence score 0.62 (Below 0.75 threshold). Symptoms span Gastroenterology and Internal Medicine. System recommends Doctor confirmation before confirming specialty queue.',
                NULL,
                'PENDING',
                datetime('now', '-6 hours')
            )
        """)

    # 10. Users table for authentication
    cursor.execute("SELECT id FROM users WHERE username = 'ahmed'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, role, name, email, related_id)
            VALUES ('USR-001', 'ahmed', 'password123', 'Patient', 'Ahmed Khan', 'ahmed.khan@medcare.pk', 'PAT-1001')
        """)
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, role, name, email, related_id)
            VALUES ('USR-002', 'dr.bilal', 'password123', 'Doctor', 'Dr. Bilal Ahmed', 'bilal.ahmed@medcare.pk', 'DOC-101')
        """)
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, role, name, email, related_id)
            VALUES ('USR-003', 'receptionist', 'password123', 'Receptionist', 'Sana Front Desk', 'frontdesk@medcare.pk', NULL)
        """)
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, role, name, email, related_id)
            VALUES ('USR-004', 'admin', 'password123', 'Admin', 'Clinic Administrator', 'admin@medcare.pk', NULL)
        """)
        print("[SEED] Created user authentication credentials")

    # 11. Follow-ups
    cursor.execute("SELECT id FROM follow_ups WHERE patient_id = 'PAT-1001'")
    if not cursor.fetchall():
        cursor.execute("""
            INSERT INTO follow_ups (id, patient_id, appointment_id, scheduled_date, reminder_type, channel, status, message_text, sent_at)
            VALUES (
                'FOL-1001-1',
                'PAT-1001',
                'APT-1001-PAST',
                datetime('now', '-18 days'),
                'POST_CONSULT_CHECKIN',
                'Email',
                'SENT',
                'Assalam-o-Alaikum Ahmed sahib! Pichli consultation ke baad aap ki tabiyat kaisi hai? Khansi aur saans ki takleef behtar hui?',
                datetime('now', '-18 days')
            )
        """)
        cursor.execute("""
            INSERT INTO follow_ups (id, patient_id, appointment_id, scheduled_date, reminder_type, channel, status, message_text)
            VALUES (
                'FOL-1001-2',
                'PAT-1001',
                'APT-1001-UPCOMING',
                datetime('now', '+1 days'),
                'PRE_VISIT_REMINDER',
                'WhatsApp',
                'SCHEDULED',
                'Reminder: MedCare Clinic mein Dr. Bilal Ahmed ke sath aap ki appointment kal subha 11:00 AM scheduled hai.'
            )
        """)

    # 12. Initial Traces & Audit Logs
    cursor.execute("SELECT id FROM audit_logs LIMIT 1")
    if not cursor.fetchone():
        logs = [
            ("USR-001", "Patient", "PAT-1001", "LOGIN", "AUTH_SERVICE", "SUCCESS", "Patient logged in via web portal"),
            ("USR-001", "Patient", "PAT-1001", "VIEW_RECORD", "MEDICAL_RECORDS", "SUCCESS", "Patient viewed past lab reports"),
            ("USR-002", "Doctor", "PAT-1001", "VIEW_PATIENT", "PATIENT_PROFILE", "SUCCESS", "Dr. Bilal Ahmed reviewed clinical profile"),
            ("SYS-ROUTER", "System", "PAT-0042", "EMERGENCY_ESCALATION", "TRIAGE_ENGINE", "ESCALATED", "Cardiac red flag triggered; routed to 1122 emergency bypass"),
            ("USR-002", "Doctor", "PAT-1001", "APPROVE_LAB", "HITL_APPROVAL", "APPROVED", "Doctor approved patient-friendly CBC explanation"),
        ]
        for actor, role, pat, action, res, outcome, detail in logs:
            cursor.execute("""
                INSERT INTO audit_logs (id, timestamp, actor, role, patient_id, action, resource, result, ip_address, details_json)
                VALUES (?, datetime('now', '-1 hours'), ?, ?, ?, ?, ?, ?, '127.0.0.1', ?)
            """, (f"AUD-{random.randint(10000, 99999)}", actor, role, pat, action, res, outcome, json.dumps({"note": detail})))

    cursor.execute("SELECT id FROM agent_traces LIMIT 1")
    if not cursor.fetchone():
        sample_nodes = [
            {"node": "Supervisor", "latency_ms": 320, "tokens": 85, "status": "COMPLETED"},
            {"node": "IntakeAgent", "latency_ms": 940, "tokens": 210, "status": "COMPLETED"},
            {"node": "RecordsAgent", "latency_ms": 480, "tokens": 140, "status": "COMPLETED"},
            {"node": "TriageAgent", "latency_ms": 520, "tokens": 160, "status": "COMPLETED"},
            {"node": "SpecialistAgent", "latency_ms": 390, "tokens": 115, "status": "COMPLETED"},
            {"node": "SchedulingAgent", "latency_ms": 610, "tokens": 175, "status": "COMPLETED"}
        ]
        cursor.execute("""
            INSERT INTO agent_traces (id, trace_id, session_id, patient_id, nodes_json, tool_calls_json, total_tokens, estimated_cost_usd, latency_ms, status, escalations_json, created_at)
            VALUES (
                'TRC-REC-001',
                'TRC-8921-A',
                'SESS- Ahmed-Khan-982',
                'PAT-1001',
                ?,
                '["patient_records.get_profile", "scheduling.find_available_slots"]',
                885,
                0.00177,
                3260.0,
                'COMPLETED',
                '[]',
                datetime('now', '-2 hours')
            )
        """, (json.dumps(sample_nodes),))

    conn.commit()
    conn.close()
    print("[SUCCESS] MedCare Clinic database seeded successfully!")

if __name__ == "__main__":
    import random
    seed_medcare_database()
