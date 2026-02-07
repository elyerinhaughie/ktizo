#!/bin/bash
# Uninstall Ktizo native installation

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Ktizo Uninstallation"
echo "=========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux-musl"* ]]; then
    OS="linux"
    # Detect package manager for Alpine
    if command -v apk &> /dev/null; then
        PKG_MANAGER="apk"
    fi
else
    echo "Error: Unsupported operating system"
    exit 1
fi

# Stop services
echo "Stopping services..."
./stop.sh 2>/dev/null || true

# Unload launchd service (macOS)
if [[ "$OS" == "macos" ]]; then
    PLIST_FILE="$HOME/Library/LaunchAgents/com.ktizo.backend.plist"
    if [ -f "$PLIST_FILE" ]; then
        echo "Unloading launchd service..."
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        rm "$PLIST_FILE"
    fi
fi

# Stop systemd service (Linux, non-Alpine)
if [[ "$OS" == "linux" ]]; then
    # Only try systemd if it's available (Alpine doesn't have it)
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet ktizo-backend 2>/dev/null; then
            echo "Stopping systemd service..."
            systemctl stop ktizo-backend
            systemctl disable ktizo-backend
        fi
        
        SERVICE_FILE="/etc/systemd/system/ktizo-backend.service"
        if [ -f "$SERVICE_FILE" ]; then
            echo "Removing systemd service..."
            rm "$SERVICE_FILE"
            systemctl daemon-reload
        fi
    else
        echo "⚠️  systemd not available (Alpine?), skipping systemd service removal"
    fi
fi

# Stop dnsmasq (optional - ask user)
echo ""
read -p "Stop dnsmasq service? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OS" == "macos" ]]; then
        brew services stop dnsmasq 2>/dev/null || true
    else
        # Try systemd first, then OpenRC (Alpine)
        if command -v systemctl &> /dev/null; then
            systemctl stop dnsmasq 2>/dev/null || true
        elif command -v rc-service &> /dev/null; then
            rc-service dnsmasq stop 2>/dev/null || true
        else
            pkill dnsmasq 2>/dev/null || true
        fi
    fi
    echo "✅ dnsmasq stopped"
fi

# Remove dnsmasq config (optional - ask user)
echo ""
read -p "Remove dnsmasq configuration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OS" == "macos" ]]; then
        if [ -f "/usr/local/etc/dnsmasq.conf" ]; then
            rm /usr/local/etc/dnsmasq.conf
            echo "✅ dnsmasq config removed"
        fi
    else
        if [ -f "/etc/dnsmasq.conf" ]; then
            rm /etc/dnsmasq.conf
            echo "✅ dnsmasq config removed"
        fi
    fi
fi

# Remove virtual environment (optional - ask user)
echo ""
read -p "Remove Python virtual environment? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$SCRIPT_DIR/venv" ]; then
        rm -rf "$SCRIPT_DIR/venv"
        echo "✅ Virtual environment removed"
    fi
fi

# Remove node_modules (optional - ask user)
echo ""
read -p "Remove node_modules? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        rm -rf "$SCRIPT_DIR/frontend/node_modules"
        echo "✅ node_modules removed"
    fi
fi

echo ""
echo "=========================================="
echo "Uninstallation Complete"
echo "=========================================="
echo ""
echo "Note: Configuration files and data are preserved:"
echo "  - $SCRIPT_DIR/compiled/"
echo "  - $SCRIPT_DIR/data/"
echo "  - $SCRIPT_DIR/templates/"
echo ""
echo "To completely remove, delete these directories manually."

