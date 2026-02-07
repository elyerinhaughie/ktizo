#!/bin/bash
# Watch for dnsmasq config changes and reload dnsmasq
# Native version (no Docker)

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPILED_DIR="$SCRIPT_DIR/compiled"
DNSMASQ_CONF="$COMPILED_DIR/dnsmasq/dnsmasq.conf"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    RELOAD_CMD="brew services restart dnsmasq"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    RELOAD_CMD="systemctl reload dnsmasq"
else
    echo "Error: Unsupported OS"
    exit 1
fi

echo "Watching for dnsmasq config changes..."
echo "Config file: $DNSMASQ_CONF"
echo ""

# Check if inotifywait is available (Linux) or use fswatch (macOS)
if [[ "$OS" == "linux" ]]; then
    if ! command -v inotifywait &> /dev/null; then
        echo "Installing inotify-tools..."
        apt-get install -y inotify-tools || yum install -y inotify-tools || dnf install -y inotify-tools
    fi
    
    while true; do
        inotifywait -e modify,create,delete "$DNSMASQ_CONF" 2>/dev/null && {
            echo "[$(date)] Detected config change, reloading dnsmasq..."
            dnsmasq --test -C "$DNSMASQ_CONF" && {
                eval "$RELOAD_CMD"
                echo "[$(date)] DNSMASQ reloaded successfully"
            } || {
                echo "[$(date)] ERROR: dnsmasq config test failed, not reloading"
            }
        }
    done
else
    # macOS - use fswatch
    if ! command -v fswatch &> /dev/null; then
        echo "Installing fswatch..."
        brew install fswatch
    fi
    
    fswatch -o "$DNSMASQ_CONF" | while read; do
        echo "[$(date)] Detected config change, reloading dnsmasq..."
        dnsmasq --test -C "$DNSMASQ_CONF" && {
            eval "$RELOAD_CMD"
            echo "[$(date)] DNSMASQ reloaded successfully"
        } || {
            echo "[$(date)] ERROR: dnsmasq config test failed, not reloading"
        }
    done
fi

