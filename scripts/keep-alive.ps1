# Keep NotebookLM session alive
# Usage: .\keep-alive.ps1 [-Interval 30] [-Headless]

param(
    [int]$Interval = 30,
    [switch]$Headless
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Creating..."
    python -m venv venv
    & "venv\Scripts\Activate.ps1"
    pip install -r requirements.txt
    playwright install chromium
}

Write-Host ""
Write-Host "=========================================="
Write-Host "NotebookLM Keep-Alive"
Write-Host "=========================================="
Write-Host ""
Write-Host "This script keeps your NotebookLM session alive by"
Write-Host "running a browser that periodically refreshes the page."
Write-Host ""
Write-Host "The browser window will open. You can minimize it."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$args = @("scripts/keep-alive.py", "--interval", $Interval)
if ($Headless) {
    $args += "--headless"
}

python @args
