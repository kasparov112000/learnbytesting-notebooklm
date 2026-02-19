#!/bin/bash
# Combined NotebookLM startup script - login then start service
# Waits for user to press Enter, runs login, then starts the service.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo ""
echo "=========================================="
echo "NotebookLM Service Startup"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Install playwright for browser auth (if not already installed)
echo "Checking Playwright..."
playwright install chromium 2>/dev/null || true

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

echo ""
echo "AUTHENTICATION"
echo "--------------"
echo "  1. Press ENTER to open browser for Google login"
echo "  2. Complete the Google login in the browser"
echo "  3. Wait until you see the NotebookLM homepage"
echo "  4. The service will start automatically after login"
echo ""
read -p "Press ENTER to start authentication..."
echo ""

# Run notebooklm login
echo "Opening browser for login..."
notebooklm login

echo ""
echo "Authentication complete!"
echo ""

# Run the service
echo "Starting NotebookLM microservice on port 3034..."
echo "=========================================="
echo ""
uvicorn src.api:app --host 0.0.0.0 --port 3034 --reload
