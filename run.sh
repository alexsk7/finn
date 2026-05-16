#!/usr/bin/env bash
# Start the finn server
# Usage: ./run.sh [port]
PORT=${1:-8080}
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
echo "Starting finn on http://localhost:$PORT"

# Prompt for name on first run if profile is not set
uv run python scripts/setup_profile.py

# Back up all portfolio databases before the server starts
uv run python scripts/backup.py

# Open browser after a short delay to let Uvicorn bind
(sleep 1.5 && python3 -m webbrowser "http://localhost:$PORT") &

uv run uvicorn main:app --host 127.0.0.1 --port "$PORT" --reload
