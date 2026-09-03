# Sara n8n Appointment Automation

## Flow

1. Sara calls an appointment tool through the VAPI webhook.
2. `VapiToolHandler` sends `book`, `reschedule`, or `cancel` to n8n.
3. n8n calls the verified Day 4 appointment API.
4. Day 4 checks the slot and updates Google Calendar and PostgreSQL CRM.
5. Day 4 sends confirmation email to the employee and, when collected, the customer.
6. n8n returns the verified result to Sara.
7. For a booking, n8n waits until 24 hours before the visit and calls the follow-up endpoint.

## Local endpoints

- n8n: `http://127.0.0.1:5678`
- n8n appointment webhook: `http://127.0.0.1:5678/webhook/sara-appointments`
- Day 4 API: `http://127.0.0.1:8004`
- Sara/VAPI webhook: `http://127.0.0.1:8007`

## Start services

Run each service in its own PowerShell terminal:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\day4\start_n8n.ps1
powershell.exe -ExecutionPolicy Bypass -File .\day4\start_day4.ps1
powershell.exe -ExecutionPolicy Bypass -File .\day7\start_vapi.ps1
```

## Re-import after editing the workflow

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\day4\import_n8n_workflow.ps1
```

Then publish workflow ID `saraAppointments1` and restart n8n:

```powershell
$env:N8N_USER_FOLDER = "E:\Netixsol\Week7\.n8n-data"
$env:N8N_ENCRYPTION_KEY = Get-Content .\.n8n-data\encryption.key -Raw
.\.n8n-runtime\node_modules\.bin\n8n.cmd publish:workflow --id=saraAppointments1
```

## Required Day 4 environment values

- `CALENDAR_BACKEND=google`
- `GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json`
- `DATABASE_URL=postgresql://...`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER`

Never commit `.env`, the Google service-account file, SMTP password, or n8n encryption key.
