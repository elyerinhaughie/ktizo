#!/bin/bash
# Build custom iPXE bootloaders with embedded chainboot scripts
# This script builds custom iPXE bootloaders that auto-chainload boot.ipxe

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
TFTP_ROOT="${TFTP_ROOT:-/var/lib/tftpboot}"
SERVER_IP="${SERVER_IP:-10.0.42.2}"
PXE_DIR="$TFTP_ROOT/pxe"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building custom iPXE chainboot bootloaders...${NC}"

# Check if base bootloaders exist
if [ ! -f "$PXE_DIR/undionly.kpxe" ]; then
    echo -e "${RED}Error: Base bootloader not found: $PXE_DIR/undionly.kpxe${NC}"
    echo "Please download iPXE bootloaders first"
    exit 1
fi

# Create chainboot script
echo -e "${YELLOW}Creating chainboot script...${NC}"
cat > "$PXE_DIR/chainboot.ipxe" << EOF
#!ipxe

echo ========================================
echo Ktizo PXE Chainboot
echo ========================================
echo Auto-loading boot script from server...
echo Server: ${SERVER_IP}
echo Boot URL: http://${SERVER_IP}:8000/pxe/boot.ipxe

# Prevent infinite loops
isset chainboot_done && exit || set chainboot_done 1

# Ensure network is ready
ifstat net0 || ifopen net0 || echo Network interface ready

# Auto-chainload the boot script (no menu, no prompts)
chain http://${SERVER_IP}:8000/pxe/boot.ipxe || {
    echo ========================================
    echo ERROR: Failed to load boot script
    echo ========================================
    echo Could not load: http://${SERVER_IP}:8000/pxe/boot.ipxe
    echo Check network connectivity and server availability
    sleep 10
    exit
}
EOF

echo -e "${GREEN}Chainboot script created: $PXE_DIR/chainboot.ipxe${NC}"

# Check for makebin (from iPXE tools)
if command -v makebin &> /dev/null; then
    echo -e "${GREEN}Found makebin - building custom bootloaders...${NC}"
    
    # Build custom undionly.kpxe
    if [ -f "$PXE_DIR/undionly.kpxe" ]; then
        echo "Building undionly-chainboot.kpxe..."
        makebin "$PXE_DIR/chainboot.ipxe" "$PXE_DIR/undionly.kpxe" "$PXE_DIR/undionly-chainboot.kpxe"
        chmod 644 "$PXE_DIR/undionly-chainboot.kpxe"
        echo -e "${GREEN}✓ Built: undionly-chainboot.kpxe${NC}"
    fi
    
    # Build custom ipxe.efi if available
    if [ -f "$PXE_DIR/ipxe.efi" ]; then
        echo "Building ipxe-chainboot.efi..."
        makebin "$PXE_DIR/chainboot.ipxe" "$PXE_DIR/ipxe.efi" "$PXE_DIR/ipxe-chainboot.efi"
        chmod 644 "$PXE_DIR/ipxe-chainboot.efi"
        echo -e "${GREEN}✓ Built: ipxe-chainboot.efi${NC}"
    fi
    
    echo -e "${GREEN}Custom bootloaders built successfully!${NC}"
    echo "Update dnsmasq config to use chainboot versions"
    
elif [ -d "/usr/src/ipxe" ] || [ -d "/tmp/ipxe" ]; then
    echo -e "${YELLOW}makebin not found, but iPXE source detected${NC}"
    echo "You can build custom bootloaders manually using iPXE source"
    echo "See: https://ipxe.org/appnote/embedded_script"
else
    echo -e "${YELLOW}makebin not available - cannot embed script${NC}"
    echo "Install iPXE tools or build manually:"
    echo "  1. Install iPXE development tools"
    echo "  2. Or clone iPXE source and build with embedded script"
    echo ""
    echo "For now, chainboot script is available at: $PXE_DIR/chainboot.ipxe"
    echo "You can configure dnsmasq to serve this as the first boot file"
fi

