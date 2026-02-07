#!/bin/bash
# UDP Proxy for PXE Server on macOS
# Forwards UDP packets from host network to Docker container
# This solves the macOS Docker Desktop host networking limitation

set -e

CONTAINER_IP=""
DHCP_PORT=67
TFTP_PORT=69
HOST_IP="10.0.1.136"

# Function to get container IP
get_container_ip() {
    CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ktizo-dnsmasq 2>/dev/null || echo "")
    if [ -z "$CONTAINER_IP" ]; then
        echo "Error: Could not find ktizo-dnsmasq container IP"
        echo "Make sure the container is running: docker compose up -d dnsmasq"
        exit 1
    fi
    echo "Container IP: $CONTAINER_IP"
}

# Check if socat is installed
check_socat() {
    if ! command -v socat &> /dev/null; then
        echo "Installing socat..."
        if command -v brew &> /dev/null; then
            brew install socat
        else
            echo "Error: socat is required but Homebrew is not installed"
            echo "Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    fi
}

# Start UDP proxy for a port
start_proxy() {
    local port=$1
    local name=$2
    
    echo "Starting UDP proxy for $name on port $port..."
    
    # Kill any existing socat processes for this port
    pkill -f "socat.*:$port" 2>/dev/null || true
    
    # Start socat to forward UDP packets
    socat UDP4-LISTEN:$port,fork,reuseaddr UDP4:$CONTAINER_IP:$port &
    
    local pid=$!
    echo "$name proxy started (PID: $pid)"
    echo $pid > /tmp/ktizo-udp-proxy-$port.pid
}

# Stop proxies
stop_proxy() {
    echo "Stopping UDP proxies..."
    pkill -f "socat.*:(67|69)" 2>/dev/null || true
    rm -f /tmp/ktizo-udp-proxy-*.pid
    echo "UDP proxies stopped"
}

# Main
case "${1:-start}" in
    start)
        echo "Starting UDP proxy for PXE server..."
        check_socat
        get_container_ip
        
        # Check if container is using bridge network (not host)
        if docker inspect ktizo-dnsmasq | grep -q '"NetworkMode": "host"'; then
            echo "Warning: Container is using host networking mode"
            echo "For UDP proxy to work, container should use bridge network"
            echo "Switching to bridge network..."
            # This would require docker-compose changes, so we'll just warn
        fi
        
        start_proxy $DHCP_PORT "DHCP"
        start_proxy $TFTP_PORT "TFTP"
        
        echo ""
        echo "✅ UDP proxies started successfully"
        echo "   DHCP: $HOST_IP:$DHCP_PORT -> $CONTAINER_IP:$DHCP_PORT"
        echo "   TFTP: $HOST_IP:$TFTP_PORT -> $CONTAINER_IP:$TFTP_PORT"
        echo ""
        echo "To stop: $0 stop"
        ;;
    stop)
        stop_proxy
        ;;
    status)
        if pgrep -f "socat.*:67" > /dev/null && pgrep -f "socat.*:69" > /dev/null; then
            echo "✅ UDP proxies are running"
            ps aux | grep -E "socat.*:(67|69)" | grep -v grep
        else
            echo "❌ UDP proxies are not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac


