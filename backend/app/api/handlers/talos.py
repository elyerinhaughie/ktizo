"""Talos version and settings handlers."""
import json
import logging

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


async def _talos_get(params: dict, ws: WebSocket, req_id: str):
    """Get combined Talos settings from NetworkSettings + ClusterSettings."""
    db = _ws._db()
    try:
        from app.crud import network as network_crud, cluster as cluster_crud
        import json as _json

        ns = network_crud.get_network_settings(db)
        cs = cluster_crud.get_cluster_settings(db)

        talos_version = ""
        if ns:
            talos_version = ns.talos_version or ""
        elif cs:
            talos_version = cs.talos_version or ""

        system_extensions = []
        kernel_modules = []
        if cs:
            if cs.system_extensions:
                try:
                    system_extensions = _json.loads(cs.system_extensions)
                except Exception:
                    pass
            if cs.kernel_modules:
                try:
                    kernel_modules = _json.loads(cs.kernel_modules)
                except Exception:
                    pass

        await _ws._respond(ws, req_id, {
            "talos_version": talos_version,
            "system_extensions": system_extensions,
            "kernel_modules": kernel_modules,
            "install_image": cs.install_image if cs else "",
            "factory_schematic_id": cs.factory_schematic_id if cs else "",
        })
    finally:
        db.close()


async def _talos_update(params: dict, ws: WebSocket, req_id: str):
    """Update Talos settings across NetworkSettings + ClusterSettings, trigger downloads + regen."""
    db = _ws._db()
    try:
        from app.crud import network as network_crud, cluster as cluster_crud, device as device_crud
        from app.schemas.network import NetworkSettingsUpdate
        from app.schemas.cluster import ClusterSettingsUpdate
        from app.db.models import DeviceStatus
        from app.services.talos_downloader import talos_downloader
        from app.services.template_service import template_service
        from app.services.ipxe_generator import IPXEGenerator
        from app.services.config_generator import ConfigGenerator
        import json as _json

        talos_version = params.get("talos_version", "")
        system_extensions = params.get("system_extensions", [])
        kernel_modules = params.get("kernel_modules", [])

        errors = []

        # Update NetworkSettings.talos_version
        ns = network_crud.get_network_settings(db)
        if ns:
            old_version = ns.talos_version
            network_crud.update_network_settings(db, ns.id, NetworkSettingsUpdate(talos_version=talos_version))
            ns = network_crud.get_network_settings(db)

            # Download Talos files if version changed
            if talos_version and talos_version != old_version:
                try:
                    ok, dl_errs = talos_downloader.download_talos_files(talos_version)
                    if not ok:
                        errors.append(f"Talos download: {'; '.join(dl_errs)}")
                except Exception as e:
                    errors.append(f"Talos download: {e}")

            # Regen dnsmasq + boot.ipxe
            try:
                config_dict = {k: getattr(ns, k) for k in [
                    "interface", "server_ip", "dhcp_mode", "dhcp_network", "dhcp_netmask",
                    "dhcp_range_start", "dhcp_range_end", "dns_port", "dns_server",
                    "tftp_root", "tftp_secure", "ipxe_boot_script", "pxe_prompt",
                    "pxe_timeout", "enable_logging",
                ]}
                template_service.compile_dnsmasq_config(**config_dict)
                template_service.deploy_dnsmasq_config()
            except Exception as e:
                errors.append(f"dnsmasq: {e}")

            try:
                ig = IPXEGenerator(tftp_root=ns.tftp_root)
                approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
                cs_temp = cluster_crud.get_cluster_settings(db)
                install_disk = cs_temp.install_disk if cs_temp else "/dev/sda"
                ig.generate_boot_script(approved, ns.server_ip,
                                        talos_version=ns.talos_version,
                                        strict_mode=ns.strict_boot_mode,
                                        install_disk=install_disk)
            except Exception as e:
                errors.append(f"boot.ipxe: {e}")

        # Update ClusterSettings (extensions, modules, talos_version for talosctl)
        from app.services.factory_service import resolve_install_image, build_factory_installer_url
        from app.schemas.cluster import ClusterSettingsCreate
        install_image = ""
        factory_schematic_id = ""
        cs = cluster_crud.get_cluster_settings(db)

        # Resolve factory installer image
        old_extensions = []
        if cs and cs.system_extensions:
            try:
                old_extensions = _json.loads(cs.system_extensions)
            except Exception:
                pass
        extensions_changed = sorted(system_extensions) != sorted(old_extensions)

        if not extensions_changed and cs and cs.factory_schematic_id:
            # Extensions unchanged, just rebuild URL with new version
            install_image = build_factory_installer_url(cs.factory_schematic_id, talos_version)
            factory_schematic_id = cs.factory_schematic_id
        else:
            # Extensions changed or no cached schematic — call Factory API
            install_image, factory_err = await resolve_install_image(system_extensions, talos_version)
            if factory_err:
                errors.append(f"Factory API: {factory_err} (using fallback installer)")
            # Extract schematic_id from URL
            factory_schematic_id = None
            if install_image and "factory.talos.dev/installer/" in install_image:
                path_part = install_image.split("factory.talos.dev/installer/")[1]
                factory_schematic_id = path_part.split(":")[0] if ":" in path_part else path_part

        if cs:
            cluster_crud.update_cluster_settings(db, cs.id, ClusterSettingsUpdate(
                talos_version=talos_version,
                system_extensions=_json.dumps(system_extensions) if system_extensions else None,
                kernel_modules=_json.dumps(kernel_modules) if kernel_modules else None,
                install_image=install_image,
                factory_schematic_id=factory_schematic_id,
            ))
        else:
            cs = cluster_crud.create_cluster_settings(db, ClusterSettingsCreate(
                cluster_name="ktizo-cluster",
                talos_version=talos_version,
                system_extensions=_json.dumps(system_extensions) if system_extensions else None,
                kernel_modules=_json.dumps(kernel_modules) if kernel_modules else None,
                install_image=install_image,
                factory_schematic_id=factory_schematic_id,
            ))

        # Regenerate all device configs
        try:
            approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
            cg = ConfigGenerator()
            cg.regenerate_all_configs(approved)
        except Exception as e:
            errors.append(f"Config regen: {e}")

        if errors:
            return await _ws._respond(ws, req_id, error="Saved but errors: " + "; ".join(errors))

        await _ws.log_action(db, "updated_talos_settings", "Talos Settings",
            json.dumps({"talos_version": talos_version, "extensions": len(system_extensions), "modules": len(kernel_modules)}),
            "talos_settings", None)

        await _ws._respond(ws, req_id, {
            "message": "Talos settings saved and configs regenerated",
            "install_image": install_image or "",
            "factory_schematic_id": factory_schematic_id or "",
        })
        await _ws._broadcast("talos_updated", {})
    finally:
        db.close()


async def _versions_talos(params: dict, ws: WebSocket, req_id: str):
    from app.services.version_service import fetch_talos_versions
    versions = await fetch_talos_versions()
    await _ws._respond(ws, req_id, versions)


async def _versions_kubernetes(params: dict, ws: WebSocket, req_id: str):
    from app.services.version_service import fetch_kubernetes_versions
    versions = await fetch_kubernetes_versions()
    await _ws._respond(ws, req_id, versions)


TALOS_ACTIONS = {
    "talos.get": _talos_get,
    "talos.update": _talos_update,
    "versions.talos": _versions_talos,
    "versions.kubernetes": _versions_kubernetes,
}
