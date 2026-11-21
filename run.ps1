# Launch MtaaBiz dev server using the project virtualenv and open the site in the default browser.
# Usage: .\run.ps1  (or right-click > Run with PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".\..\mtaa\Scripts\python.exe")) {
    Write-Error "Virtualenv not found at .\mtaa\Scripts\python.exe. Create it first: python -m venv mtaa"
}

$port = 8000
$url = "http://127.0.0.1:$port/"

# Free the port if something is already listening on it (e.g. a previous runserver)
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Port $port already in use - stopping the previous server process..." -ForegroundColor Yellow
    $existing | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 1
}

# Open the browser shortly after the server starts (server takes ~1s to bind)
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:8000/"
} | Out-Null

Write-Host "Starting MtaaBiz dev server at $url (browser will open automatically)..." -ForegroundColor Green
& ".\..\mtaa\Scripts\python.exe" manage.py runserver 127.0.0.1:$port
