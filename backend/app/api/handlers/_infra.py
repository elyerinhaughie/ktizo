"""Infrastructure helpers shared across handler modules.

These functions deal with filesystem operations (disk partitions),
kubectl/namespace management, and post-install hooks.
"""
import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from app.api.handlers._base import _db, logger

# Re-export _find_kubectl so handler modules can import it from here.
__all__ = [
    "_save_disk_partition",
    "_remove_disk_partition",
    "_regenerate_all_device_configs",
    "_label_namespace_privileged",
    "_run_post_install",
    "_post_install_metallb",
    "_find_kubectl",
    "_delete_namespace_resources",
]


def _save_disk_partition(mountpoint: str, disk: str = ""):
    """Save a disk partition config for Talos device config generation."""
    partitions_file = Path.home() / ".ktizo" / "data" / "disk_partitions.json"
    partitions_file.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if partitions_file.exists():
        try:
            existing = json.loads(partitions_file.read_text())
        except Exception:
            existing = []

    # Don't duplicate
    for p in existing:
        if p.get("mountpoint") == mountpoint:
            return

    existing.append({"mountpoint": mountpoint, "disk": disk})
    partitions_file.write_text(json.dumps(existing, indent=2))


def _remove_disk_partition(mountpoint: str):
    """Remove a disk partition config."""
    partitions_file = Path.home() / ".ktizo" / "data" / "disk_partitions.json"
    if not partitions_file.exists():
        return

    try:
        existing = json.loads(partitions_file.read_text())
        existing = [p for p in existing if p.get("mountpoint") != mountpoint]
        partitions_file.write_text(json.dumps(existing, indent=2))
    except Exception:
        pass


def _regenerate_all_device_configs(db):
    """Regenerate Talos configs for all approved devices."""
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus
    from app.services.config_generator import ConfigGenerator

    config_generator = ConfigGenerator()
    devices = device_crud.get_devices(db, skip=0, limit=1000)
    for device in devices:
        if device.status == DeviceStatus.APPROVED:
            config_generator.generate_device_config(device)
    logger.info(f"Regenerated configs for {sum(1 for d in devices if d.status == DeviceStatus.APPROVED)} approved devices")


def _find_kubectl() -> Optional[str]:
    """Find kubectl binary."""
    kubectl = shutil.which("kubectl")
    if not kubectl:
        kubectl_path = Path.home() / ".ktizo" / "bin" / "kubectl"
        if kubectl_path.exists():
            return str(kubectl_path)
        return None
    return kubectl


async def _label_namespace_privileged(namespace: str):
    """Label a namespace with privileged PodSecurity to allow hostPath/privileged containers."""
    kubectl = shutil.which("kubectl")
    if not kubectl:
        kubectl_path = Path.home() / ".ktizo" / "bin" / "kubectl"
        if kubectl_path.exists():
            kubectl = str(kubectl_path)
        else:
            logger.warning("kubectl not found, cannot label namespace")
            return

    kubeconfig = str(Path.home() / ".kube" / "config")

    # Create namespace first
    proc = await asyncio.create_subprocess_exec(
        kubectl, "create", "namespace", namespace,
        "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()  # ignore error if already exists

    proc = await asyncio.create_subprocess_exec(
        kubectl, "label", "namespace", namespace,
        "pod-security.kubernetes.io/enforce=privileged",
        "pod-security.kubernetes.io/audit=privileged",
        "pod-security.kubernetes.io/warn=privileged",
        "--overwrite", "--kubeconfig", kubeconfig,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        logger.info(f"Labeled namespace {namespace} as privileged")
    else:
        logger.warning(f"Failed to label namespace {namespace}: {stderr.decode().strip()}")


async def _run_post_install(params: dict) -> str:
    """Run post-install actions for catalog modules. Returns status message or empty string."""
    catalog_id = params.get("catalog_id")
    if not catalog_id:
        return ""

    wizard_vals = {}
    if params.get("values_json"):
        try:
            wizard_vals = json.loads(params["values_json"]) if isinstance(params["values_json"], str) else params["values_json"]
        except Exception:
            pass

    if catalog_id == "metallb":
        return await _post_install_metallb(params, wizard_vals)

    return ""


async def _post_install_metallb(params: dict, wizard_vals: dict) -> str:
    """Create MetalLB IPAddressPool and L2Advertisement after helm install."""
    address_pool = wizard_vals.get("_addressPool", "")
    if not address_pool:
        return "Warning: No address pool configured"

    namespace = params.get("namespace", "metallb-system")

    manifest = f"""apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: {namespace}
spec:
  addresses:
    - {address_pool}
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default-l2
  namespace: {namespace}
spec:
  ipAddressPools:
    - default-pool
"""

    kubectl = shutil.which("kubectl")
    if not kubectl:
        kubectl_path = Path.home() / ".ktizo" / "bin" / "kubectl"
        if kubectl_path.exists():
            kubectl = str(kubectl_path)
        else:
            return "Warning: kubectl not found, could not create IPAddressPool"

    kubeconfig = str(Path.home() / ".kube" / "config")

    # Wait for MetalLB CRDs to be available
    for attempt in range(15):
        proc = await asyncio.create_subprocess_exec(
            kubectl, "get", "crd", "ipaddresspools.metallb.io",
            "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode == 0:
            break
        await asyncio.sleep(2)
    else:
        return "Warning: MetalLB CRDs not ready after 30s, IPAddressPool not created"

    # Apply the manifest
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(manifest)
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            kubectl, "apply", "-f", tmp_path,
            "--kubeconfig", kubeconfig,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode == 0:
            logger.info(f"MetalLB: Created IPAddressPool ({address_pool}) and L2Advertisement")
            return f"IPAddressPool ({address_pool}) and L2Advertisement created"
        else:
            err = stderr.decode().strip()
            logger.warning(f"MetalLB post-install failed: {err}")
            return f"Warning: Failed to create IPAddressPool: {err}"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _delete_namespace_resources(namespace: str):
    """Delete all resources in a namespace, then delete the namespace itself."""
    kubectl = _find_kubectl()
    if not kubectl:
        logger.warning("kubectl not found, cannot clean up namespace resources")
        return
    kubeconfig = str(Path.home() / ".kube" / "config")

    # Delete all resources in the namespace
    proc = await asyncio.create_subprocess_exec(
        kubectl, "delete", "all", "--all", "--namespace", namespace,
        "--kubeconfig", kubeconfig, "--timeout=60s",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    if proc.returncode == 0:
        logger.info(f"Deleted all resources in namespace {namespace}")
    else:
        logger.warning(f"Error deleting resources in {namespace}: {stderr.decode().strip()}")

    # Also clean up PVCs, configmaps, secrets, serviceaccounts (not covered by "all")
    for resource_type in ["pvc", "configmap", "secret", "serviceaccount"]:
        proc = await asyncio.create_subprocess_exec(
            kubectl, "delete", resource_type, "--all", "--namespace", namespace,
            "--kubeconfig", kubeconfig, "--timeout=30s",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=45)

    # Delete the namespace itself
    proc = await asyncio.create_subprocess_exec(
        kubectl, "delete", "namespace", namespace,
        "--kubeconfig", kubeconfig, "--timeout=60s",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    if proc.returncode == 0:
        logger.info(f"Deleted namespace {namespace}")
    else:
        logger.warning(f"Error deleting namespace {namespace}: {stderr.decode().strip()}")
