# Strict Boot Mode

This document explains the Strict Boot Mode security feature in Ktizo.

## Overview

Strict Boot Mode controls what happens when an **unapproved device** attempts to boot via PXE. This is a critical security feature that prevents unintended disk wiping and OS installations.

## The Problem

By default (strict mode **disabled**), when an unapproved device boots via PXE:

1. iPXE loads and checks the device's MAC address
2. MAC is not in the approved list
3. iPXE attempts to boot from local disk (tries drives 0x80, 0x81, 0x82, 0x83)
4. **If no bootable OS is found:**
   - Device automatically enters Talos installation menu
   - Menu times out after 10 seconds (default selection: "Run")
   - Talos installer runs and **wipes /dev/sda**
   - New Talos OS is installed, destroying existing data

**This can cause accidental data loss on:**
- Laptops that accidentally PXE boot
- Servers being repurposed
- Devices with misconfigured BIOS boot order
- Test machines with valuable local data

## The Solution: Strict Boot Mode

When Strict Boot Mode is **enabled**:

1. iPXE loads and checks the device's MAC address
2. MAC is not in the approved list
3. iPXE immediately **exits** to the next BIOS boot device
4. Device continues to USB, CD-ROM, or other boot options
5. **No disk wiping occurs**

## Configuration

### Enable Strict Mode

**Web Interface:**
1. Navigate to **Network Settings**
2. Scroll to **PXE Boot Configuration** section
3. Check the box: **"Strict Boot Mode"**
4. Click **"Save Settings"**
5. Click **"Apply Settings"** to regenerate boot.ipxe

**API:**
```bash
curl -X PUT http://localhost:8000/api/v1/network/settings/1 \
  -H "Content-Type: application/json" \
  -d '{"strict_boot_mode": true}'

# Then apply settings to regenerate configs
curl -X POST http://localhost:8000/api/v1/network/settings/apply
```

### Warning Indicators

When strict mode is **disabled**, you'll see warnings:

**In Web UI:**
```
⚠️ Warning: With strict mode disabled, unapproved devices may attempt to boot from
local disk. If no bootable OS is found, the device will automatically enter the Talos
installation menu, which could result in unintended disk wiping and OS installation.
Enable strict mode to prevent this behavior in production environments.
```

**In iPXE Boot Screen (for unapproved devices):**
```
========================================
Unknown MAC Address
========================================
Unknown MAC: 00:11:22:33:44:55
This device is not approved.
Please add this device in the Ktizo web interface.
WARNING: Strict mode is disabled.
Attempting local boot...
If no OS is found, automatic installation may wipe this disk!
```

## Behavior Comparison

### Strict Mode: DISABLED (Default)

| Step | Approved Device | Unapproved Device |
|------|----------------|-------------------|
| 1. PXE Boot | ✓ MAC found | ✗ MAC not found |
| 2. Action | Load Talos with config | Try local disk boot |
| 3. If no local OS | N/A | **Auto-install Talos** |
| 4. Result | Installs as configured | **May wipe disk** |

**Risk Level:** 🔴 HIGH - Data loss possible

### Strict Mode: ENABLED

| Step | Approved Device | Unapproved Device |
|------|----------------|-------------------|
| 1. PXE Boot | ✓ MAC found | ✗ MAC not found |
| 2. Action | Load Talos with config | Exit immediately |
| 3. If no local OS | N/A | Continue to next boot device |
| 4. Result | Installs as configured | **No disk changes** |

**Risk Level:** 🟢 LOW - Protected

## Use Cases

### When to ENABLE Strict Mode

✅ **Production environments**
- Prevents accidental installations on production servers
- Ensures only approved devices can network boot
- Protects against misconfigured BIOS settings

✅ **Shared networks**
- Laptops and workstations on the same network
- Prevents user devices from accidentally booting
- Reduces help desk tickets from accidental wipes

✅ **Security-sensitive environments**
- Compliance requirements
- Audit trail enforcement
- Explicit approval required

### When to DISABLE Strict Mode

⚠️ **Development/testing** (with caution)
- Testing new device configurations
- Rapid prototyping with multiple machines
- Lab environments with no important data

⚠️ **Initial cluster deployment**
- Bulk device provisioning
- All devices are new/disposable
- Faster onboarding workflow

**Note:** Even in these scenarios, consider enabling strict mode and using manual device approval to maintain control.

## Technical Implementation

### Database
- Setting stored in `network_settings.strict_boot_mode` (BOOLEAN)
- Default value: `FALSE`
- Persists across restarts

### iPXE Template
```jinja2
:unknown
{% if strict_mode %}
echo Strict boot mode enabled - exiting to next boot device...
exit
{% else %}
echo WARNING: Strict mode is disabled.
echo Attempting local boot...
goto boot_local
{% endif %}
```

### Auto-Regeneration
When strict mode is changed:
1. Save network settings
2. Apply settings (regenerate configs)
3. boot.ipxe is regenerated with new strict_mode value
4. All future boots respect the new setting

## Best Practices

1. **Enable by default in production**
   - Set strict mode to `true` immediately after initial setup
   - Document the setting in your deployment procedures

2. **Use device approval workflow**
   - Add devices manually before they boot
   - OR approve them as they appear (pending status)
   - Don't rely on permissive mode for convenience

3. **BIOS configuration**
   - Set PXE boot as last option (after local disk)
   - Disable PXE boot on non-cluster devices
   - Use BIOS passwords to prevent boot order changes

4. **Network segmentation**
   - Isolate cluster network from user networks
   - Use VLANs for PXE boot traffic
   - Limit DHCP responses to cluster subnet only

5. **Monitoring**
   - Monitor device registration attempts
   - Alert on unknown MAC addresses
   - Review pending devices regularly

## Recovery Scenarios

### Scenario: Strict mode enabled, forgot to approve device

**Problem:** Device won't install because it exits immediately

**Solution:**
1. Device boots → exits to next device → fails to boot
2. Admin adds device in web UI (Device Management → Add Device)
3. Set MAC, hostname, IP, role
4. Click "Approve"
5. Device reboots → MAC now in list → installation proceeds

### Scenario: Strict mode disabled, device accidentally wiped

**Problem:** Laptop accidentally PXE booted and wiped local disk

**Prevention (for future):**
1. Enable strict mode immediately
2. Disable PXE boot on laptops in BIOS
3. Move PXE boot to last in boot order

**Recovery:**
- Data is lost if no backup exists
- Restore from backups if available
- Reinstall OS on affected device

## FAQ

**Q: Does strict mode affect approved devices?**
A: No. Approved devices boot normally regardless of strict mode setting.

**Q: Can I enable strict mode after devices are already approved?**
A: Yes. It only affects unapproved devices trying to boot.

**Q: What if I need to test a new device quickly?**
A: Add and approve the device in the web UI first, then boot it.

**Q: Does changing strict mode require restarting DNSMASQ?**
A: No. The setting is applied when you click "Apply Settings" which regenerates boot.ipxe. The config watcher automatically reloads DNSMASQ.

**Q: Is strict mode the default?**
A: No, it defaults to `false` for backward compatibility. Enable it manually.

**Q: Can strict mode be bypassed?**
A: Only by spoofing an approved MAC address, which requires network access and knowledge of approved MACs.

## Related Documentation

- [Device Management Workflow](DEVICE_WORKFLOW.md)
- [Configuration Generation](CONFIG_GENERATION.md)
- [Boot Flow](BOOT_FLOW.md)
