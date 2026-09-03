#!/usr/bin/env pwsh
# start_day4.ps1 — Day 4 Appointment Service start karne ka script
# Usage: .\start_day4.ps1

Write-Host "Starting Day 4 Appointment Service..." -ForegroundColor Cyan

# Optional: .env file load karo
if (Test-Path "$PSScriptRoot\.env") {
    Get-Content "$PSScriptRoot\.env" | ForEach-Object {
        if ($_ -match "^([^#][^=]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
        }
    }
    Write-Host ".env loaded" -ForegroundColor Green
}

Write-Host "Starting uvicorn on http://localhost:8004" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

python -m uvicorn api.main:app --app-dir $PSScriptRoot --host 0.0.0.0 --port 8004 --reload
