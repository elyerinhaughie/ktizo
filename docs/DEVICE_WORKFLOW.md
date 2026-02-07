# Device Approval Workflow

This document describes the device approval and configuration workflow in Ktizo.

## Overview

Ktizo implements a secure approval workflow for devices booting via PXE. Devices must be approved before they can download their Talos configuration and join the cluster.

## Workflow Steps

### 1. Device Discovery

When a device boots via PXE for the first time:

1. The device's iPXE script loads the Talos kernel and initramfs
2. Talos boots with a configuration URL parameter pointing to the Ktizo backend
3. During boot, Talos makes an HTTP request to the Ktizo backend with the device's MAC address to register itself
4. The backend registers the device in the database with status `PENDING`

**Talos Boot Parameter:**
```
talos.config=http://ktizo-server:8000/api/v1/config/download?mac=${mac}
```

**API Endpoint (called by Talos):** `POST /api/v1/devices/register`
```json
{
  "mac_address": "00:11:22:33:44:55"
}
```

### 2. Device Approval

Administrators can view pending devices in the Device Management UI:

1. Navigate to "Device Management" in the web interface
2. View all devices filtered by status (pending, approved, rejected)
3. For each pending device:
   - Set hostname (optional)
   - Assign static IP address (optional, defaults to DHCP)
   - Choose role: `controlplane` or `worker`
   - Add notes about the device
   - Click "Approve" or "Reject"

**API Endpoints:**
- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices?status=pending` - List pending devices
- `POST /api/v1/devices/{device_id}/approve` - Approve a device
- `POST /api/v1/devices/{device_id}/reject` - Reject a device

### 3. Configuration Download

Once a device is approved, it can download its configuration:

1. Talos boots and attempts to fetch its configuration from the URL specified in the boot parameters
2. The backend checks if the device (identified by MAC address) is approved
3. If approved, the backend:
   - Reads the base configuration from `templates/base/` (controlplane.yaml or worker.yaml)
   - Customizes it with device-specific settings (hostname, IP address)
   - Returns the configuration as YAML
4. Talos uses this configuration to install and configure itself

**API Endpoint (called by Talos):** `POST /api/v1/config/download`
```json
{
  "mac_address": "00:11:22:33:44:55"
}
```

**Response:** YAML configuration file with customizations

### 4. Configuration Customization

The backend automatically customizes the base Talos configuration for each device:

- **Hostname**: Sets `machine.network.hostname` if specified
- **Static IP**: Adds IP address to `machine.network.interfaces[0].addresses` if specified
- **Role-based Config**: Serves controlplane.yaml or worker.yaml based on device role

## Database Schema

### Device Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| mac_address | String | Unique MAC address |
| hostname | String | Device hostname (optional) |
| ip_address | String | Static IP address (optional) |
| role | Enum | `controlplane` or `worker` |
| status | Enum | `pending`, `approved`, or `rejected` |
| notes | Text | Additional notes |
| first_seen | DateTime | When device first appeared |
| approved_at | DateTime | When device was approved |
| last_config_download | DateTime | Last time device downloaded config |

## Security Considerations

1. **Default Deny**: Devices are created with `status=PENDING` and cannot download configs until approved
2. **MAC Address Validation**: Each device is identified by its unique MAC address
3. **Audit Trail**: The system tracks when devices first appeared, when they were approved, and when they last downloaded configs
4. **Manual Approval**: Requires explicit administrator action to approve devices

## iPXE Integration

The iPXE boot script loads Talos and passes the config URL as a kernel parameter:

```ipxe
#!ipxe

# Get device MAC address
set mac ${net0/mac}

# Set Talos kernel parameters
set talos-kernel http://ktizo-server/talos/vmlinuz
set talos-initrd http://ktizo-server/talos/initramfs.xz
set config-url http://ktizo-server:8000/api/v1/config/download

# Boot Talos with config URL
kernel ${talos-kernel} talos.config=${config-url} talos.platform=metal
initrd ${talos-initrd}
boot
```

**Note:** Talos will automatically include its MAC address when fetching the configuration. The backend uses this to identify and authorize the device.

## Base Configuration Generation

Before devices can boot, you must generate the base Talos configurations:

1. Navigate to "Cluster Settings"
2. Configure cluster parameters (name, endpoint, Kubernetes version, etc.)
3. Click "Generate Cluster Configuration"
4. This creates `templates/base/controlplane.yaml` and `templates/base/worker.yaml`

These base configurations are then customized per-device when downloaded.

## API Reference

### Device Management

- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices/{id}` - Get device by ID
- `POST /api/v1/devices` - Create device manually
- `PUT /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Delete device
- `POST /api/v1/devices/{id}/approve` - Approve device
- `POST /api/v1/devices/{id}/reject` - Reject device

### Device Boot Flow

- `POST /api/v1/devices/register` - Register device (called by Talos during boot)
- `POST /api/v1/config/download` - Download config (called by Talos during boot)

## Future Enhancements

Potential improvements to the workflow:

1. **Bulk Approval**: Approve multiple devices at once
2. **Auto-Approval Rules**: Automatically approve devices matching certain patterns
3. **Webhook Notifications**: Notify administrators when new devices appear
4. **Config Templates**: Custom templates per device group
5. **RBAC**: Role-based access control for device management
