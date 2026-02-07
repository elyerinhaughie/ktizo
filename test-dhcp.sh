#!/bin/bash
# Test DHCP functionality - sends DHCP discover and captures response
# Usage: sudo ./test-dhcp.sh [interface] [server_ip]

set -e

INTERFACE="${1:-en0}"
PXE_SERVER="${2:-10.0.42.2}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "DHCP Functionality Test"
echo "=========================================="
echo "Interface: $INTERFACE"
echo "PXE Server: $PXE_SERVER"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error:${NC} This script must be run as root"
    echo "Please run: sudo $0 $INTERFACE $PXE_SERVER"
    exit 1
fi

# Check if dhclient is available
if ! command -v dhclient &>/dev/null; then
    echo -e "${YELLOW}Installing dhclient...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS: dhclient comes with system, but may need to use different method"
    elif command -v apt-get &>/dev/null; then
        apt-get update && apt-get install -y isc-dhcp-client
    elif command -v yum &>/dev/null; then
        yum install -y dhclient
    fi
fi

# Get current IP
CURRENT_IP=$(ipconfig getifaddr "$INTERFACE" 2>/dev/null || \
    ip addr show "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1 || \
    echo "unknown")

echo "Current IP on $INTERFACE: $CURRENT_IP"
echo ""

# Start packet capture in background
echo "Starting packet capture..."
CAPTURE_FILE="/tmp/dhcp-test-$(date +%Y%m%d-%H%M%S).pcap"
tcpdump -i "$INTERFACE" -n -w "$CAPTURE_FILE" 'port 67 or port 68' &
TCPDUMP_PID=$!
sleep 1

# Release current lease
echo "Releasing current DHCP lease..."
dhclient -r "$INTERFACE" 2>/dev/null || true
sleep 1

# Request new lease
echo "Requesting DHCP lease (timeout: 10s)..."
echo ""

if timeout 10 dhclient -v -4 "$INTERFACE" 2>&1 | tee /tmp/dhcp-output.log; then
    NEW_IP=$(ipconfig getifaddr "$INTERFACE" 2>/dev/null || \
        ip addr show "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1 || \
        echo "unknown")
    
    echo ""
    echo -e "${GREEN}✓${NC} DHCP request completed"
    echo "New IP: $NEW_IP"
    
    # Check if we got an offer from PXE server
    if tcpdump -r "$CAPTURE_FILE" -n 2>/dev/null | grep -q "$PXE_SERVER"; then
        echo -e "${GREEN}✓${NC} Received DHCP traffic from $PXE_SERVER"
    else
        echo -e "${YELLOW}⚠${NC}  No DHCP traffic from $PXE_SERVER detected"
        echo "   May have received offer from different DHCP server"
    fi
else
    echo ""
    echo -e "${RED}✗${NC} DHCP request failed or timed out"
    echo "   Check capture file: $CAPTURE_FILE"
fi

# Stop capture
kill $TCPDUMP_PID 2>/dev/null || true
sleep 1

# Analyze capture
echo ""
echo "=========================================="
echo "Packet Analysis"
echo "=========================================="
if [ -f "$CAPTURE_FILE" ]; then
    PACKET_COUNT=$(tcpdump -r "$CAPTURE_FILE" -n 2>/dev/null | wc -l | xargs)
    echo "Packets captured: $PACKET_COUNT"
    
    if [ "$PACKET_COUNT" -gt 0 ]; then
        echo ""
        echo "DHCP Messages:"
        tcpdump -r "$CAPTURE_FILE" -n -v 2>/dev/null | grep -i "bootp" | head -5
        
        echo ""
        echo "Full capture: $CAPTURE_FILE"
        echo "View with: tcpdump -r $CAPTURE_FILE -n -v"
    else
        echo -e "${RED}No DHCP packets captured${NC}"
        echo "   Check interface name and network connectivity"
    fi
fi

