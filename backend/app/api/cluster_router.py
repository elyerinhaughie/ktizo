from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.cluster import (
    ClusterSettingsResponse,
    ClusterSettingsCreate,
    ClusterSettingsUpdate,
    GenerateSecretsRequest,
    GenerateSecretsResponse
)
from app.crud import cluster as cluster_crud
from app.core.config import ensure_v_prefix, strip_v_prefix
import subprocess
import tempfile
import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

def find_talosctl() -> str:
    """Find talosctl binary - check backend directory first, then PATH"""
    # Check if talosctl is in the backend directory (native installation)
    backend_dir = Path(__file__).parent.parent.parent
    talosctl_path = backend_dir / "talosctl"
    if talosctl_path.exists() and talosctl_path.is_file():
        return str(talosctl_path)
    
    # Check if talosctl is in PATH
    talosctl_in_path = shutil.which("talosctl")
    if talosctl_in_path:
        return talosctl_in_path
    
    # Not found
    raise FileNotFoundError(
        "talosctl not found. Please ensure talosctl is installed:\n"
        "1. Run ./install.sh (downloads talosctl to backend/ directory)\n"
        "2. Or install talosctl system-wide and ensure it's in PATH"
    )

def get_templates_base_dir() -> Path:
    """Get the base templates directory, using environment variable or config default"""
    from app.core.config import settings as app_settings
    templates_dir = os.getenv("TEMPLATES_DIR", app_settings.TEMPLATES_DIR)
    base_path = Path(templates_dir) / "base"
    if not base_path.is_absolute():
        # Resolve relative to backend/ directory (2 parents from api/cluster_router.py)
        base_path = (Path(__file__).parent.parent.parent / base_path).resolve()
    return base_path

@router.get("/settings", response_model=ClusterSettingsResponse)
async def get_cluster_settings(db: Session = Depends(get_db)):
    """Get current cluster settings"""
    settings = cluster_crud.get_cluster_settings(db)
    if not settings:
        raise HTTPException(status_code=404, detail="Cluster settings not found. Please create settings first.")
    return settings

@router.post("/settings", response_model=ClusterSettingsResponse)
async def create_cluster_settings(settings: ClusterSettingsCreate, db: Session = Depends(get_db)):
    """Create cluster settings and regenerate Talos base configs"""
    existing = cluster_crud.get_cluster_settings(db)
    if existing:
        raise HTTPException(status_code=400, detail="Cluster settings already exist. Use PUT to update.")

    created = cluster_crud.create_cluster_settings(db, settings)

    # Automatically regenerate base Talos configs if secrets exist
    try:
        await generate_cluster_config(db)
    except Exception as e:
        # Log but don't fail - configs can be generated later
        print(f"Warning: Could not auto-generate configs: {e}")

    return created

@router.put("/settings/{settings_id}", response_model=ClusterSettingsResponse)
async def update_cluster_settings(settings_id: int, settings: ClusterSettingsUpdate, db: Session = Depends(get_db)):
    """Update cluster settings and regenerate Talos base configs and device configs"""
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus
    from app.services.config_generator import ConfigGenerator
    from app.services.kubectl_downloader import KubectlDownloader

    updated = cluster_crud.update_cluster_settings(db, settings_id, settings)
    if not updated:
        raise HTTPException(status_code=404, detail="Cluster settings not found")

    # If kubectl_version was updated, download and set that version
    if settings.kubectl_version is not None:
        try:
            kubectl_downloader = KubectlDownloader()
            success, error = kubectl_downloader.set_kubectl_version(updated.kubectl_version)
            if not success:
                logger.warning(f"Failed to set kubectl version to {updated.kubectl_version}: {error}")
        except Exception as e:
            logger.warning(f"Error setting kubectl version: {e}")

    # Automatically regenerate base Talos configs after settings update
    try:
        await generate_cluster_config(db)

        # Regenerate all device-specific configs
        config_generator = ConfigGenerator()
        approved_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)
        regenerated_count = 0
        for device in approved_devices:
            if config_generator.generate_device_config(device):
                regenerated_count += 1

        print(f"Regenerated {regenerated_count} device configs after cluster settings update")
    except HTTPException as e:
        # Log but don't fail - configs can be generated later
        print(f"Warning: Could not auto-generate configs: {e.detail}")
    except Exception as e:
        # Log but don't fail - configs can be generated later
        import traceback
        print(f"Warning: Could not auto-generate configs: {e}")
        print(f"Full traceback: {traceback.format_exc()}")

    return updated

@router.post("/config/generate")
async def generate_cluster_config(db: Session = Depends(get_db)):
    """Generate full Talos cluster configuration using talosctl gen config"""
    try:
        # Get cluster settings
        settings = cluster_crud.get_cluster_settings(db)
        if not settings:
            raise HTTPException(status_code=404, detail="Cluster settings not found. Please configure cluster first.")

        # Output directory for base talos templates
        base_dir = get_templates_base_dir()
        base_dir.mkdir(parents=True, exist_ok=True)

        # Check if secrets already exist
        secrets_file = base_dir / "secrets.yaml"
        has_existing_secrets = secrets_file.exists()

        # Run talosctl gen config
        talosctl = find_talosctl()
        cmd = [
            talosctl, "gen", "config",
            settings.cluster_name,
            f"https://{settings.cluster_endpoint}:6443",
            "--output-dir", str(base_dir),
            "--kubernetes-version", strip_v_prefix(settings.kubernetes_version),
            "--force",  # Allow overwriting existing configs during regeneration
        ]

        # Use existing secrets if they exist (important for regeneration)
        if has_existing_secrets:
            cmd.extend(["--with-secrets", str(secrets_file)])

        # Add additional flags if configured
        if settings.install_disk:
            cmd.extend(["--install-disk", settings.install_disk])
        if settings.install_image:
            cmd.extend(["--install-image", settings.install_image])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"talosctl gen config failed with return code {result.returncode}")
            print(f"Command: {' '.join(cmd)}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate config: {result.stderr or result.stdout or 'Unknown error'}"
            )

        # Patch ALL Kubernetes component versions to ensure they match user-defined version
        import yaml
        k8s_version = ensure_v_prefix(settings.kubernetes_version)

        for config_file in ["controlplane.yaml", "worker.yaml"]:
            config_path = base_dir / config_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    docs = list(yaml.safe_load_all(f))
                if not docs:
                    continue
                config = docs[0]  # First document is the machine config

                # Patch machine-level kubelet version
                if 'machine' in config:
                    if 'kubelet' not in config['machine']:
                        config['machine']['kubelet'] = {}
                    config['machine']['kubelet']['image'] = f'ghcr.io/siderolabs/kubelet:{k8s_version}'

                # Patch cluster-level Kubernetes component images (controlplane only)
                if config_file == "controlplane.yaml" and 'cluster' in config:
                    if 'apiServer' not in config['cluster']:
                        config['cluster']['apiServer'] = {}
                    config['cluster']['apiServer']['image'] = f'registry.k8s.io/kube-apiserver:{k8s_version}'

                    if 'controllerManager' not in config['cluster']:
                        config['cluster']['controllerManager'] = {}
                    config['cluster']['controllerManager']['image'] = f'registry.k8s.io/kube-controller-manager:{k8s_version}'

                    if 'scheduler' not in config['cluster']:
                        config['cluster']['scheduler'] = {}
                    config['cluster']['scheduler']['image'] = f'registry.k8s.io/kube-scheduler:{k8s_version}'

                    if 'proxy' not in config['cluster']:
                        config['cluster']['proxy'] = {}
                    config['cluster']['proxy']['image'] = f'registry.k8s.io/kube-proxy:{k8s_version}'

                # Write back all documents (patched first + rest unchanged)
                docs[0] = config
                with open(config_path, 'w') as f:
                    for i, doc in enumerate(docs):
                        if i > 0:
                            f.write('---\n')
                        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

                print(f"Patched {config_file} with Kubernetes version {k8s_version}")

        # Read generated files from templates/base
        generated_files = {
            "controlplane": (base_dir / "controlplane.yaml").read_text() if (base_dir / "controlplane.yaml").exists() else None,
            "worker": (base_dir / "worker.yaml").read_text() if (base_dir / "worker.yaml").exists() else None,
            "talosconfig": (base_dir / "talosconfig").read_text() if (base_dir / "talosconfig").exists() else None,
        }

        # Save secrets to database if they exist
        secrets_file = base_dir / "secrets.yaml"
        if secrets_file.exists():
            secrets_content = secrets_file.read_text()
            cluster_crud.update_cluster_settings(
                db,
                settings.id,
                ClusterSettingsUpdate(secrets_file=secrets_content)
            )
            generated_files["secrets"] = secrets_content

        return {
            "message": "Cluster configuration generated successfully in templates/base/",
            "output_dir": str(base_dir),
            "files": generated_files,
            "command": " ".join(cmd)
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="talosctl command timed out")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="talosctl not found. Please ensure talosctl is installed in the container."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate config: {str(e)}")

@router.post("/secrets/generate", response_model=GenerateSecretsResponse)
async def generate_secrets(request: GenerateSecretsRequest, db: Session = Depends(get_db)):
    """Generate only Talos secrets using talosctl (standalone)"""
    try:
        # Output to templates/base
        base_dir = get_templates_base_dir()
        base_dir.mkdir(parents=True, exist_ok=True)
        secrets_file = base_dir / "secrets.yaml"

        # Run talosctl gen secrets (with --force to overwrite existing)
        talosctl = find_talosctl()
        result = subprocess.run(
            [talosctl, "gen", "secrets", "-o", str(secrets_file), "--force"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate secrets: {result.stderr}"
            )

        # Read the generated secrets
        secrets_content = secrets_file.read_text()

        # Update cluster settings with secrets if they exist
        cluster_settings = cluster_crud.get_cluster_settings(db)
        if cluster_settings:
            cluster_crud.update_cluster_settings(
                db,
                cluster_settings.id,
                ClusterSettingsUpdate(secrets_file=secrets_content)
            )

        return GenerateSecretsResponse(
            secrets=secrets_content,
            message=f"Secrets generated successfully and saved to {secrets_file}"
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="talosctl command timed out")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="talosctl not found. Please ensure talosctl is installed in the container."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate secrets: {str(e)}")

@router.post("/bootstrap")
async def bootstrap_cluster(db: Session = Depends(get_db)):
    """Bootstrap the Talos cluster using the first control plane node"""
    try:
        from app.crud import device as device_crud
        from app.db.models import DeviceStatus

        # Check if cluster settings exist
        settings = cluster_crud.get_cluster_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404,
                detail="Cluster settings not found. Please configure cluster settings first."
            )

        # Check if talosconfig exists
        base_dir = get_templates_base_dir()
        talosconfig_path = base_dir / "talosconfig"

        if not talosconfig_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Talosconfig not found. Please generate cluster configuration first."
            )

        # Get all approved control plane devices
        all_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)
        controlplane_devices = [d for d in all_devices if d.role == "controlplane"]

        if not controlplane_devices:
            raise HTTPException(
                status_code=400,
                detail="No approved control plane nodes found. Please approve at least one control plane node first."
            )

        # Use the first control plane node with a known IP for bootstrapping
        bootstrap_node = None
        for node in controlplane_devices:
            if node.ip_address:
                bootstrap_node = node
                break

        if not bootstrap_node:
            raise HTTPException(
                status_code=400,
                detail="No control plane node has an IP address assigned. Please set an IP for at least one control plane node."
            )

        bootstrap_ip = bootstrap_node.ip_address
        # Strip CIDR prefix if present (e.g., 10.0.128.10/16 -> 10.0.128.10)
        if '/' in bootstrap_ip:
            bootstrap_ip = bootstrap_ip.split('/')[0]

        # Run talosctl bootstrap — use the node's actual IP for both --nodes and --endpoints
        talosctl = find_talosctl()
        result = subprocess.run(
            [
                talosctl, "bootstrap",
                "--talosconfig", str(talosconfig_path),
                "--nodes", bootstrap_ip,
                "--endpoints", bootstrap_ip
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to bootstrap cluster: {result.stderr}"
            )

        return {
            "message": f"Cluster bootstrapped successfully using node {bootstrap_node.hostname or bootstrap_node.mac_address} ({bootstrap_ip})",
            "bootstrap_node": {
                "hostname": bootstrap_node.hostname,
                "mac_address": bootstrap_node.mac_address,
                "ip_address": bootstrap_ip
            },
            "output": result.stdout
        }

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Bootstrap command timed out. The cluster may still be initializing."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bootstrap cluster: {str(e)}")

@router.get("/kubeconfig")
async def download_kubeconfig(db: Session = Depends(get_db)):
    """Download the kubeconfig file by retrieving it from the Talos cluster"""
    try:
        # Check if cluster settings exist
        settings = cluster_crud.get_cluster_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404,
                detail="Cluster settings not found. Please configure cluster settings first."
            )

        # Check if talosconfig exists (needed to retrieve kubeconfig)
        base_dir = get_templates_base_dir()
        talosconfig_path = base_dir / "talosconfig"

        if not talosconfig_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Talosconfig not found. Please generate cluster configuration first."
            )

        # Create a temporary directory for the kubeconfig
        with tempfile.TemporaryDirectory() as tmp_dir:
            kubeconfig_path = Path(tmp_dir) / "kubeconfig"

            # Retrieve kubeconfig using the first controlplane node's actual IP
            from app.crud import device as device_crud
            from app.db.models import DeviceStatus, DeviceRole
            all_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)
            cp_nodes = [d for d in all_devices if d.role == DeviceRole.CONTROLPLANE and d.ip_address]
            if not cp_nodes:
                raise HTTPException(status_code=400, detail="No control plane nodes with IP addresses found.")
            cp_ip = cp_nodes[0].ip_address
            if '/' in cp_ip:
                cp_ip = cp_ip.split('/')[0]

            talosctl = find_talosctl()
            result = subprocess.run(
                [
                    talosctl, "kubeconfig",
                    "--talosconfig", str(talosconfig_path),
                    "--nodes", cp_ip,
                    str(kubeconfig_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Check if it's because cluster isn't bootstrapped yet
                if "connection refused" in result.stderr.lower() or "no such host" in result.stderr.lower():
                    raise HTTPException(
                        status_code=503,
                        detail="Cannot connect to cluster. Please ensure the cluster is bootstrapped and at least one control plane node is running."
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve kubeconfig: {result.stderr}"
                )

            # Read kubeconfig content before temp directory is deleted
            with open(kubeconfig_path, 'r') as f:
                kubeconfig_content = f.read()
            
            # Save to ~/.kube/config for terminal use
            kubeconfig_home = Path.home() / ".kube"
            kubeconfig_home.mkdir(mode=0o700, exist_ok=True)
            kubeconfig_home_path = kubeconfig_home / "config"
            
            # Write kubeconfig to home directory
            with open(kubeconfig_home_path, 'w') as f:
                f.write(kubeconfig_content)
            os.chmod(kubeconfig_home_path, 0o600)
            logger.info(f"Saved kubeconfig to {kubeconfig_home_path} for terminal use")
            
            # Return the file as a download
            from fastapi.responses import Response
            return Response(
                content=kubeconfig_content,
                media_type="application/x-yaml",
                headers={"Content-Disposition": "attachment; filename=kubeconfig.yaml"}
            )

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Request timed out while retrieving kubeconfig from cluster"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download kubeconfig: {str(e)}")
