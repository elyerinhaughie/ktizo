# Scripts Directory

This directory contains automation scripts for the Ktizo infrastructure.

## watch-dnsmasq.sh

Monitors the `compiled/` directory for configuration changes and automatically reloads DNSMASQ when changes are detected.

**Watched directories:**
- `compiled/dnsmasq/` - DNSMASQ configuration files
- `compiled/pxe/` - PXE boot configurations

**How it works:**
1. Uses `inotifywait` to monitor file system events (modify, create, delete, move)
2. When a change is detected, sends HUP signal to DNSMASQ to reload configuration
3. Falls back to container restart if signal fails

**Usage:**
This script runs automatically in the `config-watcher` service defined in docker-compose.yaml.

## watch-and-reload.Dockerfile

Dockerfile for the config-watcher service that runs the watch-dnsmasq.sh script.

**Features:**
- Alpine-based lightweight image
- Includes inotify-tools for file watching
- Has Docker CLI for controlling DNSMASQ container
- Mounts Docker socket for container management
