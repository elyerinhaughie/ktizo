#!/bin/bash
# Setup DNSMASQ on macOS host for PXE boot
# This script installs and configures dnsmasq to run on the host instead of Docker

set -e

echo "Setting up DNSMASQ on macOS host for PXE boot..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed. Please install it first:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Install dnsmasq if not already installed
if ! command -v dnsmasq &> /dev/null; then
    echo "Installing dnsmasq..."
    brew install dnsmasq
else
    echo "dnsmasq is already installed"
fi

# Get the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SOURCE="$SCRIPT_DIR/compiled/dnsmasq/dnsmasq.conf"
CONFIG_MACOS="$SCRIPT_DIR/compiled/dnsmasq/dnsmasq.conf.macos"
CONFIG_DEST="/usr/local/etc/dnsmasq.conf"

# Check if config file exists
if [ ! -f "$CONFIG_SOURCE" ]; then
    echo "Error: DNSMASQ config not found at $CONFIG_SOURCE"
    echo "Please run the backend API to generate the config first:"
    echo "  curl -X POST http://localhost:8000/api/v1/network/settings/apply"
    exit 1
fi

# Use macOS-specific config if it exists, otherwise use the regular one
if [ -f "$CONFIG_MACOS" ]; then
    echo "Using macOS-specific config with adjusted TFTP path"
    CONFIG_TO_USE="$CONFIG_MACOS"
    # Update the TFTP root path in the config to match the actual project path
    sed "s|/Users/elycin/PycharmProjects/ktizo|$SCRIPT_DIR|g" "$CONFIG_MACOS" > /tmp/dnsmasq.conf.tmp
    CONFIG_TO_USE="/tmp/dnsmasq.conf.tmp"
else
    echo "Using Docker config (you may need to adjust TFTP paths manually)"
    CONFIG_TO_USE="$CONFIG_SOURCE"
    # Create a modified version with correct TFTP path
    sed "s|tftp-root=/var/lib/tftpboot|tftp-root=$SCRIPT_DIR/compiled|g" "$CONFIG_SOURCE" > /tmp/dnsmasq.conf.tmp
    CONFIG_TO_USE="/tmp/dnsmasq.conf.tmp"
fi

# Backup existing config if it exists
if [ -f "$CONFIG_DEST" ]; then
    echo "Backing up existing dnsmasq config to ${CONFIG_DEST}.backup"
    sudo cp "$CONFIG_DEST" "${CONFIG_DEST}.backup"
fi

# Copy the generated config
echo "Copying DNSMASQ config to $CONFIG_DEST"
sudo cp "$CONFIG_TO_USE" "$CONFIG_DEST"

# Test the config
echo "Testing DNSMASQ configuration..."
sudo dnsmasq --test

# Stop any running dnsmasq service
echo "Stopping existing dnsmasq service..."
sudo brew services stop dnsmasq 2>/dev/null || true
sudo pkill dnsmasq 2>/dev/null || true

# Start dnsmasq
echo "Starting dnsmasq service..."
sudo brew services start dnsmasq

# Wait a moment for it to start
sleep 2

# Check if it's running
if sudo brew services list | grep -q "dnsmasq.*started"; then
    echo "✅ DNSMASQ is now running on the macOS host"
    echo ""
    echo "To check status: sudo brew services list"
    echo "To view logs: tail -f /usr/local/var/log/dnsmasq.log"
    echo "To stop: sudo brew services stop dnsmasq"
    echo ""
    echo "Note: Make sure to stop the Docker dnsmasq container:"
    echo "  docker compose stop dnsmasq"
else
    echo "❌ Failed to start dnsmasq. Check logs:"
    echo "  tail -f /usr/local/var/log/dnsmasq.log"
    exit 1
fi

