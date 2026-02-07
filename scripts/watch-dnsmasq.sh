#!/bin/bash
# Watch for changes in compiled configs and reload DNSMASQ

WATCH_DIR="/compiled"
CONTAINER_NAME="ktizo-dnsmasq"

echo "Starting file watcher for DNSMASQ configuration..."
echo "Watching: $WATCH_DIR"

# Install inotify-tools if not present
if ! command -v inotifywait &> /dev/null; then
    echo "Installing inotify-tools..."
    apt-get update && apt-get install -y inotify-tools
fi

# Function to reload DNSMASQ
reload_dnsmasq() {
    echo "[$(date)] Detected configuration change, reloading DNSMASQ..."
    docker exec $CONTAINER_NAME killall -HUP dnsmasq 2>/dev/null || \
    docker restart $CONTAINER_NAME
    echo "[$(date)] DNSMASQ reloaded successfully"
}

# Watch for file changes
inotifywait -m -r -e modify,create,delete,move \
    --format '%w%f %e' \
    "$WATCH_DIR/dnsmasq/" "$WATCH_DIR/pxe/" 2>/dev/null | \
while read file event; do
    # Debounce: wait a bit in case multiple files change at once
    sleep 1
    reload_dnsmasq
done
