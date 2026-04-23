#!/usr/bin/env bash
# Start the finance mission control server
# Usage: ./run.sh [port]
PORT=${1:-8080}
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
echo "Starting FINCTL on http://localhost:$PORT"
uv run uvicorn main:app --host 127.0.0.1 --port "$PORT" --reload
