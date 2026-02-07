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


def _build_env() -> dict:
    """Build environment variables for the terminal shell."""
    env = os.environ.copy()
    home = os.path.expanduser("~")

    # Set kubeconfig and talosconfig paths
    env["KUBECONFIG"] = os.path.join(home, ".kube", "config")
    env["TALOSCONFIG"] = os.path.join(home, ".talos", "config")

    # Ensure common tool paths are on PATH
    extra_paths = ["/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    existing = env.get("PATH", "")
    for p in extra_paths:
        if p not in existing:
            existing = f"{p}:{existing}"
    env["PATH"] = existing
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
