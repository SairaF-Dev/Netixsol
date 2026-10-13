-- City Care Clinics PostgreSQL / Standard SQL Schema Definition (FHIR-Inspired)

DROP TABLE IF EXISTS medication_requests;
DROP TABLE IF EXISTS observations;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS conditions;
DROP TABLE IF EXISTS allergies;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS practitioners;
DROP TABLE IF EXISTS branches;

CREATE TABLE branches (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL
);

CREATE TABLE practitioners (
    id VARCHAR(50) PRIMARY KEY,
    branch_id VARCHAR(50) REFERENCES branches(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(50) NOT NULL,
    fee_pkr INTEGER NOT NULL,
    days_available VARCHAR(100) NOT NULL,
    timing VARCHAR(50) NOT NULL,
    languages VARCHAR(100) NOT NULL
);

CREATE TABLE patients (
    id VARCHAR(50) PRIMARY KEY,
    cnic VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL,
    gender VARCHAR(10) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    city VARCHAR(50) NOT NULL,
    address VARCHAR(255) NOT NULL,
    blood_group VARCHAR(5),
    emergency_contact VARCHAR(20)
);

CREATE TABLE allergies (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(id) ON DELETE CASCADE,
    allergen VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    reaction VARCHAR(255)
);

CREATE TABLE conditions (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(id) ON DELETE CASCADE,
    condition_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL,
    onset_date VARCHAR(20)
);

CREATE TABLE appointments (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id VARCHAR(50) REFERENCES practitioners(id) ON DELETE CASCADE,
    branch_id VARCHAR(50) REFERENCES branches(id) ON DELETE CASCADE,
    appointment_date VARCHAR(20) NOT NULL,
    time_slot VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    urgency_level VARCHAR(20) NOT NULL,
    chief_complaint TEXT
);

CREATE TABLE observations (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id VARCHAR(50) REFERENCES appointments(id) ON DELETE SET NULL,
    test_name VARCHAR(100) NOT NULL,
    test_category VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20) NOT NULL,
    reference_range VARCHAR(50) NOT NULL,
    is_abnormal BOOLEAN DEFAULT FALSE,
    test_date VARCHAR(20) NOT NULL
);

CREATE TABLE medication_requests (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id VARCHAR(50) REFERENCES practitioners(id) ON DELETE CASCADE,
    appointment_id VARCHAR(50) REFERENCES appointments(id) ON DELETE SET NULL,
    drug_name VARCHAR(100) NOT NULL,
    generic_name VARCHAR(100) NOT NULL,
    dosage VARCHAR(50) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    duration VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'Active'
);

