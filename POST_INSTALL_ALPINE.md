# Post-Installation Steps for Alpine Linux

After running `./install.sh` on Alpine Linux, follow these steps:

## 1. Initialize the Database

```bash
cd backend
source ../venv/bin/activate
python -m app.db.migrate
```

## 2. Start the Services

Since Alpine doesn't use systemd, use the startup scripts:

```bash
# Start backend and frontend
./start.sh
```

Or start them separately in different terminals:

**Terminal 1 - Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start-frontend.sh
```

**Terminal 3 - Config Watcher (optional but recommended):**
```bash
./watch-dnsmasq.sh
```

## 3. Access the Web Interface

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 4. Configure Network Settings

1. Open http://localhost:5173 in your browser
2. Navigate to "Network Settings"
3. Configure:
   - **Server IP**: Your Alpine host's IP address (e.g., `10.0.1.136`)
   - **DHCP Mode**: Choose "proxy" or "server"
   - **Network Interface**: Your network interface (e.g., `eth0`, `ens33`)
4. Click "Save Settings"
5. Click "Apply Settings" to generate the dnsmasq configuration

## 5. Start dnsmasq

On Alpine, dnsmasq can be managed with OpenRC:

```bash
# Start dnsmasq
rc-service dnsmasq start

# Enable dnsmasq to start on boot
rc-update add dnsmasq

# Check status
rc-service dnsmasq status
```

Or manually:
```bash
dnsmasq --no-daemon -C /etc/dnsmasq.conf
```

## 6. Verify Everything is Working

1. Check backend is running:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. Check dnsmasq is listening:
   ```bash
   netstat -ulnp | grep -E ':(67|69)'
   ```

3. Test PXE boot with a VM or physical machine on the same network

## Troubleshooting

### Backend won't start
- Check if Python venv is activated: `source venv/bin/activate`
- Check logs: `tail -f logs/backend.log`
- Verify database exists: `ls -la data/ktizo.db`

### dnsmasq issues
- Test config: `dnsmasq --test -C /etc/dnsmasq.conf`
- Check logs: `tail -f /var/log/dnsmasq.log` or `journalctl -u dnsmasq`
- Verify ports: `netstat -ulnp | grep dnsmasq`

### Port conflicts
- Check what's using ports: `netstat -tulnp | grep -E ':(67|69|8000|5173)'`
- Stop conflicting services if needed

## Running in Background (Alpine)

Since Alpine doesn't have systemd, you can use:

1. **nohup**:
   ```bash
   nohup ./start.sh > logs/startup.log 2>&1 &
   ```

2. **screen** or **tmux**:
   ```bash
   apk add screen
   screen -S ktizo
   ./start.sh
   # Press Ctrl+A then D to detach
   ```

3. **OpenRC init script** (create manually if needed):
   ```bash
   # Create /etc/init.d/ktizo-backend
   # Use the startup scripts as ExecStart
   ```

## Next Steps

Once everything is running:
1. Configure your cluster settings in the web UI
2. Generate Talos cluster configurations
3. Boot your first node via PXE
4. Approve devices in the Device Management section


