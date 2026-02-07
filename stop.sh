#!/bin/bash
# Stop all Ktizo services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping Ktizo services..."

# Stop processes from PID files (new format)
for pidfile in "$SCRIPT_DIR/.backend.pid" "$SCRIPT_DIR/.frontend.pid" "$SCRIPT_DIR/.watcher.pid" "$SCRIPT_DIR/.dnsmasq.pid"; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping process $pid..."
            kill "$pid" 2>/dev/null || true
        fi
        rm "$pidfile" 2>/dev/null || true
    fi
done

# Legacy PID file support
if [ -f "$SCRIPT_DIR/.pids" ]; then
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping process $pid..."
            kill "$pid" 2>/dev/null || true
        fi
    done < "$SCRIPT_DIR/.pids"
    rm "$SCRIPT_DIR/.pids" 2>/dev/null || true
fi

# Kill any remaining processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true
pkill -f "watch-dnsmasq.sh" 2>/dev/null || true

echo "✅ Services stopped"

