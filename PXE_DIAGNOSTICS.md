# PXE Server Connection Diagnostics

## Issues Found

### 1. **macOS Docker Host Networking Limitation** ⚠️ **CRITICAL**
   - DNSMASQ is configured to use `network_mode: host` to access DHCP broadcasts
   - **Problem**: On macOS, Docker runs in a VM, so "host" networking doesn't actually bind to the host's network interfaces
   - **Impact**: DNSMASQ cannot bind to privileged ports (67 for DHCP, 69 for TFTP) on the actual host network
   - **Evidence**: DNSMASQ is running but not listening on ports 67/69

### 2. **Missing iPXE EFI File** ✅ **FIXED**
   - The `ipxe.efi` file was missing from `compiled/pxe/`
   - **Status**: Downloaded successfully

### 3. **DNSMASQ Configuration** ✅ **WORKING**
   - Configuration file is properly generated
   - Config-watcher is detecting changes and reloading DNSMASQ
   - ProxyDHCP mode is configured correctly

## Current Status

- ✅ DNSMASQ container is running
- ✅ Configuration file is generated and loaded
- ✅ iPXE boot files exist (undionly.kpxe, ipxe.efi, ipxe.pxe)
- ❌ DNSMASQ cannot bind to port 67 (DHCP) - macOS limitation
- ❌ DNSMASQ cannot bind to port 69 (TFTP) - macOS limitation

## Solutions for macOS

### Option 1: Run DNSMASQ on Host (Recommended for Testing)
```bash
# Install dnsmasq on macOS
brew install dnsmasq

# Copy config
sudo cp compiled/dnsmasq/dnsmasq.conf /usr/local/etc/dnsmasq.conf

# Start dnsmasq
sudo brew services start dnsmasq
```

### Option 2: Use Linux VM or Remote Server
- Deploy ktizo on a Linux server where Docker host networking works properly
- Or use a Linux VM with proper network passthrough

### Option 3: Modify Docker Setup for macOS
- Use port forwarding (won't work for DHCP broadcasts)
- Use a bridge network with proper configuration (complex)

## Testing PXE Connection

To test if PXE is working:

1. **Check if DNSMASQ is listening** (on Linux):
   ```bash
   sudo netstat -tuln | grep -E ":(67|69)"
   ```

2. **Test TFTP** (from another machine on the network):
   ```bash
   tftp <server-ip>
   tftp> get pxe/ipxe.efi
   ```

3. **Check DHCP logs**:
   ```bash
   docker compose logs dnsmasq | grep -i dhcp
   ```

## Network Settings

Current configuration:
- Server IP: 10.0.1.136
- DHCP Mode: Proxy (doesn't assign IPs, just provides PXE info)
- TFTP Root: /var/lib/tftpboot (mapped to compiled/)

## Next Steps

1. **For macOS**: Run DNSMASQ directly on the host instead of in Docker
2. **For Production**: Deploy on a Linux server where host networking works correctly
3. **Verify**: Test PXE boot from a physical machine on the same network

