"""CRM API Integration Guide - Access CRM Data Programmatically"""

# 🔌 CRM API Integration Guide

## Overview

Day 4 API appointments کو manage کرتی ہے اور PostgreSQL میں store کرتی ہے۔ یہاں CRM data کو direct API اور database سے access کرنے کے طریقے ہیں۔

---

## 1. Day 4 Appointments API

### ✅ Book an Appointment

```bash
curl -X POST http://localhost:8004/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Ali Khan",
    "client_phone": "+92-300-1234567",
    "client_email": "ali@example.com",
    "employee_name": "Sara Agent",
    "employee_email": "agent@realestateub.com",
    "employee_calendar_id": "primary",
    "property_id": 1,
    "property_name": "DHA Phase 6 Apartment",
    "starts_at": "2026-09-06T15:00:00+05:00",
    "duration_minutes": 60,
    "meeting_notes": "Client interested in 3-bedroom apartment"
  }'
```

**Response:**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "confirmed",
    "client_name": "Ali Khan",
    "client_phone": "+92-300-1234567",
    "property_name": "DHA Phase 6 Apartment",
    "starts_at": "2026-09-06T15:00:00+05:00",
    "calendar_link": "https://meet.google.com/...",
    "created_at": "2026-09-02T12:00:00+05:00"
  },
  "notification_sent": true,
  "warnings": []
}
```

---

### ✅ Get Appointment Details

```bash
curl http://localhost:8004/appointments/550e8400-e29b-41d4-a716-446655440000
```

**Note:** Current API doesn't have GET endpoint, use PostgreSQL directly.

---

### ✅ Reschedule an Appointment

```bash
curl -X PATCH http://localhost:8004/appointments/550e8400-e29b-41d4-a716-446655440000/reschedule \
  -H "Content-Type: application/json" \
  -d '{
    "starts_at": "2026-09-07T14:00:00+05:00"
  }'
```

**Response:**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "rescheduled",
    "starts_at": "2026-09-07T14:00:00+05:00",
    "previous_starts_at": "2026-09-06T15:00:00+05:00"
  },
  "notification_sent": true
}
```

---

### ✅ Cancel an Appointment

```bash
curl -X DELETE http://localhost:8004/appointments/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled"
  },
  "notification_sent": true
}
```

---

### ✅ Health Check

```bash
curl http://localhost:8004/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "day4-workflows"
}
```

---

## 2. Direct PostgreSQL Access

### Connection String
```
postgresql://postgres:Postgres123!@localhost:5432/real_estate
```

---

### ✅ Get All Appointments

```sql
SELECT 
  appointment_id,
  status,
  request_json->>'client_name' as client_name,
  request_json->>'client_phone' as client_phone,
  request_json->>'property_name' as property_name,
  (request_json->>'starts_at')::timestamp as starts_at,
  created_at,
  updated_at
FROM appointments
ORDER BY created_at DESC
LIMIT 20;
```

---

### ✅ Search Customer by Phone

```sql
SELECT * FROM appointments
WHERE request_json->>'client_phone' ILIKE '%300-1234567%'
ORDER BY created_at DESC;
```

---

### ✅ Get Appointment with Full Details

```sql
SELECT 
  appointment_id,
  status,
  request_json,
  calendar_event_id,
  calendar_link,
  created_at,
  updated_at
FROM appointments
WHERE appointment_id = '550e8400-e29b-41d4-a716-446655440000';
```

---

### ✅ Get Workflow History for an Appointment

```sql
SELECT 
  id,
  event_type,
  payload,
  created_at
FROM workflow_events
WHERE appointment_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY created_at DESC;
```

---

### ✅ Dashboard Statistics

```sql
-- Total appointments by status
SELECT 
  status,
  COUNT(*) as count
FROM appointments
GROUP BY status;

-- Appointments for a specific date
SELECT COUNT(*) as today_appointments
FROM appointments
WHERE DATE((request_json->>'starts_at')::timestamp) = CURRENT_DATE;

-- Upcoming appointments (next 7 days)
SELECT COUNT(*) as upcoming
FROM appointments
WHERE (request_json->>'starts_at')::timestamp 
BETWEEN NOW() AND NOW() + INTERVAL '7 days'
AND status IN ('confirmed', 'pending');

-- Unique customers
SELECT COUNT(DISTINCT request_json->>'client_phone') as unique_customers
FROM appointments;

-- Appointments per agent
SELECT 
  request_json->>'employee_name' as agent,
  COUNT(*) as total_appointments
FROM appointments
GROUP BY request_json->>'employee_name'
ORDER BY total_appointments DESC;
```

---

## 3. Python/HTTP Client Access

### Python Example - Using httpx

```python
import httpx
from datetime import datetime

# Initialize client
client = httpx.Client(base_url="http://localhost:8004")

# Book appointment
response = client.post(
    "/appointments",
    json={
        "client_name": "Ahmed Hassan",
        "client_phone": "+92-300-9876543",
        "client_email": "ahmed@example.com",
        "employee_name": "Sara Agent",
        "employee_email": "agent@realestateub.com",
        "property_id": 1,
        "property_name": "Gulshan Apartment",
        "starts_at": "2026-09-10T10:00:00+05:00",
        "duration_minutes": 60,
        "meeting_notes": "Walk-in customer"
    }
)

if response.status_code == 201:
    appointment = response.json()
    print(f"✅ Appointment booked: {appointment['appointment']['appointment_id']}")
else:
    print(f"❌ Error: {response.text}")

# Reschedule
apt_id = appointment['appointment']['appointment_id']
response = client.patch(
    f"/appointments/{apt_id}/reschedule",
    json={"starts_at": "2026-09-11T14:00:00+05:00"}
)

if response.status_code == 200:
    print("✅ Appointment rescheduled")

# Cancel
response = client.delete(f"/appointments/{apt_id}")
if response.status_code == 200:
    print("✅ Appointment cancelled")
```

---

### Python Example - Direct Database

```python
import psycopg
from psycopg.rows import dict_row

db_url = "postgresql://postgres:Postgres123!@localhost:5432/real_estate"

with psycopg.connect(db_url) as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        # Get all appointments
        cur.execute("""
            SELECT appointment_id, status, 
                   request_json->>'client_name' as client_name,
                   request_json->>'property_name' as property_name
            FROM appointments
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        for row in cur.fetchall():
            print(f"{row['client_name']} - {row['property_name']} ({row['status']})")
        
        # Search customer
        cur.execute("""
            SELECT * FROM appointments
            WHERE request_json->>'client_phone' LIKE %s
        """, ("+92-300-1234567",))
        
        appointments = cur.fetchall()
        print(f"Found {len(appointments)} appointments")
```

---

## 4. Day 5 LangGraph Integration

### Available Tools

```python
# From day5/src/day5_langgraph/tools.py

from day5_langgraph.tools import ToolExecutor

executor = ToolExecutor(day4_api_url="http://localhost:8004")

# Search properties
result = await executor.search_properties(
    location="Lahore",
    min_price=2000000,
    max_price=5000000,
    bedrooms=3,
    purpose="buy"
)

# Get property details
result = await executor.get_property_details(property_id=1)

# Book appointment
result = await executor.book_appointment(
    client_name="Ali Khan",
    client_phone="+92-300-1234567",
    employee_name="Sara Agent",
    employee_email="agent@realestateub.com",
    property_id=1,
    property_name="DHA Phase 6",
    starts_at="2026-09-06T15:00:00+05:00",
    duration_minutes=60,
    meeting_notes="Customer inquiry"
)

# Reschedule
result = await executor.reschedule_appointment(
    appointment_id="550e8400-e29b-41d4-a716-446655440000",
    starts_at="2026-09-07T14:00:00+05:00"
)

# Cancel
result = await executor.cancel_appointment(
    appointment_id="550e8400-e29b-41d4-a716-446655440000"
)

# Get customer history
result = await executor.get_customer_history(
    phone="+92-300-1234567"
)
```

---

## 5. CRM Export Data

### Via Python Script

```python
from scripts.crm_exporter import CRMExporter
import os

db_url = os.getenv("DATABASE_URL")
exporter = CRMExporter(db_url)

# Export all to CSV
exporter.export_to_csv("appointments.csv")

# Export all to JSON
exporter.export_to_json("appointments.json")

# Export specific customer
exporter.export_customer_appointments_csv(
    "+92-300-1234567",
    "customer_history.csv"
)

# Export workflow history
exporter.export_workflow_history_csv(
    "550e8400-e29b-41d4-a716-446655440000",
    "workflow.csv"
)

# Export daily report
from datetime import datetime
exporter.export_daily_report(
    datetime(2026, 9, 6),
    "2026-09-06_appointments.csv"
)
```

---

## 6. Error Handling

### API Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 201 | Created | ✅ Appointment booked |
| 200 | OK | ✅ Operation successful |
| 409 | Conflict | ⚠️ Slot unavailable or invalid state |
| 404 | Not Found | ❌ Appointment not found |
| 422 | Validation Error | ❌ Invalid input |
| 500 | Server Error | ❌ Internal error |

### Example Error Handling

```python
try:
    response = client.post(
        "/appointments",
        json=booking_data
    )
    response.raise_for_status()  # Raise on 4xx/5xx
    
except httpx.HTTPStatusError as e:
    if e.response.status_code == 409:
        print("❌ Slot unavailable")
    elif e.response.status_code == 422:
        print(f"❌ Validation error: {e.response.text}")
    else:
        print(f"❌ Error: {e}")
except Exception as e:
    print(f"❌ Connection error: {e}")
```

---

## 7. Common Queries

### Find All Appointments for Tomorrow

```sql
SELECT * FROM appointments
WHERE DATE((request_json->>'starts_at')::timestamp) = CURRENT_DATE + 1
ORDER BY (request_json->>'starts_at')::timestamp;
```

### Count Appointments by Property

```sql
SELECT 
  request_json->>'property_name' as property,
  COUNT(*) as total
FROM appointments
GROUP BY property_name
ORDER BY total DESC;
```

### Get Cancellation Rate

```sql
SELECT 
  status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM appointments), 2) as percentage
FROM appointments
GROUP BY status;
```

### Find Customers with Multiple Bookings

```sql
SELECT 
  request_json->>'client_phone' as phone,
  request_json->>'client_name' as name,
  COUNT(*) as total_bookings
FROM appointments
GROUP BY client_phone, client_name
HAVING COUNT(*) > 1
ORDER BY total_bookings DESC;
```

---

## 8. Integration Examples

### Integration with Day 7 VAPI

```python
# In day7/vapi_integration/tool_handler.py
import httpx

class VapiToolHandler:
    def __init__(self):
        self.day4_url = "http://localhost:8004"
    
    async def _book_appointment(self, args: dict) -> str:
        """Book appointment via Day 4 API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.day4_url}/appointments",
                json=args
            )
            result = response.json()
            
            # Confirm to customer
            return f"✅ Appointment confirmed: {result['appointment']['starts_at']}"
```

---

## 9. Real-World Workflow

```
Customer Call (VAPI Day 7)
    ↓
Intent: "Property visit چاہیے"
    ↓
LangGraph (Day 5) collects details
    ↓
Calls: POST /appointments (Day 4)
    ↓
PostgreSQL stores appointment
    ↓
Calendar event created
    ↓
Email notification sent
    ↓
Workflow event logged
    ↓
CRM Dashboard updated (real-time)
```

---

## Support & Troubleshooting

### ❓ Appointment not showing in CRM?

```bash
# Check if Day 4 API is running
curl http://localhost:8004/health

# Check database tables
psql -U postgres -d real_estate -c "SELECT COUNT(*) FROM appointments;"
```

### ❓ PostgreSQL connection error?

```bash
# Test connection
psql -U postgres -d real_estate -c "\dt"

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

### ❓ Calendar integration not working?

```bash
# Check if Google Calendar is configured
grep -i google day4/.env

# Verify service account credentials
cat day4/credentials.json
```

---

**Happy CRM Management! 🎉**
