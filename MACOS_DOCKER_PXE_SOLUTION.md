# Solving macOS Docker Desktop PXE Server Limitation

## The Problem

Docker Desktop on macOS runs in a Linux VM. Even with `network_mode: host`, containers don't have access to the macOS host's physical network interface (`en0`). The container sees Docker's VM network (192.168.65.x), not your physical network (10.0.1.136).

## Solution Options

### Option 1: Bridge Network + Port Mapping (Recommended for Docker)

**Best for**: Keeping everything in Docker, accepting some broadcast limitations

**How it works**:
- Container runs in bridge network
- Docker Desktop maps ports 67/69 to host
- Direct connections work, broadcasts may be limited

**Implementation**:
```yaml
dnsmasq:
  networks:
    - ktizo-network
  ports:
    - "67:67/udp"
    - "69:69/udp"
```

**Pros**:
- ✅ Everything stays in Docker
- ✅ Port mapping works on macOS
- ✅ Direct connections work

**Cons**:
- ⚠️ UDP broadcasts may not work perfectly
- ⚠️ Initial DHCP discovery may fail

### Option 2: UDP Proxy with socat (Hybrid Solution)

**Best for**: Keeping DNSMASQ in Docker while bridging to host network

**How it works**:
- DNSMASQ runs in Docker (bridge network)
- socat runs on macOS host
- socat forwards UDP packets from host to container

**Implementation**:

1. Switch DNSMASQ to bridge network:
```yaml
dnsmasq:
  networks:
    - ktizo-network
  # Remove network_mode: host
```

2. Run UDP proxy script:
```bash
./scripts/udp-proxy.sh start
```

**Pros**:
- ✅ DNSMASQ stays in Docker
- ✅ Can forward broadcasts properly
- ✅ Works with host network

**Cons**:
- ⚠️ Requires socat on host
- ⚠️ Extra process to manage

### Option 3: Run DNSMASQ on macOS Host (Most Reliable)

**Best for**: Maximum compatibility, accepting DNSMASQ runs outside Docker

**How it works**:
- Backend/Frontend stay in Docker
- DNSMASQ runs directly on macOS host
- Full access to physical network

**Implementation**:
```bash
./setup-host-dnsmasq.sh
```

**Pros**:
- ✅ Full network access
- ✅ Broadcasts work perfectly
- ✅ Most reliable for PXE

**Cons**:
- ⚠️ DNSMASQ not in Docker
- ⚠️ Requires Homebrew

### Option 4: Deploy on Linux Server

**Best for**: Production deployment

**How it works**:
- Deploy entire stack on Linux
- Host networking works perfectly
- No limitations

**Pros**:
- ✅ Everything works perfectly
- ✅ Production-ready
- ✅ No workarounds needed

**Cons**:
- ⚠️ Requires Linux server
- ⚠️ Not for local macOS development

## Recommended Approach

For **development on macOS**:
1. Use **Option 1** (Bridge + Port Mapping) for simplicity
2. If broadcasts don't work, use **Option 3** (Host DNSMASQ)

For **production**:
- Use **Option 4** (Linux deployment)

## Quick Implementation

### Switch to Bridge Network (Option 1)

```bash
# Update docker-compose.yaml
# Change network_mode: host to bridge network with ports

docker compose up -d dnsmasq
```

### Use UDP Proxy (Option 2)

```bash
# Install socat
brew install socat

# Start proxy
./scripts/udp-proxy.sh start

# Check status
./scripts/udp-proxy.sh status
```

### Use Host DNSMASQ (Option 3)

```bash
# Stop Docker DNSMASQ
docker compose stop dnsmasq

# Run setup script
./setup-host-dnsmasq.sh
```

## Testing

After implementing any solution:

1. **Check DNSMASQ is listening**:
   ```bash
   sudo lsof -i :67 -i :69
   ```

2. **Test from Proxmox VM**:
   - Boot VM with PXE
   - Check DNSMASQ logs
   - Verify DHCP requests appear

3. **Test TFTP**:
   ```bash
   # From another machine
   tftp 10.0.1.136
   tftp> get pxe/ipxe.efi
   ```

## Current Configuration

You're currently using `network_mode: host` which doesn't work on macOS Docker Desktop. 

**Recommended next step**: Switch to bridge network with port mapping (Option 1) for the simplest Docker-based solution.

