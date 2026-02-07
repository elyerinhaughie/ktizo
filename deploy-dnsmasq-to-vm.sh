#!/bin/bash
# Deploy dnsmasq config to remote VM
# Usage: ./deploy-dnsmasq-to-vm.sh [VM_IP] [VM_USER]

set -e

# Configuration
VM_IP="${1:-${KTIZO_VM_IP:-10.0.42.2}}"
VM_USER="${2:-${KTIZO_VM_USER:-root}}"
LOCAL_CONFIG="${KTIZO_HOME:-$HOME/.ktizo}/compiled/dnsmasq/dnsmasq.conf"
REMOTE_CONFIG="/etc/dnsmasq.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Deploying dnsmasq config to VM"
echo "=========================================="
echo "VM: $VM_USER@$VM_IP"
echo "Local config: $LOCAL_CONFIG"
echo "Remote config: $REMOTE_CONFIG"
echo ""

# Check if local config exists
if [ ! -f "$LOCAL_CONFIG" ]; then
    echo -e "${RED}Error:${NC} Local config file not found: $LOCAL_CONFIG"
    echo "Please configure network settings in the web UI first, then apply settings."
    exit 1
fi

# Test SSH connection
echo "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${RED}Error:${NC} Cannot connect to VM at $VM_IP"
    echo ""
    echo "Please ensure:"
    echo "1. VM is running and accessible"
    echo "2. SSH is enabled on the VM"
    echo "3. SSH key is set up (or password authentication is enabled)"
    echo ""
    echo "To set up SSH key:"
    echo "  ssh-copy-id $VM_USER@$VM_IP"
    exit 1
fi

# Check if dnsmasq is installed on VM
echo "Checking if dnsmasq is installed on VM..."
if ! ssh "$VM_USER@$VM_IP" "which dnsmasq" &>/dev/null; then
    echo -e "${YELLOW}Warning:${NC} dnsmasq not found on VM"
    echo "Installing dnsmasq..."
    
    # Detect OS and install
    if ssh "$VM_USER@$VM_IP" "command -v apk" &>/dev/null; then
        ssh "$VM_USER@$VM_IP" "apk add --no-cache dnsmasq"
    elif ssh "$VM_USER@$VM_IP" "command -v apt-get" &>/dev/null; then
        ssh "$VM_USER@$VM_IP" "apt-get update && apt-get install -y dnsmasq"
    elif ssh "$VM_USER@$VM_IP" "command -v yum" &>/dev/null; then
        ssh "$VM_USER@$VM_IP" "yum install -y dnsmasq"
    elif ssh "$VM_USER@$VM_IP" "command -v dnf" &>/dev/null; then
        ssh "$VM_USER@$VM_IP" "dnf install -y dnsmasq"
    else
        echo -e "${RED}Error:${NC} Cannot determine package manager on VM"
        echo "Please install dnsmasq manually on the VM"
        exit 1
    fi
fi

# Copy config to VM
echo "Copying config to VM..."
scp "$LOCAL_CONFIG" "$VM_USER@$VM_IP:$REMOTE_CONFIG" || {
    echo -e "${RED}Error:${NC} Failed to copy config to VM"
    exit 1
}

# Copy iPXE bootloader files to TFTP root
echo "Copying iPXE bootloader files to TFTP root..."
LOCAL_PXE_DIR="${KTIZO_HOME:-$HOME/.ktizo}/compiled/pxe"
REMOTE_TFTP_ROOT="/var/lib/tftpboot"
REMOTE_PXE_DIR="$REMOTE_TFTP_ROOT/pxe"

# Ensure remote PXE directory exists
ssh "$VM_USER@$VM_IP" "mkdir -p $REMOTE_PXE_DIR" || {
    echo -e "${RED}Error:${NC} Failed to create TFTP PXE directory"
    exit 1
}

# Copy iPXE bootloader files if they exist locally
# Include both standard and chainboot bootloaders, plus boot.ipxe
if [ -d "$LOCAL_PXE_DIR" ]; then
    for file in undionly.kpxe ipxe.efi ipxe.pxe snponly.efi undionly-chainboot.kpxe ipxe-chainboot.efi ipxe-chainboot.pxe chainboot.ipxe boot.ipxe; do
        if [ -f "$LOCAL_PXE_DIR/$file" ]; then
            echo "  Copying $file..."
            scp "$LOCAL_PXE_DIR/$file" "$VM_USER@$VM_IP:$REMOTE_PXE_DIR/" || {
                echo -e "${YELLOW}Warning:${NC} Failed to copy $file"
            }
        fi
    done
else
    echo -e "${YELLOW}Warning:${NC} Local PXE directory not found: $LOCAL_PXE_DIR"
    echo "  iPXE files may need to be downloaded on the VM"
fi

# Also copy from VM's compiled directory if it exists (for native installs)
echo "Checking for iPXE files in VM's compiled directory..."
ssh "$VM_USER@$VM_IP" "
    if [ -d /root/.ktizo/compiled/pxe ]; then
        for file in undionly.kpxe ipxe.efi ipxe.pxe snponly.efi undionly-chainboot.kpxe ipxe-chainboot.efi ipxe-chainboot.pxe chainboot.ipxe boot.ipxe; do
            if [ -f /root/.ktizo/compiled/pxe/\$file ] && [ ! -f $REMOTE_PXE_DIR/\$file ]; then
                echo \"  Copying \$file from compiled directory...\"
                cp /root/.ktizo/compiled/pxe/\$file $REMOTE_PXE_DIR/ || echo \"  Failed to copy \$file\"
            fi
        done
    fi
" || echo -e "${YELLOW}Warning:${NC} Could not copy files from VM's compiled directory"

# Test config on VM
echo "Testing config on VM..."
if ssh "$VM_USER@$VM_IP" "dnsmasq --test -C $REMOTE_CONFIG" 2>&1; then
    echo -e "${GREEN}✓${NC} Config is valid"
else
    echo -e "${RED}Error:${NC} Config test failed on VM"
    exit 1
fi

# Reload dnsmasq on VM
echo "Reloading dnsmasq on VM..."
if ssh "$VM_USER@$VM_IP" "command -v systemctl" &>/dev/null; then
    ssh "$VM_USER@$VM_IP" "systemctl reload dnsmasq || systemctl restart dnsmasq" 2>&1
elif ssh "$VM_USER@$VM_IP" "command -v rc-service" &>/dev/null; then
    ssh "$VM_USER@$VM_IP" "rc-service dnsmasq restart" 2>&1
else
    ssh "$VM_USER@$VM_IP" "pkill -HUP dnsmasq || (pkill dnsmasq && dnsmasq -C $REMOTE_CONFIG)" 2>&1
fi

# Check if dnsmasq is running
sleep 1
if ssh "$VM_USER@$VM_IP" "pgrep -x dnsmasq" &>/dev/null; then
    echo -e "${GREEN}✓${NC} dnsmasq is running on VM"
    
    # Check if listening on ports
    if ssh "$VM_USER@$VM_IP" "lsof -i :67 -i :69 2>/dev/null || netstat -ulnp 2>/dev/null | grep -qE ':(67|69)'"; then
        echo -e "${GREEN}✓${NC} dnsmasq is listening on ports 67/69"
    else
        echo -e "${YELLOW}⚠${NC}  dnsmasq is running but may not be listening on ports 67/69"
        echo "   Check firewall rules and ensure dnsmasq has permission to bind to privileged ports"
    fi
else
    echo -e "${YELLOW}⚠${NC}  dnsmasq may not be running. Check VM logs."
fi

echo ""
echo -e "${GREEN}✓${NC} Deployment complete!"
echo ""
echo "To verify PXE server is working:"
echo "  1. Check VM logs: ssh $VM_USER@$VM_IP 'journalctl -u dnsmasq -f'"
echo "  2. Test from a PXE client on the same network"
echo "  3. Check DHCP offers: tcpdump -i any port 67"

