#!/usr/bin/env pwsh
# start_vapi.ps1 — Sara VAPI Webhook Server start karne ka script
# Usage: .\start_vapi.ps1
# Run karo day7\ folder se

Write-Host "Starting Sara VAPI Webhook Server..." -ForegroundColor Cyan

# .env load karo
$envFile = "$PSScriptRoot\vapi_integration\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#=][^=]*)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
        }
    }
    Write-Host ".env loaded from $envFile" -ForegroundColor Green
}

Write-Host "Starting uvicorn on http://localhost:8007" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# IMPORTANT: run from day7\ so 'vapi_integration' package is found
uvicorn vapi_integration.webhook_server:app --host 0.0.0.0 --port 8007 --reload

