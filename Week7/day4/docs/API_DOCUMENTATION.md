# Day 4 Appointment Workflows API Documentation

## Overview

The Day 4 Workflows API provides a production-grade appointment management system for real estate bookings, rescheduling, and cancellations. It integrates with Google Calendar, email notifications, CRM logging, and n8n workflow automation.

## Base URL

```
http://localhost:8004
```

## Authentication

Currently, the API uses environment variables for credentials. In production, implement API key authentication:

```
Authorization: Bearer <API_KEY>
```

## Health Check

### GET /health

Check if the service is running and operational.

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "day4-workflows"
}
```

## Appointments

### POST /appointments

Book a new property visit appointment.

**Request Body:**
```json
{
  "session_id": "uuid (auto-generated if omitted)",
  "client_name": "Ali Khan",
  "client_phone": "+923001234567",
  "client_email": "ali@example.com",
  "employee_name": "Sara Ahmed",
  "employee_email": "sara@example.com",
  "employee_calendar_id": "primary",
  "property_id": 101,
  "property_name": "Horizon Heights DHA",
  "starts_at": "2030-01-05T11:00:00+05:00",
  "duration_minutes": 60,
  "meeting_notes": "Bring keys, show corner unit"
}
```

**Validation Rules:**
- `client_name`: 2-120 characters
- `client_phone`: 7-15 digits (+ - () allowed)
- `employee_name`: 2-120 characters
- `property_id`: positive integer
- `property_name`: 2-255 characters
- `starts_at`: ISO 8601 with timezone (required)
- `duration_minutes`: 15-240 (default 60)
- `meeting_notes`: max 2000 characters
- `client_email` and `employee_email`: valid email format

**Response (201 Created):**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "request": { /* echo of request */ },
    "status": "confirmed",
    "calendar_event_id": "abc123def456",
    "calendar_link": "https://calendar.google.com/calendar/u/0/r/eventedit/abc123",
    "created_at": "2030-01-04T10:00:00+05:00",
    "updated_at": "2030-01-04T10:00:00+05:00",
    "previous_starts_at": null
  },
  "notification_sent": true,
  "workflow_event_id": "event-uuid-here",
  "warnings": []
}
```

**Error Responses:**

- **409 Conflict** - Slot unavailable
  ```json
  {
    "detail": "The selected employee is not available at that time"
  }
  ```

- **422 Unprocessable Entity** - Validation error
  ```json
  {
    "detail": [
      {
        "type": "value_error",
        "loc": ["body", "client_phone"],
        "msg": "phone must contain 7 to 15 digits"
      }
    ]
  }
  ```

### PATCH /appointments/{appointment_id}/reschedule

Reschedule an existing appointment to a different time.

**Path Parameters:**
- `appointment_id`: UUID of the appointment to reschedule

**Request Body:**
```json
{
  "starts_at": "2030-01-06T14:00:00+05:00"
}
```

**Response (200 OK):**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "request": { /* updated with new starts_at */ },
    "status": "rescheduled",
    "calendar_event_id": "abc123def456",
    "calendar_link": "https://calendar.google.com/...",
    "created_at": "2030-01-04T10:00:00+05:00",
    "updated_at": "2030-01-04T15:30:00+05:00",
    "previous_starts_at": "2030-01-05T11:00:00+05:00"
  },
  "notification_sent": true,
  "workflow_event_id": "event-uuid-here",
  "warnings": []
}
```

**Error Responses:**

- **404 Not Found** - Appointment does not exist
- **409 Conflict** - Slot unavailable or invalid state (e.g., cancelled appointment)

### DELETE /appointments/{appointment_id}

Cancel an appointment and remove it from the calendar.

**Path Parameters:**
- `appointment_id`: UUID of the appointment to cancel

**Response (200 OK):**
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "request": { /* original request */ },
    "status": "cancelled",
    "calendar_event_id": null,
    "calendar_link": null,
    "created_at": "2030-01-04T10:00:00+05:00",
    "updated_at": "2030-01-04T16:00:00+05:00",
    "previous_starts_at": null
  },
  "notification_sent": true,
  "workflow_event_id": "event-uuid-here",
  "warnings": []
}
```

**Error Responses:**

- **404 Not Found** - Appointment does not exist
- **409 Conflict** - Appointment already cancelled

## Appointment Status Transitions

```
PENDING
  ├─ (book) → CONFIRMED
  └─ (error) → remains PENDING

CONFIRMED
  ├─ (reschedule) → RESCHEDULED
  └─ (cancel) → CANCELLED

RESCHEDULED
  ├─ (reschedule again) → RESCHEDULED
  └─ (cancel) → CANCELLED

CANCELLED
  └─ (no further transitions allowed)
```

## Integration Workflows

### Calendar Integration (Google Calendar)

- `CALENDAR_BACKEND=google` enables Google Calendar
- Service account credentials are loaded from `GOOGLE_SERVICE_ACCOUNT_FILE`
- Each employee calendar must be shared with the service account email
- Calendar ID is specified per appointment as `employee_calendar_id`
- Availability is checked before creation/update/cancellation

### Email Notifications

- `SMTP_HOST` and `SMTP_PORT` enable email notifications
- If empty, emails are logged in-memory (development mode)
- Email includes appointment details and Google Calendar link
- Email failures log warnings but don't block the appointment

### CRM Logging (PostgreSQL)

- `DATABASE_URL` starting with `postgres://` or `postgresql://` enables PostgreSQL
- Otherwise uses in-memory storage (development mode)
- All appointments and workflow events are persisted
- Tables: `appointments`, `workflow_events`

### n8n Workflow Automation

- `N8N_WEBHOOK_URL` enables n8n event publishing
- Events published: `appointment.booked`, `appointment.rescheduled`, `appointment.cancelled`
- Max retries: `WORKFLOW_MAX_ATTEMPTS` (default 3)
- Timeout: `WORKFLOW_TIMEOUT_SECONDS` (default 8)
- Failures result in warnings, not API errors

## Example Workflow

### Booking → Reschedule → Cancel

```bash
# 1. Book an appointment
curl -X POST http://localhost:8004/appointments \
  -H "Content-Type: application/json" \
  -d @booking.json

# Response includes appointment_id (e.g., "550e8400-e29b-41d4-a716-446655440000")

# 2. Reschedule the appointment
curl -X PATCH http://localhost:8004/appointments/550e8400-e29b-41d4-a716-446655440000/reschedule \
  -H "Content-Type: application/json" \
  -d '{"starts_at": "2030-01-06T14:00:00+05:00"}'

# 3. Cancel the appointment
curl -X DELETE http://localhost:8004/appointments/550e8400-e29b-41d4-a716-446655440000
```

## Status Codes

| Code | Meaning |
|------|---------|
| 200  | OK - Request succeeded |
| 201  | Created - Appointment booked |
| 404  | Not Found - Appointment does not exist |
| 409  | Conflict - Slot unavailable or invalid state |
| 422  | Unprocessable Entity - Validation failed |
| 500  | Internal Server Error |

## Common Errors

### Email Failure Example

If SMTP is misconfigured:
```json
{
  "appointment": { /* valid appointment */ },
  "notification_sent": false,
  "warnings": ["Email notification failed: EmailError"]
}
```

The appointment is still created and confirmed in Calendar/CRM. The warning allows the caller to retry email or escalate.

### Overlapping Slots

```bash
# First appointment OK
curl -X POST http://localhost:8004/appointments \
  -d '{"starts_at": "2030-01-05T11:00:00+05:00", ...}'

# Second appointment by same employee → 409
curl -X POST http://localhost:8004/appointments \
  -d '{"starts_at": "2030-01-05T11:30:00+05:00", ...}'
```

Result:
```json
{
  "detail": "The selected employee is not available at that time"
}
```

## Rate Limiting

Not currently implemented. Add in production using FastAPI middleware.

## Webhooks (for n8n)

The API publishes events to n8n:

```
POST {N8N_WEBHOOK_URL}
```

Payload:
```json
{
  "event_id": "unique-event-uuid",
  "event_type": "appointment.booked|rescheduled|cancelled",
  "payload": {
    "appointment": { /* full appointment object */ },
    ...
  }
}
```

Headers:
```
X-Workflow-Event-Id: <event_id>
Authorization: Bearer <N8N_API_KEY> (if configured)
```

## Monitoring & Debugging

### Health Check
```bash
curl http://localhost:8004/health
```

### View Logs

In-memory mode (development):
- Calendar events logged in `InMemoryCalendarGateway.events`
- Email messages logged in `InMemoryEmailGateway.messages`
- CRM events logged in `InMemoryCRMRepository.events`

PostgreSQL mode:
```sql
SELECT * FROM appointments ORDER BY created_at DESC LIMIT 10;
SELECT * FROM workflow_events WHERE appointment_id = 'uuid' ORDER BY created_at;
```

## Future Enhancements

- API key authentication
- Rate limiting per API key
- Idempotency keys for safe retries
- Batch operations (book multiple appointments)
- Calendar availability reporting
- WhatsApp/SMS integration
- Salesforce CRM integration
- Analytics dashboard
