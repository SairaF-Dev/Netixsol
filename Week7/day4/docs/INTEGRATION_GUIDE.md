# Day 4 Integration Guide

## Day 3 → Day 4 Handoff

The voice agent (Day 3) communicates with the appointment service (Day 4) through structured handoff.

### Day 3 Memory Output

The Day 3 `memory.pending_action` contains:

```json
{
  "type": "schedule_visit" | "reschedule_visit" | "cancel_visit",
  "property": {
    "property_id": 101,
    "name": "Horizon Heights",
    "location": "DHA",
    "price": 50000000,
    "bedrooms": 3,
    "amenities": ["Pool", "Gym"]
  }
}
```

### Integration Points

#### 1. Schedule New Visit

**Day 3 Calls Day 4 API**:
```python
import httpx

# From Day 3 LangGraph agent
async def handle_book_appointment(state):
    pending_action = state["memory"]["pending_action"]
    
    booking_request = {
        "client_name": state["user_profile"]["name"],
        "client_phone": state["user_profile"]["phone"],
        "client_email": state["user_profile"].get("email"),
        "employee_name": "Sara Ahmed",  # or assign dynamically
        "employee_email": "sara@example.com",
        "employee_calendar_id": "primary",
        "property_id": pending_action["property"]["property_id"],
        "property_name": pending_action["property"]["name"],
        "starts_at": state["proposed_appointment"]["starts_at"],  # from calendar check
        "duration_minutes": 60,
        "meeting_notes": state["conversation_context"]["notes"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8004/appointments",
            json=booking_request
        )
        result = response.json()
        
        # Store in state for confirmation
        state["appointment"] = result["appointment"]
        state["warnings"] = result["warnings"]
        
        return state
```

**Day 4 Response** (201 Created):
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "confirmed",
    "calendar_event_id": "abc123",
    "calendar_link": "https://calendar.google.com/...",
    "created_at": "2030-01-04T10:00:00+05:00"
  },
  "notification_sent": true,
  "warnings": []
}
```

**Day 3 Confirmation to Caller**:
```
"Bilkul sir! Appointment confirm ho gaya. Aap ke liye 5 January ko 11 AM par 
property visit schedule hai. Email confirmation bheji jae gi."
```

#### 2. Reschedule Existing Appointment

**Day 3 Calls Day 4 API**:
```python
async def handle_reschedule(state):
    appointment_id = state["memory"]["current_appointment"]["appointment_id"]
    new_time = state["proposed_appointment"]["starts_at"]
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"http://localhost:8004/appointments/{appointment_id}/reschedule",
            json={"starts_at": new_time}
        )
        result = response.json()
        
        state["appointment"] = result["appointment"]
        state["warnings"] = result["warnings"]
        
        return state
```

**Day 4 Response** (200 OK):
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "rescheduled",
    "previous_starts_at": "2030-01-05T11:00:00+05:00",
    "created_at": "2030-01-04T10:00:00+05:00",
    "updated_at": "2030-01-04T16:00:00+05:00"
  },
  "notification_sent": true,
  "warnings": []
}
```

**Day 3 Confirmation**:
```
"Appointment reschedule ho gaya. Ab 6 January ko 2 PM par hai. 
Employee ko notification bheji ja chuki hai."
```

#### 3. Cancel Appointment

**Day 3 Calls Day 4 API**:
```python
async def handle_cancellation(state):
    appointment_id = state["memory"]["current_appointment"]["appointment_id"]
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:8004/appointments/{appointment_id}"
        )
        result = response.json()
        
        state["appointment"] = result["appointment"]
        state["warnings"] = result["warnings"]
        
        return state
```

**Day 4 Response** (200 OK):
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "created_at": "2030-01-04T10:00:00+05:00",
    "updated_at": "2030-01-04T17:00:00+05:00"
  },
  "notification_sent": true,
  "warnings": []
}
```

**Day 3 Confirmation**:
```
"Appointment cancel ho gaya. Employee ko notification bheji ja chuki hai."
```

---

## Calendar Integration (Google Calendar)

### How It Works

1. **Availability Check**:
   - Before booking, API checks employee's Google Calendar
   - Overlapping slots are rejected with 409 Conflict
   - Day 3 can ask for alternative times

2. **Event Creation**:
   - Confirmed booking creates Google Calendar event
   - Event title: "Property visit: Horizon Heights"
   - Event description includes client details, property, notes

3. **Event Update**:
   - Reschedule updates existing event with new time
   - All attendees receive email notification from Google

4. **Event Cancellation**:
   - Cancel deletes event from calendar
   - Google sends cancellation emails

### Setup

1. Create Google service account ([see deployment guide](DEPLOYMENT.md#google-calendar-integration))
2. Share employee calendars with service account email
3. Set `CALENDAR_BACKEND=google` and `GOOGLE_SERVICE_ACCOUNT_FILE` in .env

### Employee Calendar IDs

Google Calendar ID is typically:
- **Personal**: `primary`
- **Shared**: `email@example.com`
- **Resource**: UUID-like format

Pass via API:
```json
{
  "employee_calendar_id": "primary",
  ...
}
```

Or store in employee database and look up by employee_name.

---

## Email Integration

### What Gets Emailed

**On Booking**:
- Recipient: Employee email
- Subject: "New appointment: Horizon Heights"
- Body: Client name, phone, property, date/time, notes, Google Calendar link

**On Reschedule**:
- Subject: "Appointment rescheduled: Horizon Heights"
- Body: Old time, new time, client details

**On Cancellation**:
- Subject: "Appointment cancelled: Horizon Heights"
- Body: Original appointment details, cancellation reason

### HTML Email Template

The email is both plain text and HTML for compatibility.

HTML includes:
- Property name and details
- Client contact info
- Appointment date and time with timezone
- Direct link to Google Calendar event
- Professional branding

### Email Failures

If SMTP fails:
- Appointment is still created/updated/cancelled in Calendar and CRM
- `notification_sent: false` in response
- Warning message explains the failure
- Day 3 can offer to email manually or escalate

---

## CRM Logging (PostgreSQL)

### Schema

**appointments** table:
```sql
appointment_id UUID PRIMARY KEY
session_id UUID              -- Links to Day 3 session
status TEXT                  -- pending, confirmed, rescheduled, cancelled
request_json JSONB           -- Full booking request
calendar_event_id TEXT       -- Google event ID
calendar_link TEXT           -- Google event URL
previous_starts_at TIMESTAMPTZ  -- For reschedules
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

**workflow_events** table:
```sql
id BIGSERIAL PRIMARY KEY
appointment_id UUID REFERENCES appointments
event_type TEXT              -- booked, rescheduled, cancelled
payload JSONB                -- Full event payload
created_at TIMESTAMPTZ
```

### Querying

**Find all appointments for a session**:
```sql
SELECT * FROM appointments WHERE session_id = 'uuid';
```

**View appointment history**:
```sql
SELECT event_type, payload->>'appointment'->>'status', created_at 
FROM workflow_events 
WHERE appointment_id = 'uuid'
ORDER BY created_at;
```

**Stats**:
```sql
SELECT COUNT(*), status FROM appointments GROUP BY status;
SELECT DATE(created_at), COUNT(*) 
FROM appointments 
WHERE status = 'confirmed' 
GROUP BY DATE(created_at);
```

### Day 3 Access to CRM

Day 3 LangGraph can query PostgreSQL for customer history:

```python
import psycopg

async def get_customer_history(customer_phone: str):
    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        rows = conn.execute(
            """
            SELECT appointment_id, status, request_json->>'property_name', 
                   created_at
            FROM appointments
            WHERE request_json->>'client_phone' = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (customer_phone,)
        ).fetchall()
        
        return rows
```

Use cases:
- Recognize returning customers
- Show previous properties they viewed
- Suggest new properties based on history
- Handle follow-ups

---

## n8n Workflow Integration

### Event Publishing

Day 4 publishes events to n8n whenever appointments change:

```
POST {N8N_WEBHOOK_URL}

{
  "event_id": "unique-uuid",
  "event_type": "appointment.booked|rescheduled|cancelled",
  "payload": {
    "appointment": { /* full appointment object */ },
    "notification_sent": true,
    "warnings": []
  }
}
```

### Receiving in n8n

1. Create n8n workflow with **Webhook** trigger
2. Path: `/appointments`
3. Method: `POST`
4. Receive appointment event

### n8n Workflow Actions

**Booking**:
```
Webhook → Extract property → Update Salesforce → Send Slack → Log Analytics
```

**Reschedule**:
```
Webhook → Validate → Update CRM → Notify manager → Send SMS to client
```

**Cancellation**:
```
Webhook → Delete from CRM → Release lead → Archive conversation
```

### Example n8n Node

**Update Salesforce Opportunity**:
```json
{
  "name": "Update Salesforce",
  "type": "n8n-nodes-base.salesforce",
  "parameters": {
    "resource": "opportunity",
    "operation": "update",
    "id": "={{$json.payload.request.property_id}}",
    "body": {
      "StageName": "Presentation Scheduled",
      "NextStep": "Property visit on {{$json.payload.request.starts_at}}"
    }
  }
}
```

### Webhook Configuration

In `.env`:
```bash
N8N_WEBHOOK_URL=https://n8n.example.com/webhook/apartments/appointments
N8N_API_KEY=sk_live_xxx
WORKFLOW_TIMEOUT_SECONDS=8
WORKFLOW_MAX_ATTEMPTS=3
```

The API retries failed n8n calls up to 3 times with exponential backoff.

---

## Error Handling

### Graceful Degradation

If any subsystem fails:

| Failure | Behavior |
|---------|----------|
| Calendar fails | Booking rejected (409) |
| Email fails | Booking succeeds, warning logged |
| CRM fails | Booking succeeds, warning logged |
| n8n times out | Booking succeeds, warning logged |

**Philosophy**: Confirmed appointments are authoritative. Notifications are best-effort.

### Day 3 Error Handling

When Day 4 returns 409 (Slot Unavailable):

```python
async def handle_booking_error(state, error):
    if error.status_code == 409:
        # Day 3 should offer alternatives
        state["message"] = "Yeh time available nahi hai. Kya doosra time ho sakta hai?"
        state["intent"] = "ask_alternative_time"
    elif error.status_code == 422:
        # Validation failed - ask user to provide correct info
        state["message"] = "Phone number غلط ہے. Brabar number de."
    
    return state
```

### Retry Logic

For transient failures (n8n timeout), retry automatically.

For permanent failures (invalid email), log and alert.

---

## Monitoring & Observability

### Metrics to Track

- **Booking rate**: appointments/hour
- **Success rate**: booked / attempted
- **Average latency**: from request to response
- **Email success rate**: sent / attempts
- **Calendar availability**: free slots / total
- **CRM latency**: database queries

### Alerting

Set up alerts for:
- Booking success rate < 95%
- Email success rate < 90%
- API latency > 2 seconds
- Database connection errors
- n8n webhook failures > 3 retries

### Day 3 Integration Metrics

- Conversation success rate
- Booking completion rate
- Time to book (conversation duration)
- Objection handling effectiveness
- Rescheduling frequency

---

## Testing Integration

### Local Test

```python
import asyncio
import httpx
from datetime import datetime, timedelta, timezone

async def test_booking_e2e():
    request = {
        "client_name": "Test Client",
        "client_phone": "+923001234567",
        "employee_name": "Sara",
        "employee_email": "sara@example.com",
        "property_id": 101,
        "property_name": "Test Property",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "duration_minutes": 60,
        "meeting_notes": "Test booking"
    }
    
    async with httpx.AsyncClient() as client:
        # Book
        response = await client.post(
            "http://localhost:8004/appointments",
            json=request
        )
        assert response.status_code == 201
        appointment = response.json()["appointment"]
        appointment_id = appointment["appointment_id"]
        
        # Reschedule
        new_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        response = await client.patch(
            f"http://localhost:8004/appointments/{appointment_id}/reschedule",
            json={"starts_at": new_time}
        )
        assert response.status_code == 200
        assert response.json()["appointment"]["status"] == "rescheduled"
        
        # Cancel
        response = await client.delete(
            f"http://localhost:8004/appointments/{appointment_id}"
        )
        assert response.status_code == 200
        assert response.json()["appointment"]["status"] == "cancelled"
        
        print("✓ End-to-end test passed!")

asyncio.run(test_booking_e2e())
```

---

## Future Enhancements

### Phase 2
- [ ] Bulk appointment operations
- [ ] Availability calendar API
- [ ] SMS notifications
- [ ] WhatsApp integration

### Phase 3
- [ ] Salesforce bidirectional sync
- [ ] HubSpot CRM integration
- [ ] Stripe payment collection
- [ ] Lead scoring

### Phase 4
- [ ] Predictive availability
- [ ] ML-based rescheduling
- [ ] Multi-language support
- [ ] Analytics dashboard
