# Day 4 Setup Guide

This guide walks through setting up the Day 4 appointment service on your local machine.

## Prerequisites

- **Python**: 3.11 or later
  ```bash
  python --version  # Should be 3.11+
  ```
- **Git**: For cloning repository
- **PostgreSQL** (optional): For production-like setup
- **Docker** (optional): For containerized deployment

## Step 1: Clone and Navigate

```powershell
cd Week7
cd day4
```

## Step 2: Create Virtual Environment

### PowerShell (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux
```bash
python -m venv .venv
source .venv/bin/activate
```

**Verify**: You should see `(.venv)` in your terminal prompt.

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
python -m pip install -e .
```

**Expected packages**:
- fastapi >= 0.115
- uvicorn >= 0.30
- pydantic >= 2.8
- httpx >= 0.27
- psycopg >= 3.2 (PostgreSQL driver)
- pytest >= 8.2
- google-auth >= 2.25 (for Google Calendar)
- google-api-python-client >= 2.100

## Step 4: Configure Environment

### Option A: Local Development (Recommended for Testing)

```powershell
Copy-Item .env.example .env
```

The default `.env` uses in-memory storage. No external services needed.

### Option B: PostgreSQL Setup

If you want to test with a real database:

#### Install PostgreSQL

**Windows**:
- Download from https://www.postgresql.org/download/windows/
- Install with default settings
- Note username/password during installation

**macOS** (with Homebrew):
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### Create Database

```bash
# Windows (PowerShell)
psql -U postgres -c "CREATE DATABASE realestate;"

# macOS/Linux
createdb -U postgres realestate
```

#### Run Schema

```bash
# Windows
psql -U postgres -d realestate -f schema.sql

# macOS/Linux
psql -U postgres -d realestate -f schema.sql
```

#### Update .env

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate
```

Replace `password` with your PostgreSQL password.

## Step 5: Run Server

```bash
python -m uvicorn api.main:app --reload --port 8004
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8004 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Application startup complete
```

Server is ready at: `http://localhost:8004`

## Step 6: Test Health

In a new terminal, verify the server is running:

```powershell
curl http://localhost:8004/health
```

**Expected response**:
```json
{"status":"ok","service":"day4-workflows"}
```

## Step 7: Run Test Suite

In the project directory (with `.venv` activated):

```bash
pytest -v
```

**Expected output**:
```
tests/test_api.py::test_complete_api_lifecycle PASSED
tests/test_api.py::test_api_returns_conflict_for_overlap PASSED
tests/test_appointment_workflow.py::test_booking_creates_calendar_email_crm_and_workflow_event PASSED
...
======================== 9 passed in 1.14s ========================
```

All 9 tests should pass.

## Step 8: Try the API

### Book an Appointment

```powershell
$body = @{
    client_name = "Ali Khan"
    client_phone = "+923001234567"
    employee_name = "Sara Ahmed"
    employee_email = "sara@example.com"
    property_id = 101
    property_name = "Horizon Heights"
    starts_at = "2030-01-05T11:00:00+05:00"
    duration_minutes = 60
    meeting_notes = "Bring keys"
} | ConvertTo-Json

curl -X POST http://localhost:8004/appointments `
  -H "Content-Type: application/json" `
  -d $body
```

**Expected response** (201 Created):
```json
{
  "appointment": {
    "appointment_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "confirmed",
    "calendar_event_id": "memory-event-123",
    "created_at": "2030-01-04T10:00:00+05:00",
    ...
  },
  "notification_sent": true,
  "warnings": []
}
```

### Reschedule

```powershell
$appointment_id = "550e8400-e29b-41d4-a716-446655440000"  # From previous response

$reschedule = @{
    starts_at = "2030-01-06T14:00:00+05:00"
} | ConvertTo-Json

curl -X PATCH http://localhost:8004/appointments/$appointment_id/reschedule `
  -H "Content-Type: application/json" `
  -d $reschedule
```

### Cancel

```powershell
curl -X DELETE http://localhost:8004/appointments/$appointment_id
```

## Step 9: View Logs

In in-memory mode, logs are stored in Python objects:

```python
# In Python REPL or script
from day4_workflows.calendar_service import InMemoryCalendarGateway
from day4_workflows.email_service import InMemoryEmailGateway
from day4_workflows.crm_logging import InMemoryCRMRepository

# Access stored data (if injected into service)
# calendar.events  → all calendar events
# email.messages   → all emails sent
# crm.appointments → all appointments
```

## Troubleshooting

### Error: "No module named 'fastapi'"

**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # macOS/Linux
python -m pip install -e .
```

### Error: "Cannot connect to database"

**Solution**: 
1. Check PostgreSQL is running: `pg_isready`
2. Verify DATABASE_URL in `.env` is correct
3. Check database exists: `psql -l`
4. Or use in-memory mode (empty DATABASE_URL)

### Tests fail with "Connection refused"

**Solution**: Tests use in-memory backends by default. If failing:
```bash
# Clear any cached state
rm -rf .pytest_cache

# Run tests again
pytest -xvs
```

### Port 8004 already in use

**Solution**: 
```bash
# Use a different port
uvicorn api.main:app --reload --port 8005

# Or kill existing process
lsof -i :8004  # macOS/Linux
netstat -ano | findstr :8004  # Windows
```

## Docker Setup (Optional)

For containerized development:

```bash
# Build image
docker build -t sara-day4:latest .

# Run with in-memory backends
docker run -p 8004:8004 sara-day4:latest

# Run with docker-compose (includes PostgreSQL)
docker-compose up -d
```

Check status:
```bash
# Test from host machine
curl http://localhost:8004/health

# View logs
docker logs sara-day4-api
```

## Production Checklist

Before deploying to production:

- [ ] Database: PostgreSQL configured and backed up
- [ ] Calendar: Google service account created and calendars shared
- [ ] Email: SMTP credentials tested (Gmail App Password, SendGrid, etc.)
- [ ] n8n: Webhook URL and API key configured
- [ ] Secrets: All sensitive data in environment variables (not `.env`)
- [ ] SSL/TLS: HTTPS enabled
- [ ] Monitoring: Health checks configured
- [ ] Logging: Error tracking enabled (Sentry, DataDog, etc.)
- [ ] Rate limiting: Added to prevent abuse
- [ ] API keys: Generated and distributed to clients
- [ ] Documentation: Updated for your team
- [ ] Tests: All passing, coverage > 80%

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed production setup.

## Next Steps

1. **Read the documentation**:
   - [API Reference](docs/API_DOCUMENTATION.md)
   - [Integration Guide](docs/INTEGRATION_GUIDE.md)
   - [Workflow Architecture](docs/workflow.md)

2. **Integrate with Day 3**:
   - Review how Day 3 calls Day 4 APIs
   - Implement appointment booking in LangGraph

3. **Try production deployment**:
   - Set up PostgreSQL database
   - Configure Google Calendar
   - Deploy to Docker/Railway/Render

4. **Monitor and scale**:
   - Add health checks
   - Set up logging
   - Enable performance monitoring

## Getting Help

- 📖 **Documentation**: See `/docs` folder
- 🧪 **Tests**: Run `pytest -xvs` for debugging
- 🐛 **Errors**: Check terminal output and test failures
- 💬 **Questions**: Review test files for usage examples

## Quick Reference

| Task | Command |
|------|---------|
| Activate env | `.\.venv\Scripts\Activate.ps1` (Windows) |
| Install app | `python -m pip install -e .` |
| Run server | `python -m uvicorn api.main:app --reload --port 8004` |
| Run tests | `pytest -v` |
| View API docs | http://localhost:8004/docs (auto-generated) |
| Check health | `curl http://localhost:8004/health` |
| Build Docker | `docker build -t sara-day4:latest .` |
| Docker compose | `docker-compose up -d` |

---

**Ready to go! Happy coding! 🚀**
