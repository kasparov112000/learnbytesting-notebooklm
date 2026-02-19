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

# Clean up locked browser profile if it exists
$browserProfile = "$env:USERPROFILE\.notebooklm\browser_profile"
if (Test-Path $browserProfile) {
    Write-Host "Cleaning up previous browser profile..."
    # Force close any processes that might have files locked
    Get-Process | Where-Object { $_.Path -like "*ms-playwright*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    # Try to remove the profile directory
    Remove-Item -Path $browserProfile -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $browserProfile) {
        Write-Host "WARNING: Could not fully clean browser profile. Close any Chrome windows and try again."
    }
}

# Run notebooklm login
notebooklm login

Write-Host ""
Write-Host "=========================================="
Write-Host "Authentication complete!"
Write-Host "=========================================="
Write-Host "Credentials stored in: $env:USERPROFILE\.notebooklm\"
Write-Host ""
Write-Host "IMPORTANT: Google sessions expire after a few hours."
Write-Host ""
Write-Host "To keep your session alive, run the keep-alive script:"
Write-Host "  - VS Code Task: 'NotebookLM Keep-Alive (Browser)'"
Write-Host "  - Or run: .\scripts\keep-alive.ps1"
Write-Host ""
Write-Host "The keep-alive script opens a browser that refreshes"
Write-Host "NotebookLM every 30 minutes to prevent session expiry."
Write-Host ""

$startKeepAlive = Read-Host "Start keep-alive now? (y/N)"
if ($startKeepAlive -eq 'y' -or $startKeepAlive -eq 'Y') {
    Write-Host ""
    Write-Host "Starting keep-alive..."
    & "$ScriptDir\keep-alive.ps1"
} else {
    Write-Host ""
    Write-Host "You can start keep-alive later with:"
    Write-Host "  - VS Code Task: 'NotebookLM Keep-Alive (Browser)'"
    Write-Host ""
}
