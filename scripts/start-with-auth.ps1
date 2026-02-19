# Combined NotebookLM startup script - login then start service
# Waits for user to press Enter, runs login, then starts the service.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

Write-Host ""
Write-Host "=========================================="
Write-Host "NotebookLM Service Startup"
Write-Host "=========================================="
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r requirements.txt --quiet

# Install playwright for browser auth (if not already installed)
Write-Host "Checking Playwright..."
try {
    playwright install chromium 2>$null
} catch {
    # Silently continue if already installed
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env with your configuration"
}

Write-Host ""
Write-Host "AUTHENTICATION"
Write-Host "--------------"
Write-Host "  1. Press ENTER to open browser for Google login"
Write-Host "  2. Complete the Google login in the browser"
Write-Host "  3. Wait until you see the NotebookLM homepage"
Write-Host "  4. The service will start automatically after login"
Write-Host ""
Write-Host "Press ENTER to start authentication..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host ""

# Run notebooklm login
Write-Host "Opening browser for login..."
notebooklm login

Write-Host ""
Write-Host "Authentication complete!"
Write-Host ""

# Run the service
Write-Host "Starting NotebookLM microservice on port 3034..."
Write-Host "=========================================="
Write-Host ""
uvicorn src.api:app --host 0.0.0.0 --port 3034 --reload
