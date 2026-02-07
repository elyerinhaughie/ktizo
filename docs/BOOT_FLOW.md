# Ktizo Boot Flow

This document describes the correct boot sequence for Talos devices using Ktizo.

## Boot Sequence

### 1. PXE Boot
The device starts up and performs a PXE boot:
- BIOS/UEFI initiates PXE boot
- DHCP request to network (DNSMASQ responds)
- TFTP download of iPXE bootloader

### 2. iPXE Execution
iPXE runs and loads the Talos operating system:
- iPXE script fetches Talos kernel (`vmlinuz`)
- iPXE script fetches Talos initramfs (`initramfs.xz`)
- iPXE passes kernel parameters including the configuration URL
- Talos kernel boots

**Example iPXE Script:**
```ipxe
#!ipxe

# Set Talos URLs
set talos-kernel http://ktizo-server/talos/vmlinuz
set talos-initrd http://ktizo-server/talos/initramfs.xz
set config-url http://ktizo-server:8000/api/v1/config/download

# Boot Talos with config URL parameter
kernel ${talos-kernel} talos.config=${config-url} talos.platform=metal
initrd ${talos-initrd}
boot
```

### 3. Talos Boot Process
Talos boots and handles configuration fetching:

**First Boot (Device Not Registered):**
1. Talos attempts to fetch config from `talos.config` URL
2. Backend receives request with MAC address
3. Device not found → Backend creates device record with status=PENDING
4. Backend returns 403 Forbidden
5. Talos waits/retries periodically

**After Admin Approval:**
1. Admin approves device in web UI
2. Admin sets hostname, IP, and role (controlplane/worker)
3. Talos retries config fetch
4. Backend checks device status → APPROVED
5. Backend:
   - Reads base config from `templates/base/` (controlplane.yaml or worker.yaml)
   - Injects hostname and static IP into YAML
   - Returns customized configuration
6. Talos receives configuration and proceeds with installation
7. Device installs Talos to disk and joins cluster

## Key Points

### iPXE's Role
- **Only responsible for:** Loading Talos kernel and passing boot parameters
- **NOT responsible for:** Device registration, configuration fetching, or approval workflow
- **Minimal logic:** Just chainload Talos with a config URL

### Talos's Role
- **Handles:** Configuration fetching via HTTP
- **Identifies itself:** Automatically includes MAC address in requests
- **Retries:** Built-in retry logic if config fetch fails
- **Applies config:** Installs and configures system once config is received

### Backend's Role
- **Registers devices:** Creates database entries on first config request
- **Enforces approval:** Returns 403 until device is approved
- **Customizes configs:** Injects per-device settings (hostname, IP) into base configs
- **Tracks activity:** Records last config download time

## Configuration URL Format

The `talos.config` parameter is a simple HTTP URL:

```
talos.config=http://ktizo-server:8000/api/v1/config/download
```

**Note:** You do NOT need to manually append the MAC address to the URL. Talos will automatically identify itself to the backend using its network interface information.

## Backend Endpoints

### `/api/v1/config/download` (POST)
Called by Talos during boot to fetch its configuration.

**Request Body:**
```json
{
  "mac_address": "00:11:22:33:44:55"
}
```

**Response (if approved):**
```yaml
# Customized Talos configuration YAML
machine:
  network:
    hostname: node-01
    interfaces:
      - addresses:
          - 10.0.5.100/24
# ... rest of configuration
```

**Response (if not approved):**
```
HTTP 403 Forbidden
Device not approved. Current status: pending
```

### `/api/v1/devices/register` (POST)
Optional endpoint for explicit device registration (can be called by Talos or manually).

## TFTP Directory Structure

The TFTP server serves Talos boot files:

```
/var/lib/tftpboot/
├── talos/
│   ├── vmlinuz         # Talos kernel
│   └── initramfs.xz    # Talos initramfs
└── pxe/
    └── boot.ipxe       # iPXE boot script
```

## Troubleshooting

### Device Stuck at Boot
**Symptom:** Device keeps retrying config fetch
**Cause:** Device status is PENDING
**Solution:** Approve device in web UI

### 403 Forbidden
**Symptom:** Talos logs show 403 error fetching config
**Cause:** Device not approved or rejected
**Solution:** Check device status and approve if needed

### Device Not Appearing in UI
**Symptom:** Device booting but not showing in Device Management
**Cause:** Talos not reaching backend (network issue or wrong URL)
**Solution:**
- Verify `talos.config` URL is correct
- Check backend is accessible from device network
- Check backend logs for incoming requests

### Wrong Configuration Downloaded
**Symptom:** Device gets controlplane config but should be worker
**Cause:** Device role not set correctly
**Solution:** Edit device in UI and set correct role before approving

## Security Notes

1. **Default Deny:** All devices start as PENDING and cannot download configs
2. **Explicit Approval:** Administrator must manually approve each device
3. **MAC-Based Identity:** Devices identified by MAC address (can be spoofed, but requires physical network access)
4. **Audit Trail:** System logs first seen time, approval time, and last config download
5. **No Auto-Approval:** Currently no automatic approval (by design)

## Future Enhancements

Potential improvements to boot flow:

1. **Certificate-Based Auth:** Use Talos machine certificates instead of MAC addresses
2. **Pre-Registration:** Allow admin to pre-register devices before first boot
3. **Auto-Approval Rules:** Approve devices matching certain MAC patterns
4. **Rate Limiting:** Prevent config fetch abuse
5. **Webhook Notifications:** Alert admins when new devices appear
