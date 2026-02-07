# Ktizo Native Installation Guide

This guide installs Ktizo to run directly on your host system (no Docker).

## Quick Start

```bash
./install.sh
```

The installation script will:
- Install all system dependencies (Python, Node.js, dnsmasq)
- Set up Python virtual environment
- Install Python and Node.js packages
- Download talosctl
- Configure dnsmasq
- Create startup scripts
- Set up system services (systemd/launchd)

## Manual Installation

If you prefer to install manually:

### 1. Install System Dependencies

**macOS:**
```bash
# Prefer Python 3.14, fallback to 3.13, 3.12, or 3.11
brew install python@3.14 node@20 dnsmasq || \
brew install python@3.13 node@20 dnsmasq || \
brew install python@3.12 node@20 dnsmasq || \
brew install python@3.11 node@20 dnsmasq
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
# Prefer Python 3.14, fallback to available version
sudo apt-get install -y python3.14 python3.14-venv python3-pip nodejs npm dnsmasq curl || \
sudo apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm dnsmasq curl || \
sudo apt-get install -y python3.12 python3.12-venv python3-pip nodejs npm dnsmasq curl || \
sudo apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm dnsmasq curl || \
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm dnsmasq curl
```

**Linux (RHEL/CentOS/Fedora):**
```bash
sudo dnf install -y python3 python3-pip nodejs npm dnsmasq curl
```

**Linux (Alpine):**
```bash
sudo apk update
sudo apk add --no-cache python3 py3-pip nodejs npm dnsmasq curl bash
```

### 2. Set Up Python Environment

```bash
cd /path/to/ktizo
# Prefer Python 3.14, fallback to available version
python3.14 -m venv venv || \
python3.13 -m venv venv || \
python3.12 -m venv venv || \
python3.11 -m venv venv || \
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3. Set Up Node.js Frontend

```bash
cd frontend
npm install
npm install @rollup/rollup-linux-arm64-musl --save-optional --no-save  # For ARM64
```

### 4. Download talosctl

```bash
cd backend
# Get latest version
TALOS_VERSION=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | grep -oP '"tag_name": "\K[^"]+')
# Download for your OS/arch
curl -L "https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)" -o talosctl
chmod +x talosctl
```

### 5. Create Directories

```bash
mkdir -p compiled/dnsmasq
mkdir -p compiled/pxe/talos
mkdir -p compiled/talos/configs
mkdir -p data
mkdir -p logs
```

### 6. Configure dnsmasq

**macOS:**
```bash
sudo cp compiled/dnsmasq/dnsmasq.conf /usr/local/etc/dnsmasq.conf
sudo brew services start dnsmasq
```

**Linux:**
```bash
sudo cp compiled/dnsmasq/dnsmasq.conf /etc/dnsmasq.conf
sudo systemctl enable dnsmasq
sudo systemctl start dnsmasq
```

## Running Ktizo

### Option 1: Use Startup Scripts

```bash
# Start both backend and frontend
./start.sh

# Or start individually
./start-backend.sh   # Backend only
./start-frontend.sh  # Frontend only
```

### Option 2: Use System Services

**macOS (launchd):**
```bash
launchctl load ~/Library/LaunchAgents/com.ktizo.backend.plist
launchctl start com.ktizo.backend
```

**Linux (systemd):**
```bash
sudo systemctl start ktizo-backend
sudo systemctl status ktizo-backend
```

### Option 3: Manual Start

**Backend:**
```bash
cd backend
source ../venv/bin/activate
export TEMPLATES_DIR="$(pwd)/../templates"
export COMPILED_DIR="$(pwd)/../compiled"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
export VITE_API_URL=http://localhost:8000
npm run dev -- --host 0.0.0.0
```

## Initial Setup

### 1. Initialize Database

```bash
cd backend
source ../venv/bin/activate
python -m app.db.migrate
```

### 2. Configure Network Settings

1. Open web UI: http://localhost:5173
2. Go to Network Settings
3. Configure:
   - Server IP (your host IP, e.g., 10.0.1.136)
   - DHCP mode (proxy or server)
   - Network interface (e.g., en0 on macOS)
4. Click "Save Settings"
5. Click "Apply Settings" to generate dnsmasq config

### 3. Start dnsmasq

**macOS:**
```bash
sudo brew services restart dnsmasq
```

**Linux:**
```bash
sudo systemctl restart dnsmasq
```

## Directory Structure

```
ktizo/
├── backend/          # Python backend
│   ├── app/          # Application code
│   ├── talosctl      # Talos CLI tool
│   └── requirements.txt
├── frontend/         # Vue.js frontend
│   ├── src/
│   └── package.json
├── templates/        # Jinja2 templates
├── compiled/         # Generated configs
│   ├── dnsmasq/      # dnsmasq config
│   ├── pxe/          # PXE boot files
│   └── talos/        # Talos configs
├── data/             # Database and data files
├── venv/             # Python virtual environment
├── logs/             # Application logs
├── install.sh        # Installation script
├── start.sh          # Start all services
├── start-backend.sh  # Start backend only
└── start-frontend.sh # Start frontend only
```

## Environment Variables

You can set these environment variables:

- `TEMPLATES_DIR` - Path to templates directory (default: `./templates`)
- `COMPILED_DIR` - Path to compiled directory (default: `./compiled`)
- `VITE_API_URL` - Backend API URL for frontend (default: `http://localhost:8000`)

## Troubleshooting

### Backend won't start
- Check Python version: `python3 --version` (prefers 3.14, needs 3.11+)
- Activate venv: `source venv/bin/activate`
- Check logs: `logs/backend.log` or `logs/backend.error.log`

### Frontend won't start
- Check Node.js version: `node --version` (needs 18+)
- Reinstall dependencies: `cd frontend && npm install`
- Check for port conflicts: `lsof -i :5173`

### dnsmasq issues
- Check config: `sudo dnsmasq --test`
- Check logs: `tail -f /var/log/dnsmasq.log` (Linux) or `/usr/local/var/log/dnsmasq.log` (macOS)
- Verify ports: `sudo lsof -i :67 -i :69`

### Database issues
- Reinitialize: `cd backend && source ../venv/bin/activate && python -m app.db.migrate`
- Check database file: `ls -la data/`

## Uninstallation

**macOS:**
```bash
launchctl unload ~/Library/LaunchAgents/com.ktizo.backend.plist
rm ~/Library/LaunchAgents/com.ktizo.backend.plist
sudo brew services stop dnsmasq
```

**Linux:**
```bash
sudo systemctl stop ktizo-backend
sudo systemctl disable ktizo-backend
sudo rm /etc/systemd/system/ktizo-backend.service
sudo systemctl daemon-reload
sudo systemctl stop dnsmasq  # If you want to remove dnsmasq too
```

## Advantages Over Docker

- ✅ No networking issues - direct access to host network
- ✅ Better performance - no container overhead
- ✅ Easier debugging - direct process access
- ✅ Native dnsmasq - works perfectly for PXE
- ✅ Simpler setup - no Docker Desktop required

## Production Deployment

For production, consider:
- Using systemd/launchd for service management
- Setting up reverse proxy (nginx) for frontend
- Using process manager (PM2, supervisor) for reliability
- Setting up log rotation
- Configuring firewall rules
- Using SSL/TLS certificates

