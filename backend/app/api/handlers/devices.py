"""Device management handler module for WebSocket actions."""

import asyncio
import json
import logging
import socket
import struct
import traceback
from pathlib import Path
from typing import Optional

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device list/CRUD handlers
# ---------------------------------------------------------------------------

async def _devices_list(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        status = params.get("status")
        if status:
            from app.db.models import DeviceStatus
            devices = crud.get_devices_by_status(db, DeviceStatus(status), 0, 1000)
        else:
            devices = crud.get_devices(db, 0, 1000)
        await _ws._respond(ws, req_id, devices)
    finally:
        db.close()


async def _devices_get(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        device = crud.get_device(db, params["device_id"])
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")
        await _ws._respond(ws, req_id, device)
    finally:
        db.close()


async def _devices_create(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.schemas.device import DeviceCreate
        existing = crud.get_device_by_mac(db, params["mac_address"])
        if existing:
            return await _ws._respond(ws, req_id, error="Device with this MAC address already exists")
        device = crud.create_device(db, DeviceCreate(**params))
        await _ws._respond(ws, req_id, device)
        await _ws._broadcast("device_created", device)
    finally:
        db.close()


async def _devices_update(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.schemas.device import DeviceUpdate
        from app.db.models import DeviceStatus, DeviceRole, Device

        device_id = params.pop("device_id")
        current = crud.get_device(db, device_id)
        if not current:
            return await _ws._respond(ws, req_id, error="Device not found")

        # sole-controlplane guard
        if current.status == DeviceStatus.APPROVED and current.role == DeviceRole.CONTROLPLANE:
            all_cp = db.query(Device).filter(
                Device.status == DeviceStatus.APPROVED,
                Device.role == DeviceRole.CONTROLPLANE
            ).all()
            if len(all_cp) == 1:
                if params.get("ip_address") and params["ip_address"] != current.ip_address:
                    return await _ws._respond(ws, req_id, error="Cannot change IP of the only control plane node")
                if params.get("role") and params["role"] != current.role:
                    return await _ws._respond(ws, req_id, error="Cannot change role of the only control plane node")

        # IP conflict check
        if params.get("ip_address"):
            conflict = db.query(Device).filter(Device.ip_address == params["ip_address"], Device.id != device_id).first()
            if conflict:
                return await _ws._respond(ws, req_id, error=f"IP {params['ip_address']} already assigned to {conflict.mac_address}")

        updated = crud.update_device(db, device_id, DeviceUpdate(**params))
        if not updated:
            return await _ws._respond(ws, req_id, error="Device not found")

        await _ws.log_action(db, "updated_device", "Device Management",
            json.dumps({"mac": updated.mac_address, "hostname": updated.hostname, "changes": params}),
            "device", str(device_id))

        await _ws._respond(ws, req_id, updated)
        await _ws._broadcast("device_updated", updated)
    finally:
        db.close()


async def _devices_approval_suggestions(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud, cluster as cluster_crud, network as network_crud, volume as volume_crud
        from app.db.models import DeviceStatus, DeviceRole
        from app.utils.network import get_next_available_ip, get_first_usable_ip, is_fqdn

        device_id = params["device_id"]
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")

        cluster_settings = cluster_crud.get_cluster_settings(db)
        network_settings = network_crud.get_network_settings(db)
        if not cluster_settings:
            return await _ws._respond(ws, req_id, error="Cluster settings not configured")
        if not network_settings:
            return await _ws._respond(ws, req_id, error="Network settings not configured")

        approved = crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1)
        is_first = len(approved) == 0

        if is_first:
            suggested_role = DeviceRole.CONTROLPLANE.value
            role_locked = True
            role_reason = "First device must be a control plane node"
        else:
            cp_count = len([d for d in crud.get_devices(db, 0, 1000)
                           if d.status == DeviceStatus.APPROVED and d.role == DeviceRole.CONTROLPLANE])
            suggested_role = DeviceRole.WORKER.value
            role_locked = False
            role_reason = f"{cp_count} control plane node(s). 3 recommended for HA." if cp_count < 3 else "3+ control plane nodes."

        external_subnet = cluster_settings.external_subnet
        if not external_subnet:
            return await _ws._respond(ws, req_id, error="External subnet not configured")

        if is_first:
            ce = cluster_settings.cluster_endpoint
            if is_fqdn(ce):
                suggested_ip = get_first_usable_ip(external_subnet)
                ip_reason = f"First IP in subnet (cluster endpoint '{ce}' is FQDN)"
            else:
                suggested_ip = ce
                ip_reason = "Must match cluster endpoint IP"
            ip_locked = True
        else:
            suggested_ip = get_next_available_ip(db, external_subnet)
            ip_locked = False
            ip_reason = "Next available IP in subnet"

        suggested_hostname = device.hostname or f"node-{len([d for d in crud.get_devices(db, 0, 1000) if d.status == DeviceStatus.APPROVED]) + 1:02d}"

        storage_defaults = {
            "install_disk": cluster_settings.install_disk if cluster_settings else "/dev/sda",
            "ephemeral_min_size": None,
            "ephemeral_max_size": None,
            "ephemeral_disk_selector": None,
        }
        eph = volume_crud.get_volume_config_by_name(db, "EPHEMERAL")
        if eph:
            storage_defaults["ephemeral_min_size"] = eph.min_size
            storage_defaults["ephemeral_max_size"] = eph.max_size
            storage_defaults["ephemeral_disk_selector"] = eph.disk_selector_match

        await _ws._respond(ws, req_id, {
            "device_id": device_id,
            "mac_address": device.mac_address,
            "is_first_device": is_first,
            "suggestions": {"hostname": suggested_hostname, "ip_address": suggested_ip, "role": suggested_role},
            "locked_fields": {"ip_address": ip_locked, "role": role_locked},
            "reasons": {"ip_address": ip_reason, "role": role_reason},
            "subnet": external_subnet,
            "storage_defaults": storage_defaults,
        })
    finally:
        db.close()


async def _devices_approve(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud, cluster as cluster_crud
        from app.schemas.device import DeviceApprovalRequest
        from app.db.models import DeviceStatus, DeviceRole, Device
        from app.utils.network import get_first_usable_ip, is_fqdn

        device_id = params.pop("device_id")
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")

        approval = DeviceApprovalRequest(**params)
        if not approval.hostname or not approval.ip_address or not approval.role:
            return await _ws._respond(ws, req_id, error="hostname, ip_address, and role are required")

        # IP conflict
        conflict = db.query(Device).filter(Device.ip_address == approval.ip_address, Device.id != device_id).first()
        if conflict:
            return await _ws._respond(ws, req_id, error=f"IP {approval.ip_address} already assigned to {conflict.mac_address}")

        cluster_settings = cluster_crud.get_cluster_settings(db)
        if not cluster_settings or not cluster_settings.external_subnet:
            return await _ws._respond(ws, req_id, error="Cluster settings with external subnet required")

        approved_devices = crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1)
        is_first = len(approved_devices) == 0

        if is_first:
            if approval.role != DeviceRole.CONTROLPLANE:
                return await _ws._respond(ws, req_id, error="First device must be a control plane node")
            ce = cluster_settings.cluster_endpoint
            if is_fqdn(ce):
                required_ip = get_first_usable_ip(cluster_settings.external_subnet)
                if approval.ip_address != required_ip:
                    return await _ws._respond(ws, req_id, error=f"First device with FQDN endpoint must use {required_ip}")
            else:
                if approval.ip_address != ce:
                    return await _ws._respond(ws, req_id, error=f"First device must use cluster endpoint IP: {ce}")

        device.hostname = approval.hostname
        device.ip_address = approval.ip_address
        device.role = approval.role
        device.install_disk = approval.install_disk
        device.ephemeral_min_size = approval.ephemeral_min_size
        device.ephemeral_max_size = approval.ephemeral_max_size
        device.ephemeral_disk_selector = approval.ephemeral_disk_selector
        db.commit()

        device = crud.approve_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found after approval")

        # Update talosconfig for control plane nodes
        if device.role == DeviceRole.CONTROLPLANE and device.ip_address:
            cp_ip = device.ip_address.split('/')[0] if '/' in device.ip_address else device.ip_address
            try:
                from app.api.cluster_router import update_talosconfig_endpoint_and_node
                update_talosconfig_endpoint_and_node(cp_ip)
            except Exception as e:
                logger.warning(f"Error updating talosconfig: {e}")

        await _ws.log_action(db, "approved_device", "Device Management",
            json.dumps({"mac": device.mac_address, "hostname": device.hostname, "role": device.role.value, "ip": device.ip_address}),
            "device", str(device_id))

        await _ws._respond(ws, req_id, device)
        await _ws._broadcast("device_approved", {"device_id": device_id, "mac_address": device.mac_address, "hostname": device.hostname})
    finally:
        db.close()


async def _devices_reject(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        device = crud.reject_device(db, params["device_id"])
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")

        await _ws.log_action(db, "rejected_device", "Device Management",
            json.dumps({"mac": device.mac_address}), "device", str(params["device_id"]))

        await _ws._respond(ws, req_id, device)
        await _ws._broadcast("device_rejected", {"device_id": params["device_id"], "mac_address": device.mac_address, "hostname": device.hostname})
    finally:
        db.close()


async def _devices_delete(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.db.models import DeviceStatus

        device_id = params["device_id"]
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")

        mac = device.mac_address
        hostname = device.hostname

        if device.status == DeviceStatus.APPROVED and hostname:
            from app.services.kubectl_runner import kubectl_delete_node
            ok, msg = kubectl_delete_node(hostname)
            logger.info(f"kubectl delete node {hostname}: {msg}")

        success = crud.delete_device(db, device_id)
        if not success:
            return await _ws._respond(ws, req_id, error="Device not found")

        await _ws.log_action(db, "deleted_device", "Device Management",
            json.dumps({"mac": mac, "hostname": hostname}), "device", str(device_id))

        await _ws._respond(ws, req_id, {"message": "Device deleted successfully"})
        await _ws._broadcast("device_deleted", {"device_id": device_id, "mac_address": mac, "hostname": hostname})
    finally:
        db.close()


async def _devices_regenerate(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import device as crud, network as network_crud
        from app.db.models import DeviceStatus
        from app.services.config_generator import ConfigGenerator
        from app.services.ipxe_generator import IPXEGenerator

        approved = crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
        cg = ConfigGenerator()
        config_count = cg.regenerate_all_configs(approved)

        network_settings = network_crud.get_network_settings(db)
        tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
        ig = IPXEGenerator(tftp_root=tftp_root)
        server_ip = ig.get_server_ip_from_settings(db)
        strict = ig.get_strict_mode_from_settings(db)
        ipxe_ok = ig.generate_boot_script(approved, server_ip, strict_mode=strict)

        await _ws._respond(ws, req_id, {
            "message": "Configuration regeneration completed",
            "device_configs_generated": config_count,
            "boot_script_generated": ipxe_ok,
            "approved_devices": len(approved),
        })
        await _ws._broadcast("configs_regenerated", {})
    finally:
        db.close()


async def _devices_health(params: dict, ws: WebSocket, req_id: str):
    from app.services.health_checker import get_health_status
    await _ws._respond(ws, req_id, get_health_status())


async def _devices_shutdown(params: dict, ws: WebSocket, req_id: str):
    """Shutdown a Talos node via talosctl shutdown."""
    import asyncio
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.api.cluster_router import find_talosctl, get_templates_base_dir

        device_id = params["device_id"]
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")
        if device.status != "approved":
            return await _ws._respond(ws, req_id, error="Can only shutdown approved devices")
        if not device.ip_address:
            return await _ws._respond(ws, req_id, error="Device has no IP address")

        ip = device.ip_address.split('/')[0] if '/' in device.ip_address else device.ip_address
        talosctl = find_talosctl()
        talosconfig = str(get_templates_base_dir() / "talosconfig")

        proc = await asyncio.create_subprocess_exec(
            talosctl, "shutdown",
            "--talosconfig", talosconfig,
            "--nodes", ip,
            "--endpoints", ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err_msg = stderr.decode().strip() or stdout.decode().strip()
            return await _ws._respond(ws, req_id, error=f"Shutdown failed: {err_msg}")

        name = device.hostname or device.mac_address
        await _ws.log_action(db, "shutdown_device", "Device Management",
            json.dumps({"mac": device.mac_address, "hostname": device.hostname, "ip": ip}),
            "device", str(device_id))

        await _ws._respond(ws, req_id, {"message": f"{name} shutdown command sent"})
        await _ws._broadcast("device_shutdown", {
            "device_id": device_id,
            "mac_address": device.mac_address,
            "hostname": device.hostname,
            "ip_address": ip,
        })
    except FileNotFoundError:
        await _ws._respond(ws, req_id, error="talosctl not found on server")
    except asyncio.TimeoutError:
        await _ws._respond(ws, req_id, error="Shutdown command timed out")
    finally:
        db.close()


async def _devices_wake(params: dict, ws: WebSocket, req_id: str):
    """Send a Wake-on-LAN magic packet to a device."""
    import socket
    import struct
    db = _ws._db()
    try:
        from app.crud import device as crud

        device_id = params["device_id"]
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")
        if not device.mac_address:
            return await _ws._respond(ws, req_id, error="Device has no MAC address")

        # Parse MAC address
        mac_str = device.mac_address.replace(":", "").replace("-", "")
        if len(mac_str) != 12:
            return await _ws._respond(ws, req_id, error=f"Invalid MAC address: {device.mac_address}")
        mac_bytes = bytes.fromhex(mac_str)

        # Build magic packet: 6 bytes of 0xFF + MAC repeated 16 times
        magic = b'\xff' * 6 + mac_bytes * 16

        # Send to broadcast on port 9
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic, ('255.255.255.255', 9))
        sock.close()

        name = device.hostname or device.mac_address
        await _ws.log_action(db, "wol_device", "Device Management",
            json.dumps({"mac": device.mac_address, "hostname": device.hostname}),
            "device", str(device_id))

        await _ws._respond(ws, req_id, {"message": f"Wake-on-LAN packet sent to {name}"})
        await _ws._broadcast("device_wol", {
            "device_id": device_id,
            "mac_address": device.mac_address,
            "hostname": device.hostname,
        })
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Device reboot
# ---------------------------------------------------------------------------

async def _devices_reboot(params: dict, ws: WebSocket, req_id: str):
    """Reboot a Talos node via talosctl reboot."""
    import asyncio as _asyncio
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.api.cluster_router import find_talosctl, get_templates_base_dir

        device_id = params["device_id"]
        device = crud.get_device(db, device_id)
        if not device:
            return await _ws._respond(ws, req_id, error="Device not found")
        if device.status != "approved":
            return await _ws._respond(ws, req_id, error="Can only reboot approved devices")
        if not device.ip_address:
            return await _ws._respond(ws, req_id, error="Device has no IP address")

        ip = device.ip_address.split('/')[0] if '/' in device.ip_address else device.ip_address
        talosctl = find_talosctl()
        talosconfig = str(get_templates_base_dir() / "talosconfig")

        proc = await _asyncio.create_subprocess_exec(
            talosctl, "reboot",
            "--mode", "powercycle",
            "--wait=false",
            "--talosconfig", talosconfig,
            "--nodes", ip,
            "--endpoints", ip,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.PIPE,
        )
        stdout, stderr = await _asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err_msg = stderr.decode().strip() or stdout.decode().strip()
            return await _ws._respond(ws, req_id, error=f"Reboot failed: {err_msg}")

        name = device.hostname or device.mac_address
        await _ws.log_action(db, "reboot_device", "Device Management",
            json.dumps({"mac": device.mac_address, "hostname": device.hostname, "ip": ip}),
            "device", str(device_id))

        await _ws._respond(ws, req_id, {"message": f"{name} reboot command sent"})
        await _ws._broadcast("device_reboot", {
            "device_id": device_id,
            "mac_address": device.mac_address,
            "hostname": device.hostname,
            "ip_address": ip,
        })
    except FileNotFoundError:
        await _ws._respond(ws, req_id, error="talosctl not found on server")
    except _asyncio.TimeoutError:
        await _ws._respond(ws, req_id, error="Reboot command timed out")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Rolling refresh — Worker node wipe & reinstall
# Supports: sequential (one at a time), parallel (N at a time), all_at_once (no drain)
# ---------------------------------------------------------------------------

_rolling_refresh_active = False
_rolling_refresh_cancel = False
_rolling_refresh_state = {}  # varies by mode


async def _kubectl_drain(kubectl: str, kubeconfig: str, hostname: str) -> tuple:
    """Cordon and drain a Kubernetes node. Returns (success, message)."""
    # Cordon
    proc = await asyncio.create_subprocess_exec(
        kubectl, "cordon", hostname, "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        err = stderr.decode().strip() or stdout.decode().strip()
        logger.warning(f"Cordon failed for {hostname}: {err}")
        return False, f"Cordon failed: {err}"

    # Drain
    proc = await asyncio.create_subprocess_exec(
        kubectl, "drain", hostname,
        "--ignore-daemonsets", "--delete-emptydir-data", "--force",
        "--timeout=120s", "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=150)
    if proc.returncode != 0:
        err = stderr.decode().strip() or stdout.decode().strip()
        logger.warning(f"Drain failed for {hostname}: {err}")
        return False, f"Drain failed: {err}"

    return True, "Drained successfully"


async def _kubectl_uncordon(kubectl: str, kubeconfig: str, hostname: str):
    """Uncordon a Kubernetes node."""
    proc = await asyncio.create_subprocess_exec(
        kubectl, "uncordon", hostname, "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.wait_for(proc.communicate(), timeout=30)


async def _wait_for_node_boot(ip: str, timeout: int = 600) -> bool:
    """Wait for a node to boot (ping + Talos API). Returns True if up within timeout."""
    from app.services.health_checker import _check_ping, _check_talos_api

    elapsed = 0
    interval = 15
    while elapsed < timeout:
        ping_ok = await _check_ping(ip)
        talos_ok = await _check_talos_api(ip)
        if ping_ok and talos_ok:
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return False


async def _wait_for_node_ready(kubectl: str, kubeconfig: str, hostname: str, timeout: int = 300) -> bool:
    """Wait for a Kubernetes node to become Ready. Returns True if ready within timeout."""
    elapsed = 0
    interval = 15
    while elapsed < timeout:
        proc = await asyncio.create_subprocess_exec(
            kubectl, "get", "node", hostname,
            "-o", "jsonpath={.status.conditions[?(@.type==\"Ready\")].status}",
            "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0 and stdout.decode().strip() == "True":
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return False


async def _refresh_single_node(
    idx: int, dev: dict, total: int,
    kubectl: str, kubeconfig: str, talosctl: str, talosconfig: str,
    skip_drain: bool = False,
) -> bool:
    """Refresh a single worker node through the full 7-step pipeline.

    Broadcasts per-node progress events with node_index.
    Returns True on success, False on failure.
    """
    global _rolling_refresh_state

    from app.crud import device as device_crud
    from app.schemas.device import DeviceUpdate

    from app.api.handlers.longhorn import (
        _longhorn_reset_disks_after_wipe,
        _longhorn_use_all_disks_for_node,
        _load_longhorn_auto_config,
        _LONGHORN_NS,
    )

    device_id = dev["id"]
    hostname = dev["hostname"]
    ip = dev["ip_address"]

    def _update_node_state(step, message=""):
        if "node_states" in _rolling_refresh_state:
            _rolling_refresh_state["node_states"][idx] = {"device": dev, "step": step, "message": message}

    async def _progress(step, message):
        _update_node_state(step, message)
        await _ws._broadcast("rolling_refresh_progress", {
            "node_index": idx, "total": total, "device": dev,
            "step": step, "message": message,
        })

    # Step 1: Drain (skipped in all-at-once mode)
    if not skip_drain:
        await _progress("draining", f"Draining pods from {hostname}...")
        if kubectl:
            drain_ok, drain_msg = await _kubectl_drain(kubectl, kubeconfig, hostname)
            if not drain_ok:
                logger.warning(f"Drain warning for {hostname}: {drain_msg}")
        else:
            logger.warning("kubectl not found, skipping drain")

    # Step 2: Set wipe flag and regenerate configs
    await _progress("setting_wipe", f"Setting wipe flag on {hostname}...")
    db = _ws._db()
    try:
        device_crud.update_device(db, device_id, DeviceUpdate(wipe_on_next_boot=True))
        await asyncio.to_thread(_ws._regenerate_all_device_configs, db)
    finally:
        db.close()

    # Step 3: Reboot
    await _progress("rebooting", f"Rebooting {hostname}...")
    proc = await asyncio.create_subprocess_exec(
        talosctl, "reboot",
        "--mode", "powercycle", "--wait=false",
        "--talosconfig", talosconfig,
        "--nodes", ip, "--endpoints", ip,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error(f"Reboot failed for {hostname}: {err}")
        await _progress("failed", f"Reboot failed: {err}")
        await _ws._broadcast("rolling_refresh_error", {"device": dev, "error": f"Reboot failed: {err}"})
        return False

    # Step 4: Wait for boot
    await _progress("waiting_for_boot", f"Waiting for {hostname} to boot...")
    await asyncio.sleep(30)  # Give the node time to actually go down
    booted = await _wait_for_node_boot(ip, timeout=600)
    if not booted:
        await _progress("failed", f"{hostname} did not come back within timeout")
        await _ws._broadcast("rolling_refresh_error", {"device": dev, "error": "Node did not boot within 10 minutes"})
        return False

    # Step 5: Wait for Kubernetes readiness
    if kubectl:
        await _progress("waiting_for_kubernetes", f"Waiting for {hostname} to join cluster...")
        ready = await _wait_for_node_ready(kubectl, kubeconfig, hostname, timeout=300)
        if not ready:
            await _progress("failed", f"{hostname} did not become Ready within timeout")
            await _ws._broadcast("rolling_refresh_error", {"device": dev, "error": "Node not Ready within 5 minutes"})
            return False

        # Step 6: Uncordon
        await _kubectl_uncordon(kubectl, kubeconfig, hostname)

    # Step 7: Clear wipe flag and regenerate configs
    db = _ws._db()
    try:
        device_crud.update_device(db, device_id, DeviceUpdate(wipe_on_next_boot=False))
        await asyncio.to_thread(_ws._regenerate_all_device_configs, db)
    finally:
        db.close()

    # Step 8: Post-provisioning Longhorn disk reset + auto-add
    # After a wipe, Longhorn disk entries have stale UUIDs — reset them
    _kubectl = _ws._find_kubectl()
    _kc = str(Path.home() / ".kube" / "config")
    longhorn_node_ready = False

    # Wait for Longhorn node CRD to appear (poll up to 2 min)
    await _progress("configuring_storage", f"Waiting for Longhorn on {hostname}...")
    for _attempt in range(24):
        proc = await asyncio.create_subprocess_exec(
            _kubectl, "get", "nodes.longhorn.io", hostname, "-n", _LONGHORN_NS,
            "--kubeconfig", _kc,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode == 0:
            longhorn_node_ready = True
            break
        await asyncio.sleep(5)

    if longhorn_node_ready:
        # Reset existing disks to avoid UUID mismatch after wipe
        await _progress("configuring_storage", f"Resetting Longhorn disks on {hostname}...")
        try:
            await _longhorn_reset_disks_after_wipe(hostname)
        except Exception as e:
            logger.warning(f"Longhorn disk reset failed for {hostname}: {e}")

        # Auto-add additional disks if configured
        auto_config = _load_longhorn_auto_config()
        if auto_config.get(hostname, {}).get("auto_add_disks"):
            await _progress("configuring_storage", f"Auto-adding disks on {hostname}...")
            added, err = await _longhorn_use_all_disks_for_node(hostname)
            if err:
                logger.warning(f"Longhorn auto-add failed for {hostname}: {err}")
            elif added > 0:
                logger.info(f"Longhorn auto-added {added} disk(s) on {hostname}")
    else:
        logger.warning(f"Longhorn node CRD not found for {hostname} after 2 min, skipping disk reset")

    await _progress("completed", f"{hostname} refreshed successfully")
    return True


async def _do_sequential_refresh(devices: list):
    """Background: sequentially wipe and reinstall worker nodes (one at a time)."""
    global _rolling_refresh_active, _rolling_refresh_cancel, _rolling_refresh_state

    from app.api.cluster_router import find_talosctl, get_templates_base_dir

    total = len(devices)
    succeeded = 0
    failed = 0

    kubectl = _ws._find_kubectl()
    kubeconfig = str(Path.home() / ".kube" / "config")
    talosctl = find_talosctl()
    talosconfig = str(get_templates_base_dir() / "talosconfig")

    try:
        for idx, dev in enumerate(devices):
            if _rolling_refresh_cancel:
                _rolling_refresh_state["node_states"][idx] = {"device": dev, "step": "cancelled", "message": "Cancelled"}
                await _ws._broadcast("rolling_refresh_complete", {
                    "total": total, "succeeded": succeeded, "failed": failed, "cancelled": True,
                })
                return

            success = await _refresh_single_node(idx, dev, total, kubectl, kubeconfig, talosctl, talosconfig)
            if success:
                succeeded += 1
            else:
                failed += 1
                break  # Stop on failure in sequential mode

            _rolling_refresh_state["succeeded"] = succeeded
            _rolling_refresh_state["failed"] = failed

        await _ws._broadcast("rolling_refresh_complete", {
            "total": total, "succeeded": succeeded, "failed": failed, "cancelled": False,
        })

    except Exception as e:
        logger.error(f"Sequential refresh error: {e}\n{traceback.format_exc()}")
        await _ws._broadcast("rolling_refresh_error", {"device": dev if 'dev' in dir() else None, "error": str(e)})
        await _ws._broadcast("rolling_refresh_complete", {
            "total": total, "succeeded": succeeded, "failed": failed + 1, "cancelled": False,
        })
    finally:
        _rolling_refresh_active = False
        _rolling_refresh_cancel = False
        _rolling_refresh_state = {}


async def _do_concurrent_refresh(devices: list, parallelism: int, skip_drain: bool = False):
    """Background: refresh worker nodes concurrently with a concurrency limit.

    Used for both 'parallel' mode (with drain, limited concurrency) and
    'all_at_once' mode (no drain, unlimited concurrency).
    """
    global _rolling_refresh_active, _rolling_refresh_cancel, _rolling_refresh_state

    from app.api.cluster_router import find_talosctl, get_templates_base_dir

    total = len(devices)
    results = {}  # idx -> bool

    kubectl = _ws._find_kubectl()
    kubeconfig = str(Path.home() / ".kube" / "config")
    talosctl = find_talosctl()
    talosconfig = str(get_templates_base_dir() / "talosconfig")

    sem = asyncio.Semaphore(parallelism)

    async def _run_one(idx, dev):
        if _rolling_refresh_cancel:
            _rolling_refresh_state["node_states"][idx] = {"device": dev, "step": "cancelled", "message": "Cancelled"}
            results[idx] = False
            return
        async with sem:
            if _rolling_refresh_cancel:
                _rolling_refresh_state["node_states"][idx] = {"device": dev, "step": "cancelled", "message": "Cancelled"}
                results[idx] = False
                return
            try:
                success = await _refresh_single_node(
                    idx, dev, total, kubectl, kubeconfig, talosctl, talosconfig,
                    skip_drain=skip_drain,
                )
                results[idx] = success
            except Exception as e:
                logger.error(f"Concurrent refresh error for {dev['hostname']}: {e}")
                results[idx] = False
                _rolling_refresh_state["node_states"][idx] = {"device": dev, "step": "failed", "message": str(e)}
                await _ws._broadcast("rolling_refresh_error", {"device": dev, "error": str(e)})

    try:
        tasks = [asyncio.create_task(_run_one(i, d)) for i, d in enumerate(devices)]
        await asyncio.gather(*tasks, return_exceptions=True)

        succeeded = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        await _ws._broadcast("rolling_refresh_complete", {
            "total": total, "succeeded": succeeded, "failed": failed,
            "cancelled": _rolling_refresh_cancel,
        })

    except Exception as e:
        logger.error(f"Concurrent refresh error: {e}\n{traceback.format_exc()}")
        succeeded = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        await _ws._broadcast("rolling_refresh_complete", {
            "total": total, "succeeded": succeeded, "failed": failed + 1, "cancelled": False,
        })
    finally:
        _rolling_refresh_active = False
        _rolling_refresh_cancel = False
        _rolling_refresh_state = {}


async def _devices_rolling_refresh(params: dict, ws: WebSocket, req_id: str):
    """Start a rolling refresh of worker nodes.

    Params:
      mode: 'sequential' (default), 'parallel', or 'all_at_once'
      parallelism: int (batch size for parallel mode, default 2)
      device_ids: optional list of specific device IDs
    """
    global _rolling_refresh_active, _rolling_refresh_cancel, _rolling_refresh_state

    if _rolling_refresh_active:
        return await _ws._respond(ws, req_id, error="A rolling refresh is already in progress")

    mode = params.get("mode", "sequential")
    parallelism = params.get("parallelism", 2)
    if mode not in ("sequential", "parallel", "all_at_once"):
        return await _ws._respond(ws, req_id, error=f"Invalid mode: {mode}")
    if mode == "parallel" and (not isinstance(parallelism, int) or parallelism < 2):
        parallelism = 2

    db = _ws._db()
    try:
        from app.crud import device as device_crud
        from app.db.models import DeviceStatus, DeviceRole

        all_devices = device_crud.get_devices(db, skip=0, limit=1000)
        workers = [d for d in all_devices
                   if d.status == DeviceStatus.APPROVED
                   and d.role == DeviceRole.WORKER
                   and d.ip_address]

        device_ids = params.get("device_ids")
        if device_ids:
            workers = [d for d in workers if d.id in device_ids]

        if not workers:
            return await _ws._respond(ws, req_id, error="No approved worker nodes with IP addresses found")

        device_list = []
        for d in workers:
            ip = d.ip_address.split("/")[0] if "/" in d.ip_address else d.ip_address
            device_list.append({
                "id": d.id,
                "hostname": d.hostname or d.mac_address,
                "mac_address": d.mac_address,
                "ip_address": ip,
            })

        _rolling_refresh_active = True
        _rolling_refresh_cancel = False
        _rolling_refresh_state = {
            "total": len(device_list),
            "mode": mode,
            "parallelism": parallelism if mode == "parallel" else (len(device_list) if mode == "all_at_once" else 1),
            "node_states": {i: {"device": d, "step": "pending", "message": "Waiting..."} for i, d in enumerate(device_list)},
            "succeeded": 0,
            "failed": 0,
        }

        mode_label = {"sequential": "sequential", "parallel": f"parallel (batch {parallelism})", "all_at_once": "all at once"}[mode]
        await _ws._respond(ws, req_id, {
            "message": f"Rolling refresh started for {len(device_list)} worker node(s) — {mode_label}",
            "devices": device_list,
            "mode": mode,
        })

        await _ws.log_action(db, "rolling_refresh_started", "Device Management",
            json.dumps({"count": len(device_list), "mode": mode, "devices": [d["hostname"] for d in device_list]}),
            "device", "rolling_refresh")

        if mode == "sequential":
            asyncio.create_task(_do_sequential_refresh(device_list))
        elif mode == "parallel":
            asyncio.create_task(_do_concurrent_refresh(device_list, parallelism))
        elif mode == "all_at_once":
            asyncio.create_task(_do_concurrent_refresh(device_list, len(device_list), skip_drain=True))
    finally:
        db.close()


async def _devices_rolling_refresh_cancel(params: dict, ws: WebSocket, req_id: str):
    """Cancel a rolling refresh after the current node(s) complete."""
    global _rolling_refresh_cancel

    if not _rolling_refresh_active:
        return await _ws._respond(ws, req_id, error="No rolling refresh in progress")

    _rolling_refresh_cancel = True
    await _ws._respond(ws, req_id, {"message": "Cancellation requested — will stop after current node(s)"})


async def _devices_rolling_refresh_status(params: dict, ws: WebSocket, req_id: str):
    """Return current rolling refresh state."""
    await _ws._respond(ws, req_id, {
        "active": _rolling_refresh_active,
        **_rolling_refresh_state,
    })


# ---------------------------------------------------------------------------
# Action dispatcher dictionary
# ---------------------------------------------------------------------------

DEVICE_ACTIONS = {
    "devices.list": _devices_list,
    "devices.get": _devices_get,
    "devices.create": _devices_create,
    "devices.update": _devices_update,
    "devices.approval_suggestions": _devices_approval_suggestions,
    "devices.approve": _devices_approve,
    "devices.reject": _devices_reject,
    "devices.delete": _devices_delete,
    "devices.regenerate": _devices_regenerate,
    "devices.health": _devices_health,
    "devices.shutdown": _devices_shutdown,
    "devices.reboot": _devices_reboot,
    "devices.wake": _devices_wake,
    "devices.rolling_refresh": _devices_rolling_refresh,
    "devices.rolling_refresh_cancel": _devices_rolling_refresh_cancel,
    "devices.rolling_refresh_status": _devices_rolling_refresh_status,
}
