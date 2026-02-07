#!/bin/bash
# DHCP debugging tool - captures and analyzes DHCP traffic
# Usage: sudo ./debug-dhcp.sh [interface] [duration_seconds]

set -e

INTERFACE="${1:-any}"
DURATION="${2:-30}"
LOG_FILE="/tmp/dhcp-debug-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "DHCP Debugging Tool"
echo "=========================================="
echo "Interface: $INTERFACE"
echo "Duration: ${DURATION}s"
echo "Log file: $LOG_FILE"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error:${NC} This script must be run as root"
    echo "Please run: sudo $0 $INTERFACE $DURATION"
    exit 1
fi

# Check if tcpdump is available
if ! command -v tcpdump &>/dev/null; then
    echo -e "${YELLOW}Installing tcpdump...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install tcpdump
    elif command -v apt-get &>/dev/null; then
        apt-get update && apt-get install -y tcpdump
    elif command -v yum &>/dev/null; then
        yum install -y tcpdump
    elif command -v apk &>/dev/null; then
        apk add --no-cache tcpdump
    fi
fi

echo -e "${GREEN}Starting DHCP packet capture...${NC}"
echo "Press Ctrl+C to stop early"
echo ""

# Capture DHCP traffic
tcpdump -i "$INTERFACE" -n -v -s 0 -w "$LOG_FILE.pcap" \
    'port 67 or port 68' &
TCPDUMP_PID=$!

# Also show live output
timeout "$DURATION" tcpdump -i "$INTERFACE" -n -v \
    'port 67 or port 68' 2>&1 | tee "$LOG_FILE" &
LIVE_PID=$!

# Wait for duration or interrupt
trap "kill $TCPDUMP_PID $LIVE_PID 2>/dev/null; exit" INT TERM
wait $LIVE_PID 2>/dev/null || true
kill $TCPDUMP_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "Analysis"
echo "=========================================="

# Analyze captured packets
if [ -f "$LOG_FILE.pcap" ]; then
    echo "Captured packets:"
    tcpdump -r "$LOG_FILE.pcap" -n 2>/dev/null | wc -l | xargs echo "  Total:"
    
    echo ""
    echo "DHCP Message Types:"
    tcpdump -r "$LOG_FILE.pcap" -n -v 2>/dev/null | grep -i "bootp" | while read line; do
        if echo "$line" | grep -qi "discover"; then
            echo -e "  ${BLUE}DISCOVER${NC} - Client looking for DHCP server"
        elif echo "$line" | grep -qi "offer"; then
            echo -e "  ${GREEN}OFFER${NC} - Server offering IP address"
        elif echo "$line" | grep -qi "request"; then
            echo -e "  ${YELLOW}REQUEST${NC} - Client requesting IP"
        elif echo "$line" | grep -qi "ack"; then
            echo -e "  ${GREEN}ACK${NC} - Server acknowledging request"
        elif echo "$line" | grep -qi "nak"; then
            echo -e "  ${RED}NAK${NC} - Server rejecting request"
        fi
    done
    
    echo ""
    echo "Source/Destination IPs:"
    tcpdump -r "$LOG_FILE.pcap" -n 2>/dev/null | \
        grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort -u | head -10
    
    echo ""
    echo "Full capture saved to: $LOG_FILE.pcap"
    echo "View with: tcpdump -r $LOG_FILE.pcap -n -v"
fi

echo ""
echo "Live log saved to: $LOG_FILE"


