# ktizo

Greek word for "to create," "to found," or "to form," - An extremely fast PXE based way of deploying Talos for Kubernetes.

## Project Structure

```
ktizo/
├── backend/          # FastAPI backend application
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Configuration and settings
│   │   ├── models/   # Pydantic models
│   │   └── services/ # Business logic (Jinja2 template rendering)
│   └── requirements.txt
├── frontend/         # Vue.js frontend application
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── services/ # API client
│   └── package.json
├── templates/        # Jinja2 templates for config generation
│   ├── talos/        # Talos Linux configurations
│   ├── pxe/          # PXE boot configurations
│   └── network/      # Network infrastructure configs
├── compiled/         # Auto-generated configs (from templates)
│   ├── dnsmasq/      # Compiled DNSMASQ configurations
│   ├── pxe/          # Compiled PXE boot configurations
│   └── talos/        # Compiled Talos node configurations
├── scripts/          # Automation scripts
│   └── watch-dnsmasq.sh  # Auto-reload DNSMASQ on config changes
└── docker-compose.yaml
```

## Getting Started

### Installation Options

#### Option 1: Native Installation (Recommended)

Run directly on your host system - no Docker required:

```bash
# Run the installation script
./install.sh

# Start services
./start.sh
```

**Advantages:**
- ✅ No Docker networking issues
- ✅ Direct access to host network for PXE
- ✅ Better performance
- ✅ Simpler debugging

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

#### Option 2: Docker Installation

For containerized deployment:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Note:** Docker on macOS has networking limitations for PXE. Native installation is recommended for macOS.

### Services

- **Frontend**: http://localhost:5173 - Vue.js web interface
- **Backend API**: http://localhost:8000 - FastAPI REST API
- **API Docs**: http://localhost:8000/docs - Interactive API documentation
- **DNSMASQ**: Ports 53 (DNS), 67 (DHCP), 69 (TFTP)
- **Config Watcher**: Automatically reloads DNSMASQ when configurations change

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Features

- **Configuration Generator**: Web-based UI for generating Talos Linux configurations
- **Volume Configuration**: Control system partition sizes (EPHEMERAL, IMAGE-CACHE) to reserve space for Rook/Ceph
- **Template System**: Jinja2-based template rendering for customizable deployments
- **Device Approval Workflow**: MAC-based device identification with approval system
- **PXE Boot Server**: DNSMASQ-based network boot infrastructure
- **API-Driven**: RESTful API for programmatic access
- **Auto-Reload**: DNSMASQ automatically reloads when configurations change
- **Hot Reload**: Backend and frontend support hot module replacement for development

## Architecture

The system uses FastAPI to render Jinja2 templates based on user input from the Vue.js frontend. Generated configurations are written to the `compiled/` directory, where DNSMASQ and other services read them.

### Configuration Flow

1. User configures deployment via Vue.js frontend
2. Frontend sends configuration to FastAPI backend (`/api/v1/config/compile`)
3. Backend renders Jinja2 template with user variables
4. Compiled configuration written to `compiled/` directory
5. Config watcher detects file change
6. DNSMASQ automatically reloads with new configuration
7. Talos nodes boot via PXE using the new configuration

### Auto-Reload Mechanism

The `config-watcher` service monitors the `compiled/` directory using `inotifywait` and automatically reloads DNSMASQ when changes are detected in:
- `compiled/dnsmasq/` - DNSMASQ configuration files
- `compiled/pxe/` - PXE boot configurations
