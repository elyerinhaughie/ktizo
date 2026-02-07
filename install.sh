#!/bin/bash
# Ktizo Native Installation Script
# Installs and configures ktizo to run directly on the host (no Docker)

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_USER="${SERVICE_USER:-$(whoami)}"

echo "=========================================="
echo "Ktizo Native Installation"
echo "=========================================="
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PKG_MANAGER="brew"
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux-musl"* ]]; then
    OS="linux"
    if command -v apk &> /dev/null; then
        PKG_MANAGER="apk"
    elif command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
    else
        echo "Error: Unsupported Linux distribution"
        exit 1
    fi
else
    echo "Error: Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo "Package manager: $PKG_MANAGER"
echo ""

# Function to install dependencies
install_dependencies() {
    echo "Installing system dependencies..."
    
    if [[ "$OS" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        echo "Installing packages via Homebrew..."
        # Try Python 3.14 first, fallback to 3.13, 3.12, 3.11
        PYTHON_VERSION=""
        if brew info python@3.14 &>/dev/null; then
            brew install python@3.14 || brew list python@3.14 &>/dev/null
            PYTHON_VERSION="3.14"
            echo "Using Python 3.14"
        elif brew info python@3.13 &>/dev/null; then
            brew install python@3.13 || brew list python@3.13 &>/dev/null
            PYTHON_VERSION="3.13"
            echo "Using Python 3.13 (3.14 not available)"
        elif brew info python@3.12 &>/dev/null; then
            brew install python@3.12 || brew list python@3.12 &>/dev/null
            PYTHON_VERSION="3.12"
            echo "Using Python 3.12 (3.14 not available)"
        else
            brew install python@3.11 || brew list python@3.11 &>/dev/null || true
            PYTHON_VERSION="3.11"
            echo "Using Python 3.11 (3.14 not available)"
        fi
        brew install node@20 dnsmasq || true
        
    elif [[ "$OS" == "linux" ]]; then
        if [[ "$PKG_MANAGER" == "apk" ]]; then
            apk update
            # Try Python 3.14 first, fallback to available version
            if apk search python3.14 &>/dev/null && apk add --no-cache python3.14 py3-pip nodejs npm dnsmasq curl bash 2>/dev/null; then
                echo "Using Python 3.14"
            elif apk search python3.13 &>/dev/null && apk add --no-cache python3.13 py3-pip nodejs npm dnsmasq curl bash 2>/dev/null; then
                echo "Using Python 3.13 (3.14 not available)"
            elif apk search python3.12 &>/dev/null && apk add --no-cache python3.12 py3-pip nodejs npm dnsmasq curl bash 2>/dev/null; then
                echo "Using Python 3.12 (3.14 not available)"
            else
                apk add --no-cache python3 py3-pip nodejs npm dnsmasq curl bash
                echo "Using system Python 3 (3.14 not available)"
            fi
        elif [[ "$PKG_MANAGER" == "apt" ]]; then
            apt-get update
            # Try Python 3.14 first, fallback to 3.13, 3.12, 3.11, then python3
            if apt-cache show python3.14 &>/dev/null && apt-get install -y python3.14 python3.14-venv python3-pip nodejs npm dnsmasq curl 2>/dev/null; then
                echo "Using Python 3.14"
            elif apt-cache show python3.13 &>/dev/null && apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm dnsmasq curl 2>/dev/null; then
                echo "Using Python 3.13 (3.14 not available)"
            elif apt-cache show python3.12 &>/dev/null && apt-get install -y python3.12 python3.12-venv python3-pip nodejs npm dnsmasq curl 2>/dev/null; then
                echo "Using Python 3.12 (3.14 not available)"
            elif apt-cache show python3.11 &>/dev/null && apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm dnsmasq curl 2>/dev/null; then
                echo "Using Python 3.11 (3.14 not available)"
            else
                apt-get install -y python3 python3-venv python3-pip nodejs npm dnsmasq curl
                echo "Using system Python 3 (3.14 not available)"
            fi
        elif [[ "$PKG_MANAGER" == "yum" ]] || [[ "$PKG_MANAGER" == "dnf" ]]; then
            $PKG_MANAGER install -y python3 python3-pip nodejs npm dnsmasq curl
        fi
    fi
    
    echo "✅ System dependencies installed"
}

# Function to setup Python virtual environment
setup_python() {
    echo ""
    echo "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    
    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        # Try Python 3.14 first, then fallback to 3.13, 3.12, 3.11, then python3
        if command -v python3.14 &> /dev/null; then
            python3.14 -m venv "$VENV_DIR"
            echo "Created venv with Python 3.14"
        elif command -v python3.13 &> /dev/null; then
            python3.13 -m venv "$VENV_DIR"
            echo "Created venv with Python 3.13"
        elif command -v python3.12 &> /dev/null; then
            python3.12 -m venv "$VENV_DIR"
            echo "Created venv with Python 3.12"
        elif command -v python3.11 &> /dev/null; then
            python3.11 -m venv "$VENV_DIR"
            echo "Created venv with Python 3.11"
        else
            python3 -m venv "$VENV_DIR"
            echo "Created venv with system Python 3"
        fi
    fi
    
    # Activate venv and install dependencies
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    
    echo "✅ Python environment ready"
}

# Function to setup Node.js frontend
setup_node() {
    echo ""
    echo "Setting up Node.js frontend..."
    
    cd "$INSTALL_DIR/frontend"
    
    # Install dependencies
    npm install
    npm install @rollup/rollup-linux-arm64-musl --save-optional --no-save 2>/dev/null || true
    
    echo "✅ Node.js environment ready"
}

# Function to download talosctl
download_talosctl() {
    echo ""
    echo "Downloading talosctl..."
    
    cd "$INSTALL_DIR/backend"
    
    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        TALOS_ARCH="arm64"
    elif [[ "$ARCH" == "x86_64" ]]; then
        TALOS_ARCH="amd64"
    else
        TALOS_ARCH="amd64"  # Default fallback
    fi
    
    # Get latest version
    # Use sed instead of grep -P for better Alpine compatibility
    TALOS_VERSION=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p' | head -1)
    if [ -z "$TALOS_VERSION" ]; then
        TALOS_VERSION="v1.7.0"
    fi
    
    # Download talosctl
    if [[ "$OS" == "macos" ]]; then
        TALOS_OS="darwin"
    else
        TALOS_OS="linux"
    fi
    
    TALOS_URL="https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-${TALOS_OS}-${TALOS_ARCH}"
    
    echo "Downloading talosctl from: $TALOS_URL"
    curl -L "$TALOS_URL" -o talosctl
    chmod +x talosctl
    
    echo "✅ talosctl downloaded ($TALOS_VERSION)"
}

# Function to create directories
create_directories() {
    echo ""
    echo "Creating required directories..."
    
    mkdir -p "$INSTALL_DIR/compiled/dnsmasq"
    mkdir -p "$INSTALL_DIR/compiled/pxe/talos"
    mkdir -p "$INSTALL_DIR/compiled/talos/configs"
    mkdir -p "$INSTALL_DIR/data"
    
    echo "✅ Directories created"
}

# Function to setup dnsmasq
setup_dnsmasq() {
    echo ""
    echo "Configuring dnsmasq..."
    
    if [[ "$OS" == "macos" ]]; then
        DNSMASQ_CONF="/usr/local/etc/dnsmasq.conf"
        DNSMASQ_DIR="/usr/local/etc"
    else
        if [[ "$PKG_MANAGER" == "apk" ]]; then
            # Alpine uses /etc/dnsmasq.conf
            DNSMASQ_CONF="/etc/dnsmasq.conf"
            DNSMASQ_DIR="/etc"
        else
            DNSMASQ_CONF="/etc/dnsmasq.conf"
            DNSMASQ_DIR="/etc/dnsmasq.d"
            mkdir -p "$DNSMASQ_DIR"
        fi
    fi
    
    # Backup existing config
    if [ -f "$DNSMASQ_CONF" ]; then
        echo "Backing up existing dnsmasq config..."
        cp "$DNSMASQ_CONF" "${DNSMASQ_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create initial config (will be overwritten by backend)
    echo "# Ktizo dnsmasq configuration
# This file is managed by Ktizo backend
# Manual edits will be overwritten

# Default placeholder - will be generated by backend
port=0
log-dhcp
" | tee "$DNSMASQ_CONF" > /dev/null
    
    echo "✅ dnsmasq configured"
    echo "   Config location: $DNSMASQ_CONF"
}

# Function to create systemd service (Linux)
create_systemd_service() {
    if [[ "$OS" != "linux" ]]; then
        return
    fi
    
    echo ""
    echo "Creating systemd service..."
    
    # Check if systemd is available (Alpine might not have it)
    if ! command -v systemctl &> /dev/null; then
        echo "⚠️  systemd not available (Alpine?), skipping systemd service creation"
        echo "   Use startup scripts instead: ./start.sh"
        return
    fi
    
    SERVICE_FILE="/etc/systemd/system/ktizo-backend.service"
    
    tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Ktizo Backend API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    if command -v systemctl &> /dev/null; then
        systemctl daemon-reload
        systemctl enable ktizo-backend
        echo "✅ systemd service created"
        echo "   Start with: systemctl start ktizo-backend"
    else
        echo "⚠️  systemctl not available, service file created but not enabled"
        echo "   Use startup scripts instead: ./start.sh"
    fi
}

# Function to create launchd plist (macOS)
create_launchd_service() {
    if [[ "$OS" != "macos" ]]; then
        return
    fi
    
    echo ""
    echo "Creating launchd service..."
    
    PLIST_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$PLIST_DIR"
    
    PLIST_FILE="$PLIST_DIR/com.ktizo.backend.plist"
    
    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ktizo.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR/backend</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>TEMPLATES_DIR</key>
        <string>$INSTALL_DIR/templates</string>
        <key>COMPILED_DIR</key>
        <string>$INSTALL_DIR/compiled</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/backend.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/backend.error.log</string>
</dict>
</plist>
EOF

    mkdir -p "$INSTALL_DIR/logs"
    
    echo "✅ launchd service created"
    echo "   Load with: launchctl load $PLIST_FILE"
    echo "   Start with: launchctl start com.ktizo.backend"
}

# Function to create startup scripts
create_startup_scripts() {
    echo ""
    echo "Creating startup scripts..."
    
    # Backend start script
    cat > "$INSTALL_DIR/start-backend.sh" <<EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR/backend"
source "\$SCRIPT_DIR/venv/bin/activate"
# Use absolute paths for templates and compiled directories
export TEMPLATES_DIR="\$(cd "\$SCRIPT_DIR/templates" && pwd)"
export COMPILED_DIR="\$(cd "\$SCRIPT_DIR/compiled" && pwd)"
export PYTHONUNBUFFERED=1
uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF

    # Frontend start script
    cat > "$INSTALL_DIR/start-frontend.sh" <<EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR/frontend"
export VITE_API_URL=http://localhost:8000
npm run dev -- --host 0.0.0.0
EOF

    # Config watcher script (already exists, just ensure it's executable)
    chmod +x "$INSTALL_DIR/watch-dnsmasq.sh" 2>/dev/null || true

    # Start all script
    cat > "$INSTALL_DIR/start.sh" <<EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Ktizo services..."

# Start backend
echo "Starting backend..."
cd "\$SCRIPT_DIR"
./start-backend.sh > "\$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=\$!
echo "Backend started (PID: \$BACKEND_PID)"

# Wait for backend to be ready
sleep 3

# Start frontend
echo "Starting frontend..."
./start-frontend.sh > "\$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=\$!
echo "Frontend started (PID: \$FRONTEND_PID)"

echo ""
echo "Services started:"
echo "  Backend:  http://localhost:8000 (PID: \$BACKEND_PID)"
echo "  Frontend: http://localhost:5173 (PID: \$FRONTEND_PID)"
echo ""
echo "Logs:"
echo "  Backend:  \$SCRIPT_DIR/logs/backend.log"
echo "  Frontend: \$SCRIPT_DIR/logs/frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo "PIDs saved to: \$SCRIPT_DIR/.pids"

mkdir -p "\$SCRIPT_DIR/logs"
echo "\$BACKEND_PID" > "\$SCRIPT_DIR/.pids"
echo "\$FRONTEND_PID" >> "\$SCRIPT_DIR/.pids"

# Wait for interrupt
trap "kill \$BACKEND_PID \$FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
EOF

    chmod +x "$INSTALL_DIR/start-backend.sh"
    chmod +x "$INSTALL_DIR/start-frontend.sh"
    chmod +x "$INSTALL_DIR/start.sh"
    
    echo "✅ Startup scripts created"
}

# Main installation
main() {
    echo "Starting installation..."
    echo ""
    
    install_dependencies
    create_directories
    setup_python
    setup_node
    download_talosctl
    setup_dnsmasq
    create_startup_scripts
    
    if [[ "$OS" == "linux" ]]; then
        create_systemd_service
    elif [[ "$OS" == "macos" ]]; then
        create_launchd_service
    fi
    
    echo ""
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start services (handles everything automatically):"
    echo "   $INSTALL_DIR/run.sh"
    echo ""
    echo "   Or manually:"
    echo "2. Initialize the database:"
    echo "   cd $INSTALL_DIR/backend"
    echo "   source ../venv/bin/activate"
    echo "   python -m app.db.migrate"
    echo ""
    echo "3. Start services:"
    echo "   $INSTALL_DIR/run.sh"
    echo ""
    echo "   The run.sh script will:"
    echo "   - Initialize database if needed"
    echo "   - Start backend and frontend"
    echo "   - Start config watcher"
    echo "   - Check dnsmasq status"
    echo ""
    echo "   Or use individual scripts:"
    echo "   $INSTALL_DIR/start.sh"
    echo ""
    if [[ "$OS" == "macos" ]]; then
        echo "   Or use launchd:"
        echo "   launchctl load $HOME/Library/LaunchAgents/com.ktizo.backend.plist"
    elif [[ "$OS" == "linux" ]]; then
        echo "   Or use systemd:"
        echo "   systemctl start ktizo-backend"
    fi
    echo ""
    echo "4. Access the web interface:"
    echo "   Frontend: http://localhost:5173"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "4. Configure network settings via the web UI"
    echo "   Then apply settings to generate dnsmasq config"
    echo ""
}

# Run installation
main

