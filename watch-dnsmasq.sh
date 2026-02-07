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
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux-musl"* ]]; then
    OS="linux"
    # Detect if Alpine (uses OpenRC) or systemd
    if command -v rc-service &> /dev/null; then
        RELOAD_CMD="rc-service dnsmasq restart"
    elif command -v systemctl &> /dev/null; then
        RELOAD_CMD="systemctl reload dnsmasq"
    else
        RELOAD_CMD="pkill -HUP dnsmasq"  # Fallback: send SIGHUP
    fi
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
        # Detect package manager for Alpine
        if command -v apk &> /dev/null; then
            apk add --no-cache inotify-tools
        elif command -v apt-get &> /dev/null; then
            apt-get install -y inotify-tools
        elif command -v yum &> /dev/null; then
            yum install -y inotify-tools
        elif command -v dnf &> /dev/null; then
            dnf install -y inotify-tools
        else
            echo "Error: Cannot determine package manager to install inotify-tools"
            exit 1
        fi
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

