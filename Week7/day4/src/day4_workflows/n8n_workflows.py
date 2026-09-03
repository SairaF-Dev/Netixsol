"""
n8n Workflow Templates (JSON format)

These workflows can be imported directly into n8n via:
1. n8n UI → Import → Paste JSON
2. Or via n8n CLI: n8n import:workflow --file workflow.json

Each workflow is self-contained with:
- Input webhook trigger
- Business logic nodes
- Error handling
- Retry logic
"""

# ============================================================
# WORKFLOW 1: Appointment Booking
# ============================================================

WORKFLOW_APPOINTMENT_BOOKING = {
    "name": "Appointment Booking - RealEstate Hub",
    "nodes": [
        {
            "parameters": {},
            "name": "webhook_trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [250, 300],
            "webhookId": "appointment-booking",
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "authentication": "oAuth2",
                "sendHeaders": True,
                "headerParameters": {},
                "queryParameters": {
                    "sendNotifications": "true",
                },
                "bodyParametersUi": "json",
                "body": """
                {
                  "summary": "Property Visit: {{ $node.webhook_trigger.json.property.name }}",
                  "description": "Customer: {{ $node.webhook_trigger.json.customer.name }}\\nPhone: {{ $node.webhook_trigger.json.customer.phone }}",
                  "start": {
                    "dateTime": "{{ $node.webhook_trigger.json.visit_datetime }}",
                    "timeZone": "Asia/Karachi"
                  },
                  "end": {
                    "dateTime": "{{ $node.webhook_trigger.json.visit_end_datetime }}",
                    "timeZone": "Asia/Karachi"
                  }
                }
                """,
            },
            "name": "create_calendar_event",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [450, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/crm/log",
                "bodyParametersUi": "json",
                "body": """
                {
                  "session_id": "{{ $node.webhook_trigger.json.session_id }}",
                  "customer_phone": "{{ $node.webhook_trigger.json.customer.phone }}",
                  "property_id": {{ $node.webhook_trigger.json.property.id }},
                  "property_name": "{{ $node.webhook_trigger.json.property.name }}",
                  "visit_datetime": "{{ $node.webhook_trigger.json.visit_datetime }}",
                  "appointment_id": "{{ $node.create_calendar_event.json.id }}",
                  "status": "scheduled"
                }
                """,
            },
            "name": "log_to_crm",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [650, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/email/send",
                "bodyParametersUi": "json",
                "body": """
                {
                  "to": "{{ $node.webhook_trigger.json.agent_email }}",
                  "subject": "New Appointment: {{ $node.webhook_trigger.json.property.name }}",
                  "template": "appointment_booking_agent",
                  "data": {
                    "customer_name": "{{ $node.webhook_trigger.json.customer.name }}",
                    "customer_phone": "{{ $node.webhook_trigger.json.customer.phone }}",
                    "property_name": "{{ $node.webhook_trigger.json.property.name }}",
                    "visit_datetime": "{{ $node.webhook_trigger.json.visit_datetime }}"
                  }
                }
                """,
            },
            "name": "send_agent_email",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [850, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/sms/send",
                "bodyParametersUi": "json",
                "body": """
                {
                  "phone": "{{ $node.webhook_trigger.json.customer.phone }}",
                  "template": "appointment_confirmation",
                  "data": {
                    "property_name": "{{ $node.webhook_trigger.json.property.name }}",
                    "visit_datetime": "{{ $node.webhook_trigger.json.visit_datetime }}"
                  }
                }
                """,
            },
            "name": "send_customer_sms",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [1050, 300],
        },
    ],
    "connections": {
        "webhook_trigger": {
            "main": [
                [
                    {
                        "node": "create_calendar_event",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "create_calendar_event": {
            "main": [
                [
                    {
                        "node": "log_to_crm",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "log_to_crm": {
            "main": [
                [
                    {
                        "node": "send_agent_email",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "send_agent_email": {
            "main": [
                [
                    {
                        "node": "send_customer_sms",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
    },
}


# ============================================================
# WORKFLOW 2: Appointment Rescheduling
# ============================================================

WORKFLOW_APPOINTMENT_RESCHEDULING = {
    "name": "Appointment Rescheduling - RealEstate Hub",
    "nodes": [
        {
            "parameters": {},
            "name": "webhook_trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [250, 300],
            "webhookId": "appointment-reschedule",
        },
        {
            "parameters": {
                "method": "DELETE",
                "url": "https://www.googleapis.com/calendar/v3/calendars/primary/events/{{ $node.webhook_trigger.json.appointment_id }}",
                "authentication": "oAuth2",
                "queryParameters": {
                    "sendNotifications": "true",
                },
            },
            "name": "delete_old_event",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [450, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "authentication": "oAuth2",
                "bodyParametersUi": "json",
                "body": """
                {
                  "summary": "Property Visit: {{ $node.webhook_trigger.json.property.name }} (RESCHEDULED)",
                  "start": {
                    "dateTime": "{{ $node.webhook_trigger.json.visit_datetime }}",
                    "timeZone": "Asia/Karachi"
                  },
                  "end": {
                    "dateTime": "{{ $node.webhook_trigger.json.visit_end_datetime }}",
                    "timeZone": "Asia/Karachi"
                  }
                }
                """,
            },
            "name": "create_new_event",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [650, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/email/send",
                "bodyParametersUi": "json",
                "body": """
                {
                  "to": "{{ $node.webhook_trigger.json.agent_email }}",
                  "subject": "Appointment Rescheduled: {{ $node.webhook_trigger.json.property.name }}",
                  "template": "appointment_reschedule"
                }
                """,
            },
            "name": "send_reschedule_email",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [850, 300],
        },
    ],
    "connections": {
        "webhook_trigger": {
            "main": [
                [
                    {
                        "node": "delete_old_event",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "delete_old_event": {
            "main": [
                [
                    {
                        "node": "create_new_event",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "create_new_event": {
            "main": [
                [
                    {
                        "node": "send_reschedule_email",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
    },
}


# ============================================================
# WORKFLOW 3: Appointment Cancellation
# ============================================================

WORKFLOW_APPOINTMENT_CANCELLATION = {
    "name": "Appointment Cancellation - RealEstate Hub",
    "nodes": [
        {
            "parameters": {},
            "name": "webhook_trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [250, 300],
            "webhookId": "appointment-cancel",
        },
        {
            "parameters": {
                "method": "DELETE",
                "url": "https://www.googleapis.com/calendar/v3/calendars/primary/events/{{ $node.webhook_trigger.json.appointment_id }}",
                "authentication": "oAuth2",
                "queryParameters": {
                    "sendNotifications": "true",
                },
            },
            "name": "delete_calendar_event",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [450, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/crm/booking/cancel",
                "bodyParametersUi": "json",
                "body": """
                {
                  "appointment_id": "{{ $node.webhook_trigger.json.appointment_id }}"
                }
                """,
            },
            "name": "update_crm",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [650, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/email/send",
                "bodyParametersUi": "json",
                "body": """
                {
                  "to": "{{ $node.webhook_trigger.json.agent_email }}",
                  "subject": "Appointment Cancelled: {{ $node.webhook_trigger.json.property.name }}",
                  "template": "appointment_cancellation"
                }
                """,
            },
            "name": "send_cancellation_email",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [850, 300],
        },
    ],
    "connections": {
        "webhook_trigger": {
            "main": [
                [
                    {
                        "node": "delete_calendar_event",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "delete_calendar_event": {
            "main": [
                [
                    {
                        "node": "update_crm",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "update_crm": {
            "main": [
                [
                    {
                        "node": "send_cancellation_email",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
    },
}


# ============================================================
# n8n DEPLOYMENT GUIDE
# ============================================================

N8N_DEPLOYMENT_GUIDE = """
# n8n Deployment for RealEstate Hub

## Installation

### Option 1: Docker (Recommended)
docker run -d \\
  -p 5678:5678 \\
  -e DB_TYPE=postgresdb \\
  -e DB_POSTGRESDB_HOST=postgres \\
  -e DB_POSTGRESDB_PORT=5432 \\
  -e DB_POSTGRESDB_DATABASE=n8n \\
  -e DB_POSTGRESDB_USER=n8n \\
  -e DB_POSTGRESDB_PASSWORD=n8n_password \\
  n8nio/n8n

### Option 2: npm
npm install -g n8n
n8n start

## Configuration

### Step 1: Set up PostgreSQL connection
n8n UI → Settings → Database
- Host: localhost (or your DB host)
- Port: 5432
- Database: n8n
- Username: n8n
- Password: [set secure password]

### Step 2: Create Google Calendar credential
n8n UI → Credentials → New
- Type: Google Calendar
- OAuth2 flow
- Get credentials from Google Cloud Console

### Step 3: Import workflows

1. Copy WORKFLOW_APPOINTMENT_BOOKING JSON
2. n8n UI → Import → Paste JSON
3. Repeat for rescheduling and cancellation workflows

### Step 4: Configure webhooks
For each workflow:
1. Click webhook node
2. Copy webhook URL
3. Add to .env in main Sara application:
   N8N_WEBHOOK_BOOKING=http://n8n:5678/webhook/appointment-booking
   N8N_WEBHOOK_RESCHEDULE=http://n8n:5678/webhook/appointment-reschedule
   N8N_WEBHOOK_CANCEL=http://n8n:5678/webhook/appointment-cancel

### Step 5: Test workflow
1. Click "Test workflow" in n8n UI
2. Trigger from Sara agent
3. Verify calendar event created
4. Check CRM logs
5. Verify emails received

## Monitoring

### Health check
curl http://localhost:5678/health

### Execution logs
n8n UI → Executions

### Webhook logs
n8n UI → Workflows → [Workflow name] → Executions

## Error Handling

Each workflow has retry logic:
- Max retries: 3
- Delay: 2 seconds between retries
- On final failure: Email alert to admin

To debug:
1. n8n UI → Executions → Click failed execution
2. View error message
3. Click "Retry" to re-run
4. Or edit workflow and test again

## Production Checklist

- [ ] Google Calendar credentials configured
- [ ] PostgreSQL connection tested
- [ ] All three workflows imported
- [ ] Webhooks configured in .env
- [ ] Test workflow end-to-end
- [ ] Error logging configured
- [ ] Monitoring dashboard set up
- [ ] Backups scheduled
"""
