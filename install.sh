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
        brew install node@20 dnsmasq git make gcc || true
        # Install Xcode command line tools if not present (needed for gcc)
        xcode-select --install 2>/dev/null || true
        
    elif [[ "$OS" == "linux" ]]; then
        if [[ "$PKG_MANAGER" == "apk" ]]; then
            apk update
            # Try Python 3.14 first, fallback to available version
            # Install build tools for iPXE chainboot bootloaders (makebin)
            BUILD_TOOLS="git gcc make binutils perl xz-dev mtools syslinux bash musl-dev"
            if apk search python3.14 &>/dev/null && apk add --no-cache python3.14 py3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.14"
            elif apk search python3.13 &>/dev/null && apk add --no-cache python3.13 py3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.13 (3.14 not available)"
            elif apk search python3.12 &>/dev/null && apk add --no-cache python3.12 py3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.12 (3.14 not available)"
            else
                apk add --no-cache python3 py3-pip nodejs npm dnsmasq curl $BUILD_TOOLS
                echo "Using system Python 3 (3.14 not available)"
            fi
        elif [[ "$PKG_MANAGER" == "apt" ]]; then
            apt-get update
            # Install build tools for iPXE chainboot bootloaders (makebin)
            BUILD_TOOLS="git make gcc binutils perl xz-utils mtools syslinux bash build-essential"
            # Try Python 3.14 first, fallback to 3.13, 3.12, 3.11, then python3
            if apt-cache show python3.14 &>/dev/null && apt-get install -y python3.14 python3.14-venv python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.14"
            elif apt-cache show python3.13 &>/dev/null && apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.13 (3.14 not available)"
            elif apt-cache show python3.12 &>/dev/null && apt-get install -y python3.12 python3.12-venv python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.12 (3.14 not available)"
            elif apt-cache show python3.11 &>/dev/null && apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS 2>/dev/null; then
                echo "Using Python 3.11 (3.14 not available)"
            else
                apt-get install -y python3 python3-venv python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS
                echo "Using system Python 3 (3.14 not available)"
            fi
        elif [[ "$PKG_MANAGER" == "yum" ]] || [[ "$PKG_MANAGER" == "dnf" ]]; then
            # Install build tools for iPXE chainboot bootloaders (makebin)
            BUILD_TOOLS="git make gcc binutils perl xz-devel mtools syslinux bash"
            $PKG_MANAGER install -y python3 python3-pip nodejs npm dnsmasq curl $BUILD_TOOLS
        fi
    fi
    
    # Verify makebin or build tools are available for chainboot bootloaders
    echo ""
    echo "Checking for iPXE build tools (for custom chainboot bootloaders)..."
    if command -v makebin &> /dev/null; then
        echo "✅ makebin found - custom bootloaders can be built automatically"
    elif command -v make &> /dev/null && command -v gcc &> /dev/null && command -v git &> /dev/null; then
        echo "✅ Build tools installed - makebin will be built from iPXE source automatically"
        echo "   (This happens on first backend startup)"
    else
        echo "⚠️  Build tools not fully available - custom bootloaders may not be built"
        echo "   Standard bootloaders will be used (may show menu prompts)"
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
    
    # Install dependencies (includes terminal integration: @xterm/xterm, @xterm/addon-fit)
    npm install
    npm install @rollup/rollup-linux-arm64-musl --save-optional --no-save 2>/dev/null || true
    
    echo "✅ Node.js environment ready (includes terminal integration)"
}

# Function to download talosctl
download_talosctl() {
    local TALOS_VERSION="${1:-}"
    
    echo ""
    echo "Installing talosctl to project directory..."
    
    # Install to project backend directory
    TALOSCTL_INSTALL_DIR="$INSTALL_DIR/backend"
    
    # Ensure install directory exists
    mkdir -p "$TALOSCTL_INSTALL_DIR"
    cd /tmp
    
    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        TALOS_ARCH="arm64"
    elif [[ "$ARCH" == "x86_64" ]]; then
        TALOS_ARCH="amd64"
    else
        TALOS_ARCH="amd64"  # Default fallback
    fi
    
    # Get version - use provided version, or check database, or use latest
    if [ -z "$TALOS_VERSION" ]; then
        # Try to get version from database if it exists
        if [ -f "$INSTALL_DIR/backend/app.db" ]; then
            # Try to extract talos_version from database (SQLite)
            TALOS_VERSION=$(sqlite3 "$INSTALL_DIR/backend/app.db" "SELECT talos_version FROM cluster_settings LIMIT 1" 2>/dev/null || echo "")
            if [ -n "$TALOS_VERSION" ]; then
                echo "Using Talos version from cluster settings: $TALOS_VERSION"
                # Ensure version has 'v' prefix
                if [[ ! "$TALOS_VERSION" =~ ^v ]]; then
                    TALOS_VERSION="v${TALOS_VERSION}"
                fi
            fi
        fi
        
        # If still no version, get latest
        if [ -z "$TALOS_VERSION" ]; then
            TALOS_VERSION=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p' | head -1)
            if [ -z "$TALOS_VERSION" ]; then
                TALOS_VERSION="v1.12.2"
                echo "Warning: Could not determine latest Talos version, using $TALOS_VERSION"
            else
                echo "Using latest Talos version: $TALOS_VERSION"
            fi
        fi
    else
        # Ensure provided version has 'v' prefix
        if [[ ! "$TALOS_VERSION" =~ ^v ]]; then
            TALOS_VERSION="v${TALOS_VERSION}"
        fi
        echo "Using specified Talos version: $TALOS_VERSION"
    fi
    
    # Download talosctl
    if [[ "$OS" == "macos" ]]; then
        TALOS_OS="darwin"
    else
        TALOS_OS="linux"
    fi
    
    TALOS_URL="https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-${TALOS_OS}-${TALOS_ARCH}"
    
    echo "Downloading talosctl from: $TALOS_URL"
    
    # Download to temp location first
    TEMP_TALOSCTL="/tmp/talosctl-${TALOS_VERSION}"
    
    # Download with error handling
    if curl -L "$TALOS_URL" -o "$TEMP_TALOSCTL"; then
        chmod +x "$TEMP_TALOSCTL"
        
        # Verify the file was downloaded and is executable
        if [ -f "$TEMP_TALOSCTL" ] && [ -x "$TEMP_TALOSCTL" ]; then
            # Test that it works
            if "$TEMP_TALOSCTL" version --client >/dev/null 2>&1; then
                # Install to project directory
                if cp "$TEMP_TALOSCTL" "$TALOSCTL_INSTALL_DIR/talosctl"; then
                    chmod +x "$TALOSCTL_INSTALL_DIR/talosctl"
                    echo "✅ talosctl installed successfully ($TALOS_VERSION)"
                    echo "   Location: $TALOSCTL_INSTALL_DIR/talosctl"
                    echo "✅ talosctl verified and working"
                    # Clean up temp file
                    rm -f "$TEMP_TALOSCTL"
                else
                    echo "❌ Error: Failed to install talosctl to $TALOSCTL_INSTALL_DIR"
                    exit 1
                fi
            else
                echo "⚠️  Warning: talosctl downloaded but version check failed"
                exit 1
            fi
        else
            echo "❌ Error: talosctl download failed or file is not executable"
            exit 1
        fi
    else
        echo "❌ Error: Failed to download talosctl from $TALOS_URL"
        echo "   Please check your internet connection and try again"
        exit 1
    fi
}

# Function to download kubectl
download_kubectl() {
    echo ""
    echo "Downloading kubectl..."
    
    cd "$INSTALL_DIR/backend"
    
    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        KUBECTL_ARCH="arm64"
    elif [[ "$ARCH" == "x86_64" ]]; then
        KUBECTL_ARCH="amd64"
    else
        KUBECTL_ARCH="amd64"  # Default fallback
    fi
    
    # Get latest stable version (follow redirects)
    KUBECTL_VERSION=$(curl -sL https://dl.k8s.io/release/stable.txt | tr -d 'v' | tr -d '\n' | tr -d '\r')
    if [ -z "$KUBECTL_VERSION" ] || [[ "$KUBECTL_VERSION" =~ ^[^0-9] ]]; then
        KUBECTL_VERSION="1.28.0"
        echo "Warning: Could not determine latest kubectl version, using $KUBECTL_VERSION"
    else
        echo "Using kubectl version: $KUBECTL_VERSION"
    fi
    
    # Download kubectl
    if [[ "$OS" == "macos" ]]; then
        KUBECTL_OS="darwin"
    else
        KUBECTL_OS="linux"
    fi
    
    # Create kubectl-versions directory
    mkdir -p kubectl-versions
    
    KUBECTL_URL="https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/${KUBECTL_OS}/${KUBECTL_ARCH}/kubectl"
    KUBECTL_VERSIONED="kubectl-versions/kubectl-${KUBECTL_VERSION}"
    
    echo "Downloading kubectl ${KUBECTL_VERSION} to project directory..."
    echo "URL: $KUBECTL_URL"
    
    # Download with error handling
    if curl -L "$KUBECTL_URL" -o "$KUBECTL_VERSIONED"; then
        chmod +x "$KUBECTL_VERSIONED"
        
        # Verify it works (check if it's actually a binary, not HTML)
        if file "$KUBECTL_VERSIONED" | grep -q "ELF\|Mach-O\|executable"; then
            # Test that it works
            if "$KUBECTL_VERSIONED" version --client >/dev/null 2>&1; then
                # Create symlink to default version
                ln -sf "$KUBECTL_VERSIONED" kubectl
                echo "✅ kubectl downloaded ($KUBECTL_VERSION)"
                echo "   Location: $INSTALL_DIR/backend/kubectl"
                echo "✅ kubectl verified and working"
            else
                echo "⚠️  Warning: kubectl downloaded but version check failed"
            fi
        else
            echo "❌ Error: Downloaded file is not a valid binary (may be HTML/error page)"
            echo "   Please check the download URL and try again"
            rm -f "$KUBECTL_VERSIONED"
            exit 1
        fi
    else
        echo "❌ Error: Failed to download kubectl from $KUBECTL_URL"
        echo "   Please check your internet connection and try again"
        exit 1
    fi
}

# Function to download helm
download_helm() {
    echo ""
    echo "Downloading helm..."

    cd "$INSTALL_DIR/backend"

    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        HELM_ARCH="arm64"
    elif [[ "$ARCH" == "x86_64" ]]; then
        HELM_ARCH="amd64"
    else
        HELM_ARCH="amd64"  # Default fallback
    fi

    # Get latest helm version
    HELM_VERSION=$(curl -sL https://api.github.com/repos/helm/helm/releases/latest | sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p' | head -1)
    if [ -z "$HELM_VERSION" ]; then
        HELM_VERSION="v3.17.1"
        echo "Warning: Could not determine latest helm version, using $HELM_VERSION"
    else
        echo "Using helm version: $HELM_VERSION"
    fi

    # Download helm
    if [[ "$OS" == "macos" ]]; then
        HELM_OS="darwin"
    else
        HELM_OS="linux"
    fi

    HELM_URL="https://get.helm.sh/helm-${HELM_VERSION}-${HELM_OS}-${HELM_ARCH}.tar.gz"
    HELM_TMP="/tmp/helm-${HELM_VERSION}.tar.gz"

    echo "Downloading helm from: $HELM_URL"

    if curl -L "$HELM_URL" -o "$HELM_TMP"; then
        # Extract helm binary from tarball
        HELM_EXTRACT_DIR="/tmp/helm-extract-$$"
        mkdir -p "$HELM_EXTRACT_DIR"
        tar -xzf "$HELM_TMP" -C "$HELM_EXTRACT_DIR"

        HELM_BIN="$HELM_EXTRACT_DIR/${HELM_OS}-${HELM_ARCH}/helm"

        if [ -f "$HELM_BIN" ] && [ -x "$HELM_BIN" ]; then
            if "$HELM_BIN" version --short >/dev/null 2>&1; then
                cp "$HELM_BIN" "$INSTALL_DIR/backend/helm"
                chmod +x "$INSTALL_DIR/backend/helm"
                echo "✅ helm installed successfully ($HELM_VERSION)"
                echo "   Location: $INSTALL_DIR/backend/helm"
            else
                echo "⚠️  Warning: helm downloaded but version check failed"
            fi
        else
            echo "❌ Error: Could not find helm binary in archive"
        fi

        # Clean up
        rm -rf "$HELM_EXTRACT_DIR" "$HELM_TMP"
    else
        echo "❌ Error: Failed to download helm from $HELM_URL"
        echo "   Please check your internet connection and try again"
        exit 1
    fi
}

# Function to create directories
create_directories() {
    echo ""
    echo "Creating required directories..."
    
    # Use ~/.ktizo for persistent data
    KTIZO_HOME="${KTIZO_HOME:-$HOME/.ktizo}"
    KTIZO_DATA="$KTIZO_HOME/data"
    KTIZO_COMPILED="$KTIZO_HOME/compiled"
    KTIZO_LOGS="$KTIZO_HOME/logs"
    
    mkdir -p "$KTIZO_DATA"
    mkdir -p "$KTIZO_COMPILED/dnsmasq"
    mkdir -p "$KTIZO_COMPILED/pxe/talos"
    mkdir -p "$KTIZO_COMPILED/talos/configs"
    mkdir -p "$KTIZO_LOGS"
    
    echo "✅ Directories created in $KTIZO_HOME"
    echo "   Data: $KTIZO_DATA"
    echo "   Compiled: $KTIZO_COMPILED"
    echo "   Logs: $KTIZO_LOGS"
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

# Use ~/.ktizo for persistent data
KTIZO_HOME="\${KTIZO_HOME:-\$HOME/.ktizo}"
export TEMPLATES_DIR="\$(cd "\$SCRIPT_DIR/templates" && pwd)"
export COMPILED_DIR="\$(cd "\$KTIZO_HOME/compiled" && pwd)"
export DATA_DIR="\$(cd "\$KTIZO_HOME/data" && pwd)"
export LOGS_DIR="\$(cd "\$KTIZO_HOME/logs" && pwd)"
export PYTHONUNBUFFERED=1
uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF

    # Frontend start script
    cat > "$INSTALL_DIR/start-frontend.sh" <<EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR/frontend"
# Don't set VITE_API_URL - let frontend detect hostname dynamically
# This allows the frontend to work when accessed from remote IPs
# export VITE_API_URL=http://localhost:8000
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

# Function to update PATH
update_path() {
    echo ""
    echo "Updating PATH to include ktizo backend directory..."
    
    # Get absolute path to backend directory
    BACKEND_BIN_DIR="$(cd "$INSTALL_DIR/backend" && pwd)"
    
    # Add backend directory to PATH for current session
    export PATH="$BACKEND_BIN_DIR:$PATH"
    
    # Update shell profiles
    SHELL_PROFILES=(
        "$HOME/.bashrc"
        "$HOME/.bash_profile"
        "$HOME/.zshrc"
        "$HOME/.profile"
    )
    
    PATH_LINE="export PATH=\"$BACKEND_BIN_DIR:\$PATH\""
    
    for profile in "${SHELL_PROFILES[@]}"; do
        if [ -f "$profile" ]; then
            # Remove old ktizo PATH entries if they exist
            sed -i.bak '/# Added by Ktizo installer/,+1d' "$profile" 2>/dev/null || true
            # Add new PATH entry
            echo "" >> "$profile"
            echo "# Added by Ktizo installer" >> "$profile"
            echo "$PATH_LINE" >> "$profile"
            echo "✅ Updated $profile"
        fi
    done
    
    # Also update /etc/profile.d for system-wide (if root)
    if [ "$EUID" -eq 0 ] && [ -d "/etc/profile.d" ]; then
        KTIZO_PATH_FILE="/etc/profile.d/ktizo-path.sh"
        echo "$PATH_LINE" > "$KTIZO_PATH_FILE"
        chmod +x "$KTIZO_PATH_FILE"
        echo "✅ Created system-wide PATH update: $KTIZO_PATH_FILE"
    fi
    
    echo "✅ PATH updated (includes $BACKEND_BIN_DIR)"
}

# Main installation
main() {
    echo "Starting installation..."
    echo ""
    
    install_dependencies
    create_directories
    update_path
    setup_python
    setup_node
    download_talosctl
    download_kubectl
    download_helm
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
    echo "5. Configure network settings via the web UI"
    echo "   Then apply settings to generate dnsmasq config"
    echo ""
    echo "6. Features available:"
    echo "   - Device Management: Add and approve PXE-booting devices"
    echo "   - Network Configuration: Configure DHCP and PXE boot settings"
    echo "   - Cluster Management: Generate Talos machine configs"
    echo "   - Terminal: Web-based terminal access (via /terminal route)"
    echo ""
}

# Run installation
main

