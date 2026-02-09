"""Network handler functions for WebSocket actions."""
import json
import logging

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


async def _network_detect(params: dict, ws: WebSocket, req_id: str):
    """Auto-detect network configuration from a given interface."""
    import asyncio, ipaddress, re
    interface = params.get("interface", "").strip()
    if not interface:
        return await _ws._respond(ws, req_id, error="Interface name is required")

    result = {}

    # Get IP address and netmask — parse text output (works with BusyBox ip)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "addr", "show", interface,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode != 0:
            return await _ws._respond(ws, req_id, error=f"Interface '{interface}' not found")

        output = stdout.decode()
        # Match "inet 10.0.42.2/16" pattern
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", output)
        if m:
            ip = m.group(1)
            prefix = int(m.group(2))
            network = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
            result["server_ip"] = ip
            result["dhcp_network"] = str(network.network_address)
            result["dhcp_netmask"] = str(network.netmask)

        if "server_ip" not in result:
            return await _ws._respond(ws, req_id, error=f"No IPv4 address found on '{interface}'")
    except asyncio.TimeoutError:
        return await _ws._respond(ws, req_id, error="Timed out reading interface info")
    except Exception as e:
        return await _ws._respond(ws, req_id, error=f"Failed to read interface: {e}")

    # Get default gateway — parse text output
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "route", "show", "default",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode == 0:
            output = stdout.decode()
            # Match "default via 10.0.0.1 dev eth0"
            for line in output.strip().splitlines():
                parts = line.split()
                if "via" in parts and "dev" in parts:
                    gw = parts[parts.index("via") + 1]
                    dev = parts[parts.index("dev") + 1]
                    if dev == interface:
                        result["gateway"] = gw
                        break
                    elif "gateway" not in result:
                        result["gateway"] = gw
    except Exception:
        pass

    # Get DNS server from /etc/resolv.conf
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    dns = line.split()[1]
                    if not dns.startswith("127."):
                        result["dns_server"] = dns
                        break
    except Exception:
        pass

    if "dns_server" not in result and "gateway" in result:
        result["dns_server"] = result["gateway"]

    result["interface"] = interface
    await _ws._respond(ws, req_id, result)


async def _network_interfaces(params: dict, ws: WebSocket, req_id: str):
    """List available network interfaces."""
    import asyncio, re
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "link", "show",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode != 0:
            return await _ws._respond(ws, req_id, error="Failed to list interfaces")

        output = stdout.decode()
        interfaces = []
        # Parse lines like: "2: eth0@if48: <BROADCAST,...,UP,...> ... state UP ..."
        for m in re.finditer(r"^\d+:\s+(\S+?)(?:@\S+)?:\s+<([^>]*)>.*?state\s+(\S+)", output, re.MULTILINE):
            name = m.group(1)
            state = m.group(3)
            if name == "lo" or name.startswith("veth") or name.startswith("docker") or name.startswith("br-"):
                continue
            interfaces.append({"name": name, "state": state})
        await _ws._respond(ws, req_id, interfaces)
    except Exception as e:
        await _ws._respond(ws, req_id, error=f"Failed to list interfaces: {e}")




async def _network_get(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import network as crud
        settings = crud.get_network_settings(db)
        if not settings:
            return await _ws._respond(ws, req_id, error="Network settings not found")
        await _ws._respond(ws, req_id, settings)
    finally:
        db.close()


async def _network_create(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import network as crud
        from app.schemas.network import NetworkSettingsCreate
        existing = crud.get_network_settings(db)
        if existing:
            return await _ws._respond(ws, req_id, error="Network settings already exist. Use network.update.")
        created = crud.create_network_settings(db, NetworkSettingsCreate(**params))
        await _ws._respond(ws, req_id, created)
        await _ws._broadcast("network_updated", created)
    finally:
        db.close()


async def _network_update(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import network as network_crud, device as device_crud, cluster as cluster_crud
        from app.db.models import DeviceStatus
        from app.schemas.network import NetworkSettingsUpdate
        from app.services.template_service import template_service
        from app.services.talos_downloader import talos_downloader
        from app.services.ipxe_generator import IPXEGenerator

        settings_id = params.pop("settings_id")
        current = network_crud.get_network_settings(db)
        old_version = current.talos_version if current else None

        updated = network_crud.update_network_settings(db, settings_id, NetworkSettingsUpdate(**params))
        if not updated:
            return await _ws._respond(ws, req_id, error="Network settings not found")

        errors = []

        # Talos files
        v = updated.talos_version
        if v:
            try:
                vm_exists = talos_downloader.file_exists(v, "vmlinuz-amd64")
                ir_exists = talos_downloader.file_exists(v, "initramfs-amd64.xz")
                if v != old_version or not vm_exists or not ir_exists:
                    ok, dl_errs = talos_downloader.download_talos_files(v)
                    if not ok:
                        errors.append(f"Talos download: {'; '.join(dl_errs)}")
            except Exception as e:
                errors.append(f"Talos download: {e}")

        # dnsmasq
        try:
            config_dict = {k: getattr(updated, k) for k in [
                "interface", "server_ip", "dhcp_mode", "dhcp_network", "dhcp_netmask",
                "dhcp_range_start", "dhcp_range_end", "dns_port", "dns_server",
                "tftp_root", "tftp_secure", "ipxe_boot_script", "pxe_prompt",
                "pxe_timeout", "enable_logging",
            ]}
            template_service.compile_dnsmasq_config(**config_dict)
            if not template_service.deploy_dnsmasq_config():
                errors.append("Failed to deploy dnsmasq config")
        except Exception as e:
            errors.append(f"dnsmasq config: {e}")

        # boot.ipxe
        try:
            ig = IPXEGenerator(tftp_root=updated.tftp_root)
            approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
            cs = cluster_crud.get_cluster_settings(db)
            install_disk = cs.install_disk if cs else "/dev/sda"
            ig.generate_boot_script(approved, updated.server_ip,
                                    talos_version=updated.talos_version,
                                    strict_mode=updated.strict_boot_mode,
                                    install_disk=install_disk)
        except Exception as e:
            errors.append(f"boot.ipxe: {e}")

        if errors:
            return await _ws._respond(ws, req_id, error="Settings saved but apply errors: " + "; ".join(errors))

        await _ws.log_action(db, "updated_network_settings", "Network Settings",
            json.dumps({"server_ip": updated.server_ip, "dhcp_mode": updated.dhcp_mode}),
            "network_settings", str(settings_id))

        await _ws._respond(ws, req_id, updated)
        await _ws._broadcast("network_updated", updated)
    finally:
        db.close()


async def _network_apply(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import network as network_crud, device as device_crud, cluster as cluster_crud
        from app.db.models import DeviceStatus
        from app.services.template_service import template_service
        from app.services.ipxe_generator import IPXEGenerator

        settings = network_crud.get_network_settings(db)
        if not settings:
            return await _ws._respond(ws, req_id, error="Network settings not found")

        errors = []
        config_dict = {k: getattr(settings, k) for k in [
            "interface", "server_ip", "dhcp_mode", "dhcp_network", "dhcp_netmask",
            "dhcp_range_start", "dhcp_range_end", "dns_port", "dns_server",
            "tftp_root", "tftp_secure", "ipxe_boot_script", "pxe_prompt",
            "pxe_timeout", "enable_logging",
        ]}
        try:
            _, output_path = template_service.compile_dnsmasq_config(**config_dict)
            if not template_service.deploy_dnsmasq_config():
                errors.append("Failed to deploy dnsmasq config")
        except Exception as e:
            errors.append(f"dnsmasq: {e}")
            output_path = None

        try:
            ig = IPXEGenerator(tftp_root=settings.tftp_root)
            approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
            cs = cluster_crud.get_cluster_settings(db)
            install_disk = cs.install_disk if cs else "/dev/sda"
            ig.generate_boot_script(approved, settings.server_ip,
                                    talos_version=settings.talos_version,
                                    strict_mode=settings.strict_boot_mode,
                                    install_disk=install_disk)
        except Exception as e:
            errors.append(f"boot.ipxe: {e}")

        if errors:
            return await _ws._respond(ws, req_id, error="; ".join(errors))

        await _ws.log_action(db, "applied_network_settings", "Network Settings",
            json.dumps({"output_path": output_path}), "network_settings", None)

        await _ws._respond(ws, req_id, {"message": "Network settings applied successfully", "path": output_path})
        await _ws._broadcast("network_applied", {})
    finally:
        db.close()


NETWORK_ACTIONS = {
    "network.detect": _network_detect,
    "network.interfaces": _network_interfaces,
    "network.get": _network_get,
    "network.create": _network_create,
    "network.update": _network_update,
    "network.apply": _network_apply,
}
