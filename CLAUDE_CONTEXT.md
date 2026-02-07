# Claude Code Session Context
**Date:** 2026-02-06
**Project:** Ktizo - Talos Linux PXE Deployment System

---

## Project Overview

**Ktizo** is a PXE-based deployment system for Talos Linux clusters with:
- FastAPI backend (Python 3.14 preferred, 3.11+ supported)
- Vue.js frontend
- DNSMASQ for PXE boot (DHCP proxy + TFTP)
- Device approval workflow (MAC-based)
- SQLite database

**Key Directories:**
- `backend/` - FastAPI application
- `frontend/` - Vue.js application
- `templates/` - Jinja2 templates and Talos base configs
- `compiled/` - Generated configurations (served via TFTP/HTTP)
- `data/` - SQLite database (ktizo.db)

---

## Completed Work (Previous Sessions)

### 1. VolumeConfig Implementation (COMPLETED)

**Problem:** UI existed for configuring disk layout (EPHEMERAL partition size limits) but backend never generated the VolumeConfig documents for Talos.

**Solution:** Implemented full VolumeConfig generation in `backend/app/services/config_generator.py`

**Changes Made:**
1. Added `_generate_volume_configs()` method to query volume configs from database
2. Modified `generate_config_from_params()` and `generate_device_config()` to:
   - Load multi-document base templates with `yaml.safe_load_all()`
   - Generate VolumeConfig documents alongside machine configs
   - Output multi-document YAML with `---` separators

**Files Modified:**
- `backend/app/services/config_generator.py` - Core implementation
- `backend/test_volume_config.py` - Test script (NEW)
- `docs/VOLUME_CONFIG.md` - Complete documentation (NEW)
- `docs/VOLUME_CONFIG_EXAMPLE.yaml` - Example output (NEW)
- `README.md` - Updated feature list

**Database Schema:**
```sql
CREATE TABLE volume_configs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- 'EPHEMERAL' or 'IMAGE-CACHE'
    disk_selector_match TEXT,   -- CEL expression (optional)
    min_size TEXT,              -- e.g., '2GB', '100GB'
    max_size TEXT,              -- e.g., '100GB', '1TB'
    grow BOOLEAN DEFAULT TRUE
);
```

**Use Case:** Limit EPHEMERAL to 100GB on 1TB disk, leaving ~900GB for Rook/Ceph OSDs.
**Current Volume Config:** EPHEMERAL with max_size=100GB, min_size=2GB

### 2. PXE Boot - Host Networking (COMPLETED)

Changed DNSMASQ to `network_mode: host` in `docker-compose.yaml` to see DHCP broadcasts.

### 3. Line Ending Fix (COMPLETED)

Fixed CRLF issues in `scripts/watch-dnsmasq.sh`.

---

## Current Session Work - PXE Network Diagnosis

### Problem: Proxmox VM Cannot Discover PXE Server

**Symptom:** Proxmox VM thinks there is no boot device. Cannot see PXE server.

### Root Cause: Docker Desktop WSL2 Network Isolation

**Diagnosed the real networking issue.** The stack is:

| Component | Network | IP |
|-----------|---------|-----|
| Windows host | Physical LAN | `10.0.1.11` |
| WSL2 | NAT'd virtual network | `172.25.68.129/20` |
| DNSMASQ container (`host` mode) | Docker Desktop LinuxKit VM | `192.168.65.3/24` |
| Proxmox VMs | Physical LAN | `10.0.x.x` |

**The problem:** `network_mode: host` on Docker Desktop for Windows does NOT give the container access to the physical network. It gives access to Docker Desktop's internal LinuxKit VM network (`192.168.65.x`). DNSMASQ is listening for DHCP broadcasts on `10.0.0.0/16` but it's isolated on `192.168.65.0/24` - it will NEVER see broadcasts from the Proxmox network.

### Solution In Progress: WSL2 Mirrored Networking

**Created `.wslconfig`** at `C:\Users\elyci\.wslconfig`:
```ini
[wsl2]
networkingMode=mirrored
```

**Next Steps Required (user must do):**
1. Stop containers: `docker-compose down`
2. From PowerShell: `wsl --shutdown`
3. Reopen WSL terminal
4. Verify network changed: `ip addr show` - should now show physical LAN IP (`10.0.1.x`) instead of `172.25.x.x`
5. Start containers: `docker-compose up -d`
6. Test if DNSMASQ can now see physical network: `docker exec ktizo-dnsmasq ip addr show`

**Fallback Plan:** If Docker Desktop's `network_mode: host` still maps to the LinuxKit VM (not the WSL2 host), then DNSMASQ must be run directly in WSL2 (outside Docker) since it needs raw L2 broadcast access. The rest of the stack (backend, frontend) can stay in Docker.

---

## Current System State

### Network Configuration
- **Ktizo Server IP:** 10.0.1.11
- **DHCP Range (Proxy):** 10.0.0.0/255.255.0.0
- **Talos Version:** v1.12.2
- **Gateway:** 10.0.0.1

### DNSMASQ Configuration
- **Mode:** Proxy DHCP (doesn't assign IPs)
- **TFTP Root:** /var/lib/tftpboot -> ./compiled/
- **DNS:** Disabled (port=0)
- **Logging:** DHCP logging enabled
- **Config file:** `compiled/dnsmasq/dnsmasq.conf`

### Available Boot Files
```
compiled/pxe/
├── boot.ipxe              # Main iPXE boot script
├── undionly.kpxe         # BIOS iPXE loader
├── ipxe.efi              # UEFI iPXE loader
├── ipxe.pxe              # Generic iPXE
├── snponly.efi           # UEFI SNP loader
└── talos/                # Talos boot files
    ├── vmlinuz-amd64-v1.12.2
    ├── initramfs-amd64-v1.12.2.xz
    └── (multiple versions available)
```

### Database State
- **Location:** `data/ktizo.db`
- **Tables:** cluster_settings, network_settings, devices, volume_configs

### Docker Containers
```
ktizo-backend          - FastAPI (port 8000)
ktizo-frontend         - Vue.js/Vite (port 5173)
ktizo-dnsmasq          - DNSMASQ (host networking)
ktizo-config-watcher   - Monitors compiled/ for changes
```

---

## Boot Script Behavior (boot.ipxe)

**Current Logic:**
1. Checks MAC address against approved devices database
2. **No match found:** Goes to `:unknown` handler
3. **Strict mode disabled:** Attempts local boot
4. **No OS found:** Auto-installs Talos (DANGER - WIPES DISK!)

**Strict boot mode is currently DISABLED.**

---

## Key Config File Locations

- DNSMASQ config: `compiled/dnsmasq/dnsmasq.conf`
- iPXE boot script: `compiled/pxe/boot.ipxe`
- Device configs: `compiled/talos/configs/{mac}.yaml`
- Base templates: `templates/base/controlplane.yaml`, `templates/base/worker.yaml`
- WSL config: `C:\Users\elyci\.wslconfig`
- Docker Compose: `docker-compose.yaml`

---

## API Endpoints Reference

### Volume Configuration
- `GET /api/v1/volume/configs` - List all volume configs
- `GET /api/v1/volume/configs/name/EPHEMERAL` - Get EPHEMERAL config
- `POST /api/v1/volume/configs` - Create volume config
- `PUT /api/v1/volume/configs/{id}` - Update volume config
- `DELETE /api/v1/volume/configs/{id}` - Delete volume config

### Device Management
- `GET /api/v1/devices` - List all devices
- `POST /api/v1/devices/{id}/approve` - Approve device
- `POST /api/v1/devices/regenerate` - Regenerate all configs

### Cluster Settings
- `GET /api/v1/cluster/settings` - Get cluster settings
- `POST /api/v1/cluster/config/generate` - Generate base Talos configs

---

## Quick Reference Commands

### Container Management
```bash
docker-compose up -d              # Start all services
docker-compose down               # Stop all services
docker-compose logs -f dnsmasq    # Watch DNSMASQ logs
docker-compose restart dnsmasq    # Restart DNSMASQ
docker-compose ps                 # Check container status
```

### Testing
```bash
docker-compose exec backend python test_volume_config.py  # Test VolumeConfig
docker exec ktizo-dnsmasq ls -la /var/lib/tftpboot/pxe/   # Verify TFTP files
ip addr show                                               # Check WSL2 network
docker exec ktizo-dnsmasq ip addr show                     # Check container network
```

---

## Remaining Tasks (After WSL Restart)

1. **Verify mirrored networking works** - `ip addr show` should show `10.0.x.x`
2. **Test DNSMASQ sees physical network** - Check container interfaces
3. **If Docker still isolated:** Move DNSMASQ out of Docker, run natively in WSL2
4. **PXE boot test** - Boot Proxmox VM, check DNSMASQ logs for DHCP request
5. **Device approval flow** - Approve device, verify VolumeConfig in generated config
6. **Full Talos installation test** - End-to-end with EPHEMERAL volume limits
7. **Enable strict boot mode** for production safety

---

## Important Notes

- **Strict Boot Mode:** Currently DISABLED - unapproved devices may auto-wipe disks!
- **VolumeConfig:** Fully implemented and tested
- **Line Endings:** Always use LF for shell scripts (not CRLF)
- **Docker Desktop limitation:** `network_mode: host` maps to LinuxKit VM, not physical network
- **WSL2 mirrored networking:** Configured in `.wslconfig`, requires `wsl --shutdown` to apply

---

**End of Context Document**
