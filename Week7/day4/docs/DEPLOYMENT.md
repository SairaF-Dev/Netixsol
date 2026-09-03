# Day 4 Deployment & Setup Guide

## Quick Start (Local Development)

### 1. Setup Environment

```powershell
cd day4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

For local development, default values use in-memory storage. No credentials required.

### 3. Run Server

```powershell
uvicorn api.main:app --reload --port 8004
```

Server runs at: `http://localhost:8004`

### 4. Test Health

```bash
curl http://localhost:8004/health
```

### 5. Run Tests

```powershell
pytest -q
```

---

## Production Deployment

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google Cloud service account (for Calendar)
- SMTP server credentials (for email)
- n8n instance (optional, for workflow automation)
- Slack webhook (optional, for monitoring)

### Environment Variables

Create `.env` based on `.env.example` with production values:

```bash
APP_ENV=production
DATABASE_URL=postgresql://user:password@db.example.com:5432/realestate
CALENDAR_BACKEND=google
GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/google-service-account.json
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=appointments@example.com
SMTP_PASSWORD=<app-password>
SMTP_SENDER=appointments@example.com
SMTP_USE_TLS=1
N8N_WEBHOOK_URL=https://n8n.example.com/webhook/appointments
N8N_API_KEY=<n8n-api-key>
WORKFLOW_TIMEOUT_SECONDS=8
WORKFLOW_MAX_ATTEMPTS=3
```

### Docker Deployment

#### 1. Build Image

```bash
docker build -t sara-day4:latest .
```

If `Dockerfile` doesn't exist, create one:

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8004
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8004"]
```

#### 2. Run Container

```bash
docker run -d \
  --name sara-day4 \
  --env-file .env \
  -v /path/to/secrets:/app/secrets:ro \
  -p 8004:8004 \
  sara-day4:latest
```

#### 3. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.9'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: realestate
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: realestate
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U realestate"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    environment:
      DATABASE_URL: postgresql://realestate:${DB_PASSWORD}@db:5432/realestate
      CALENDAR_BACKEND: google
      GOOGLE_SERVICE_ACCOUNT_FILE: /app/secrets/google-service-account.json
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USERNAME: ${SMTP_USERNAME}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      N8N_WEBHOOK_URL: ${N8N_WEBHOOK_URL}
      N8N_API_KEY: ${N8N_API_KEY}
    volumes:
      - ./secrets:/app/secrets:ro
    ports:
      - "8004:8004"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
```

Run:
```bash
docker-compose up -d
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sara-day4
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sara-day4
  template:
    metadata:
      labels:
        app: sara-day4
    spec:
      containers:
      - name: api
        image: sara-day4:latest
        ports:
        - containerPort: 8004
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sara-secrets
              key: database-url
        - name: SMTP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sara-secrets
              key: smtp-password
        - name: N8N_API_KEY
          valueFrom:
            secretKeyRef:
              name: sara-secrets
              key: n8n-api-key
        volumeMounts:
        - name: google-secrets
          mountPath: /app/secrets
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: google-secrets
        secret:
          secretName: google-service-account

---
apiVersion: v1
kind: Service
metadata:
  name: sara-day4-service
spec:
  selector:
    app: sara-day4
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8004
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
```

### Railway Deployment

1. **Create Railway Account**: https://railway.app

2. **Connect Repository**:
   ```bash
   railway login
   railway link
   ```

3. **Add Environment Variables** via Railway UI:
   - `DATABASE_URL` → Railway PostgreSQL
   - `GOOGLE_SERVICE_ACCOUNT_FILE` → Upload JSON
   - SMTP credentials
   - n8n webhook URL

4. **Deploy**:
   ```bash
   railway up
   ```

### Render Deployment

1. **Create Render Account**: https://render.com

2. **Create Web Service**:
   - Connect GitHub repository
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables** in Render UI

4. **Deploy**: Automatic on git push

### AWS Deployment (Elastic Container Service)

1. **Create ECR Repository**:
```bash
aws ecr create-repository --repository-name sara-day4
```

2. **Build and Push Image**:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL
docker tag sara-day4:latest $ECR_URL/sara-day4:latest
docker push $ECR_URL/sara-day4:latest
```

3. **Create ECS Task Definition** (JSON):
```json
{
  "family": "sara-day4",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "$ECR_URL/sara-day4:latest",
      "portMappings": [{"containerPort": 8004}],
      "environment": [
        {"name": "CALENDAR_BACKEND", "value": "google"},
        {"name": "WORKFLOW_TIMEOUT_SECONDS", "value": "8"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "SMTP_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sara-day4",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

4. **Create ECS Service** via AWS Console or CLI

---

## Google Calendar Integration

### 1. Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "sara-real-estate"
3. Enable **Google Calendar API**
4. Create Service Account:
   - Service account name: `sara-appointments`
   - Grant role: **Calendar API Editor**
5. Create JSON key → Download `google-service-account.json`

### 2. Share Calendars with Service Account

1. Open Google Calendar
2. For each employee calendar:
   - Settings → Share with specific people
   - Add service account email: `sara-appointments@PROJECT_ID.iam.gserviceaccount.com`
   - Grant **Make changes to events** permission

### 3. Set Environment Variable

```bash
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/google-service-account.json
```

---

## SMTP Email Setup

### Gmail (Recommended for Testing)

1. Enable 2-Step Verification
2. Create App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Set environment:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=<app-password>
SMTP_USE_TLS=1
```

### Corporate SMTP (e.g., Office 365)

```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=user@company.com
SMTP_PASSWORD=<password>
SMTP_USE_TLS=1
```

### SendGrid

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_USE_TLS=1
```

---

## PostgreSQL Setup

### Local Development

```bash
# Install PostgreSQL
# Create database
createdb -U postgres realestate

# Run schema
psql -U postgres -d realestate -f schema.sql

# Set environment
DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate
```

### Docker PostgreSQL

```bash
docker run -d \
  --name pg-realestate \
  -e POSTGRES_DB=realestate \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:16
```

---

## Monitoring & Logging

### Health Check Endpoint

```bash
curl http://localhost:8004/health
```

### Application Logs

```bash
# Docker
docker logs -f sara-day4

# Kubernetes
kubectl logs -f deployment/sara-day4
```

### PostgreSQL Queries

```sql
-- Recent appointments
SELECT appointment_id, status, created_at 
FROM appointments 
ORDER BY created_at DESC 
LIMIT 20;

-- Workflow events
SELECT appointment_id, event_type, created_at 
FROM workflow_events 
ORDER BY created_at DESC 
LIMIT 50;

-- Failed events (by checking for warning logs)
SELECT * FROM workflow_events WHERE payload::text LIKE '%error%';
```

### n8n Monitoring

View execution history in n8n UI at `https://n8n.example.com`

### Prometheus Metrics (Optional)

Add to `main.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

bookings = Counter('appointments_booked_total', 'Total bookings')
reschedules = Counter('appointments_rescheduled_total', 'Total reschedules')
cancellations = Counter('appointments_cancelled_total', 'Total cancellations')
booking_duration = Histogram('booking_duration_seconds', 'Time to book')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## Troubleshooting

### Calendar Integration Fails

**Error**: "GOOGLE_SERVICE_ACCOUNT_FILE is required"
- Ensure file path is correct and file exists
- Verify Google Calendar API is enabled
- Check service account email has calendar access

### Email Fails but Booking Succeeds

This is intentional! Email failures result in warnings, not errors.
- Check SMTP credentials
- Verify `SMTP_HOST` and `SMTP_PORT` are correct
- For Gmail, use App Password, not regular password

### PostgreSQL Connection Error

```
Error: could not connect to server
```

Check:
- PostgreSQL is running: `pg_isready -d realestate`
- `DATABASE_URL` is correct format
- Database exists: `psql -l`
- User has permissions

### n8n Webhook Times Out

- Increase `WORKFLOW_TIMEOUT_SECONDS` (default 8)
- Check n8n server is running
- Verify webhook URL is reachable from API server
- Check n8n logs for errors

---

## Security Checklist

- [ ] Store secrets in environment variables, not `.env` file
- [ ] Rotate Google service account keys quarterly
- [ ] Use SMTP TLS/SSL (set `SMTP_USE_TLS=1`)
- [ ] Enable database encryption at rest
- [ ] Use API key auth in production (not yet implemented)
- [ ] Enable request logging and audit trails
- [ ] Rate limit API endpoints (not yet implemented)
- [ ] Validate all input data (already implemented)
- [ ] Use HTTPS for n8n webhooks
- [ ] Regularly update dependencies: `pip install --upgrade -r requirements.txt`

---

## Scaling Considerations

- **Database**: Ensure PostgreSQL is replicated and backed up
- **API**: Deploy multiple instances behind a load balancer
- **Caching**: Add Redis for appointment availability cache
- **Async Jobs**: Move n8n publishing to background queue
- **Monitoring**: Add Prometheus + Grafana for metrics
- **APM**: Integrate with DataDog or New Relic
