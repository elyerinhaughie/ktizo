# iPXE "Nothing to Boot" Troubleshooting

## Problem
iPXE loads but shows "nothing to boot" message.

## Root Causes

### 1. No Approved Devices + Strict Mode Enabled ✅ **FIXED**
- **Issue**: Boot script had no approved devices, strict mode was enabled
- **Result**: Script exits immediately with "nothing to boot"
- **Fix**: Disabled strict mode so it attempts local boot

### 2. No Local OS to Boot
- **Issue**: VM has no operating system installed
- **Result**: Local boot attempts fail, shows "nothing to boot"
- **Fix**: The script should auto-install Talos if no OS is found

### 3. Boot Script Flow Issue
- **Issue**: Script doesn't reach the auto-install section
- **Result**: Falls through without booting anything
- **Fix**: Verify boot script logic

## Current Status

✅ **Strict mode disabled** - Script will now attempt local boot
✅ **Boot script regenerated** - Updated with new settings

## Boot Script Flow (After Fix)

1. **MAC Check**: Checks if device MAC is approved
2. **If Unknown MAC** (current situation):
   - Shows warning message
   - Attempts local boot (strict mode disabled)
   - If no OS found → Auto-installs Talos
3. **If Approved MAC**:
   - Shows boot menu
   - User can choose installation or local boot

## Next Steps

### Option 1: Test with Current Setup
The VM should now:
1. Load iPXE
2. Show "Unknown MAC" warning
3. Attempt local boot
4. If no OS → Auto-install Talos

### Option 2: Add Device to System
To properly register the device:

1. **Get the MAC address** from iPXE output
2. **Register device** via API or web UI:
   ```bash
   curl -X POST http://localhost:8000/api/v1/devices/register \
     -H "Content-Type: application/json" \
     -d '{"mac_address": "XX:XX:XX:XX:XX:XX"}'
   ```
3. **Approve device** in web UI
4. Boot script will regenerate with device included

### Option 3: Check Boot Script Logic
If it still shows "nothing to boot", check:
- Does the script reach `:boot_local`?
- Does it try all drives (0x80, 0x81, etc.)?
- Does it fall through to `:auto_install`?

## Debugging

### Check Boot Script
```bash
cat compiled/pxe/boot.ipxe
```

### Monitor DNSMASQ Logs
```bash
docker compose logs -f dnsmasq
```

### Check if Talos Files Exist
```bash
ls -la compiled/pxe/talos/
# Should have:
# - vmlinuz-amd64-v1.12.0
# - initramfs-amd64-v1.12.0.xz
```

## Expected Behavior Now

With strict mode disabled:
1. iPXE loads `boot.ipxe`
2. Shows "Unknown MAC" message
3. Attempts to boot from local drives
4. If no bootable OS found → Auto-installs Talos
5. Should NOT show "nothing to boot" anymore

If it still shows "nothing to boot", the issue is likely:
- Boot script not reaching auto-install section
- Or Talos kernel/initrd files missing

