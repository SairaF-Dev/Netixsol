#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $projectRoot ".n8n-runtime\node_modules\.bin\n8n.cmd"
$dataDirectory = Join-Path $projectRoot ".n8n-data"
$keyFile = Join-Path $dataDirectory "encryption.key"
$workflow = Join-Path $PSScriptRoot "n8n\appointment_workflow.json"

if (-not (Test-Path -LiteralPath $keyFile)) {
    throw "Run start_n8n.ps1 once to initialize the local encryption key."
}
$env:Path = "C:\Program Files\nodejs;" + $env:Path
$env:N8N_USER_FOLDER = $dataDirectory
$env:N8N_ENCRYPTION_KEY = Get-Content -LiteralPath $keyFile -Raw
$env:GENERIC_TIMEZONE = "Asia/Karachi"
$env:TZ = "Asia/Karachi"

& $runtime import:workflow --input=$workflow
