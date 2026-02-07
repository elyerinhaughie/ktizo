# macOS Docker PXE Server - Solution Summary

## The Hurdle

**Problem**: Docker Desktop on macOS runs containers in a Linux VM. Even with `network_mode: host`, containers cannot access the macOS host's physical network interface. The container sees Docker's VM network (192.168.65.x), not your physical network (10.0.1.136).

**Impact**: Your Proxmox VM on the physical network (10.0.x.x) cannot reach the PXE server running in Docker.

## Solution Implemented

### ✅ Bridge Network + Port Mapping

I've switched the DNSMASQ container from `network_mode: host` to a **bridge network with port mapping**. This is the best Docker-based solution for macOS.

**Configuration**:
- Container runs in `ktizo-network` (bridge)
- Ports 67/udp and 69/udp are mapped to the host
- Container has privileged mode for full capabilities

**How it works**:
1. DNSMASQ listens on ports 67/69 inside the container
2. Docker Desktop maps these ports to the macOS host
3. External VMs can connect to `10.0.1.136:67` and `10.0.1.136:69`

## Current Status

- ✅ DNSMASQ running in Docker (bridge network)
- ✅ Ports 67/udp and 69/udp mapped to host
- ✅ Privileged mode enabled
- ✅ Configuration correct

## Testing

1. **Verify ports are mapped**:
   ```bash
   docker compose ps dnsmasq
   # Should show: 0.0.0.0:67->67/udp, 0.0.0.0:69->69/udp
   ```

2. **Check if ports are listening on host**:
   ```bash
   lsof -i :67 -i :69
   ```

3. **Test from Proxmox VM**:
   - Boot VM with PXE enabled
   - Monitor logs: `docker compose logs -f dnsmasq`
   - Check for DHCP requests

## If It Still Doesn't Work

### Alternative 1: UDP Proxy (Hybrid)
If broadcasts don't work, use the UDP proxy:
```bash
brew install socat
./scripts/udp-proxy.sh start
```

### Alternative 2: Host DNSMASQ (Most Reliable)
Run DNSMASQ on macOS host instead:
```bash
docker compose stop dnsmasq
./setup-host-dnsmasq.sh
```

### Alternative 3: Linux Deployment
For production, deploy on a Linux server where host networking works perfectly.

## Files Created

- `MACOS_DOCKER_PXE_SOLUTION.md` - Detailed solution guide
- `scripts/udp-proxy.sh` - UDP forwarding script (if needed)
- `setup-host-dnsmasq.sh` - Host DNSMASQ setup (if needed)

## Next Steps

1. Test with your Proxmox VM
2. Check DNSMASQ logs for DHCP requests
3. If broadcasts don't work, try UDP proxy or host DNSMASQ

The Docker setup is now configured for macOS compatibility. Test and let me know if you need to try the alternatives!

