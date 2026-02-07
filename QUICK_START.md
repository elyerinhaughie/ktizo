# Ktizo Quick Start (Native Installation)

## Installation

```bash
./install.sh
```

## Initialize Database

```bash
cd backend
source ../venv/bin/activate
python -m app.db.migrate
```

## Start Services

```bash
# Start backend and frontend
./start.sh

# In another terminal, start config watcher (optional)
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
sudo brew services start dnsmasq
```

**Linux:**
```bash
sudo systemctl start dnsmasq
```

## Verify

```bash
# Check if dnsmasq is listening
sudo lsof -i :67 -i :69

# Check dnsmasq logs
tail -f /var/log/dnsmasq.log  # Linux
tail -f /usr/local/var/log/dnsmasq.log  # macOS
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

