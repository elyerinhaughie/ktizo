import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_kubeconfig() -> bool:
    """Ensure kubeconfig exists and is up-to-date. Returns True if kubeconfig is available."""
    from app.db.database import SessionLocal
    from app.crud import cluster as cluster_crud
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus, DeviceRole
    from pathlib import Path
    import subprocess
    import tempfile
    
    home = Path.home()
    kubeconfig_path = home / ".kube" / "config"
    
    # Check if kubeconfig exists and is recent (less than 1 hour old)
    kubeconfig_exists = kubeconfig_path.exists()
    kubeconfig_recent = False
    if kubeconfig_exists:
        import time
        file_age = time.time() - kubeconfig_path.stat().st_mtime
        kubeconfig_recent = file_age < 3600  # 1 hour
    
    # If kubeconfig doesn't exist or is stale, try to fetch it
    if not kubeconfig_exists or not kubeconfig_recent:
        db = SessionLocal()
        try:
            cluster_settings = cluster_crud.get_cluster_settings(db)
            if not cluster_settings:
                logger.debug("No cluster settings found, skipping kubeconfig fetch")
                return False
            
            # Check if talosconfig exists
            from app.api.cluster_router import get_templates_base_dir
            base_dir = get_templates_base_dir()
            talosconfig_path = base_dir / "talosconfig"
            
            if not talosconfig_path.exists():
                logger.debug("Talosconfig not found, skipping kubeconfig fetch")
                return False
            
            # Get control plane node IP
            all_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)
            cp_nodes = [d for d in all_devices if d.role == DeviceRole.CONTROLPLANE and d.ip_address]
            if not cp_nodes:
                logger.debug("No control plane nodes found, skipping kubeconfig fetch")
                return False
            
            cp_ip = cp_nodes[0].ip_address
            if '/' in cp_ip:
                cp_ip = cp_ip.split('/')[0]
            
            # Fetch kubeconfig using talosctl
            from app.api.cluster_router import find_talosctl
            try:
                talosctl = find_talosctl()
            except FileNotFoundError:
                logger.debug("talosctl not found, skipping kubeconfig fetch")
                return False
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_kubeconfig = Path(tmp_dir) / "kubeconfig"
                result = subprocess.run(
                    [
                        talosctl, "kubeconfig",
                        "--talosconfig", str(talosconfig_path),
                        "--nodes", cp_ip,
                        str(tmp_kubeconfig)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and tmp_kubeconfig.exists():
                    # Save to ~/.kube/config
                    kubeconfig_dir = home / ".kube"
                    kubeconfig_dir.mkdir(mode=0o700, exist_ok=True)
                    
                    with open(tmp_kubeconfig, 'r') as f:
                        kubeconfig_content = f.read()
                    
                    with open(kubeconfig_path, 'w') as f:
                        f.write(kubeconfig_content)
                    os.chmod(kubeconfig_path, 0o600)
                    logger.info(f"Auto-fetched and saved kubeconfig to {kubeconfig_path}")
                    return True
                else:
                    logger.debug(f"Failed to fetch kubeconfig: {result.stderr}")
                    return False
        except Exception as e:
            logger.warning(f"Error ensuring kubeconfig: {e}")
            return False
        finally:
            db.close()
    
    return kubeconfig_exists


def _build_env() -> dict:
    """Build environment variables for the terminal shell."""
    from app.db.database import SessionLocal
    from app.crud import cluster as cluster_crud
    from app.services.kubectl_downloader import KubectlDownloader
    
    env = os.environ.copy()
    home = os.path.expanduser("~")

    # Get cluster settings to determine kubectl version
    db = SessionLocal()
    try:
        cluster_settings = cluster_crud.get_cluster_settings(db)
        kubectl_version = cluster_settings.kubectl_version if cluster_settings else "1.28.0"
    finally:
        db.close()
    
    # Set kubectl version and add to PATH
    kubectl_downloader = KubectlDownloader()
    kubectl_path = kubectl_downloader.get_kubectl_path()
    
    # Ensure kubectl is in PATH (prioritize our version)
    extra_paths = []
    if kubectl_path and kubectl_path.parent.exists():
        # Add directory containing kubectl to PATH
        extra_paths.append(str(kubectl_path.parent.resolve()))
    
    # Add standard paths
    extra_paths.extend(["/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    
    existing = env.get("PATH", "")
    for p in extra_paths:
        if p not in existing:
            existing = f"{p}:{existing}"
    env["PATH"] = existing

    # Set kubeconfig path - ensure directory exists
    kubeconfig_dir = os.path.join(home, ".kube")
    kubeconfig_path = os.path.join(kubeconfig_dir, "config")
    os.makedirs(kubeconfig_dir, mode=0o700, exist_ok=True)
    
    # Try to ensure kubeconfig is available (auto-fetch if needed)
    _ensure_kubeconfig()
    
    # Set kubeconfig and talosconfig paths
    env["KUBECONFIG"] = kubeconfig_path
    env["TALOSCONFIG"] = os.path.join(home, ".talos", "config")
    
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
