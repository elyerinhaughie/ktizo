# PXE Server on Remote VM Setup

If your PXE server (dnsmasq) is running on a remote VM instead of the local host, follow these steps:

## Quick Setup

1. **Set the VM IP address:**
   ```bash
   export KTIZO_VM_IP=10.0.42.2
   export KTIZO_VM_USER=root  # Optional, defaults to root
   ```

2. **Set up SSH access to the VM:**
   ```bash
   ssh-copy-id root@10.0.42.2
   # Or use password authentication (will prompt for password)
   ```

3. **Configure network settings in the web UI:**
   - Open http://localhost:5173 (or your server IP)
   - Go to Network Settings
   - Configure your network settings
   - Click "Apply Settings" to generate the dnsmasq config

4. **Deploy the config to the VM:**
   ```bash
   ./deploy-dnsmasq-to-vm.sh
   ```

   Or let the watcher do it automatically:
   ```bash
   export KTIZO_VM_IP=10.0.42.2
   ./run.sh
   ```

## Manual Deployment

If you prefer to deploy manually:

```bash
# Deploy config to VM
./deploy-dnsmasq-to-vm.sh [VM_IP] [VM_USER]

# Example:
./deploy-dnsmasq-to-vm.sh 10.0.42.2 root
```

The script will:
- ✅ Test SSH connection
- ✅ Install dnsmasq on VM if needed
- ✅ Copy config file to VM
- ✅ Test config validity
- ✅ Reload dnsmasq on VM
- ✅ Verify dnsmasq is running and listening on ports 67/69

## Automatic Deployment (Watcher)

The `watch-dnsmasq.sh` script can automatically deploy config changes to the VM:

```bash
# Set VM IP
export KTIZO_VM_IP=10.0.42.2
export KTIZO_VM_USER=root

# Start watcher (will auto-deploy on config changes)
./watch-dnsmasq.sh
```

Or use `run.sh` which will start the watcher automatically:

```bash
export KTIZO_VM_IP=10.0.42.2
./run.sh
```

## VM Requirements

The VM needs:
- ✅ SSH access enabled
- ✅ dnsmasq installed (script will install if missing)
- ✅ Root/sudo access to manage dnsmasq service
- ✅ Network access to the same network as PXE clients
- ✅ Ports 67 (DHCP) and 69 (TFTP) available

## Troubleshooting

### SSH Connection Failed
```bash
# Test SSH connection
ssh root@10.0.42.2 "echo 'Connection test'"

# Set up SSH key
ssh-copy-id root@10.0.42.2
```

### dnsmasq Not Listening on Ports
```bash
# Check if dnsmasq is running
ssh root@10.0.42.2 "systemctl status dnsmasq"

# Check if ports are in use
ssh root@10.0.42.2 "lsof -i :67 -i :69"

# Check firewall
ssh root@10.0.42.2 "iptables -L -n | grep -E '67|69'"
```

### Config Not Deploying
```bash
# Check if config exists locally
ls -la ~/.ktizo/compiled/dnsmasq/dnsmasq.conf

# Deploy manually
./deploy-dnsmasq-to-vm.sh 10.0.42.2 root
```

### PXE Clients Not Seeing Server
1. Ensure VM is on the same network as clients
2. Check dnsmasq logs on VM: `ssh root@10.0.42.2 "journalctl -u dnsmasq -f"`
3. Verify DHCP is working: `tcpdump -i any port 67` on VM
4. Check firewall rules on VM


