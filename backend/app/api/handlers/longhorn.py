"""Longhorn storage disk management via CRDs."""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# longhorn.* — Longhorn storage disk management via CRDs
# ---------------------------------------------------------------------------

_LONGHORN_NS = "longhorn-system"
_LONGHORN_AUTO_CONFIG_FILE = Path.home() / ".ktizo" / "data" / "longhorn_auto_disks.json"


def _resolve_node_ip(node_name: str) -> Optional[str]:
    """Resolve a K8s node name (hostname) to its IP from the devices table."""
    db = _ws._db()
    try:
        from app.crud import device as crud
        from app.db.models import DeviceStatus
        devices = crud.get_devices(db, skip=0, limit=1000)
        for d in devices:
            if d.status == DeviceStatus.APPROVED and d.hostname == node_name:
                ip = d.ip_address
                return ip.split("/")[0] if "/" in ip else ip
        return None
    finally:
        db.close()


def _load_longhorn_auto_config() -> dict:
    """Load per-node Longhorn auto-disk config from JSON file."""
    try:
        if _LONGHORN_AUTO_CONFIG_FILE.exists():
            return json.loads(_LONGHORN_AUTO_CONFIG_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_longhorn_auto_config(config: dict):
    """Save per-node Longhorn auto-disk config to JSON file."""
    _LONGHORN_AUTO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LONGHORN_AUTO_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _disk_name_from_path(path: str) -> str:
    """Generate a Longhorn disk name from a mount path."""
    # /var/mnt/longhorn → disk-var-mnt-longhorn
    clean = path.strip("/").replace("/", "-").replace(".", "-")
    return f"disk-{clean}" if clean else "disk-default"


async def _longhorn_reset_disks_after_wipe(node_name: str):
    """Reset Longhorn disk entries for a node after a wipe to avoid UUID mismatch.

    After a Talos wipe, the filesystem UUID changes but the Longhorn CRD retains
    the old UUID, causing DiskFilesystemChanged errors and 0-byte storage.

    This removes all existing disk entries and re-adds them with fresh names
    so Longhorn picks up the new UUID.
    """
    import time

    kubectl = _ws._find_kubectl()
    if not kubectl:
        return
    kubeconfig = str(Path.home() / ".kube" / "config")

    # Get current Longhorn node spec
    proc = await asyncio.create_subprocess_exec(
        kubectl, "get", "nodes.longhorn.io", node_name, "-n", _LONGHORN_NS,
        "-o", "json", "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    if proc.returncode != 0:
        logger.warning(f"Longhorn node {node_name} not found for disk reset")
        return

    try:
        node_data = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return

    spec_disks = node_data.get("spec", {}).get("disks", {})
    if not spec_disks:
        return

    # Collect disk paths and their scheduling state
    disk_entries = []
    for disk_name, disk_spec in spec_disks.items():
        disk_entries.append({
            "old_name": disk_name,
            "path": disk_spec.get("path", ""),
            "allowScheduling": disk_spec.get("allowScheduling", True),
            "storageReserved": disk_spec.get("storageReserved", 0),
            "tags": disk_spec.get("tags", []),
        })

    # Remove all old disk entries (set to null in merge patch)
    remove_patch = {"spec": {"disks": {e["old_name"]: None for e in disk_entries}}}
    proc = await asyncio.create_subprocess_exec(
        kubectl, "patch", "nodes.longhorn.io", node_name,
        "-n", _LONGHORN_NS, "--type", "merge", "--patch", json.dumps(remove_patch),
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        logger.warning(f"Failed to remove old Longhorn disks from {node_name}")
        return

    # Brief pause for Longhorn to process the removal
    await asyncio.sleep(3)

    # Re-add each disk with a fresh name (timestamp suffix avoids UUID cache)
    ts = str(int(time.time()))[-6:]
    new_disks = {}
    for entry in disk_entries:
        new_name = f"{_disk_name_from_path(entry['path'])}-{ts}"
        new_disks[new_name] = {
            "path": entry["path"],
            "allowScheduling": entry["allowScheduling"],
            "diskType": "filesystem",
            "evictionRequested": False,
            "storageReserved": entry["storageReserved"],
            "tags": entry["tags"],
        }

    add_patch = {"spec": {"disks": new_disks}}
    proc = await asyncio.create_subprocess_exec(
        kubectl, "patch", "nodes.longhorn.io", node_name,
        "-n", _LONGHORN_NS, "--type", "merge", "--patch", json.dumps(add_patch),
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode == 0:
        logger.info(f"Longhorn disk reset completed for {node_name}: {len(disk_entries)} disk(s) re-added")
    else:
        err = (await proc.communicate())[1].decode().strip() if proc.returncode else ""
        logger.warning(f"Failed to re-add Longhorn disks on {node_name}: {err}")


async def _longhorn_nodes(params: dict, ws: WebSocket, req_id: str):
    """List all Longhorn nodes with disk configuration and status."""
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return await _ws._respond(ws, req_id, error="kubectl not found")
    kubeconfig = str(Path.home() / ".kube" / "config")

    proc = await asyncio.create_subprocess_exec(
        kubectl, "get", "nodes.longhorn.io", "-n", _LONGHORN_NS, "-o", "json",
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return await _ws._respond(ws, req_id, error=f"Failed to get Longhorn nodes: {stderr.decode().strip()}")

    try:
        data = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return await _ws._respond(ws, req_id, error="Failed to parse Longhorn nodes response")

    auto_config = _load_longhorn_auto_config()
    nodes = []
    for item in data.get("items", []):
        node_name = item["metadata"]["name"]
        spec = item.get("spec", {})
        spec_disks = spec.get("disks", {})
        status_disks = item.get("status", {}).get("diskStatus", {})

        disks = []
        for dk, dv in spec_disks.items():
            st = status_disks.get(dk, {})
            replicas = st.get("scheduledReplica", {})
            disks.append({
                "name": dk,
                "path": dv.get("path", ""),
                "allowScheduling": dv.get("allowScheduling", False),
                "diskType": dv.get("diskType", "filesystem"),
                "storageReserved": dv.get("storageReserved", 0),
                "evictionRequested": dv.get("evictionRequested", False),
                "tags": dv.get("tags", []),
                "storageMaximum": st.get("storageMaximum", 0),
                "storageAvailable": st.get("storageAvailable", 0),
                "storageScheduled": st.get("storageScheduled", 0),
                "replicaCount": len(replicas),
            })

        node_auto = auto_config.get(node_name, {})
        nodes.append({
            "name": node_name,
            "allowScheduling": spec.get("allowScheduling", True),
            "disks": disks,
            "conditions": item.get("status", {}).get("conditions", {}),
            "autoAddDisks": node_auto.get("auto_add_disks", False),
        })

    await _ws._respond(ws, req_id, nodes)


async def _longhorn_discover_disks(params: dict, ws: WebSocket, req_id: str):
    """Discover available block devices on a Talos node."""
    node_name = params.get("node_name")
    if not node_name:
        return await _ws._respond(ws, req_id, error="node_name required")

    ip = _resolve_node_ip(node_name)
    if not ip:
        return await _ws._respond(ws, req_id, error=f"Cannot resolve IP for node {node_name}")

    from app.api.cluster_router import find_talosctl, get_templates_base_dir
    talosctl = find_talosctl()
    talosconfig = str(get_templates_base_dir() / "talosconfig")

    # Get all block devices
    proc = await asyncio.create_subprocess_exec(
        talosctl, "get", "disks", "--nodes", ip, "--endpoints", ip,
        "--talosconfig", talosconfig, "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return await _ws._respond(ws, req_id, error=f"Failed to get disks: {stderr.decode().strip()}")

    # Parse newline-delimited JSON
    all_disks = []
    for line in stdout.decode().strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            spec = obj.get("spec", {})
            disk_id = obj.get("metadata", {}).get("id", "")
            # Skip loop, sr (cdrom), readonly, tiny disks
            if disk_id.startswith("loop") or disk_id.startswith("sr"):
                continue
            if spec.get("readonly"):
                continue
            if spec.get("size", 0) < 1_000_000_000:  # < 1GB
                continue
            all_disks.append({
                "id": disk_id,
                "dev_path": spec.get("dev_path", f"/dev/{disk_id}"),
                "size": spec.get("size", 0),
                "pretty_size": spec.get("pretty_size", ""),
                "model": spec.get("model", ""),
                "serial": spec.get("serial", ""),
                "transport": spec.get("transport", ""),
                "rotational": spec.get("rotational", False),
                "bus_path": spec.get("bus_path", ""),
            })
        except json.JSONDecodeError:
            continue

    # Get discovered volumes to identify the system disk
    proc2 = await asyncio.create_subprocess_exec(
        talosctl, "get", "discoveredvolumes", "--nodes", ip, "--endpoints", ip,
        "--talosconfig", talosconfig, "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=30)

    system_disk_ids = set()
    if proc2.returncode == 0:
        for line in stdout2.decode().strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                vol = json.loads(line)
                vol_spec = vol.get("spec", {})
                partition_label = vol_spec.get("partition_label", "") or ""
                vol_id = vol.get("metadata", {}).get("id", "")
                # System partitions: EPHEMERAL, BOOT, STATE, META, EFI, BIOS
                if partition_label in ("EPHEMERAL", "BOOT", "STATE", "META", "EFI", "BIOS"):
                    # The parent disk is the id without trailing digits (e.g., sda1 → sda)
                    parent = vol_id.rstrip("0123456789")
                    system_disk_ids.add(parent)
            except json.JSONDecodeError:
                continue

    # Get Longhorn disk paths to exclude already-registered disks
    kubectl = _ws._find_kubectl()
    kubeconfig = str(Path.home() / ".kube" / "config")
    longhorn_paths = set()
    if kubectl:
        proc3 = await asyncio.create_subprocess_exec(
            kubectl, "get", "nodes.longhorn.io", node_name, "-n", _LONGHORN_NS,
            "-o", "json", "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout3, _ = await asyncio.wait_for(proc3.communicate(), timeout=15)
        if proc3.returncode == 0:
            try:
                ln = json.loads(stdout3.decode())
                for dv in ln.get("spec", {}).get("disks", {}).values():
                    longhorn_paths.add(dv.get("path", ""))
            except json.JSONDecodeError:
                pass

    # Filter: exclude system disks and already-registered Longhorn disks
    available = []
    for d in all_disks:
        if d["id"] in system_disk_ids:
            d["is_system_disk"] = True
        else:
            d["is_system_disk"] = False
        d["in_longhorn"] = d["dev_path"] in longhorn_paths
        available.append(d)

    await _ws._respond(ws, req_id, available)


async def _longhorn_add_disk(params: dict, ws: WebSocket, req_id: str):
    """Add a disk to a Longhorn node via CRD patch."""
    node_name = params.get("node_name")
    disk_path = params.get("disk_path")
    if not node_name or not disk_path:
        return await _ws._respond(ws, req_id, error="node_name and disk_path required")

    disk_name = params.get("disk_name") or _disk_name_from_path(disk_path)
    allow_scheduling = params.get("allow_scheduling", True)

    kubectl = _ws._find_kubectl()
    if not kubectl:
        return await _ws._respond(ws, req_id, error="kubectl not found")
    kubeconfig = str(Path.home() / ".kube" / "config")

    patch = json.dumps({
        "spec": {
            "disks": {
                disk_name: {
                    "path": disk_path,
                    "allowScheduling": allow_scheduling,
                    "diskType": "filesystem",
                    "evictionRequested": False,
                    "storageReserved": 0,
                    "tags": [],
                }
            }
        }
    })

    proc = await asyncio.create_subprocess_exec(
        kubectl, "patch", "nodes.longhorn.io", node_name,
        "-n", _LONGHORN_NS, "--type", "merge", "--patch", patch,
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return await _ws._respond(ws, req_id, error=f"Failed to add disk: {stderr.decode().strip()}")

    await _ws._respond(ws, req_id, {"message": f"Disk '{disk_name}' added to {node_name} at {disk_path}"})
    await _ws._broadcast("longhorn_disk_changed", {"node": node_name, "action": "added", "disk": disk_name, "path": disk_path})


async def _longhorn_remove_disk(params: dict, ws: WebSocket, req_id: str):
    """Remove a disk from a Longhorn node. Disables scheduling first, then removes."""
    node_name = params.get("node_name")
    disk_name = params.get("disk_name")
    force = params.get("force", False)
    if not node_name or not disk_name:
        return await _ws._respond(ws, req_id, error="node_name and disk_name required")

    kubectl = _ws._find_kubectl()
    if not kubectl:
        return await _ws._respond(ws, req_id, error="kubectl not found")
    kubeconfig = str(Path.home() / ".kube" / "config")

    if not force:
        # Step 1: Disable scheduling and request eviction
        patch = json.dumps({
            "spec": {
                "disks": {
                    disk_name: {
                        "allowScheduling": False,
                        "evictionRequested": True,
                    }
                }
            }
        })
        proc = await asyncio.create_subprocess_exec(
            kubectl, "patch", "nodes.longhorn.io", node_name,
            "-n", _LONGHORN_NS, "--type", "merge", "--patch", patch,
            "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return await _ws._respond(ws, req_id, error=f"Failed to disable disk: {stderr.decode().strip()}")

        # Check if disk still has replicas
        proc2 = await asyncio.create_subprocess_exec(
            kubectl, "get", "nodes.longhorn.io", node_name, "-n", _LONGHORN_NS,
            "-o", "json", "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=15)
        if proc2.returncode == 0:
            try:
                ln = json.loads(stdout2.decode())
                replicas = ln.get("status", {}).get("diskStatus", {}).get(disk_name, {}).get("scheduledReplica", {})
                if replicas:
                    return await _ws._respond(ws, req_id, {
                        "message": f"Disk '{disk_name}' scheduling disabled and eviction requested. {len(replicas)} replica(s) still present — will be removed once evacuated.",
                        "evicting": True,
                        "replicaCount": len(replicas),
                    })
            except json.JSONDecodeError:
                pass

    # Step 2: Remove disk from spec using strategic merge patch with null
    # kubectl patch with --type=json to remove the key
    patch = json.dumps([{"op": "remove", "path": f"/spec/disks/{disk_name}"}])
    proc = await asyncio.create_subprocess_exec(
        kubectl, "patch", "nodes.longhorn.io", node_name,
        "-n", _LONGHORN_NS, "--type", "json", "--patch", patch,
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return await _ws._respond(ws, req_id, error=f"Failed to remove disk: {stderr.decode().strip()}")

    await _ws._respond(ws, req_id, {"message": f"Disk '{disk_name}' removed from {node_name}"})
    await _ws._broadcast("longhorn_disk_changed", {"node": node_name, "action": "removed", "disk": disk_name})


async def _longhorn_use_all_disks_for_node(node_name: str) -> tuple:
    """Internal: discover and add all available non-system disks to a Longhorn node.
    Returns (added_count, error_msg)."""
    ip = _resolve_node_ip(node_name)
    if not ip:
        return 0, f"Cannot resolve IP for {node_name}"

    from app.api.cluster_router import find_talosctl, get_templates_base_dir
    talosctl = find_talosctl()
    talosconfig = str(get_templates_base_dir() / "talosconfig")
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return 0, "kubectl not found"
    kubeconfig = str(Path.home() / ".kube" / "config")

    # Get all disks
    proc = await asyncio.create_subprocess_exec(
        talosctl, "get", "disks", "--nodes", ip, "--endpoints", ip,
        "--talosconfig", talosconfig, "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return 0, f"Failed to get disks: {stderr.decode().strip()}"

    all_disks = []
    for line in stdout.decode().strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            spec = obj.get("spec", {})
            disk_id = obj.get("metadata", {}).get("id", "")
            if disk_id.startswith("loop") or disk_id.startswith("sr"):
                continue
            if spec.get("readonly") or spec.get("size", 0) < 1_000_000_000:
                continue
            all_disks.append({"id": disk_id, "dev_path": spec.get("dev_path", f"/dev/{disk_id}"), "size": spec.get("size", 0)})
        except json.JSONDecodeError:
            continue

    # Get discovered volumes to find system disk
    proc2 = await asyncio.create_subprocess_exec(
        talosctl, "get", "discoveredvolumes", "--nodes", ip, "--endpoints", ip,
        "--talosconfig", talosconfig, "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=30)
    system_disk_ids = set()
    if proc2.returncode == 0:
        for line in stdout2.decode().strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                vol = json.loads(line)
                pl = vol.get("spec", {}).get("partition_label", "") or ""
                vid = vol.get("metadata", {}).get("id", "")
                if pl in ("EPHEMERAL", "BOOT", "STATE", "META", "EFI", "BIOS"):
                    system_disk_ids.add(vid.rstrip("0123456789"))
            except json.JSONDecodeError:
                continue

    # Get existing Longhorn disk paths
    longhorn_paths = set()
    proc3 = await asyncio.create_subprocess_exec(
        kubectl, "get", "nodes.longhorn.io", node_name, "-n", _LONGHORN_NS,
        "-o", "json", "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout3, _ = await asyncio.wait_for(proc3.communicate(), timeout=15)
    if proc3.returncode == 0:
        try:
            ln = json.loads(stdout3.decode())
            for dv in ln.get("spec", {}).get("disks", {}).values():
                longhorn_paths.add(dv.get("path", ""))
        except json.JSONDecodeError:
            pass

    # Find available disks (non-system, not already in Longhorn)
    available = [d for d in all_disks if d["id"] not in system_disk_ids and d["dev_path"] not in longhorn_paths]

    if not available:
        return 0, None  # No additional disks to add

    # Add each available disk to Longhorn
    # Note: These are raw block devices. Longhorn needs mounted paths.
    # For now, we add them as Longhorn "block" disks or assume they're pre-mounted.
    # The existing partition system via Talos config handles the mount.
    added = 0
    for d in available:
        disk_name = _disk_name_from_path(d["dev_path"])
        patch = json.dumps({
            "spec": {
                "disks": {
                    disk_name: {
                        "path": d["dev_path"],
                        "allowScheduling": True,
                        "diskType": "filesystem",
                        "evictionRequested": False,
                        "storageReserved": 0,
                        "tags": [],
                    }
                }
            }
        })
        proc = await asyncio.create_subprocess_exec(
            kubectl, "patch", "nodes.longhorn.io", node_name,
            "-n", _LONGHORN_NS, "--type", "merge", "--patch", patch,
            "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            added += 1

    return added, None


async def _longhorn_use_all_disks(params: dict, ws: WebSocket, req_id: str):
    """Discover and add all available non-system disks to a Longhorn node."""
    node_name = params.get("node_name")
    if not node_name:
        return await _ws._respond(ws, req_id, error="node_name required")

    added, err = await _longhorn_use_all_disks_for_node(node_name)
    if err:
        return await _ws._respond(ws, req_id, error=err)

    if added == 0:
        await _ws._respond(ws, req_id, {"message": f"No additional disks found on {node_name}", "added": 0})
    else:
        await _ws._respond(ws, req_id, {"message": f"Added {added} disk(s) to {node_name}", "added": added})
        await _ws._broadcast("longhorn_disk_changed", {"node": node_name, "action": "use_all", "added": added})


async def _longhorn_auto_config(params: dict, ws: WebSocket, req_id: str):
    """Get or set per-node Longhorn disk automation config."""
    node_name = params.get("node_name")
    auto_add = params.get("auto_add_disks")

    config = _load_longhorn_auto_config()

    if auto_add is not None:
        # SET mode
        if not node_name:
            return await _ws._respond(ws, req_id, error="node_name required for set")
        if auto_add:
            config[node_name] = {"auto_add_disks": True}
        else:
            config.pop(node_name, None)
        _save_longhorn_auto_config(config)
        await _ws._respond(ws, req_id, {"message": f"Auto-add {'enabled' if auto_add else 'disabled'} for {node_name}"})
    else:
        # GET mode
        if node_name:
            nc = config.get(node_name, {})
            await _ws._respond(ws, req_id, {"node_name": node_name, "auto_add_disks": nc.get("auto_add_disks", False)})
        else:
            await _ws._respond(ws, req_id, config)


# Export actions for ws_handler integration
LONGHORN_ACTIONS = {
    "longhorn.nodes": _longhorn_nodes,
    "longhorn.discover_disks": _longhorn_discover_disks,
    "longhorn.add_disk": _longhorn_add_disk,
    "longhorn.remove_disk": _longhorn_remove_disk,
    "longhorn.use_all_disks": _longhorn_use_all_disks,
    "longhorn.auto_config": _longhorn_auto_config,
}
