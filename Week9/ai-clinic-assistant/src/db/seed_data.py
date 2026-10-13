"""
Synthetic Data Generator & Database Seeder for City Care Clinics.
Generates:
- 5 Clinic Branches in Lahore & Islamabad
- 30 Doctors across 6 Specialties
- 500+ Synthetic Patients with Pakistani Demographics
- Allergies, Medical Conditions, Visit History, Lab Results (Observations), and Prescriptions.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "clinic.db")

# Seed Data Lists for Pakistani Healthcare Context
MALE_FIRST_NAMES = [
    "Muhammad", "Ahmed", "Ali", "Tariq", "Usman", "Bilal", "Hamza", "Zaid", "Fahad", "Omer",
    "Kamran", "Salman", "Imran", "Hassan", "Hussein", "Asad", "Kashif", "Waqas", "Adnan", "Rizwan",
    "Faisal", "Danish", "Haris", "Shehryar", "Noman", "Ahsan", "Babar", "Saad", "Shahid", "Zubair"
]

FEMALE_FIRST_NAMES = [
    "Fatima", "Ayesha", "Zainab", "Maryam", "Sana", "Amna", "Hira", "Iqra", "Sadia", "Nida",
    "Mehwish", "Anum", "Sara", "Mahnoor", "Laiba", "Khadija", "Sidra", "Bushra", "Farah", "Rabia",
    "Rimsha", "Sundas", "Noreen", "Maimoona", "Tehreem", "Kiran", "Samreen", "Nazia", "Mona", "Sumaira"
]

LAST_NAMES = [
    "Khan", "Mahmood", "Chaudhry", "Malik", "Sheikh", "Qureshi", "Siddiqui", "Raza", "Bhatti", "Shah",
    "Abbasi", "Mirza", "Ghafoor", "Akhtar", "Hussain", "Javed", "Farooq", "Aziz", "Tariq", "Rehman"
]

CITIES_BRANCHES = [
    {"id": "BRANCH-LHR-01", "name": "DHA Branch", "city": "Lahore", "address": "Phase 5, DHA, Lahore", "phone": "+92-42-35690001"},
    {"id": "BRANCH-LHR-02", "name": "Gulberg Branch", "city": "Lahore", "address": "Main Boulevard, Gulberg III, Lahore", "phone": "+92-42-35750002"},
    {"id": "BRANCH-LHR-03", "name": "Johar Town Branch", "city": "Lahore", "address": "Doctor Hospital Chowk, Johar Town, Lahore", "phone": "+92-42-35200003"},
    {"id": "BRANCH-ISB-01", "name": "F-7 Markaz Branch", "city": "Islamabad", "address": "F-7 Markaz, Islamabad", "phone": "+92-51-2650004"},
    {"id": "BRANCH-ISB-02", "name": "Blue Area Branch", "city": "Islamabad", "address": "Jinnah Avenue, Blue Area, Islamabad", "phone": "+92-51-2800005"},
]

SPECIALTIES = [
    "General Medicine", "Paediatrics", "Gynaecology", "Cardiology", "Dermatology", "ENT"
]

DOCTOR_PREFIXES = ["Dr.", "Dr. Prof.", "Dr. Assoc. Prof."]

ALLERGENS = [
    {"name": "Penicillin", "severity": "High", "reaction": "Anaphylaxis, severe hives, rash"},
    {"name": "Amoxicillin", "severity": "High", "reaction": "Skin rash, facial swelling"},
    {"name": "Aspirin / NSAIDs", "severity": "Moderate", "reaction": "Bronchospasm, gastric discomfort"},
    {"name": "Sulfa Drugs", "severity": "High", "reaction": "Stevens-Johnson syndrome risk, skin eruption"},
    {"name": "Peanuts / Nuts", "severity": "High", "reaction": "Throat swelling, difficulty breathing"},
    {"name": "Dust & Pollen", "severity": "Low", "reaction": "Allergic rhinitis, sneezing"},
    {"name": "Ibuprofen", "severity": "Moderate", "reaction": "Urticaria, wheezing"},
]

CHRONIC_CONDITIONS = [
    "Essential Hypertension", "Type 2 Diabetes Mellitus", "Bronchial Asthma",
    "Ischemic Heart Disease", "Hyperlipidemia", "Hypothyroidism", "Allergic Rhinitis"
]

COMMON_DRUGS = [
    {"drug": "Panadol 500mg", "generic": "Paracetamol", "dosage": "1 tablet", "frequency": "Every 8 hours", "duration": "5 days"},
    {"drug": "Augmentin 625mg", "generic": "Amoxicillin + Clavulanic Acid", "dosage": "1 tablet", "frequency": "Twice daily", "duration": "7 days"},
    {"drug": "Flygyl 400mg", "generic": "Metronidazole", "dosage": "1 tablet", "frequency": "Three times daily", "duration": "5 days"},
    {"drug": "Lopressor 50mg", "generic": "Metoprolol", "dosage": "1 tablet", "frequency": "Once daily", "duration": "30 days"},
    {"drug": "Glucophage 500mg", "generic": "Metformin", "dosage": "1 tablet", "frequency": "Twice daily with meals", "duration": "30 days"},
    {"drug": "Softin 10mg", "generic": "Loratadine", "dosage": "1 tablet", "frequency": "Once daily at bedtime", "duration": "10 days"},
    {"drug": "Risek 20mg", "generic": "Omeprazole", "dosage": "1 capsule", "frequency": "Before breakfast", "duration": "14 days"},
]

LAB_TESTS = [
    {"test": "Hemoglobin", "category": "CBC", "unit": "g/dL", "ref": "13.5 - 17.5", "min": 9.0, "max": 18.0, "abnormal_below": 12.0},
    {"test": "WBC Count", "category": "CBC", "unit": "x10^3/uL", "ref": "4.5 - 11.0", "min": 3.0, "max": 20.0, "abnormal_above": 11.0},
    {"test": "Platelet Count", "category": "CBC", "unit": "x10^3/uL", "ref": "150 - 450", "min": 80.0, "max": 500.0, "abnormal_below": 150.0},
    {"test": "Fasting Blood Sugar", "category": "Diabetes", "unit": "mg/dL", "ref": "70 - 99", "min": 65.0, "max": 250.0, "abnormal_above": 100.0},
    {"test": "HbA1c", "category": "Diabetes", "unit": "%", "ref": "< 5.7", "min": 4.8, "max": 11.5, "abnormal_above": 5.7},
    {"test": "Serum Creatinine", "category": "Renal", "unit": "mg/dL", "ref": "0.7 - 1.3", "min": 0.5, "max": 3.5, "abnormal_above": 1.3},
    {"test": "ALT (SGPT)", "category": "LFT", "unit": "U/L", "ref": "7 - 56", "min": 10.0, "max": 180.0, "abnormal_above": 56.0},
    {"test": "Total Cholesterol", "category": "Lipid", "unit": "mg/dL", "ref": "< 200", "min": 130.0, "max": 320.0, "abnormal_above": 200.0},
]

def generate_cnic():
    # Format: 35202-xxxxxxx-x
    prefix = random.choice(["35201", "35202", "35204", "61101", "37405"])
    mid = f"{random.randint(1000000, 9999999)}"
    last = f"{random.randint(1, 9)}"
    return f"{prefix}-{mid}-{last}"

def generate_phone():
    codes = ["0300", "0301", "0302", "0321", "0333", "0345", "0312"]
    return f"+92-{random.choice(codes)[1:]}-{random.randint(1000000, 9999999)}"

def create_tables(conn):
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()

def seed_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    create_tables(conn)

    print("[*] Seeding Branches...")
    for b in CITIES_BRANCHES:
        cursor.execute("INSERT INTO branches VALUES (?, ?, ?, ?, ?)", (b["id"], b["name"], b["city"], b["address"], b["phone"]))

    print("[*] Seeding 30 Practitioners across 6 Specialties...")
    practitioner_ids = []
    doc_counter = 1
    for spec in SPECIALTIES:
        for i in range(5): # 5 doctors per specialty = 30 total
            doc_id = f"DOC-{doc_counter:03d}"
            practitioner_ids.append((doc_id, spec))
            gender = random.choice(["Male", "Female"])
            fname = random.choice(MALE_FIRST_NAMES if gender == "Male" else FEMALE_FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            name = f"{random.choice(DOCTOR_PREFIXES)} {fname} {lname}"
            branch = CITIES_BRANCHES[(doc_counter - 1) % len(CITIES_BRANCHES)]
            fee = random.choice([2000, 2500, 3000, 3500, 4000])
            days = "Mon - Fri" if i % 2 == 0 else "Mon - Sat"
            timing = "09:00 AM - 01:00 PM" if i % 2 == 0 else "05:00 PM - 09:00 PM"
            langs = "Urdu, English, Punjabi"
            cursor.execute("INSERT INTO practitioners VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (doc_id, branch["id"], name, spec, fee, days, timing, langs))
            doc_counter += 1

    print("[*] Seeding 500+ Synthetic Patients...")
    patient_ids = []
    for p_num in range(1, 521):
        pid = f"PAT-{p_num:04d}"
        patient_ids.append(pid)
        gender = random.choice(["Male", "Female"])
        fname = random.choice(MALE_FIRST_NAMES if gender == "Male" else FEMALE_FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        cnic = generate_cnic()
        age = random.randint(3, 82)
        phone = generate_phone()
        city = random.choice(["Lahore", "Islamabad", "Rawalpindi"])
        address = f"House #{random.randint(1, 200)}, Street #{random.randint(1, 40)}, Sector {random.choice(['G-9', 'F-10', 'DHA Phase 3', 'Johar Town'])}, {city}"
        blood = random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+"])
        e_contact = generate_phone()

        cursor.execute("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (pid, cnic, name, age, gender, phone, city, address, blood, e_contact))

        # Add Allergies for ~18% of patients
        if random.random() < 0.18:
            alg = random.choice(ALLERGENS)
            cursor.execute("INSERT INTO allergies VALUES (?, ?, ?, ?, ?)",
                           (f"ALG-{p_num:04d}", pid, alg["name"], alg["severity"], alg["reaction"]))

        # Add Chronic Conditions for ~25% of patients
        if random.random() < 0.25:
            cond = random.choice(CHRONIC_CONDITIONS)
            onset = f"202{random.randint(0, 5)}-{random.randint(1,12):02d}-15"
            cursor.execute("INSERT INTO conditions VALUES (?, ?, ?, ?, ?)",
                           (f"CND-{p_num:04d}", pid, cond, "Active", onset))

    print("[*] Seeding Appointments, Observations, and Prescriptions...")
    complaints = [
        "Fever and dry cough for 3 days", "Severe headache and dizziness", "Chest pain and breathlessness",
        "Stomach pain after meals", "Skin rash and itching", "Ear pain and discharge",
        "Routine diabetes checkup", "Child vomiting and low appetite", "Joint pain and stiffness"
    ]

    apt_count = 1
    for pid in patient_ids[:350]: # First 350 patients have visit history
        num_visits = random.randint(1, 3)
        for v in range(num_visits):
            apt_id = f"APT-{apt_count:05d}"
            doc_id, spec = random.choice(practitioner_ids)
            branch_id = CITIES_BRANCHES[random.randint(0, 4)]["id"]
            days_ago = random.randint(1, 180)
            apt_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            slot = random.choice(["10:30 AM", "11:00 AM", "05:30 PM", "06:30 PM", "07:30 PM"])
            urgency = random.choice(["Routine", "Routine", "Urgent", "Emergency"]) if complaints else "Routine"
            complaint = random.choice(complaints)

            cursor.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (apt_id, pid, doc_id, branch_id, apt_date, slot, "Completed", urgency, complaint))

            # Add Lab Observation for visit
            test = random.choice(LAB_TESTS)
            val = round(random.uniform(test["min"], test["max"]), 1)
            is_ab = False
            if "abnormal_below" in test and val < test["abnormal_below"]:
                is_ab = True
            elif "abnormal_above" in test and val > test["abnormal_above"]:
                is_ab = True

            cursor.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (f"OBS-{apt_count:05d}", pid, apt_id, test["test"], test["category"], val, test["unit"], test["ref"], is_ab, apt_date))

            # Add Prescription for visit
            drug = random.choice(COMMON_DRUGS)
            cursor.execute("INSERT INTO medication_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (f"MED-{apt_count:05d}", pid, doc_id, apt_id, drug["drug"], drug["generic"], drug["dosage"], drug["frequency"], drug["duration"], "Active"))

            apt_count += 1

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Successfully seeded SQLite Database at {DB_PATH}")

if __name__ == "__main__":
    seed_database()
