"""CRM Admin Dashboard - Quick Start Guide"""

# 🎯 CRM Admin Dashboard - Quick Start

## Overview

ایک مکمل **Streamlit-based CRM Dashboard** جو PostgreSQL سے appointments، workflow history، اور customer data کو manage کرتا ہے۔

---

## ✨ Features

### 📊 Dashboard View
- **Statistics Overview**: Total appointments، confirmed، pending، cancelled
- **Unique Customers**: کتنے الگ الگ customers ہیں
- **Upcoming Appointments**: اگلے 7 دنوں میں کتنی appointments ہیں
- **Recent Appointments**: آخری 20 appointments کی فہرست

### 📋 All Appointments View
- تمام appointments کی مکمل list
- **Status Filter**: Confirmed، Pending، Cancelled، Rescheduled
- **Date Range Filter**: کسی خاص تاریخ کے appointments دیکھیں
- Excel-style table میں data

### 🔍 Search Customer
- فون نمبر سے customer تلاش کریں
- ایک customer کی تمام appointments دیکھیں
- Customer کی مکمل history

### 📋 Appointment Details
- کوئی بھی appointment select کریں
- **Customer Information**: نام، فون، ای میل
- **Property & Agent Details**: پراپرٹی، ایجنٹ، status
- **Appointment Details**: تاریخ، وقت، calendar link
- **Workflow History**: Timeline میں تمام events

### 📥 Export Data
- **CSV Export**: سب appointments کو CSV میں
- **JSON Export**: مکمل data JSON میں
- **Customer Report**: ایک customer کی report
- **Daily Reports**: کسی دن کی appointments

---

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```powershell
cd day3
pip install -r requirements.txt
pip install pandas  # Already in requirements.txt
```

### Step 2: Configure .env

```bash
# day3/.env
DATABASE_URL=postgresql://postgres:Postgres123!@localhost:5432/real_estate
```

### Step 3: Ensure PostgreSQL is Running

```powershell
# Check if PostgreSQL is running
psql -U postgres -d real_estate -c "SELECT 1"

# If Day 4 API hasn't created tables, create them:
psql -U postgres -d real_estate -f ../../day4/schema.sql
```

---

## 📖 Usage

### Run the CRM Dashboard

```powershell
cd day3

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start Streamlit
streamlit run ui/crm_dashboard.py
```

Browser میں کھل جائے گا: `http://localhost:8501`

---

## 📚 Dashboard Sections

### 1️⃣ Dashboard View (Default)

**یہ دیکھیں:**
```
📊 Stats:
  - Total Appointments: 45
  - Confirmed: 32
  - Pending: 8
  - Cancelled: 3
  - Rescheduled: 2
  - Unique Customers: 18
  - Upcoming (7 days): 5

📅 Recent Appointments (Last 20):
  - Table with all appointment details
```

---

### 2️⃣ All Appointments View

**Filters:**
```
- Status: ✅ Select کریں (confirmed/pending/cancelled/rescheduled)
- Date Range: کوئی بھی date range چنیں

Results:
- appointment_id
- customer_name
- client_phone
- property_name
- employee_name
- starts_at
- status
- created_at
```

---

### 3️⃣ Search Customer View

**Input:**
```
Phone Number: +92-300-1234567
or: 03001234567
or: 300-1234567
```

**Output:**
```
✅ Found 5 appointments

Customer Details:
- Name: Ali Khan
- Email: ali@example.com
- Total Bookings: 5

Appointment History:
(تمام appointments کی table)
```

---

### 4️⃣ Appointment Details View

**Steps:**
1. List میں سے کوئی appointment select کریں
2. مکمل details دیکھیں:
   ```
   👤 Customer Info:
   - Name
   - Phone
   - Email
   
   🏠 Property & Agent:
   - Property Name
   - Agent Name
   - Status
   
   📅 Appointment:
   - Date & Time
   - Created/Updated dates
   
   🔗 Calendar:
   - Calendar Event ID
   - Google Meet Link
   
   📝 Notes
   
   📜 Workflow History:
   (Timeline میں تمام events)
   ```

---

## 💾 Export Data

### Python Script سے Export کریں

```powershell
cd day3
python scripts/crm_exporter.py
```

یہ generate کرے گا:
- `crm_export_appointments.csv` — تمام appointments
- `crm_export_appointments.json` — JSON format میں
- `crm_export_today.csv` — آج کی appointments

### Custom Exports (Python میں)

```python
from scripts.crm_exporter import CRMExporter
import os

db_url = os.getenv("DATABASE_URL")
exporter = CRMExporter(db_url)

# Export تمام appointments
exporter.export_to_csv("my_appointments.csv")

# ایک customer کی appointments
exporter.export_customer_appointments_csv("+92-300-1234567", "customer.csv")

# ایک appointment کی workflow history
exporter.export_workflow_history_csv("APT-UUID-HERE", "workflow.csv")

# کسی specific date کی appointments
from datetime import datetime
exporter.export_daily_report(datetime(2026, 9, 2), "2026-09-02.csv")
```

---

## 🔍 Database Queries (Direct)

### تمام Appointments دیکھیں

```sql
SELECT * FROM appointments ORDER BY created_at DESC;
```

### Specific Customer کی Appointments

```sql
SELECT * FROM appointments 
WHERE request_json->>'client_phone' ILIKE '%300-1234567%';
```

### Workflow History

```sql
SELECT * FROM workflow_events 
WHERE appointment_id = 'APT-UUID-HERE'
ORDER BY created_at DESC;
```

### Stats

```sql
SELECT 
  status,
  COUNT(*) as count
FROM appointments
GROUP BY status;
```

---

## 🛠️ Troubleshooting

### ❌ "DATABASE_URL not set in .env"

**Fix:**
```bash
# Check .env file
cat day3/.env | grep DATABASE_URL

# Should output:
# DATABASE_URL=postgresql://postgres:Postgres123!@localhost:5432/real_estate
```

### ❌ "connection refused" (PostgreSQL)

**Fix:**
```powershell
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Start PostgreSQL if not running
# (Platform-specific, usually: services.msc on Windows)
```

### ❌ "No data showing"

**Fix:**
```powershell
# Check if tables exist
psql -U postgres -d real_estate -c "\dt"

# Create tables if missing
cd day4
.\.venv\Scripts\Activate.ps1
python -c "from day4_workflows.crm_logging import PostgresCRMRepository; import asyncio; asyncio.run(PostgresCRMRepository('postgresql://postgres:Postgres123!@localhost:5432/real_estate').initialize())"

# Or run Day 4 API first (creates tables)
uvicorn api.main:app --port 8004
```

---

## 📊 Example Workflow

### Scenario: Customer کی Appointment Track کریں

```
1. Dashboard میں stats دیکھیں
   ↓
2. "Search Customer" میں فون ڈالیں
   ↓
3. تمام appointments دیکھیں
   ↓
4. کسی appointment کو details میں دیکھیں
   ↓
5. Workflow history دیکھیں (booking سے آج تک)
   ↓
6. CSV میں export کریں
```

---

## 🔐 Security Notes

- ✅ PostgreSQL credentials `.env` میں محفوظ ہیں
- ✅ Database connection pooling استعمال ہو رہی ہے
- ✅ SQL injection سے محفوظ (parameterized queries)
- ⚠️ Production میں reverse proxy / authentication add کریں

---

## 📞 Support

**کوئی مسئلہ ہو تو:**

1. `crm_dashboard.py` میں logs دیکھیں
2. Database connection test کریں:
   ```sql
   SELECT COUNT(*) FROM appointments;
   ```
3. Day 4 API check کریں (appointments create ہو رہے ہیں؟)

---

## 🎯 Next Steps

1. ✅ CRM Dashboard چلائیں
2. ✅ Test data کے ساتھ explore کریں
3. ✅ Custom reports بنائیں
4. ✅ Emails/Webhooks integrate کریں
5. ✅ Production میں deploy کریں

---

**Made with ❤️ for Sara Real Estate Platform**
