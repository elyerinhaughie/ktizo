#!/bin/bash
# Stop all Ktizo services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping Ktizo services..."

# Stop processes from PID file
if [ -f "$SCRIPT_DIR/.pids" ]; then
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping process $pid..."
            kill "$pid" 2>/dev/null
        fi
    done < "$SCRIPT_DIR/.pids"
    rm "$SCRIPT_DIR/.pids"
fi

# Kill any remaining processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true

echo "✅ Services stopped"

