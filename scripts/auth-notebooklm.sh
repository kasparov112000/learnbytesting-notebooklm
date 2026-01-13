#!/bin/bash
# Authenticate with NotebookLM (one-time setup)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Run run-local.sh first."
    exit 1
fi

echo ""
echo "=========================================="
echo "NotebookLM Authentication"
echo "=========================================="
echo ""
echo "INSTRUCTIONS:"
echo "  1. A browser window will open for Google login"
echo "  2. Complete the Google login in the browser"
echo "  3. Wait until you see the NotebookLM homepage"
echo "  4. Return HERE and press ENTER to save credentials"
echo ""
echo "NOTE: This re-authentication is needed periodically when"
echo "      the Google session expires (typically every few hours)."
echo ""
read -p "Press ENTER to start authentication..."
echo ""

# Run notebooklm login
notebooklm login

echo ""
echo "=========================================="
echo "Authentication complete!"
echo "=========================================="
echo "Credentials stored in: ~/.notebooklm/"
echo ""
echo "You can now:"
echo "  - Start the service: Run 'NotebookLM Service (Start)' task"
echo "  - Ask questions via: POST http://localhost:3034/ask"
echo ""
