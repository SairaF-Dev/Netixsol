#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $projectRoot ".n8n-runtime\node_modules\.bin\n8n.cmd"
$dataDirectory = Join-Path $projectRoot ".n8n-data"
$keyFile = Join-Path $dataDirectory "encryption.key"

if (-not (Test-Path -LiteralPath $runtime)) {
    throw "n8n runtime is missing. Install it under .n8n-runtime first."
}
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $keyFile)) {
    $key = -join ((1..64) | ForEach-Object { "0123456789abcdef"[(Get-Random -Maximum 16)] })
    Set-Content -LiteralPath $keyFile -Value $key -NoNewline
}

$env:Path = "C:\Program Files\nodejs;" + $env:Path
$env:N8N_USER_FOLDER = $dataDirectory
$env:N8N_ENCRYPTION_KEY = Get-Content -LiteralPath $keyFile -Raw
$env:N8N_PORT = "5678"
$env:N8N_HOST = "127.0.0.1"
$env:N8N_PROTOCOL = "http"
$env:GENERIC_TIMEZONE = "Asia/Karachi"
$env:TZ = "Asia/Karachi"

& $runtime start
