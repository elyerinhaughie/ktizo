import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import termios
import yaml

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_controlplane_ip() -> str | None:
    """Get the first control plane node IP (without CIDR suffix)."""
    from app.db.database import SessionLocal
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus, DeviceRole

    db = SessionLocal()
    try:
        all_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)
        cp_nodes = [d for d in all_devices if d.role == DeviceRole.CONTROLPLANE and d.ip_address]
        if not cp_nodes:
            return None
        ip = cp_nodes[0].ip_address
        return ip.split('/')[0] if '/' in ip else ip
    finally:
        db.close()


def _ensure_talosconfig() -> bool:
    """Write a ready-to-use talosconfig to ~/.talos/config with correct endpoints/nodes.

    Copies the generated talosconfig from templates/base/talosconfig, fills in
    the controlplane IP for endpoints and nodes, and writes it to the standard
    talosctl default path so that ``talosctl`` works without extra flags.

    Returns True if the file was written successfully.
    """
    from pathlib import Path

    home = Path.home()
    dest = home / ".talos" / "config"

    # Source talosconfig from templates/base
    from app.api.cluster_router import get_templates_base_dir
    src = get_templates_base_dir() / "talosconfig"
    if not src.exists():
        logger.warning(f"Source talosconfig not found at {src}")
        return False

    cp_ip = _get_controlplane_ip()

    try:
        with open(src, 'r') as f:
            tc = yaml.safe_load(f)

        # Set endpoints and nodes to the controlplane IP
        if cp_ip:
            ctx_name = tc.get('context', '')
            if ctx_name and ctx_name in tc.get('contexts', {}):
                tc['contexts'][ctx_name]['endpoints'] = [cp_ip]
                tc['contexts'][ctx_name]['nodes'] = [cp_ip]

        dest.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with open(dest, 'w') as f:
            yaml.dump(tc, f, default_flow_style=False)
        os.chmod(dest, 0o600)
        logger.info(f"Wrote talosconfig to {dest} (endpoint: {cp_ip})")
        return True
    except Exception as e:
        logger.error(f"Failed to write talosconfig: {e}")
        return False


def _ensure_kubeconfig() -> bool:
    """Ensure kubeconfig exists at ~/.kube/config with the correct server endpoint.

    Uses ``talosctl kubeconfig`` to fetch credentials from the controlplane,
    then patches the server URL to ``https://<controlplane_ip>:6443``.

    Returns True if kubeconfig is available.
    """
    from app.db.database import SessionLocal
    from app.crud import cluster as cluster_crud
    from pathlib import Path
    import subprocess
    import time

    home = Path.home()
    kubeconfig_path = home / ".kube" / "config"
    talosconfig_path = home / ".talos" / "config"

    cp_ip = _get_controlplane_ip()
    if not cp_ip:
        logger.warning("No control plane nodes found, skipping kubeconfig fetch")
        return False

    api_server_url = f"https://{cp_ip}:6443"

    # If kubeconfig exists, is recent (<1h), and has the right endpoint, skip
    if kubeconfig_path.exists():
        file_age = time.time() - kubeconfig_path.stat().st_mtime
        if file_age < 3600:
            try:
                with open(kubeconfig_path, 'r') as f:
                    existing = yaml.safe_load(f)
                server = existing['clusters'][0]['cluster'].get('server', '')
                if server == api_server_url:
                    logger.info(f"Kubeconfig up to date at {kubeconfig_path}")
                    return True
            except Exception:
                pass  # Re-fetch on any parse error

    # Need talosconfig to fetch kubeconfig — try to set it up if missing
    if not talosconfig_path.exists():
        _ensure_talosconfig()
    if not talosconfig_path.exists():
        logger.warning(f"Talosconfig not found at {talosconfig_path}, skipping kubeconfig fetch")
        return False

    from app.api.cluster_router import find_talosctl
    try:
        talosctl = find_talosctl()
    except FileNotFoundError:
        logger.warning("talosctl not found, skipping kubeconfig fetch")
        return False

    db = SessionLocal()
    try:
        cluster_settings = cluster_crud.get_cluster_settings(db)
        if not cluster_settings:
            logger.warning("No cluster settings found, skipping kubeconfig fetch")
            return False

        # Determine API server endpoint from cluster settings or controlplane IP
        endpoint = cluster_settings.cluster_endpoint or cp_ip
        if ':' in endpoint and not endpoint.startswith('http'):
            endpoint = endpoint.split(':')[0]
        api_server_url = f"https://{endpoint}:6443"
    finally:
        db.close()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_kubeconfig = Path(tmp_dir) / "kubeconfig"
        cmd = [
            talosctl, "kubeconfig",
            "--talosconfig", str(talosconfig_path),
            "--nodes", cp_ip,
            "--endpoints", cp_ip,
            str(tmp_kubeconfig),
        ]
        logger.info(f"Fetching kubeconfig: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0 or not tmp_kubeconfig.exists():
            logger.warning(f"talosctl kubeconfig failed: {result.stderr or result.stdout}")
            return False

        # Parse fetched kubeconfig and patch server endpoint
        with open(tmp_kubeconfig, 'r') as f:
            kubeconfig = yaml.safe_load(f)

        if 'clusters' in kubeconfig and len(kubeconfig['clusters']) > 0:
            kubeconfig['clusters'][0]['cluster']['server'] = api_server_url
            logger.info(f"Set kubeconfig server to {api_server_url}")

        # Write to ~/.kube/config
        kubeconfig_dir = home / ".kube"
        kubeconfig_dir.mkdir(mode=0o700, exist_ok=True)
        with open(kubeconfig_path, 'w') as f:
            yaml.dump(kubeconfig, f, default_flow_style=False, sort_keys=False)
        os.chmod(kubeconfig_path, 0o600)
        logger.info(f"Wrote kubeconfig to {kubeconfig_path}")
        return True


def _build_env() -> dict:
    """Build environment variables for the terminal shell.

    Sets up PATH (kubectl, talosctl), KUBECONFIG, and TALOSCONFIG so that
    both ``kubectl`` and ``talosctl`` work out of the box.
    """
    from app.db.database import SessionLocal
    from app.crud import cluster as cluster_crud
    from app.services.kubectl_downloader import KubectlDownloader
    from app.api.cluster_router import find_talosctl

    env = os.environ.copy()
    home = os.path.expanduser("~")

    # --- PATH ---
    extra_paths = []

    # kubectl
    db = SessionLocal()
    try:
        cluster_settings = cluster_crud.get_cluster_settings(db)
    finally:
        db.close()

    kubectl_downloader = KubectlDownloader()
    kubectl_path = kubectl_downloader.get_kubectl_path()
    if kubectl_path and kubectl_path.parent.exists():
        extra_paths.append(str(kubectl_path.parent.resolve()))

    # talosctl
    try:
        talosctl = find_talosctl()
        from pathlib import Path
        talosctl_dir = str(Path(talosctl).parent.resolve())
        if talosctl_dir not in extra_paths:
            extra_paths.append(talosctl_dir)
    except FileNotFoundError:
        pass

    extra_paths.extend(["/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    existing = env.get("PATH", "")
    for p in extra_paths:
        if p not in existing:
            existing = f"{p}:{existing}"
    env["PATH"] = existing

    # --- Configs ---
    talosconfig_path = os.path.join(home, ".talos", "config")
    kubeconfig_path = os.path.join(home, ".kube", "config")

    # Write talosconfig to ~/.talos/config (talosctl default location)
    _ensure_talosconfig()

    # Fetch/update kubeconfig at ~/.kube/config
    _ensure_kubeconfig()

    env["TALOSCONFIG"] = talosconfig_path
    env["KUBECONFIG"] = kubeconfig_path
    env["TERM"] = "xterm-256color"

    return env


@router.websocket("/ws/terminal")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()

    child_pid = None
    master_fd = None

    try:
        # Create PTY
        master_fd, slave_fd = pty.openpty()

        env = _build_env()

        child_pid = os.fork()
        if child_pid == 0:
            # Child process — become the shell
            os.close(master_fd)
            os.setsid()

            # Set slave as controlling terminal
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

            # Redirect stdio to slave PTY
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)

            shell = os.environ.get("SHELL", "/bin/sh")
            os.execvpe(shell, [shell, "-l"], env)
            # execvpe never returns

        # Parent process
        os.close(slave_fd)

        # Set master_fd to non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        loop = asyncio.get_event_loop()

        # Task to read PTY output and send to WebSocket
        async def read_pty():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        await websocket.send_json({
                            "type": "output",
                            "data": data.decode("utf-8", errors="replace"),
                        })
                    except OSError:
                        # EAGAIN from non-blocking read — no data yet
                        continue
            except (WebSocketDisconnect, Exception):
                pass

        reader_task = asyncio.create_task(read_pty())

        # Read WebSocket messages and write to PTY
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)

                if msg["type"] == "input":
                    os.write(master_fd, msg["data"].encode("utf-8"))
                elif msg["type"] == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        except WebSocketDisconnect:
            logger.info("Terminal WebSocket disconnected")
        finally:
            reader_task.cancel()

    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        # Cleanup
        if master_fd is not None:
            try:
                os.close(master_fd)
            except OSError:
                pass
        if child_pid and child_pid > 0:
            try:
                os.kill(child_pid, signal.SIGHUP)
                os.waitpid(child_pid, os.WNOHANG)
            except (OSError, ChildProcessError):
                pass
