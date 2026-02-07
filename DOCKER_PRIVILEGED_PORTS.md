# Docker Privileged Ports Configuration

## Solution Applied ✅

Added `NET_BIND_SERVICE` capability to the DNSMASQ container to allow binding to privileged ports (< 1024).

### Changes Made

In `docker-compose.yaml`, added:
```yaml
cap_add:
  - NET_ADMIN
  - NET_BIND_SERVICE  # Allow binding to privileged ports (< 1024)
```

### Verification

DNSMASQ is now listening on:
- **Port 67 (UDP)** - DHCP/ProxyDHCP
- **Port 69 (UDP)** - TFTP

Verified with: `docker compose exec dnsmasq netstat -tuln`

## macOS Limitation ⚠️

**Important**: Even though DNSMASQ can bind to privileged ports inside the container, Docker Desktop on macOS runs in a VM. The `network_mode: host` doesn't actually expose these ports to your physical network interface.

### Why This Matters

- Container can bind to ports ✅
- Ports are accessible inside Docker's VM ✅
- Ports may NOT be accessible from physical network ❌ (macOS limitation)

### Solutions for macOS

#### Option 1: Test from Docker Network
If testing with other containers, they can reach DNSMASQ on ports 67/69.

#### Option 2: Use Port Forwarding (Limited)
Port forwarding won't work for DHCP broadcasts, but you can test TFTP:
```yaml
ports:
  - "69:69/udp"  # TFTP (DHCP won't work with port mapping)
```

#### Option 3: Run DNSMASQ on Host (Best for macOS)
```bash
# Install dnsmasq
brew install dnsmasq

# Copy config
sudo cp compiled/dnsmasq/dnsmasq.conf /usr/local/etc/dnsmasq.conf

# Start dnsmasq
sudo brew services start dnsmasq
```

#### Option 4: Deploy on Linux
For production, deploy on a Linux server where host networking works correctly.

## Alternative: Privileged Mode

If `NET_BIND_SERVICE` doesn't work, you can use full privileged mode:

```yaml
dnsmasq:
  privileged: true  # Gives all capabilities (less secure)
```

## Testing

To verify ports are listening:
```bash
# Inside container
docker compose exec dnsmasq netstat -tuln | grep -E ':(67|69)'

# On host (macOS - may not show Docker ports)
lsof -i :67 -i :69
```

## Current Status

- ✅ DNSMASQ container has `NET_BIND_SERVICE` capability
- ✅ DNSMASQ is listening on ports 67 and 69 inside container
- ⚠️ macOS Docker Desktop limitation may prevent external access
- ✅ Configuration is correct for Linux deployment

