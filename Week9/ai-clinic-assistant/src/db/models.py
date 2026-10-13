"""
SQLAlchemy ORM models for City Care Clinics FHIR-inspired database.
Supports both SQLite (local development/testing) and PostgreSQL (production).
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Branch(Base):
    __tablename__ = 'branches'

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)

    practitioners = relationship("Practitioner", back_populates="branch")
    appointments = relationship("Appointment", back_populates="branch")

class Practitioner(Base):
    __tablename__ = 'practitioners'

    id = Column(String(50), primary_key=True)
    branch_id = Column(String(50), ForeignKey('branches.id'), nullable=False)
    name = Column(String(100), nullable=False)
    specialty = Column(String(50), nullable=False)
    fee_pkr = Column(Integer, nullable=False)
    days_available = Column(String(100), nullable=False)
    timing = Column(String(50), nullable=False)
    languages = Column(String(100), nullable=False)

    branch = relationship("Branch", back_populates="practitioners")
    appointments = relationship("Appointment", back_populates="doctor")
    prescriptions = relationship("MedicationRequest", back_populates="doctor")

class Patient(Base):
    __tablename__ = 'patients'

    id = Column(String(50), primary_key=True)
    cnic = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    city = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    blood_group = Column(String(5), nullable=True)
    emergency_contact = Column(String(20), nullable=True)

    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
    prescriptions = relationship("MedicationRequest", back_populates="patient", cascade="all, delete-orphan")

class Allergy(Base):
    __tablename__ = 'allergies'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    allergen = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False) # High, Moderate, Low
    reaction = Column(String(255), nullable=True)

    patient = relationship("Patient", back_populates="allergies")

class Condition(Base):
    __tablename__ = 'conditions'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    condition_name = Column(String(150), nullable=False)
    status = Column(String(20), nullable=False) # Active, Resolved, Chronic
    onset_date = Column(String(20), nullable=True)

    patient = relationship("Patient", back_populates="conditions")

class Appointment(Base):
    __tablename__ = 'appointments'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    doctor_id = Column(String(50), ForeignKey('practitioners.id'), nullable=False)
    branch_id = Column(String(50), ForeignKey('branches.id'), nullable=False)
    appointment_date = Column(String(20), nullable=False)
    time_slot = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False) # Scheduled, Completed, Cancelled
    urgency_level = Column(String(20), nullable=False) # Emergency, Urgent, Routine
    chief_complaint = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Practitioner", back_populates="appointments")
    branch = relationship("Branch", back_populates="appointments")
    observations = relationship("Observation", back_populates="appointment")
    prescriptions = relationship("MedicationRequest", back_populates="appointment")

class Observation(Base):
    __tablename__ = 'observations'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    appointment_id = Column(String(50), ForeignKey('appointments.id'), nullable=True)
    test_name = Column(String(100), nullable=False)
    test_category = Column(String(50), nullable=False) # CBC, LFT, Lipid, HbA1c, Vitals
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    reference_range = Column(String(50), nullable=False)
    is_abnormal = Column(Boolean, default=False)
    test_date = Column(String(20), nullable=False)

    patient = relationship("Patient", back_populates="observations")
    appointment = relationship("Appointment", back_populates="observations")

class MedicationRequest(Base):
    __tablename__ = 'medication_requests'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    doctor_id = Column(String(50), ForeignKey('practitioners.id'), nullable=False)
    appointment_id = Column(String(50), ForeignKey('appointments.id'), nullable=True)
    drug_name = Column(String(100), nullable=False)
    generic_name = Column(String(100), nullable=False)
    dosage = Column(String(50), nullable=False)
    frequency = Column(String(50), nullable=False)
    duration = Column(String(50), nullable=False)
    status = Column(String(20), default="Active") # Active, Completed, Discontinued

    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("Practitioner", back_populates="prescriptions")
    appointment = relationship("Appointment", back_populates="prescriptions")

class User(Base):
    __tablename__ = 'users'

    id = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # Patient, Doctor, Receptionist, Admin
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    related_id = Column(String(50), nullable=True) # e.g. PAT-1001 or DOC-001
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())

class PatientPreference(Base):
    __tablename__ = 'patient_preferences'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    preferred_language = Column(String(50), default="Urdu")
    preferred_doctor_id = Column(String(50), ForeignKey('practitioners.id'), nullable=True)
    communication_channel = Column(String(50), default="WhatsApp")
    appointment_preference = Column(String(50), default="Morning")

class PatientMemory(Base):
    __tablename__ = 'patient_memories'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    memory_type = Column(String(50), nullable=False) # PREFERENCE, PAST_COMPLAINT, CLINICAL_CONTEXT
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())

class LabReport(Base):
    __tablename__ = 'lab_reports'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    test_name = Column(String(100), nullable=False)
    file_name = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=True)
    structured_data = Column(Text, nullable=True) # JSON
    status = Column(String(50), default="Uploaded") # Uploaded, Processing, AI Draft Ready, Awaiting Doctor Review, Doctor Approved, Available to Patient
    ai_explanation = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    doctor_approved_by = Column(String(50), ForeignKey('practitioners.id'), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    approved_at = Column(String(50), nullable=True)

class DoctorApproval(Base):
    __tablename__ = 'doctor_approvals'

    id = Column(String(50), primary_key=True)
    approval_type = Column(String(50), nullable=False) # LAB_EXPLANATION, PRESCRIPTION, LOW_CONFIDENCE_TRIAGE
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    doctor_id = Column(String(50), ForeignKey('practitioners.id'), nullable=False)
    original_payload = Column(Text, nullable=True) # JSON
    proposed_text = Column(Text, nullable=False)
    doctor_edits = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, EDITED, REJECTED
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    resolved_at = Column(String(50), nullable=True)

class ConversationSession(Base):
    __tablename__ = 'conversations'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    channel = Column(String(50), default="web")
    started_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    status = Column(String(50), default="ACTIVE") # ACTIVE, CLOSED, ESCALATED

class ChatMessage(Base):
    __tablename__ = 'messages'

    id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), ForeignKey('conversations.id'), nullable=False)
    sender = Column(String(50), nullable=False) # Patient, AI, Doctor, Receptionist
    message_text = Column(Text, nullable=False)
    timestamp = Column(String(50), default=lambda: datetime.datetime.now().isoformat())

class FollowUp(Base):
    __tablename__ = 'follow_ups'

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey('patients.id'), nullable=False)
    appointment_id = Column(String(50), ForeignKey('appointments.id'), nullable=True)
    scheduled_date = Column(String(50), nullable=False)
    reminder_type = Column(String(50), nullable=False) # PRE_VISIT_REMINDER, POST_CONSULT_CHECKIN, MEDICATION_ADHERENCE
    channel = Column(String(50), default="Email")
    status = Column(String(50), default="SCHEDULED") # SCHEDULED, SENT, RESPONDED
    message_text = Column(Text, nullable=False)
    sent_at = Column(String(50), nullable=True)

class AgentTrace(Base):
    __tablename__ = 'agent_traces'

    id = Column(String(50), primary_key=True)
    trace_id = Column(String(50), unique=True, nullable=False)
    session_id = Column(String(50), nullable=True)
    patient_id = Column(String(50), nullable=True)
    nodes_json = Column(Text, nullable=True)
    tool_calls_json = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    status = Column(String(50), default="COMPLETED")
    escalations_json = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(String(50), primary_key=True)
    timestamp = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    actor = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    patient_id = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    result = Column(String(50), nullable=False)
    ip_address = Column(String(50), default="127.0.0.1")
    details_json = Column(Text, nullable=True)


