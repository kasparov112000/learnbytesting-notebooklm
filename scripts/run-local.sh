#!/bin/bash
# Run NotebookLM microservice locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install playwright for browser auth
echo "Installing Playwright..."
playwright install chromium || echo "Playwright install skipped (may need manual install)"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Check if authenticated
echo ""
echo "=========================================="
echo "NotebookLM Authentication Check"
echo "=========================================="
echo "If not authenticated, run: notebooklm login"
echo ""

# Run the service
echo "Starting NotebookLM microservice on port 3034..."
uvicorn src.api:app --host 0.0.0.0 --port 3034 --reload
