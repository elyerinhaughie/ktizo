# Ktizo Quick Start (Native Installation)

## Installation

```bash
./install.sh
```

## Start Everything (Recommended)

```bash
# Intelligent run script - handles everything automatically
./run.sh
```

This will:
- ✅ Check and initialize database if needed
- ✅ Start backend and frontend
- ✅ Start config watcher
- ✅ Check dnsmasq status
- ✅ Show service URLs and log locations

## Manual Start (Alternative)

If you prefer manual control:

```bash
# 1. Initialize database
cd backend
source ../venv/bin/activate
python -m app.db.migrate

# 2. Start services
./start.sh

# 3. In another terminal, start config watcher (optional)
./watch-dnsmasq.sh
```

## Access Web UI

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Configure PXE Server

1. Open http://localhost:5173
2. Go to **Network Settings**
3. Configure:
   - **Server IP**: Your host IP (e.g., 10.0.1.136)
   - **Interface**: Your network interface (e.g., en0 on macOS)
   - **DHCP Mode**: Proxy (recommended) or Server
   - **Strict Boot Mode**: Disable for testing
4. Click **"Save Settings"**
5. Click **"Apply Settings"** to generate dnsmasq config

## Start dnsmasq

**macOS:**
```bash
brew services start dnsmasq
```

**Linux (systemd):**
```bash
systemctl start dnsmasq
```

**Alpine Linux (OpenRC):**
```bash
rc-service dnsmasq start
rc-update add dnsmasq  # Enable on boot
```

## Verify

```bash
# Check if dnsmasq is listening
lsof -i :67 -i :69  # macOS/Linux
netstat -ulnp | grep -E ':(67|69)'  # Alpine/Linux alternative

# Check dnsmasq logs
tail -f /var/log/dnsmasq.log  # Linux
tail -f /usr/local/var/log/dnsmasq.log  # macOS
journalctl -u dnsmasq -f  # systemd
```

## Boot Your VM

1. Boot Proxmox VM with PXE enabled
2. Monitor dnsmasq logs for DHCP requests
3. Device should boot and install Talos

## Stop Services

```bash
./stop.sh
```

## Troubleshooting

- **Backend won't start**: Check `logs/backend.log`
- **Frontend won't start**: Check Node.js version and port 5173
- **dnsmasq issues**: Run `sudo dnsmasq --test` to check config
- **PXE not working**: Verify ports 67/69 are accessible, check firewall

For detailed troubleshooting, see [INSTALL.md](INSTALL.md).

