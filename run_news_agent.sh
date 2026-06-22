#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================"
echo "  FIFA 2027 AI News Poster Generator"
echo "========================================"
echo ""

if [ ! -f ".venv/bin/python" ]; then
    echo "ERROR: .venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    read -rp "Press Enter to close..."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Copy .env.example and fill in your API keys."
    read -rp "Press Enter to close..."
    exit 1
fi

echo "Starting pipeline..."
echo ""
.venv/bin/python main.py "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "Pipeline finished successfully."
else
    echo "Pipeline exited with code $EXIT_CODE."
fi

read -rp "Press Enter to close..."
