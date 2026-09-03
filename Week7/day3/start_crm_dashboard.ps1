#!/usr/bin/env powershell
"""
CRM Admin Dashboard Launcher
ایک مکمل CRM management solution
"""

# Colors
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"
$CYAN = "Cyan"

function Print-Header {
    param([string]$Text)
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor $CYAN
    Write-Host "║ $($Text.PadRight(36)) ║" -ForegroundColor $CYAN
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor $CYAN
}

function Print-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor $GREEN
}

function Print-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor $YELLOW
}

function Print-Error {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor $RED
}

# Main
Clear-Host
Print-Header "SARA CRM DASHBOARD"

# Check .env
Write-Host ""
Write-Host "📋 Checking configuration..." -ForegroundColor $CYAN

if (-not (Test-Path ".env")) {
    Print-Error ".env file not found!"
    Write-Host "Please create .env with DATABASE_URL"
    exit 1
}

Print-Success ".env file found"

# Check DATABASE_URL
$env_content = Get-Content ".env" | Select-String "DATABASE_URL"
if ($env_content) {
    Print-Success "DATABASE_URL configured"
} else {
    Print-Error "DATABASE_URL not found in .env"
    exit 1
}

# Check PostgreSQL connection
Write-Host ""
Write-Host "🔗 Testing PostgreSQL connection..." -ForegroundColor $CYAN

try {
    python -c "
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg.connect(db_url)
conn.close()
print('OK')
"
    if ($LASTEXITCODE -eq 0) {
        Print-Success "PostgreSQL connection successful"
    } else {
        Print-Error "PostgreSQL connection failed"
        exit 1
    }
} catch {
    Print-Error "PostgreSQL connection error: $_"
    exit 1
}

# Check appointments table
Write-Host ""
Write-Host "📊 Checking database tables..." -ForegroundColor $CYAN

$table_check = python -c "
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg.connect(db_url)
cur = conn.cursor()
cur.execute('''
    SELECT COUNT(*) FROM information_schema.tables 
    WHERE table_name = 'appointments'
''')
result = cur.fetchone()
conn.close()
print('YES' if result[0] > 0 else 'NO')
"

if ($table_check -eq "YES") {
    Print-Success "Appointments table exists"
} else {
    Print-Warning "Appointments table not found. Will be created by Day 4 API."
    Write-Host "Run Day 4 API first: uvicorn api.main:app --port 8004"
}

# Display menu
Write-Host ""
Write-Host "🎯 Select an option:" -ForegroundColor $CYAN
Write-Host ""
Write-Host "  1️⃣  Start CRM Dashboard (Streamlit)" -ForegroundColor $GREEN
Write-Host "  2️⃣  Export All Appointments (CSV)" -ForegroundColor $GREEN
Write-Host "  3️⃣  Export All Appointments (JSON)" -ForegroundColor $GREEN
Write-Host "  4️⃣  View Database Stats" -ForegroundColor $GREEN
Write-Host "  5️⃣  Show Help" -ForegroundColor $GREEN
Write-Host "  6️⃣  Exit" -ForegroundColor $RED
Write-Host ""

$choice = Read-Host "Enter your choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host ""
        Print-Success "Starting CRM Dashboard..."
        Write-Host "Opening browser at http://localhost:8501"
        Write-Host ""
        Start-Sleep -Seconds 2
        
        streamlit run ui/crm_dashboard.py
    }
    
    "2" {
        Write-Host ""
        Print-Success "Exporting appointments to CSV..."
        python scripts/crm_exporter.py
        Write-Host ""
        Print-Success "Export complete! Files created:"
        Write-Host "  - crm_export_appointments.csv"
        Write-Host "  - crm_export_appointments.json"
        Write-Host "  - crm_export_today.csv"
    }
    
    "3" {
        Write-Host ""
        Print-Success "Exporting appointments to JSON..."
        python -c "
from scripts.crm_exporter import CRMExporter
import os

db_url = os.getenv('DATABASE_URL')
exporter = CRMExporter(db_url)
exporter.export_to_json('crm_appointments.json')
print('✅ Export complete: crm_appointments.json')
"
    }
    
    "4" {
        Write-Host ""
        Print-Success "Database Statistics:"
        python -c "
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg.connect(db_url)

with conn.cursor(row_factory=dict_row) as cur:
    # Total appointments
    cur.execute('SELECT COUNT(*) as total FROM appointments')
    total = cur.fetchone()['total']
    print(f'📊 Total Appointments: {total}')
    
    # By status
    cur.execute('''
        SELECT status, COUNT(*) as count 
        FROM appointments 
        GROUP BY status 
        ORDER BY count DESC
    ''')
    rows = cur.fetchall()
    print('  Status breakdown:')
    for row in rows:
        print(f'    - {row[\"status\"]}: {row[\"count\"]}')
    
    # Unique customers
    cur.execute('''
        SELECT COUNT(DISTINCT request_json->>'client_phone') as unique_customers 
        FROM appointments
    ''')
    unique = cur.fetchone()['unique_customers']
    print(f'👥 Unique Customers: {unique}')
    
    # Events
    cur.execute('SELECT COUNT(*) as total FROM workflow_events')
    events = cur.fetchone()['total']
    print(f'📝 Workflow Events: {events}')

conn.close()
"
    }
    
    "5" {
        Write-Host ""
        Print-Header "CRM DASHBOARD HELP"
        Write-Host ""
        Write-Host "📋 CRM Admin Dashboard - All-in-One Solution" -ForegroundColor $CYAN
        Write-Host ""
        Write-Host "Features:" -ForegroundColor $GREEN
        Write-Host "  📊 Dashboard View - Statistics & Overview"
        Write-Host "  📋 All Appointments - List with filters"
        Write-Host "  🔍 Search Customer - Find by phone number"
        Write-Host "  📋 Appointment Details - Full history & workflow"
        Write-Host "  📥 Export Data - CSV/JSON exports"
        Write-Host ""
        Write-Host "Database:" -ForegroundColor $GREEN
        Write-Host "  Tables: appointments, workflow_events"
        Write-Host "  Location: PostgreSQL (real_estate DB)"
        Write-Host ""
        Write-Host "Files:" -ForegroundColor $GREEN
        Write-Host "  ui/crm_dashboard.py - Main Streamlit app"
        Write-Host "  scripts/crm_exporter.py - Export utilities"
        Write-Host "  CRM_DASHBOARD_GUIDE.md - Full documentation"
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "6" {
        Write-Host ""
        Print-Success "Goodbye! 👋"
        exit 0
    }
    
    default {
        Print-Error "Invalid choice!"
        exit 1
    }
}
