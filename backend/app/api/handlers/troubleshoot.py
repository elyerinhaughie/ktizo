"""Troubleshooting action handlers for WebSocket API."""
import logging
from typing import Optional

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# troubleshooting
# ---------------------------------------------------------------------------

async def _troubleshoot_fix_kubeconfig(params: dict, ws: WebSocket, req_id: str):
    """Ensure talosconfig + kubeconfig are set up on the local machine."""
    from app.api.terminal_router import _ensure_talosconfig, _ensure_kubeconfig
    results = {}
    results["talosconfig"] = _ensure_talosconfig()
    results["kubeconfig"] = _ensure_kubeconfig()
    if results["kubeconfig"]:
        await _ws._respond(ws, req_id, {"message": "Kubeconfig is ready at ~/.kube/config", **results})
    else:
        await _ws._respond(ws, req_id, error="Could not fetch kubeconfig. Is the cluster running and bootstrapped?")


async def _troubleshoot_fix_talosconfig(params: dict, ws: WebSocket, req_id: str):
    """Copy talosconfig to ~/.talos/config with correct endpoints."""
    from app.api.terminal_router import _ensure_talosconfig
    ok = _ensure_talosconfig()
    if ok:
        await _ws._respond(ws, req_id, {"message": "Talosconfig is ready at ~/.talos/config"})
    else:
        await _ws._respond(ws, req_id, error="Could not set up talosconfig. Has the cluster config been generated?")


async def _troubleshoot_regen_configs(params: dict, ws: WebSocket, req_id: str):
    """Regenerate all device configs and boot.ipxe."""
    db = _ws._db()
    try:
        from app.crud import device as device_crud, network as network_crud, cluster as cluster_crud
        from app.db.models import DeviceStatus
        from app.services.config_generator import ConfigGenerator
        from app.services.ipxe_generator import IPXEGenerator

        approved = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000)
        cg = ConfigGenerator()
        count = cg.regenerate_all_configs(approved)

        # Also regenerate boot.ipxe
        ns = network_crud.get_network_settings(db)
        boot_ok = False
        if ns:
            try:
                cs = cluster_crud.get_cluster_settings(db)
                ig = IPXEGenerator(tftp_root=ns.tftp_root)
                ig.generate_boot_script(approved, ns.server_ip,
                                        talos_version=ns.talos_version,
                                        strict_mode=ns.strict_boot_mode,
                                        install_disk=cs.install_disk if cs else "/dev/sda")
                boot_ok = True
            except Exception as e:
                logger.warning(f"boot.ipxe regen: {e}")

        await _ws._respond(ws, req_id, {
            "message": f"Regenerated {count} device config(s)" + (" and boot.ipxe" if boot_ok else ""),
            "configs_regenerated": count,
            "boot_ipxe": boot_ok,
        })
    finally:
        db.close()


async def _troubleshoot_regen_dnsmasq(params: dict, ws: WebSocket, req_id: str):
    """Recompile and deploy dnsmasq config."""
    db = _ws._db()
    try:
        from app.crud import network as network_crud
        from app.services.template_service import template_service

        ns = network_crud.get_network_settings(db)
        if not ns:
            return await _ws._respond(ws, req_id, error="No network settings configured")

        config_dict = {k: getattr(ns, k) for k in [
            "interface", "server_ip", "dhcp_mode", "dhcp_network", "dhcp_netmask",
            "dhcp_range_start", "dhcp_range_end", "dns_port", "dns_server",
            "tftp_root", "tftp_secure", "ipxe_boot_script", "pxe_prompt",
            "pxe_timeout", "enable_logging",
        ]}
        template_service.compile_dnsmasq_config(**config_dict)
        deployed = template_service.deploy_dnsmasq_config()

        await _ws._respond(ws, req_id, {
            "message": "dnsmasq config regenerated" + (" and deployed" if deployed else " (deploy to /etc manually)"),
            "deployed": deployed,
        })
    finally:
        db.close()


async def _troubleshoot_restart_dnsmasq(params: dict, ws: WebSocket, req_id: str):
    """Restart dnsmasq service."""
    import subprocess as _sp
    try:
        # Try OpenRC first (Alpine), then systemd
        for cmd in [
            ["rc-service", "dnsmasq", "restart"],
            ["systemctl", "restart", "dnsmasq"],
        ]:
            try:
                r = _sp.run(cmd, capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    return await _ws._respond(ws, req_id, {"message": f"dnsmasq restarted ({' '.join(cmd)})"})
            except FileNotFoundError:
                continue
        # Fallback: pkill + start
        _sp.run(["pkill", "-x", "dnsmasq"], capture_output=True, timeout=5)
        r = _sp.run(["dnsmasq", "-C", "/etc/dnsmasq.conf"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return await _ws._respond(ws, req_id, {"message": "dnsmasq restarted (direct)"})
        await _ws._respond(ws, req_id, error=f"Failed to restart dnsmasq: {r.stderr}")
    except Exception as e:
        await _ws._respond(ws, req_id, error=f"Failed to restart dnsmasq: {e}")


async def _troubleshoot_download_talosctl(params: dict, ws: WebSocket, req_id: str):
    """Download/reinstall talosctl for the configured Talos version."""
    db = _ws._db()
    try:
        from app.crud import cluster as cluster_crud
        from app.services.talosctl_downloader import TalosctlDownloader

        cs = cluster_crud.get_cluster_settings(db)
        version = params.get("version") or (cs.talos_version if cs else None)
        if not version:
            return await _ws._respond(ws, req_id, error="No Talos version configured")

        dl = TalosctlDownloader()
        ok, err = dl.set_talosctl_version(version)
        if ok:
            await _ws._respond(ws, req_id, {"message": f"talosctl {version} installed"})
        else:
            await _ws._respond(ws, req_id, error=f"Failed to install talosctl: {err}")
    finally:
        db.close()


async def _troubleshoot_download_kubectl(params: dict, ws: WebSocket, req_id: str):
    """Download/reinstall kubectl for the configured Kubernetes version."""
    db = _ws._db()
    try:
        from app.crud import cluster as cluster_crud
        from app.services.kubectl_downloader import KubectlDownloader

        cs = cluster_crud.get_cluster_settings(db)
        version = params.get("version") or (cs.kubernetes_version if cs else None)
        if not version:
            return await _ws._respond(ws, req_id, error="No Kubernetes version configured")

        dl = KubectlDownloader()
        ok, err = dl.set_kubectl_version(version)
        if ok:
            await _ws._respond(ws, req_id, {"message": f"kubectl {version} installed"})
        else:
            await _ws._respond(ws, req_id, error=f"Failed to install kubectl: {err}")
    finally:
        db.close()


async def _troubleshoot_download_talos_files(params: dict, ws: WebSocket, req_id: str):
    """Download Talos PXE boot files (vmlinuz + initramfs) for the configured version."""
    db = _ws._db()
    try:
        from app.crud import network as network_crud
        from app.services.talos_downloader import talos_downloader

        ns = network_crud.get_network_settings(db)
        version = params.get("version") or (ns.talos_version if ns else None)
        if not version:
            return await _ws._respond(ws, req_id, error="No Talos version configured")

        ok, errs = talos_downloader.download_talos_files(version)
        if ok:
            await _ws._respond(ws, req_id, {"message": f"Talos PXE files for {version} downloaded"})
        else:
            await _ws._respond(ws, req_id, error=f"Download errors: {'; '.join(errs)}")
    finally:
        db.close()


async def _troubleshoot_reinstall_cni(params: dict, ws: WebSocket, req_id: str):
    """Reinstall the configured CNI plugin via helm upgrade --install."""
    db = _ws._db()
    try:
        from app.crud import cluster as cluster_crud, device as device_crud
        from app.api.cluster_router import _deploy_cni
        from app.db.models import DeviceRole

        cs = cluster_crud.get_cluster_settings(db)
        if not cs:
            return await _ws._respond(ws, req_id, error="No cluster settings configured")

        cni = (cs.cni or "flannel").lower()
        if cni == "flannel":
            return await _ws._respond(ws, req_id, error="Flannel is built into Talos — no helm install needed")

        # Resolve control plane IP (needed for Cilium's k8sServiceHost)
        cp_ip = ""
        try:
            devices = device_crud.get_devices(db, 0, 1000)
            for d in devices:
                if d.role == DeviceRole.CONTROLPLANE and d.ip_address:
                    cp_ip = d.ip_address
                    break
        except Exception:
            pass

        ok = _deploy_cni(cni, api_server_ip=cp_ip, upgrade=True)
        if ok:
            await _ws._respond(ws, req_id, {"message": f"{cni.title()} CNI reinstalled successfully"})
        else:
            await _ws._respond(ws, req_id, error=f"Failed to install {cni.title()} CNI. Check backend logs for details.")
    finally:
        db.close()


async def _troubleshoot_check_status(params: dict, ws: WebSocket, req_id: str):
    """Gather system status: binaries, configs, services."""
    from pathlib import Path
    import subprocess as _sp
    import shutil

    home = Path.home()
    status = {}

    # Kubeconfig
    kc = home / ".kube" / "config"
    status["kubeconfig"] = {"exists": kc.exists(), "path": str(kc)}

    # Talosconfig
    tc = home / ".talos" / "config"
    status["talosconfig"] = {"exists": tc.exists(), "path": str(tc)}

    # talosctl
    try:
        from app.api.cluster_router import find_talosctl
        path = find_talosctl()
        r = _sp.run([path, "version", "--client"], capture_output=True, text=True, timeout=5)
        status["talosctl"] = {"installed": True, "path": path, "version": r.stdout.strip().split("\n")[0] if r.returncode == 0 else "unknown"}
    except FileNotFoundError:
        status["talosctl"] = {"installed": False}

    # kubectl
    kubectl = shutil.which("kubectl")
    if not kubectl:
        try:
            from app.services.kubectl_downloader import KubectlDownloader
            kubectl = str(KubectlDownloader.get_kubectl_path())
            if not Path(kubectl).exists():
                kubectl = None
        except Exception:
            pass
    if kubectl:
        r = _sp.run([kubectl, "version", "--client", "--short"], capture_output=True, text=True, timeout=5)
        status["kubectl"] = {"installed": True, "path": kubectl, "version": r.stdout.strip() if r.returncode == 0 else "unknown"}
    else:
        status["kubectl"] = {"installed": False}

    # dnsmasq
    try:
        r = _sp.run(["pgrep", "-x", "dnsmasq"], capture_output=True, timeout=3)
        status["dnsmasq"] = {"running": r.returncode == 0}
    except Exception:
        status["dnsmasq"] = {"running": False}

    # Templates
    from app.api.cluster_router import get_templates_base_dir
    base = get_templates_base_dir()
    status["templates"] = {
        "secrets": (base / "secrets.yaml").exists(),
        "talosconfig": (base / "talosconfig").exists(),
        "controlplane": (base / "controlplane.yaml").exists(),
        "worker": (base / "worker.yaml").exists(),
    }

    # Database device counts
    db = _ws._db()
    try:
        from app.crud import device as device_crud
        from app.db.models import DeviceStatus
        all_devs = device_crud.get_devices(db, 0, 1000)
        status["devices"] = {
            "total": len(all_devs),
            "approved": len([d for d in all_devs if d.status == DeviceStatus.APPROVED]),
            "pending": len([d for d in all_devs if d.status == DeviceStatus.PENDING]),
        }
    finally:
        db.close()

    await _ws._respond(ws, req_id, status)


# ---------------------------------------------------------------------------
# Export action mapping
# ---------------------------------------------------------------------------

TROUBLESHOOT_ACTIONS = {
    "troubleshoot.status": _troubleshoot_check_status,
    "troubleshoot.fix_kubeconfig": _troubleshoot_fix_kubeconfig,
    "troubleshoot.fix_talosconfig": _troubleshoot_fix_talosconfig,
    "troubleshoot.regen_configs": _troubleshoot_regen_configs,
    "troubleshoot.regen_dnsmasq": _troubleshoot_regen_dnsmasq,
    "troubleshoot.restart_dnsmasq": _troubleshoot_restart_dnsmasq,
    "troubleshoot.download_talosctl": _troubleshoot_download_talosctl,
    "troubleshoot.download_kubectl": _troubleshoot_download_kubectl,
    "troubleshoot.download_talos_files": _troubleshoot_download_talos_files,
    "troubleshoot.reinstall_cni": _troubleshoot_reinstall_cni,
}
