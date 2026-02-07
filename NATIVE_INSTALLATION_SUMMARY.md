# Native Installation - Complete

## What Was Created

### Installation Scripts
- **`install.sh`** - Complete automated installation script
  - Installs all dependencies (Python, Node.js, dnsmasq)
  - Sets up virtual environments
  - Downloads talosctl
  - Configures dnsmasq
  - Creates system services (systemd/launchd)
  - Creates startup scripts

### Management Scripts
- **`start.sh`** - Start all services (backend + frontend)
- **`start-backend.sh`** - Start backend only
- **`start-frontend.sh`** - Start frontend only
- **`stop.sh`** - Stop all services
- **`uninstall.sh`** - Remove installation
- **`watch-dnsmasq.sh`** - Watch for config changes and reload dnsmasq

### Documentation
- **`INSTALL.md`** - Detailed installation guide
- **`QUICK_START.md`** - Quick start guide
- **`README.md`** - Updated with native installation option

## Installation Process

### 1. Run Installation
```bash
./install.sh
```

This will:
- ✅ Install Python 3.14 (or latest available), Node.js 20, dnsmasq
- ✅ Create Python virtual environment
- ✅ Install all Python dependencies
- ✅ Install all Node.js dependencies
- ✅ Download talosctl
- ✅ Create required directories
- ✅ Configure dnsmasq
- ✅ Create startup scripts
- ✅ Set up system services

### 2. Initialize Database
```bash
cd backend
source ../venv/bin/activate
python -c 'from app.db.database import init_db; init_db()'
```

### 3. Start Services
```bash
./start.sh
```

### 4. Configure Network Settings
1. Open http://localhost:5173
2. Configure network settings
3. Apply settings to generate dnsmasq config

### 5. Start dnsmasq
```bash
# macOS
sudo brew services start dnsmasq

# Linux
sudo systemctl start dnsmasq
```

## Advantages Over Docker

✅ **No Networking Issues**
- Direct access to host network interface
- No Docker Desktop VM limitations
- Perfect PXE/DHCP/TFTP support

✅ **Better Performance**
- No container overhead
- Direct file system access
- Faster startup times

✅ **Easier Debugging**
- Direct process access
- Native logging
- Simple troubleshooting

✅ **Simpler Setup**
- No Docker Desktop required
- Standard package managers
- Native system services

## File Locations

- **Backend**: `backend/` (runs from venv)
- **Frontend**: `frontend/` (runs with npm)
- **Database**: `data/ktizo.db`
- **Configs**: `compiled/`
- **Logs**: `logs/` (created automatically)
- **dnsmasq config**: `/usr/local/etc/dnsmasq.conf` (macOS) or `/etc/dnsmasq.conf` (Linux)

## Service Management

### macOS (launchd)
```bash
# Load service
launchctl load ~/Library/LaunchAgents/com.ktizo.backend.plist

# Start/Stop
launchctl start com.ktizo.backend
launchctl stop com.ktizo.backend

# Unload
launchctl unload ~/Library/LaunchAgents/com.ktizo.backend.plist
```

### Linux (systemd)
```bash
# Start/Stop
sudo systemctl start ktizo-backend
sudo systemctl stop ktizo-backend

# Enable/Disable
sudo systemctl enable ktizo-backend
sudo systemctl disable ktizo-backend

# Status
sudo systemctl status ktizo-backend
```

## Next Steps

1. **Run installation**: `./install.sh`
2. **Initialize database**: See INSTALL.md
3. **Start services**: `./start.sh`
4. **Configure**: Use web UI at http://localhost:5173
5. **Test PXE**: Boot your Proxmox VM

The native installation is ready to use!

