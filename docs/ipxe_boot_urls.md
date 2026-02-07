# iPXE Boot URLs and Configuration

This document contains important URLs and configuration information for iPXE boot files.

## Purpose
This file stores vital information about iPXE bootloader URLs, download locations, and related configuration that will be used for the Ktizo PXE boot system.

## Information to be added
 577 sudo curl -L -o undionly.kpxe https://boot.ipxe.org/undionly.kpxe && \
 578 sudo curl -L -o ipxe-i386.efi https://boot.ipxe.org/ipxe-i386.efi && \
 579 sudo curl -L -o ipxe-x86_64.efi https://boot.ipxe.org/ipxe-x86_64.efi && \
 580 sudo curl -L -o ipxe-arm32.efi https://boot.ipxe.org/ipxe-arm32.efi && \
 581 sudo curl -L -o ipxe-arm64.efi https://boot.ipxe.org/ipxe-arm64.efi && \
 582 sudo curl -L -o snponly-x86_64.efi https://boot.ipxe.org/snponly-x86_64.efi && \
 589 sudo curl -L -o undionly.kpxe https://boot.ipxe.org/undionly.kpxe && \
 590 sudo curl -L -o ipxe-i386.efi https://boot.ipxe.org/ipxe-i386.efi && \
 591 sudo curl -L -o ipxe-x86_64.efi https://boot.ipxe.org/ipxe-x86_64.efi && \
 592 sudo curl -L -o ipxe-arm32.efi https://boot.ipxe.org/ipxe-arm32.efi && \
 593 sudo curl -L -o ipxe-arm64.efi https://boot.ipxe.org/ipxe-arm64.efi && \
 594 sudo curl -L -o snponly-x86_64.efi https://boot.ipxe.org/snponly-x86_64.efi && \

Please add these URLS to the boot sequence, take a look at the dnsmasq config to see how these could be used.
From what I recall, we had some kind of chain boot issue where we needed to rebuild undi.
---

#!/bin/sh
# Build custom iPXE with embedded Talos boot script for Alpine Linux

set -e

echo "Building custom iPXE for Talos PXE boot..."

# Backup existing undionly.kpxe
cd /srv/tftp
if [ -f undionly.kpxe ]; then
    echo "Backing up existing undionly.kpxe..."
    mv undionly.kpxe undionly.kpxe.backup
fi

# Create embedded chain script
echo "Creating embedded boot script..."
cat > /srv/tftp/chain-boot.ipxe << 'EOF'
#!ipxe

echo ================================
echo Talos PXE Boot - Network Init
echo ================================

echo Initializing network interface...
ifopen net0

echo Requesting DHCP configuration...
dhcp net0 || goto dhcp_failed

echo Network configured successfully
echo IP Address: ${net0/ip}
echo Subnet: ${net0/netmask}
echo Gateway: ${net0/gateway}
echo DHCP Server: ${dhcp-server}
echo Next Server: ${next-server}

#echo
#echo Loading Talos boot configuration...
#chain tftp://${next-server}/talos/boot.ipxe || goto fallback

#:fallback
echo First attempt failed, trying static server...
chain tftp://10.0.5.113/talos/boot.ipxe || goto error

:dhcp_failed
echo DHCP configuration failed!
echo Dropping to iPXE shell for debugging...
shell

:error
echo Failed to load boot configuration!
echo Dropping to iPXE shell for debugging...
shell
EOF

# Install build dependencies
echo "Installing build dependencies..."
apk add --no-cache git gcc make binutils perl xz-dev mtools syslinux bash musl-dev

# Clone iPXE if not already present
if [ ! -d /tmp/ipxe ]; then
    echo "Cloning iPXE repository..."
    git clone https://github.com/ipxe/ipxe.git /tmp/ipxe
else
    echo "iPXE repository already exists, updating..."
    cd /tmp/ipxe


/srv/tftp # cat chain-boot.ipxe
#!ipxe

echo ================================
echo Talos PXE Boot - Network Init
echo ================================

echo Initializing network interface...
ifopen net0

echo Requesting DHCP configuration...
dhcp net0 || goto dhcp_failed

echo Network configured successfully
echo IP Address: ${net0/ip}
echo Subnet: ${net0/netmask}
echo Gateway: ${net0/gateway}
echo DHCP Server: ${dhcp-server}
echo Next Server: ${next-server}

#echo
#echo Loading Talos boot configuration...
#chain tftp://${next-server}/talos/boot.ipxe || goto fallback

#:fallback
echo First attempt failed, trying static server...
chain tftp://10.0.5.113/talos/boot.ipxe || goto error

:dhcp_failed
echo DHCP configuration failed!
echo Dropping to iPXE shell for debugging...
shell

:error
echo Failed to load boot configuration!
echo Dropping to iPXE shell for debugging...
shell
---

---

## Notes
- Created: 2025-10-22
- Last Updated: 2025-10-22
