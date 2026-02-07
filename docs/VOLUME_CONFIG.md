# Volume Configuration (Disk Layout)

This document explains how to use the Volume Configuration feature in Ktizo to control Talos system partition sizes.

## Overview

The Volume Configuration feature allows you to limit the size of Talos system partitions, particularly the **EPHEMERAL** partition. This is useful when you want to:

- Reserve disk space for storage solutions like Rook/Ceph
- Prevent Talos from consuming the entire disk
- Allocate specific disk space for container data and images

## What is EPHEMERAL?

The EPHEMERAL partition stores:
- Container runtime data
- Downloaded container images
- System logs
- etcd database (on control plane nodes)

By default, EPHEMERAL grows to consume all available disk space. With Volume Configuration, you can limit its size.

## Feature Requirements

- **Talos Linux v1.8+** (project defaults to v1.11.3)
- Volume configuration is applied during device installation

## How It Works

### 1. Configure in UI

Navigate to **Storage Settings** in the web interface:

1. Enable "Limit EPHEMERAL partition size"
2. Set **Maximum Size** (e.g., `100GB`)
3. Optionally set **Minimum Size** (default: `2GB`)
4. Optionally set **Disk Selector** (CEL expression) for advanced use cases
5. Click "Save Configuration"

### 2. Configuration Storage

The configuration is stored in the database (`volume_configs` table):

```sql
CREATE TABLE volume_configs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- 'EPHEMERAL' or 'IMAGE-CACHE'
    disk_selector_match TEXT,   -- CEL expression (optional)
    min_size TEXT,              -- e.g., '2GB'
    max_size TEXT,              -- e.g., '100GB'
    grow BOOLEAN DEFAULT TRUE
);
```

### 3. Configuration Generation

When a device is approved, the backend generates a **multi-document YAML** configuration:

**Document 1: Machine Config** (standard Talos config)
```yaml
version: v1alpha1
debug: false
persist: true
machine:
  type: worker
  # ... rest of machine config
cluster:
  # ... cluster config
```

**Document 2: VolumeConfig** (partition size limits)
```yaml
---
apiVersion: v1alpha1
kind: VolumeConfig
name: EPHEMERAL
provisioning:
  minSize: 2GB
  maxSize: 100GB
  grow: false
```

The two documents are separated by `---` (YAML multi-document separator).

### 4. Talos Installation

When a device boots and downloads its configuration:

1. Talos receives the multi-document YAML
2. Talos applies the machine configuration
3. Talos applies the VolumeConfig during installation
4. EPHEMERAL partition is created with the specified size limits
5. Remaining disk space is left unpartitioned (available for Rook/Ceph)

## Configuration Options

### Maximum Size

Limits the EPHEMERAL partition to a specific size.

**Format:** `<number><unit>` (e.g., `100GB`, `50GiB`, `1TB`)

**Recommendations:**
- Control plane nodes: 50-100GB
- Worker nodes: 50-200GB (depending on workload)
- Minimum for basic operation: 20GB

### Minimum Size

Ensures EPHEMERAL has at least this much space (default: 2GB).

**Format:** Same as maximum size

### Disk Selector (Advanced)

CEL (Common Expression Language) expression to select which disk to use for EPHEMERAL.

**Examples:**
- `disk.transport == 'nvme'` - Use NVMe drives
- `disk.size > 500GB` - Use disks larger than 500GB
- `disk.model == 'Samsung SSD'` - Use specific drive model

**Note:** Most users should leave this blank to use the default installation disk.

### Grow Behavior

- `grow: false` - Partition stays at maxSize (recommended when maxSize is set)
- `grow: true` - Partition can grow (only if no maxSize is set)

The system automatically sets `grow: false` when maxSize is configured.

## API Endpoints

### List Volume Configurations
```bash
GET /api/v1/volume/configs
```

### Get Volume Configuration by Name
```bash
GET /api/v1/volume/configs/name/EPHEMERAL
```

### Create Volume Configuration
```bash
POST /api/v1/volume/configs
Content-Type: application/json

{
  "name": "EPHEMERAL",
  "max_size": "100GB",
  "min_size": "2GB",
  "disk_selector_match": null,
  "grow": false
}
```

### Update Volume Configuration
```bash
PUT /api/v1/volume/configs/{id}
Content-Type: application/json

{
  "max_size": "150GB"
}
```

### Delete Volume Configuration
```bash
DELETE /api/v1/volume/configs/{id}
```

## Example Use Case: Rook/Ceph Integration

**Scenario:** You have 1TB disks and want to use Rook/Ceph for persistent storage.

**Configuration:**
1. Set EPHEMERAL maxSize to `100GB`
2. Leave ~900GB unpartitioned
3. Rook/Ceph will use the unpartitioned space for OSDs

**Result:**
```
Disk Layout:
├── EFI       ~100MB
├── META      ~1MB
├── STATE     ~100MB
├── EPHEMERAL 100GB (Talos system)
└── Unpartitioned ~900GB (Available for Rook/Ceph)
```

## Implementation Details

### Backend Service

The `ConfigGenerator` service (`app/services/config_generator.py`) handles volume configuration:

1. **Query Volume Configs:** Reads configurations from database
2. **Generate VolumeConfig Documents:** Creates separate YAML documents
3. **Multi-Document YAML:** Combines machine config + volume configs
4. **Output Format:** Writes multi-document YAML to `compiled/talos/configs/{mac}.yaml`

### Key Methods

```python
class ConfigGenerator:
    def _generate_volume_configs(self, db) -> List[Dict[str, Any]]:
        """Generate VolumeConfig documents for system volumes"""
        # Queries database and generates VolumeConfig YAML structures

    def generate_device_config(self, device: Device) -> Optional[Path]:
        """Generate complete config including VolumeConfigs"""
        # Generates multi-document YAML with machine + volume configs
```

### Multi-Document YAML Format

Talos supports multi-document YAML for applying multiple configurations:

```yaml
# Document 1: MachineConfig
version: v1alpha1
machine:
  # ...

---
# Document 2: VolumeConfig
apiVersion: v1alpha1
kind: VolumeConfig
name: EPHEMERAL
provisioning:
  maxSize: 100GB
```

## Testing

A test script is provided to verify the implementation:

```bash
docker-compose exec backend python test_volume_config.py
```

The test:
1. Creates a test EPHEMERAL configuration
2. Generates VolumeConfig documents
3. Generates full multi-document YAML
4. Verifies VolumeConfig is included in output

## Troubleshooting

### VolumeConfig Not Applied

**Symptom:** EPHEMERAL still uses full disk despite configuration

**Causes:**
1. Configuration saved but device not re-provisioned
2. Talos version < v1.8 (VolumeConfig not supported)
3. Device installed before configuration was added

**Solutions:**
1. Regenerate device configs: `POST /api/v1/devices/regenerate`
2. Wipe and reinstall the device
3. Check Talos version in Network Settings

### Invalid Size Format

**Symptom:** Configuration saved but not applied correctly

**Cause:** Invalid size format (e.g., `100G` instead of `100GB`)

**Solution:** Use proper format: `100GB`, `50GiB`, `1TB`

Valid units:
- GB, GiB (gigabytes)
- TB, TiB (terabytes)
- MB, MiB (megabytes)

### Disk Selector Not Matching

**Symptom:** EPHEMERAL not created on expected disk

**Cause:** CEL expression doesn't match any disk

**Solution:**
1. Remove disk selector to use default disk
2. Boot device and check disk attributes: `talosctl get disks`
3. Adjust CEL expression to match actual disk attributes

## References

- [Talos Disk Layout Documentation](https://docs.siderolabs.com/talos/v1.12/configure-your-talos-cluster/storage-and-disk-management/disk-management/layout/)
- [Talos VolumeConfig Reference](https://docs.siderolabs.com/talos/v1.8/reference/configuration/block/volumeconfig)
- [Common Expression Language (CEL)](https://github.com/google/cel-spec)

## Version History

- **v1.0** (Current): Initial implementation
  - Support for EPHEMERAL partition size limits
  - UI for configuration
  - Multi-document YAML generation
  - CEL-based disk selection
