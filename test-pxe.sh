#!/bin/bash
# Test PXE server connectivity and functionality
# Tests from local machine to PXE server (typically on VM)

set -e

PXE_SERVER="${1:-10.0.42.2}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "PXE Server Test"
echo "=========================================="
echo "Testing PXE server at: $PXE_SERVER"
echo ""

# Test 1: Ping test
echo -n "1. Testing connectivity (ping)... "
if ping -c 1 -W 2 "$PXE_SERVER" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Server is reachable"
else
    echo -e "${RED}✗${NC} Server is not reachable"
    echo "   Check network connectivity and firewall"
    exit 1
fi

# Test 2: Check if ports are open
echo -n "2. Testing DHCP port (67/UDP)... "
if timeout 2 bash -c "echo > /dev/udp/$PXE_SERVER/67" 2>/dev/null || nc -u -z -w 2 "$PXE_SERVER" 67 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Port 67 is open"
else
    echo -e "${YELLOW}⚠${NC}  Cannot verify port 67 (UDP ports are hard to test)"
    echo "   This is normal - UDP doesn't respond to connection attempts"
fi

echo -n "3. Testing TFTP port (69/UDP)... "
if timeout 2 bash -c "echo > /dev/udp/$PXE_SERVER/69" 2>/dev/null || nc -u -z -w 2 "$PXE_SERVER" 69 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Port 69 is open"
else
    echo -e "${YELLOW}⚠${NC}  Cannot verify port 69 (UDP ports are hard to test)"
fi

# Test 3: Try to get DHCP offer (if tcpdump/dhclient available)
echo ""
echo "4. Testing DHCP (requires root or sudo)..."
if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
    echo "   Sending DHCP discover..."
    
    # Try using dhclient if available
    if command -v dhclient &>/dev/null; then
        TMP_IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
        if [ -n "$TMP_IFACE" ]; then
            echo "   Using interface: $TMP_IFACE"
            # Release any existing lease
            sudo dhclient -r "$TMP_IFACE" 2>/dev/null || true
            # Try to get DHCP offer (timeout after 5 seconds)
            timeout 5 sudo dhclient -v "$TMP_IFACE" 2>&1 | grep -i "dhcp\|offer\|ack" || echo "   No DHCP response (may be normal if server only responds to PXE requests)"
        fi
    else
        echo "   dhclient not available, skipping DHCP test"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Skipping DHCP test (requires root/sudo)"
    echo "   Run with sudo to test DHCP: sudo $0 $PXE_SERVER"
fi

# Test 4: Test TFTP (if tftp client available)
echo ""
echo "5. Testing TFTP..."
if command -v tftp &>/dev/null; then
    echo "   Attempting to fetch boot.ipxe..."
    if echo "get boot.ipxe /tmp/test-boot.ipxe" | tftp "$PXE_SERVER" 2>/dev/null; then
        if [ -f /tmp/test-boot.ipxe ]; then
            echo -e "${GREEN}✓${NC} TFTP is working - boot.ipxe retrieved"
            echo "   File size: $(stat -f%z /tmp/test-boot.ipxe 2>/dev/null || stat -c%s /tmp/test-boot.ipxe 2>/dev/null) bytes"
            rm -f /tmp/test-boot.ipxe
        else
            echo -e "${YELLOW}⚠${NC}  TFTP command succeeded but file not found"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  Could not fetch boot.ipxe via TFTP"
        echo "   This may be normal if file doesn't exist or path is different"
    fi
else
    echo -e "${YELLOW}⚠${NC}  tftp client not available"
    echo "   Install with: brew install tftp-hpa (macOS) or apt-get install tftp (Linux)"
fi

# Test 5: Check HTTP endpoint (for iPXE configs)
echo ""
echo "6. Testing HTTP endpoint (for iPXE configs)..."
HTTP_URL="http://$PXE_SERVER:8000"
if curl -s --max-time 2 "$HTTP_URL/health" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Backend API is accessible at $HTTP_URL"
    
    # Try to get boot script
    if curl -s --max-time 2 "$HTTP_URL/talos/configs/test.yaml" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Config endpoint is responding"
    else
        echo -e "${YELLOW}⚠${NC}  Config endpoint not accessible (may require valid MAC address)"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Backend API not accessible at $HTTP_URL"
    echo "   Backend may be running on different port or not accessible from this network"
fi

# Test 6: Network connectivity summary
echo ""
echo "=========================================="
echo "Network Summary"
echo "=========================================="
echo "PXE Server IP: $PXE_SERVER"
echo "Local IP: $(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}' || echo 'unknown')"
echo ""

# Test 7: Check if on same network
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}' || echo "")
if [ -n "$LOCAL_IP" ]; then
    LOCAL_NET=$(echo "$LOCAL_IP" | cut -d. -f1-3)
    PXE_NET=$(echo "$PXE_SERVER" | cut -d. -f1-3)
    
    if [ "$LOCAL_NET" = "$PXE_NET" ]; then
        echo -e "${GREEN}✓${NC} On same network segment ($LOCAL_NET.x)"
    else
        echo -e "${YELLOW}⚠${NC}  Different network segments (Local: $LOCAL_NET.x, PXE: $PXE_NET.x)"
        echo "   PXE clients must be on same network as PXE server for DHCP to work"
    fi
fi

echo ""
echo "=========================================="
echo "Recommendations"
echo "=========================================="
echo "1. Ensure PXE server (dnsmasq) is running on $PXE_SERVER"
echo "2. Check firewall rules allow UDP ports 67 and 69"
echo "3. Verify dnsmasq config is correct:"
echo "   ssh root@$PXE_SERVER 'cat /etc/dnsmasq.conf'"
echo "4. Check dnsmasq logs:"
echo "   ssh root@$PXE_SERVER 'journalctl -u dnsmasq -f'"
echo "5. Test from a PXE client on the same network"
echo ""

