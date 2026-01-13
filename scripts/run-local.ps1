# Run NotebookLM microservice locally (Windows PowerShell)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r requirements.txt

# Install playwright for browser auth
Write-Host "Installing Playwright..."
try {
    playwright install chromium
} catch {
    Write-Host "Playwright install skipped (may need manual install)"
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env with your configuration"
}

# Display auth info
Write-Host ""
Write-Host "=========================================="
Write-Host "NotebookLM Authentication Check"
Write-Host "=========================================="
Write-Host "If not authenticated, run: notebooklm login"
Write-Host ""

# Run the service
Write-Host "Starting NotebookLM microservice on port 3034..."
uvicorn src.api:app --host 0.0.0.0 --port 3034 --reload
