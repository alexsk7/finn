#!/usr/bin/env bash
# Start the finn server
# Usage: ./run.sh [port]
PORT=${1:-8080}
export PATH="$HOME/.local/bin:$PATH"

if command -v mise >/dev/null 2>&1; then
	MISE_BIN="$(command -v mise)"
elif [[ -x /opt/homebrew/bin/mise ]]; then
	MISE_BIN="/opt/homebrew/bin/mise"
else
	echo "mise is required to run finn. Install it and run 'make setup'." >&2
	exit 1
fi

cd "$(dirname "$0")"
echo "Starting finn on http://localhost:$PORT"

# Prompt for name on first run if profile is not set
"$MISE_BIN" exec -- uv run python scripts/setup_profile.py

# Back up all portfolio databases before the server starts
"$MISE_BIN" exec -- uv run python scripts/backup.py

# Open browser after a short delay to let Uvicorn bind
(sleep 1.5 && "$MISE_BIN" exec -- python -m webbrowser "http://localhost:$PORT") &

"$MISE_BIN" exec -- uv run python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
