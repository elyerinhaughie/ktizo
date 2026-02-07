#!/bin/bash
# Intelligent Ktizo run script
# Handles initialization, service startup, and status checks
# Usage: ./run.sh

# Don't exit on error - we want to continue even if some services fail
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
BACKEND_DIR="$SCRIPT_DIR/backend"
DATA_DIR="$SCRIPT_DIR/data"
DB_FILE="$DATA_DIR/ktizo.db"
LOGS_DIR="$SCRIPT_DIR/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux-musl"* ]]; then
    OS="linux"
    if command -v rc-service &> /dev/null; then
        USE_OPENRC=true
    elif command -v systemctl &> /dev/null; then
        USE_SYSTEMD=true
    fi
else
    OS="unknown"
fi

echo "=========================================="
echo "Ktizo Intelligent Run Script"
echo "=========================================="
echo ""

# Function to check if service is actually responding (not just port in use)
check_service() {
    local url=$1
    local name=$2
    # Actually try to connect to the service
    if curl -s --max-time 2 "$url" &>/dev/null; then
        return 0
    fi
    return 1
}

# Function to check if port is in use (for detection, not verification)
check_port() {
    local port=$1
    if lsof -i :$port &>/dev/null 2>&1 || (netstat -ulnp 2>/dev/null | grep -q ":$port"); then
        return 0
    fi
    return 1
}

# Function to kill process on a port
kill_port() {
    local port=$1
    local name=$2
    
    # Try to find and kill process using the port
    local pid=""
    
    # Try lsof first (works on macOS and Linux)
    if command -v lsof &>/dev/null; then
        pid=$(lsof -ti :$port 2>/dev/null | head -1)
    fi
    
    # Fallback to netstat/fuser on Linux
    if [ -z "$pid" ] && command -v fuser &>/dev/null; then
        pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}' | head -1)
    fi
    
    # Fallback to ss/netstat
    if [ -z "$pid" ] && command -v ss &>/dev/null; then
        pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
    fi
    
    if [ -n "$pid" ] && [ "$pid" != "$$" ]; then
        echo "   Killing existing process $pid on port $port..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        return 0
    fi
    return 1
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $name to be ready..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" &>/dev/null; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Step 1: Check Python virtual environment
echo "1. Checking Python environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo "Please run ./install.sh first"
    exit 1
fi

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${RED}Error: Virtual environment is incomplete${NC}"
    echo "Please run ./install.sh again"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python environment found"

# Step 2: Check if database is initialized (check for tables, not just file)
echo ""
echo "2. Checking database..."
DB_INITIALIZED=false

if [ -f "$DB_FILE" ]; then
    # Check if database actually has tables
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Use Python to check if tables exist
    if python -c "
from app.db.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
required_tables = ['devices', 'cluster_settings', 'network_settings']
if all(t in tables for t in required_tables):
    exit(0)
else:
    exit(1)
" 2>/dev/null; then
        DB_INITIALIZED=true
        echo -e "${GREEN}✓${NC} Database is initialized"
    else
        echo -e "${YELLOW}⚠${NC}  Database file exists but tables are missing"
    fi
else
    echo "Database file not found"
fi

if [ "$DB_INITIALIZED" = false ]; then
    echo "Initializing database..."
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Try to initialize database
    if python -m app.db.migrate 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Database initialized"
    elif python -c 'from app.db.database import init_db; init_db()' 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Database initialized"
    else
        echo -e "${RED}✗${NC} Could not auto-initialize database"
        echo "Please run manually: cd backend && source ../venv/bin/activate && python -m app.db.migrate"
        exit 1
    fi
fi

# Step 3: Check if services are already running (actually test connections)
echo ""
echo "3. Checking existing services..."
BACKEND_RUNNING=false
FRONTEND_RUNNING=false

# Check if backend is actually responding (not just port in use)
if check_service "http://localhost:8000/docs" "backend"; then
    BACKEND_RUNNING=true
    echo -e "${GREEN}✓${NC} Backend is already running and responding"
elif check_port 8000; then
    echo -e "${YELLOW}⚠${NC}  Port 8000 is in use but backend is not responding"
    echo "   This might be a different service. Will attempt to start backend anyway."
else
    echo -e "${GREEN}✓${NC} Backend is not running"
fi

# Check if frontend is actually responding
if check_service "http://localhost:5173" "frontend"; then
    FRONTEND_RUNNING=true
    echo -e "${GREEN}✓${NC} Frontend is already running and responding"
elif check_port 5173; then
    echo -e "${YELLOW}⚠${NC}  Port 5173 is in use but frontend is not responding"
    echo "   This might be a different service. Will attempt to start frontend anyway."
else
    echo -e "${GREEN}✓${NC} Frontend is not running"
fi

# Step 4: Start backend if not running
if [ "$BACKEND_RUNNING" = false ]; then
    echo ""
    echo "4. Starting backend..."
    
    # Kill any existing process on port 8000
    if check_port 8000; then
        kill_port 8000 "backend"
    fi
    
    cd "$SCRIPT_DIR"
    mkdir -p "$LOGS_DIR"
    
    # Set absolute paths for templates and compiled directories
    export TEMPLATES_DIR="$(cd "$SCRIPT_DIR/templates" && pwd)"
    export COMPILED_DIR="$(cd "$SCRIPT_DIR/compiled" && pwd)"
    export PYTHONUNBUFFERED=1
    
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOGS_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$SCRIPT_DIR/.backend.pid"
    
    if wait_for_service "http://localhost:8000/docs" "backend"; then
        echo -e "${GREEN}✓${NC} Backend started (PID: $BACKEND_PID)"
    else
        echo -e "${RED}✗${NC} Backend failed to start. Check logs: $LOGS_DIR/backend.log"
        exit 1
    fi
else
    echo ""
    echo "4. Backend already running, skipping..."
fi

# Step 5: Start frontend if not running
if [ "$FRONTEND_RUNNING" = false ]; then
    echo ""
    echo "5. Starting frontend..."
    
    # Kill any existing process on port 5173
    if check_port 5173; then
        kill_port 5173 "frontend"
    fi
    
    cd "$SCRIPT_DIR/frontend"
    export VITE_API_URL=http://localhost:8000
    
    nohup npm run dev -- --host 0.0.0.0 > "$LOGS_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$SCRIPT_DIR/.frontend.pid"
    
    sleep 3
    if check_service "http://localhost:5173" "frontend"; then
        echo -e "${GREEN}✓${NC} Frontend started (PID: $FRONTEND_PID)"
    else
        echo -e "${YELLOW}⚠${NC}  Frontend may still be starting. Check logs: $LOGS_DIR/frontend.log"
        echo "   It may take a few more seconds for Vite to compile..."
    fi
else
    echo ""
    echo "5. Frontend already running, skipping..."
fi

# Step 6: Check dnsmasq
echo ""
echo "6. Checking dnsmasq..."
DNSMASQ_RUNNING=false

# Check multiple ways to detect dnsmasq
if [ "$OS" = "macos" ]; then
    if brew services list 2>/dev/null | grep -q "dnsmasq.*started"; then
        DNSMASQ_RUNNING=true
    fi
    # Also check if process is running
    if pgrep -x dnsmasq &>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
elif [ "$USE_SYSTEMD" = true ]; then
    if systemctl is-active --quiet dnsmasq 2>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
    # Also check if process is running
    if pgrep -x dnsmasq &>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
elif [ "$USE_OPENRC" = true ]; then
    if rc-service dnsmasq status &>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
    # Also check if process is running
    if pgrep -x dnsmasq &>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
else
    # Fallback: check if process is running
    if pgrep -x dnsmasq &>/dev/null; then
        DNSMASQ_RUNNING=true
    fi
fi

# Also check if dnsmasq is listening on required ports
if [ "$DNSMASQ_RUNNING" = true ]; then
    # Verify it's actually listening on ports 67 or 69
    if ! (lsof -i :67 -i :69 &>/dev/null 2>&1 || netstat -ulnp 2>/dev/null | grep -qE ':(67|69)'); then
        echo -e "${YELLOW}⚠${NC}  dnsmasq process found but not listening on ports 67/69"
        DNSMASQ_RUNNING=false
    fi
fi

if [ "$DNSMASQ_RUNNING" = true ]; then
    echo -e "${GREEN}✓${NC} dnsmasq is running"
else
    echo -e "${YELLOW}⚠${NC}  dnsmasq is not running"
    
    # Check if we're root (required to start dnsmasq)
    if [ "$EUID" -eq 0 ]; then
        echo "   Starting dnsmasq..."
        
        if [ "$OS" = "macos" ]; then
            if brew services start dnsmasq 2>&1; then
                sleep 2
                if brew services list 2>/dev/null | grep -q "dnsmasq.*started"; then
                    echo -e "${GREEN}✓${NC} dnsmasq started"
                else
                    echo -e "${YELLOW}⚠${NC}  dnsmasq start command succeeded but service may not be running"
                    echo "   Check: brew services list dnsmasq"
                fi
            else
                echo -e "${RED}✗${NC} Failed to start dnsmasq. Check: brew services list dnsmasq"
            fi
        elif [ "$USE_SYSTEMD" = true ]; then
            echo "   Attempting to start dnsmasq with systemctl..."
            START_OUTPUT=$(systemctl start dnsmasq 2>&1)
            START_EXIT=$?
            sleep 2
            if systemctl is-active --quiet dnsmasq 2>/dev/null; then
                echo -e "${GREEN}✓${NC} dnsmasq started"
            else
                echo -e "${RED}✗${NC} dnsmasq failed to start (exit code: $START_EXIT)"
                if [ -n "$START_OUTPUT" ]; then
                    echo "   Error output: $START_OUTPUT"
                fi
                echo "   Full status:"
                systemctl status dnsmasq --no-pager -l 2>&1 | head -15
                echo ""
                echo "   Common issues:"
                echo "   - Config file error: dnsmasq --test -C /etc/dnsmasq.conf"
                echo "   - Port already in use: lsof -i :67 -i :69"
                echo "   - Missing config: Check /etc/dnsmasq.conf exists"
            fi
        elif [ "$USE_OPENRC" = true ]; then
            echo "   Attempting to start dnsmasq with rc-service..."
            START_OUTPUT=$(rc-service dnsmasq start 2>&1)
            START_EXIT=$?
            sleep 2
            if rc-service dnsmasq status &>/dev/null; then
                echo -e "${GREEN}✓${NC} dnsmasq started"
            else
                echo -e "${RED}✗${NC} dnsmasq failed to start (exit code: $START_EXIT)"
                if [ -n "$START_OUTPUT" ]; then
                    echo "   Error output: $START_OUTPUT"
                fi
                echo "   Check status: rc-service dnsmasq status"
                echo "   Check config: dnsmasq --test -C /etc/dnsmasq.conf"
            fi
        else
            # Fallback: try to start dnsmasq directly
            DNSMASQ_CONF="/etc/dnsmasq.conf"
            if [ ! -f "$DNSMASQ_CONF" ]; then
                DNSMASQ_CONF="/usr/local/etc/dnsmasq.conf"
            fi
            
            if [ -f "$DNSMASQ_CONF" ]; then
                if dnsmasq --test -C "$DNSMASQ_CONF" 2>&1; then
                    # Start in background
                    dnsmasq -C "$DNSMASQ_CONF" 2>&1 &
                    DNSMASQ_PID=$!
                    sleep 1
                    if kill -0 "$DNSMASQ_PID" 2>/dev/null; then
                        echo "$DNSMASQ_PID" > "$SCRIPT_DIR/.dnsmasq.pid"
                        echo -e "${GREEN}✓${NC} dnsmasq started (PID: $DNSMASQ_PID)"
                    else
                        echo -e "${RED}✗${NC} dnsmasq process died immediately. Check config and logs."
                    fi
                else
                    echo -e "${RED}✗${NC} dnsmasq config test failed. Check: dnsmasq --test -C $DNSMASQ_CONF"
                fi
            else
                echo -e "${YELLOW}⚠${NC}  dnsmasq config not found at $DNSMASQ_CONF"
                echo "   Please configure dnsmasq first via the web UI, then apply settings"
            fi
        fi
    else
        echo "   Cannot start dnsmasq (requires root privileges)"
        echo "   To start dnsmasq manually:"
        if [ "$OS" = "macos" ]; then
            echo "     brew services start dnsmasq"
        elif [ "$USE_SYSTEMD" = true ]; then
            echo "     systemctl start dnsmasq"
        elif [ "$USE_OPENRC" = true ]; then
            echo "     rc-service dnsmasq start"
        else
            echo "     dnsmasq --no-daemon -C /etc/dnsmasq.conf"
        fi
    fi
fi

# Step 7: Start config watcher in background (optional)
echo ""
echo "7. Starting config watcher..."
if [ -f "$SCRIPT_DIR/watch-dnsmasq.sh" ]; then
    # Check if already running
    if pgrep -f "watch-dnsmasq.sh" &>/dev/null; then
        echo -e "${YELLOW}⚠${NC}  Config watcher already running"
    else
        nohup "$SCRIPT_DIR/watch-dnsmasq.sh" > "$LOGS_DIR/watch-dnsmasq.log" 2>&1 &
        WATCHER_PID=$!
        echo "$WATCHER_PID" > "$SCRIPT_DIR/.watcher.pid"
        echo -e "${GREEN}✓${NC} Config watcher started (PID: $WATCHER_PID)"
    fi
else
    echo -e "${YELLOW}⚠${NC}  watch-dnsmasq.sh not found, skipping"
fi

# Summary
echo ""
echo "=========================================="
echo "Ktizo is running!"
echo "=========================================="
echo ""
echo "Services:"
echo "  ${GREEN}Backend:${NC}  http://localhost:8000"
echo "  ${GREEN}Frontend:${NC} http://localhost:5173"
echo "  ${GREEN}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  $LOGS_DIR/backend.log"
echo "  Frontend: $LOGS_DIR/frontend.log"
echo "  Watcher:  $LOGS_DIR/watch-dnsmasq.log"
echo ""
echo "PIDs saved to:"
echo "  $SCRIPT_DIR/.backend.pid"
echo "  $SCRIPT_DIR/.frontend.pid"
echo "  $SCRIPT_DIR/.watcher.pid"
echo ""
echo "To stop all services:"
echo "  ./stop.sh"
echo ""
echo "To view logs:"
echo "  tail -f $LOGS_DIR/backend.log"
echo "  tail -f $LOGS_DIR/frontend.log"
echo ""

