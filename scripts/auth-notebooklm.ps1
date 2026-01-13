# Authenticate with NotebookLM (one-time setup)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Run run-local.ps1 first."
    exit 1
}

Write-Host ""
Write-Host "=========================================="
Write-Host "NotebookLM Authentication"
Write-Host "=========================================="
Write-Host ""
Write-Host "INSTRUCTIONS:"
Write-Host "  1. A browser window will open for Google login"
Write-Host "  2. Complete the Google login in the browser"
Write-Host "  3. Wait until you see the NotebookLM homepage"
Write-Host "  4. Return HERE and press ENTER to save credentials"
Write-Host ""
Write-Host "NOTE: This re-authentication is needed periodically when"
Write-Host "      the Google session expires (typically every few hours)."
Write-Host ""
Write-Host "Press any key to start authentication..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host ""

# Run notebooklm login
notebooklm login

Write-Host ""
Write-Host "=========================================="
Write-Host "Authentication complete!"
Write-Host "=========================================="
Write-Host "Credentials stored in: $env:USERPROFILE\.notebooklm\"
Write-Host ""
Write-Host "You can now:"
Write-Host "  - Start the service: Run 'NotebookLM Service (Start)' task"
Write-Host "  - Ask questions via: POST http://localhost:3034/ask"
Write-Host ""
