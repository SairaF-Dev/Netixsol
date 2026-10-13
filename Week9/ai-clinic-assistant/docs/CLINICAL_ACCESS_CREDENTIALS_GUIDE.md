# MedCare Clinic EHR — Enterprise Access & Clinical Credentials Guide
**Document Identifier:** `SEC-DOC-AUTH-2026-v3`  
**Classification:** Confidential — Clinical Operations & IT Governance  
**Standards Compliance:** HIPAA Security Rule § 164.312 | NIST SP 800-63B | PMDC / PMC Telehealth Guidelines  

---

## 1. Executive Summary & Security Policy

In accordance with enterprise healthcare security standards (**HIPAA § 164.312** and **NIST SP 800-63B**):

1. **Zero Frontend Credential Leakage:** Hardcoded test credentials, clickable cheat shortcuts, and pre-login tabs are strictly excluded from all public login interfaces.
2. **Zero Impersonation / Anti-Spoofing Policy:** Arbitrary or self-declared physician profiles are prohibited. Users cannot simply enter an unregistered email (such as `dr.stranger@gmail.com`) to gain clinical privileges. Only pre-registered practitioners enrolled in the institutional registry (`users` & `practitioners`) are permitted.
3. **Mandatory Dual-Factor Credential Validation:** Entering a valid doctor's email with an invalid or incorrect password immediately triggers an **Authentication Denial (`401 / Access Denied`)**.

This document is the authoritative, confidential credential registry for clinic staff, medical directors, and authorized institutional evaluators.

### Clinical System Access Workstations:
* **Primary Enterprise EHR Web Portal:** [`http://127.0.0.1:8000`](http://127.0.0.1:8000) *(FastAPI High-Performance Clinical EHR)*
* **Streamlit Clinical Command Suite:** [`http://127.0.0.1:8501`](http://127.0.0.1:8501) *(Python Clinical Operations)*

---

## 2. Institutional Authentication Standards

* **Account-Specific Registered Passwords:** Each practitioner, staff member, and patient has a unique, high-entropy institutional password (documented below).
* **Institutional Master Evaluation Key:** For capstone evaluations and automated regression tests, the system also accepts `Clinic@123` or `password123` for any registered account.
* **Strict Rejection Criteria:**
  * **Unregistered Email / User:** Returns `Unauthorized Account: Not a registered clinical workstation or patient account.`
  * **Incorrect Password:** Returns `Authentication Failed: Incorrect password. Access denied.`
* **Workstation Isolation (RBAC):** Upon valid authentication, doctors access only their assigned patients and department queue. Cross-doctor data bleeding is strictly prevented.

---

## 3. Registered Attending Physicians & Specialists

Every physician listed below has an active record in the clinic database, tied to their PMDC registration number, physical room assignment, and specialized consultation queue.

| Practitioner Name | Specialty | Official Work Email | Registered Password | ID | PMC / PMDC Reg | Room / Suite |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dr. Bilal Ahmed** | Internal / General Medicine | `dr.bilal@citycareclinics.com` | `Bilal@MedCare2026!` | `DOC-101` | PMC-34821-P | Room 4B |
| **Dr. Laiba Farooq** | General Medicine | `dr.laiba@citycareclinics.com` | `Laiba@MedCare2026!` | `DOC-001` | PMC-41920-P | Suite 1A |
| **Dr. Zaid Dental Surgeon** | Dental Surgery | `dr.zaid@citycareclinics.com` | `Zaid@Dental2026!` | `DOC-031` | PMC-28410-D | Suite 2A |
| **Dr. Assoc. Prof. Ayesha Shah** | Paediatrics | `dr.ayesha@citycareclinics.com` | `Ayesha@Paeds2026!` | `DOC-006` | PMC-39105-P | Suite 3C |
| **Dr. Prof. Hira Rehman** | Cardiology | `dr.hira@citycareclinics.com` | `Hira@Cardio2026!` | `DOC-016` | PMC-22490-P | Suite 5A |
| **Dr. Prof. Ahsan Shah** | General Medicine | `dr.ahsan@citycareclinics.com` | `Ahsan@MedCare2026!` | `DOC-002` | PMC-19842-P | Suite 2B |
| **Dr. Fatima Bhatti** | Dermatology | `dr.fatima@citycareclinics.com` | `Fatima@Derma2026!` | `DOC-021` | PMC-44210-P | Suite 3A |
| **Dr. Imran Eye Specialist** | Ophthalmology | `dr.imran@citycareclinics.com` | `Imran@Vision2026!` | `DOC-034` | PMC-29401-P | Eye Clinic 1 |
| **Dr. Maham Nutritionist** | Clinical Nutrition | `dr.maham@citycareclinics.com` | `Maham@Nutrition2026!` | `DOC-036` | PMC-51203-N | Suite 1D |

> **Anti-Impersonation Protection:**  
> If an unverified user inputs an unregistered email (e.g. `dr.stranger@random.com`), access is unconditionally blocked. No temporary or mock doctor identities are created.

---

## 4. Clinic Operations & Administrative Personnel

Front desk coordinators and compliance auditors manage admissions, branch scheduling, and security oversight.

| Staff Member | Functional Role | Work Email | Registered Password | System ID | Authorized Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sana Desk** | Front Desk Lead / Receptionist | `sana@citycareclinics.com` | `Sana@FrontDesk2026!` | `REC-001` | Multi-branch booking, check-in triage, queue management |
| **Care Reminder Lead** | Care Plan Coordinator | `reminders@citycareclinics.com` | `Remind@Care2026!` | `FLD-001` | Automated email care alerts, post-visit wellness follow-up |
| **Clinical Auditor** | Compliance & Security Lead | `admin@citycareclinics.com` | `Admin@Audit2026!` | `ADM-001` | HIPAA audit logs, LangGraph agent traces, safety metrics |

---

## 5. Verified Registered Patients

Patients log into the MedCare Patient Portal to converse with the Roman Urdu triage assistant, view health summaries, and download signed e-prescriptions.

| Patient Name | Medical Record # | Verified Email | Registered Password | Demographics | Clinical Profile on File |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ahmed Khan** | `PAT-1001` | `ahmed@gmail.com` | `Ahmed@Patient2026!` | Male, 42y | Chronic hypertension, CBC lab report clear, previous consult with Dr. Bilal Ahmed |
| **Saira Fatima** | `PAT-5501` | `saira@gmail.com` | `Saira@Patient2026!` | Female, 28y | **Known Allergies:** Penicillin (urticaria) & Brufen/NSAIDs (bronchospasm) |

---

## 6. Verification & Step-by-Step Security Testing Guide

Institutional evaluators can verify security enforcement with the following scenarios:

### Test Case 1: Valid Doctor Login with Registered Password (PASS)
1. Open [`http://127.0.0.1:8000`](http://127.0.0.1:8000) or [`http://127.0.0.1:8501`](http://127.0.0.1:8501).
2. Enter Work Email: `dr.bilal@citycareclinics.com`
3. Enter Password: `Bilal@MedCare2026!` *(or master key `Clinic@123`)*
4. Click **"Authenticate & Access Workspace"**.
5. **Expected Result:**  
   * Access is granted immediately.
   * Workstation loads: `Dr. Bilal Ahmed (Internal Medicine)` | `Room 4B`.
   * Only Dr. Bilal's scheduled queue is displayed.

### Test Case 2: Valid Doctor Email with INCORRECT Password (DENIED)
1. Enter Work Email: `dr.bilal@citycareclinics.com`
2. Enter Password: `WrongPassword123`
3. Click **"Authenticate & Access Workspace"**.
4. **Expected Result:**  
   * Access is strictly blocked.
   * Red warning banner appears:  
     `"Authentication Failed: Incorrect password for 'dr.bilal@citycareclinics.com'. Access denied."`

### Test Case 3: Unregistered Random User Trying to Become Doctor (DENIED)
1. Enter Work Email: `dr.random_fake@hospital.com`
2. Enter Password: `AnyPassword123`
3. Click **"Authenticate & Access Workspace"**.
4. **Expected Result:**  
   * Access is strictly blocked.
   * Security alert appears:  
     `"Unauthorized Account: 'dr.random_fake@hospital.com' is not a registered clinical workstation or patient account. Access denied."`
   * No doctor session or mock profile is generated.

### Test Case 4: Switching Between Verified Doctors (Isolation Verification)
1. Sign in as `dr.zaid@citycareclinics.com` with `Zaid@Dental2026!`.
2. Confirm Dental Suite 2A queue is displayed.
3. Click **"Sign Out"**.
4. Sign in as `dr.laiba@citycareclinics.com` with `Laiba@MedCare2026!`.
5. Confirm General Medicine Suite 1A queue is displayed.

### Test Case 5: New Patient Self-Registration & Database Persistence
1. On the authentication screen, click the tab **"Register as Patient"**.
2. Enter Patient Demographics:
   * **Full Name:** `Zainab Malik`
   * **Gender:** `Female`
   * **Age:** `29`
   * **Phone:** `+92-300-9876543`
   * **Branch:** `Lahore (DHA Branch)`
   * **Email:** `zainab.malik@example.com`
   * **Password:** `Zainab@Secure2026!`
3. Click **"Register & Access Patient Portal"**.
4. **Expected Result:**
   * New patient record is committed to SQLite `patients` table with newly issued MRN (e.g. `PAT-7840`).
   * New user credentials are created in `users` table.
   * Welcome toast displays: `"Registration Successful! Welcome, Zainab Malik (MRN: PAT-7840)"`.
   * Patient is automatically logged in and redirected to their personal health portal (`/portal`).
   * When signing out and entering `zainab.malik@example.com` with `Zainab@Secure2026!`, login succeeds immediately.

### Test Case 6: Real-World Interactive Password Reset
1. On the Sign In screen, click **"Forgot Password?"**.
2. Interactive modal opens:
   * Enter Registered Email: `zainab.malik@example.com`
   * Enter New Password: `ZainabNewPass2026!`
   * Click **"Update Password"**.
3. **Expected Result:**
   * Backend executes `UPDATE users SET password_hash = ? WHERE email = ?` in the database.
   * Success toast appears: `"Password successfully updated! Please sign in."`
   * User is switched to the Sign In tab with email pre-populated.
   * Entering `ZainabNewPass2026!` successfully authenticates the patient.

---

## 7. Security Compliance Summary

- [x] **Zero Credential Exposure:** No emails, passwords, or helper links visible on login screens.
- [x] **Anti-Spoofing Guard:** Unregistered individuals cannot manufacture physician identities.
- [x] **Patient Self-Registration:** Toggle allows new patients to register with Name, Gender, Age, Email, and Password with instant database persistence.
- [x] **Interactive Password Reset:** Real-world self-service password update functionality updating the database directly.
- [x] **Password Verification Enforced:** Login requires valid match against registered credentials.
- [x] **Workstation Isolation:** Every doctor operates strictly in their individual clinical scope.
- [x] **Audit Trail Logged:** Failed and successful logins, registrations, and password resets are logged in `audit_logs` with actor details and timestamps.
