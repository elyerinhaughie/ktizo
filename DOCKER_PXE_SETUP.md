# Docker PXE Setup for macOS

## Changes Made

### 1. Network Configuration
- **Changed from**: `network_mode: host` (doesn't work on macOS Docker Desktop)
- **Changed to**: Bridge network with port mapping

### 2. Port Mapping
Added explicit port mappings:
```yaml
ports:
  - "67:67/udp"    # DHCP
  - "69:69/udp"    # TFTP
  - "8080:8080"    # Webproc admin interface
```

### 3. Interface Binding
- **Removed**: Interface specification (`interface=en0`)
- **Reason**: Docker containers can't access host network interfaces on macOS
- DNSMASQ now listens on all interfaces within the container

### 4. Network Settings
- Set `interface` to `null` or empty string in network settings
- This prevents DNSMASQ from trying to bind to a non-existent interface

## How It Works

1. **DNSMASQ Container**: Runs in bridge network, listens on ports 67/69 inside container
2. **Port Mapping**: Docker Desktop maps these ports to the macOS host
3. **Network Access**: External VMs can connect to `10.0.1.136:67` and `10.0.1.136:69`

## Limitations on macOS

### DHCP Broadcasts
- **Issue**: Docker Desktop on macOS doesn't properly forward UDP broadcast packets
- **Impact**: Initial DHCP discovery broadcasts from PXE clients may not reach the container
- **Workaround**: If the client already knows the server IP, direct connections will work

### ProxyDHCP Mode
- ProxyDHCP should work if:
  - The client can reach the server IP directly
  - The client's existing DHCP server forwards PXE options
  - The client makes direct requests to the server

## Testing

### 1. Verify DNSMASQ is Running
```bash
docker compose ps dnsmasq
docker compose logs dnsmasq
```

### 2. Check Port Mapping
```bash
# Should show ports 67 and 69 mapped
docker compose ps dnsmasq

# Check if ports are listening inside container
docker compose exec dnsmasq netstat -tuln | grep -E ':(67|69)'
```

### 3. Test TFTP (from another machine)
```bash
# From your Proxmox VM or another machine on the network
tftp 10.0.1.136
tftp> get pxe/ipxe.efi
```

### 4. Test DHCP (from Proxmox VM)
1. Boot Proxmox VM with PXE enabled
2. Check DNSMASQ logs:
   ```bash
   docker compose logs -f dnsmasq
   ```
3. Look for DHCP requests in the logs

## Troubleshooting

### DNSMASQ Not Receiving DHCP Requests

**Problem**: Proxmox VM can't see the PXE server

**Possible Causes**:
1. Docker Desktop port mapping not working for UDP broadcasts
2. macOS firewall blocking ports
3. Network routing issues

**Solutions**:

1. **Check macOS Firewall**:
   ```bash
   # System Preferences > Security & Privacy > Firewall
   # Allow Docker Desktop through firewall
   ```

2. **Verify Port Mapping**:
   ```bash
   # Check if ports are actually mapped
   lsof -i :67 -i :69
   ```

3. **Test Direct Connection**:
   ```bash
   # From Proxmox VM, test if you can reach the server
   ping 10.0.1.136
   tftp 10.0.1.136
   ```

4. **Check DNSMASQ Logs**:
   ```bash
   docker compose logs dnsmasq | grep -i dhcp
   ```

### Alternative: Use Host DNSMASQ

If Docker port mapping doesn't work for DHCP broadcasts, you can:
1. Keep backend/frontend in Docker
2. Run DNSMASQ on macOS host (see `setup-host-dnsmasq.sh`)

## Configuration

### Network Settings API
Update network settings to remove interface binding:
```bash
curl -X PUT http://localhost:8000/api/v1/network/settings/1 \
  -H "Content-Type: application/json" \
  -d '{
    "interface": null,
    "server_ip": "10.0.1.136",
    "dhcp_mode": "proxy"
  }'
```

### Regenerate Config
After updating settings:
```bash
curl -X POST http://localhost:8000/api/v1/network/settings/apply
```

## Current Configuration

- **Server IP**: 10.0.1.136
- **DHCP Mode**: Proxy (doesn't assign IPs)
- **Interface**: None (listens on all interfaces in container)
- **TFTP Root**: `/var/lib/tftpboot` (mapped to `./compiled`)

## Next Steps

1. **Test with Proxmox VM**:
   - Boot VM with PXE enabled
   - Monitor DNSMASQ logs
   - Check if DHCP requests appear

2. **If DHCP Broadcasts Don't Work**:
   - Consider running DNSMASQ on macOS host
   - Or deploy on a Linux server where host networking works

3. **Verify TFTP**:
   - Test TFTP file transfer from VM
   - Ensure iPXE boot files are accessible

## Files Modified

- `docker-compose.yaml` - Changed DNSMASQ to use bridge network with port mapping
- Network settings - Interface set to null

## Platform Notes

- **macOS**: Port mapping works, but UDP broadcasts may be limited
- **Linux**: Host networking works perfectly, use `network_mode: host`
- **Windows**: Similar limitations to macOS

For production, consider deploying on Linux where host networking works correctly.

