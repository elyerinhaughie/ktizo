"""Background health checker for approved devices.

Runs every 10 seconds, performing:
  1. ICMP ping (network reachability)
  2. Talos API TCP connect on port 50000 (OS health)

Results are stored in-memory (not persisted) and broadcast via WebSocket.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

# In-memory health status: {mac_address: {ping: bool, talos_api: bool, last_checked: str}}
_health_status: Dict[str, Dict[str, Any]] = {}

CHECK_INTERVAL = 10  # seconds
PING_TIMEOUT = 1     # seconds
TCP_TIMEOUT = 2      # seconds
TALOS_API_PORT = 50000


async def _check_ping(ip: str) -> bool:
    """ICMP ping check — 1 packet, 1s timeout."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(PING_TIMEOUT), ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=PING_TIMEOUT + 2)
        return proc.returncode == 0
    except Exception:
        return False


async def _check_talos_api(ip: str) -> bool:
    """TCP connect to Talos API port 50000."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, TALOS_API_PORT),
            timeout=TCP_TIMEOUT,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def _check_device(ip: str) -> dict:
    """Run ping and Talos API checks in parallel for a single device."""
    ping_result, talos_result = await asyncio.gather(
        _check_ping(ip),
        _check_talos_api(ip),
    )
    return {
        "ping": ping_result,
        "talos_api": talos_result,
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }


def get_health_status() -> dict:
    """Return current health status dict (for on-demand WS queries)."""
    return dict(_health_status)


async def _run_checks():
    """Single check cycle for all approved devices with IPs."""
    from app.db.database import SessionLocal
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus

    db = SessionLocal()
    try:
        approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
        targets = [(d.mac_address, d.ip_address.split("/")[0] if "/" in d.ip_address else d.ip_address)
                    for d in approved if d.ip_address]
    finally:
        db.close()

    if not targets:
        return

    # Check all devices in parallel
    results = await asyncio.gather(
        *[_check_device(ip) for _, ip in targets]
    )

    for (mac, _), result in zip(targets, results):
        _health_status[mac] = result

    # Remove stale entries for devices no longer approved
    active_macs = {mac for mac, _ in targets}
    for mac in list(_health_status.keys()):
        if mac not in active_macs:
            del _health_status[mac]


async def health_check_loop():
    """Main loop — runs indefinitely, checking every CHECK_INTERVAL seconds."""
    from app.services.websocket_manager import websocket_manager

    logger.info(f"Health checker started (interval={CHECK_INTERVAL}s)")
    while True:
        try:
            await _run_checks()
            # Broadcast to all connected clients
            if _health_status:
                await websocket_manager.broadcast_event({
                    "type": "device_health",
                    "data": _health_status,
                })
        except Exception as e:
            logger.error(f"Health check cycle error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
