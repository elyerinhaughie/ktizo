# Proxmox VM PXE Boot Troubleshooting

## Problem
Your Proxmox VM with iPXE cannot see the PXE server despite being on the same network (10.0.x.x).

## Root Cause
Docker Desktop on macOS runs in a VM. Even with `network_mode: host`, the DNSMASQ container cannot access the physical network interface (`en0`). The container is isolated in Docker's internal network (192.168.65.x), not your physical network (10.0.1.136).

## Solution: Run DNSMASQ on macOS Host

### Step 1: Stop Docker DNSMASQ Container
```bash
cd /Users/elycin/PycharmProjects/ktizo
docker compose stop dnsmasq
```

### Step 2: Run Setup Script
```bash
./setup-host-dnsmasq.sh
```

This script will:
- Install dnsmasq via Homebrew (if not installed)
- Copy the generated config to `/usr/local/etc/dnsmasq.conf`
- Adjust TFTP paths for macOS
- Start dnsmasq as a system service

### Step 3: Verify DNSMASQ is Running
```bash
# Check service status
sudo brew services list | grep dnsmasq

# Check if it's listening on ports 67 and 69
sudo lsof -i :67 -i :69

# View logs
tail -f /usr/local/var/log/dnsmasq.log
```

### Step 4: Test from Proxmox VM
1. Boot your Proxmox VM with PXE enabled
2. Check DNSMASQ logs for DHCP requests:
   ```bash
   tail -f /usr/local/var/log/dnsmasq.log
   ```
3. You should see DHCP requests from the VM's MAC address

## Manual Setup (Alternative)

If the script doesn't work, you can set it up manually:

```bash
# Install dnsmasq
brew install dnsmasq

# Copy config (adjust TFTP path to your project directory)
sudo cp compiled/dnsmasq/dnsmasq.conf /usr/local/etc/dnsmasq.conf

# Edit the config to fix TFTP path
sudo nano /usr/local/etc/dnsmasq.conf
# Change: tftp-root=/var/lib/tftpboot
# To: tftp-root=/Users/elycin/PycharmProjects/ktizo/compiled

# Test config
sudo dnsmasq --test

# Start service
sudo brew services start dnsmasq
```

## Verification Checklist

- [ ] DNSMASQ is running on macOS host (not in Docker)
- [ ] DNSMASQ is listening on port 67 (UDP) for DHCP
- [ ] DNSMASQ is listening on port 69 (UDP) for TFTP
- [ ] DNSMASQ config has correct interface (en0)
- [ ] DNSMASQ config has correct server IP (10.0.1.136)
- [ ] TFTP root path points to your `compiled/` directory
- [ ] Proxmox VM is on the same network (10.0.x.x)
- [ ] Firewall allows UDP ports 67 and 69

## Testing Connectivity

### From macOS Host
```bash
# Test TFTP server (from another machine on network)
tftp 10.0.1.136
tftp> get pxe/ipxe.efi
```

### From Proxmox VM
1. Enable PXE boot in VM settings
2. Boot the VM
3. Check DNSMASQ logs for DHCP requests
4. VM should receive PXE boot information

## Common Issues

### DNSMASQ not starting
- Check logs: `tail -f /usr/local/var/log/dnsmasq.log`
- Verify config: `sudo dnsmasq --test`
- Check if ports are already in use: `sudo lsof -i :67 -i :69`

### VM still can't see server
- Verify VM is on same network segment (10.0.x.x)
- Check macOS firewall settings
- Verify DNSMASQ is listening on en0 interface
- Check DNSMASQ logs for incoming DHCP requests

### TFTP file not found
- Verify TFTP root path in config matches your project directory
- Check file permissions: `ls -la compiled/pxe/`
- Ensure files exist: `ls compiled/pxe/ipxe.efi compiled/pxe/undionly.kpxe`

## Switching Back to Docker

If you want to use Docker DNSMASQ again (e.g., on Linux):
```bash
# Stop host dnsmasq
sudo brew services stop dnsmasq

# Start Docker container
docker compose up -d dnsmasq
```

## Network Configuration

Current settings:
- **Server IP**: 10.0.1.136
- **Network Interface**: en0
- **DHCP Mode**: Proxy (doesn't assign IPs, just provides PXE info)
- **TFTP Root**: `/Users/elycin/PycharmProjects/ktizo/compiled`

Make sure your Proxmox VM is on the same network (10.0.x.x subnet).


