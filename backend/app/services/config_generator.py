"""Service for generating static Talos configuration files"""
from pathlib import Path
import json
import yaml
import logging
import os
from typing import Optional, Tuple, List, Dict, Any
from app.db.models import Device, DeviceRole, VolumeConfig
from app.crud import cluster as cluster_crud
from app.crud import volume as volume_crud
from app.db.database import SessionLocal
from app.core.config import settings, ensure_v_prefix

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self):
        # Use environment variables if set, otherwise use config defaults, otherwise Docker paths
        templates_dir = os.getenv("TEMPLATES_DIR", settings.TEMPLATES_DIR)
        compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
        
        base_path = Path(templates_dir) / "base"
        if not base_path.is_absolute():
            # Resolve relative to backend/ directory (3 parents from services/config_generator.py)
            base_path = (Path(__file__).parent.parent.parent / base_path).resolve()

        output_path = Path(compiled_dir) / "talos" / "configs"
        if not output_path.is_absolute():
            output_path = (Path(__file__).parent.parent.parent / output_path).resolve()
        
        # Fallback to Docker paths if environment not set and relative path doesn't exist
        if not base_path.exists() and not os.getenv("TEMPLATES_DIR"):
            base_path = Path("/templates") / "base"
        if not output_path.exists() and not os.getenv("COMPILED_DIR"):
            output_path = Path("/compiled") / "talos" / "configs"
        
        self.base_dir = base_path
        self.output_dir = output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_volume_configs(self, db, device=None) -> List[Dict[str, Any]]:
        """
        Generate VolumeConfig documents for system volumes.

        If a device is provided and has per-device EPHEMERAL overrides, those are
        used instead of the global EPHEMERAL VolumeConfig from the database.

        Returns:
            List of VolumeConfig dictionaries ready to be serialized to YAML
        """
        volume_configs = []

        # Check if device has per-device EPHEMERAL overrides
        device_has_ephemeral = device and (
            device.ephemeral_max_size or device.ephemeral_min_size or device.ephemeral_disk_selector
        )

        # Get all configured volumes from database
        volumes = volume_crud.get_volume_configs(db)

        for volume in volumes:
            # Skip global EPHEMERAL if device has per-device overrides
            if device_has_ephemeral and volume.name.value == "EPHEMERAL":
                continue

            # Only generate VolumeConfig if size limits are configured
            if volume.max_size or volume.min_size or volume.disk_selector_match:
                vol_config = {
                    'apiVersion': 'v1alpha1',
                    'kind': 'VolumeConfig',
                    'name': volume.name.value  # Convert enum to string (EPHEMERAL or IMAGE-CACHE)
                }

                # Build provisioning section
                provisioning = {}

                # Add disk selector if configured
                if volume.disk_selector_match:
                    provisioning['diskSelector'] = {
                        'match': volume.disk_selector_match
                    }

                # Add size constraints if configured
                if volume.min_size:
                    provisioning['minSize'] = volume.min_size

                if volume.max_size:
                    provisioning['maxSize'] = volume.max_size

                # Set grow behavior
                # If maxSize is set, we typically don't want auto-grow
                # But respect the database setting
                if volume.max_size and not volume.grow:
                    provisioning['grow'] = False
                elif volume.grow and not volume.max_size:
                    # Only explicitly set grow if true and no maxSize
                    provisioning['grow'] = True

                # Only add provisioning section if it has content
                if provisioning:
                    vol_config['provisioning'] = provisioning
                    volume_configs.append(vol_config)
                    logger.info(f"Generated VolumeConfig for {volume.name.value}")

        # Add per-device EPHEMERAL VolumeConfig if device has overrides
        if device_has_ephemeral:
            vol_config = {
                'apiVersion': 'v1alpha1',
                'kind': 'VolumeConfig',
                'name': 'EPHEMERAL'
            }
            provisioning = {}
            if device.ephemeral_disk_selector:
                provisioning['diskSelector'] = {'match': device.ephemeral_disk_selector}
            if device.ephemeral_min_size:
                provisioning['minSize'] = device.ephemeral_min_size
            if device.ephemeral_max_size:
                provisioning['maxSize'] = device.ephemeral_max_size
                provisioning['grow'] = False
            if provisioning:
                vol_config['provisioning'] = provisioning
                volume_configs.append(vol_config)
                logger.info(f"Generated per-device EPHEMERAL VolumeConfig for {device.mac_address}")

        return volume_configs

    def _get_kubernetes_version(self) -> Optional[str]:
        """Get Kubernetes version from cluster settings"""
        db = SessionLocal()
        try:
            settings = cluster_crud.get_cluster_settings(db)
            return settings.kubernetes_version if settings else None
        finally:
            db.close()

    def _get_cni(self) -> Optional[str]:
        """Get CNI plugin name from cluster settings"""
        db = SessionLocal()
        try:
            settings = cluster_crud.get_cluster_settings(db)
            return settings.cni if settings else None
        finally:
            db.close()

    def _get_system_extensions(self) -> List[str]:
        """Get system extension images from cluster settings"""
        import json
        db = SessionLocal()
        try:
            cs = cluster_crud.get_cluster_settings(db)
            if cs and cs.system_extensions:
                return json.loads(cs.system_extensions)
            return []
        except Exception:
            return []
        finally:
            db.close()

    def _get_install_image(self) -> Optional[str]:
        """Get the install image URL from cluster settings (set by factory service)."""
        db = SessionLocal()
        try:
            cs = cluster_crud.get_cluster_settings(db)
            return cs.install_image if cs else None
        except Exception:
            return None
        finally:
            db.close()

    def _get_kernel_modules(self) -> List[str]:
        """Get kernel module names from cluster settings"""
        db = SessionLocal()
        try:
            cs = cluster_crud.get_cluster_settings(db)
            if cs and cs.kernel_modules:
                return json.loads(cs.kernel_modules)
            return []
        except Exception:
            return []
        finally:
            db.close()

    def _get_disk_partitions(self, device=None) -> List[dict]:
        """Get extra disk partition configs based on EPHEMERAL sizing.

        If EPHEMERAL has a maxSize cap AND Longhorn is installed, creates a
        separate partition on the remaining disk space at /var/mnt/longhorn.

        If EPHEMERAL grows to fill the disk, no separate partition is needed —
        Longhorn uses /var/lib/longhorn inside the EPHEMERAL partition.

        Returns list of dicts: [{"mountpoint": "/var/mnt/longhorn", "disk": ""}]
        """
        # Check if EPHEMERAL is capped (per-device overrides take priority)
        ephemeral_capped = False
        db = SessionLocal()
        try:
            if device and device.ephemeral_max_size:
                ephemeral_capped = True
            else:
                volumes = volume_crud.get_volume_configs(db)
                for v in volumes:
                    if v.name.value == "EPHEMERAL" and v.max_size:
                        ephemeral_capped = True
                        break

            if not ephemeral_capped:
                # EPHEMERAL fills the disk — no separate partition needed
                return []

            # EPHEMERAL is capped — check if Longhorn is installed
            from app.db.models import HelmRelease
            longhorn = db.query(HelmRelease).filter(
                HelmRelease.chart_name.contains("longhorn"),
                HelmRelease.status != "uninstalling",
            ).first()

            if longhorn:
                return [{"mountpoint": "/var/mnt/longhorn", "disk": ""}]
            return []
        finally:
            db.close()

    def _get_network_settings(self) -> dict:
        """Get network settings (nameservers, gateway, subnet) from database"""
        from app.crud import network as network_crud
        db = SessionLocal()
        try:
            ns = network_crud.get_network_settings(db)
            if not ns:
                return {}
            return {
                'dns_server': ns.dns_server or ns.server_ip,
                'dhcp_netmask': ns.dhcp_netmask or '255.255.0.0',
                'server_ip': ns.server_ip,
            }
        finally:
            db.close()

    @staticmethod
    def _netmask_to_cidr(netmask: str) -> int:
        """Convert dotted netmask to CIDR prefix length"""
        import struct, socket
        try:
            packed = socket.inet_aton(netmask)
            bits = struct.unpack('!I', packed)[0]
            return bin(bits).count('1')
        except Exception:
            return 16  # safe default

    def _ensure_cidr(self, ip_address: str, netmask: str) -> str:
        """Ensure an IP address has CIDR notation, e.g. 10.0.128.10/16"""
        if '/' in ip_address:
            return ip_address
        prefix = self._netmask_to_cidr(netmask)
        return f"{ip_address}/{prefix}"

    def generate_config_from_params(
        self,
        mac_address: str,
        node_type: str,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        save_to_disk: bool = True,
        wipe_on_next_boot: bool = False,
        install_disk: Optional[str] = None,
        ephemeral_min_size: Optional[str] = None,
        ephemeral_max_size: Optional[str] = None,
        ephemeral_disk_selector: Optional[str] = None
    ) -> Tuple[str, Optional[Path]]:
        """
        Generate Talos configuration from raw parameters.

        Args:
            mac_address: Device MAC address (required for file naming)
            node_type: "controlplane" or "worker"
            hostname: Hostname to set in config (optional)
            ip_address: Static IP address to set (optional)
            save_to_disk: If True, saves to compiled/talos/configs/{mac}.yaml

        Returns:
            Tuple of (config_yaml_string, output_path or None)
        """
        try:
            # Determine which base config to use
            if node_type == "controlplane":
                base_config_file = self.base_dir / "controlplane.yaml"
            elif node_type == "worker":
                base_config_file = self.base_dir / "worker.yaml"
            else:
                raise ValueError(f"Invalid node_type: {node_type}. Must be 'controlplane' or 'worker'")

            if not base_config_file.exists():
                logger.error(f"Base config file not found: {base_config_file}")
                raise FileNotFoundError(f"Base config template not found: {base_config_file}")

            # Read base configuration (handle multi-document YAML)
            with open(base_config_file, 'r') as f:
                # Load all documents and use the first one (machine config)
                docs = list(yaml.safe_load_all(f))
                if not docs:
                    raise ValueError(f"No YAML documents found in {base_config_file}")
                config = docs[0]  # Use the first document (machine config)

            # Customize configuration with provided settings
            if 'machine' not in config:
                config['machine'] = {}
            if 'network' not in config['machine']:
                config['machine']['network'] = {}

            # Set hostname if provided
            if hostname:
                config['machine']['network']['hostname'] = hostname

            # Get network settings for CIDR, gateway, nameservers
            net_settings = self._get_network_settings()
            netmask = net_settings.get('dhcp_netmask', '255.255.0.0')
            gateway = net_settings.get('dns_server', '')
            nameservers = [net_settings['dns_server']] if net_settings.get('dns_server') else []

            # Set static IP by MAC address if provided
            if ip_address and mac_address:
                # Configure interface with MAC address selector, static IP, and default route
                interface_config = {
                    'deviceSelector': {
                        'hardwareAddr': mac_address
                    },
                    'addresses': [self._ensure_cidr(ip_address, netmask)],
                }

                # Add default route via gateway
                if gateway:
                    interface_config['routes'] = [
                        {'network': '0.0.0.0/0', 'gateway': gateway}
                    ]

                config['machine']['network']['interfaces'] = [interface_config]

            # Set nameservers
            if nameservers:
                config['machine']['network']['nameservers'] = nameservers

            # Set wipe/reinstall flag if requested
            if wipe_on_next_boot:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['force'] = True
                logger.info(f"Set machine.install.force=true for MAC {mac_address} (wipe on next boot)")

            # Update kubelet version to match Kubernetes version
            k8s_version = self._get_kubernetes_version()
            if k8s_version and 'machine' in config and 'kubelet' in config['machine']:
                config['machine']['kubelet']['image'] = f'ghcr.io/siderolabs/kubelet:{ensure_v_prefix(k8s_version)}'
                logger.info(f"Set kubelet version to {ensure_v_prefix(k8s_version)} for MAC {mac_address}")

            # Patch CNI settings: disable built-in flannel for custom CNIs
            cni = self._get_cni()
            if cni and cni.lower() != "flannel":
                if 'cluster' not in config:
                    config['cluster'] = {}
                if 'network' not in config['cluster']:
                    config['cluster']['network'] = {}
                config['cluster']['network']['cni'] = {'name': 'none'}
                # Disable kube-proxy for Cilium (it provides its own replacement)
                if cni.lower() == "cilium":
                    if 'proxy' not in config['cluster']:
                        config['cluster']['proxy'] = {}
                    config['cluster']['proxy']['disabled'] = True
                logger.info(f"Set CNI to none (custom CNI: {cni}) for MAC {mac_address}")

            # Override install disk if per-device setting provided
            if install_disk:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['disk'] = install_disk
                logger.info(f"Set per-device install disk to {install_disk} for MAC {mac_address}")

            # Override install image with factory URL (or vanilla installer)
            install_image = self._get_install_image()
            if install_image:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['image'] = install_image
                logger.info(f"Set install image to {install_image} for MAC {mac_address}")

            # Inject kernel modules
            kernel_modules = self._get_kernel_modules()
            if kernel_modules:
                config['machine']['kernel'] = {'modules': [{'name': m} for m in kernel_modules]}
                logger.info(f"Added {len(kernel_modules)} kernel modules for MAC {mac_address}")

            # Generate multi-document YAML with VolumeConfigs
            config_docs = [config]

            # Build a lightweight object for per-device storage overrides
            class _StorageOverrides:
                pass
            storage_overrides = None
            if ephemeral_min_size or ephemeral_max_size or ephemeral_disk_selector:
                storage_overrides = _StorageOverrides()
                storage_overrides.ephemeral_min_size = ephemeral_min_size
                storage_overrides.ephemeral_max_size = ephemeral_max_size
                storage_overrides.ephemeral_disk_selector = ephemeral_disk_selector
                storage_overrides.mac_address = mac_address

            # Add VolumeConfig documents
            db = SessionLocal()
            try:
                volume_configs = self._generate_volume_configs(db, device=storage_overrides)
                if volume_configs:
                    config_docs.extend(volume_configs)
                    logger.info(f"Added {len(volume_configs)} VolumeConfig documents for MAC {mac_address}")
            finally:
                db.close()

            # Convert all documents to YAML string, separated by ---
            config_yaml = '\n---\n'.join([
                yaml.dump(doc, default_flow_style=False, sort_keys=False)
                for doc in config_docs
            ])

            output_path = None
            if save_to_disk:
                # Generate output filename: {mac}.yaml
                output_filename = f"{mac_address}.yaml"
                output_path = self.output_dir / output_filename

                # Write configuration to file
                with open(output_path, 'w') as f:
                    f.write(config_yaml)

                logger.info(f"Generated config for MAC {mac_address} at {output_path}")

            return config_yaml, output_path

        except Exception as e:
            logger.error(f"Failed to generate config for MAC {mac_address}: {e}")
            raise

    def generate_device_config(self, device: Device) -> Optional[Path]:
        """
        Generate a static configuration file for an approved device.

        Args:
            device: Device model with role, hostname, ip_address, and mac_address

        Returns:
            Path to the generated config file, or None if generation failed
        """
        try:
            # Determine which base config to use
            if device.role == DeviceRole.CONTROLPLANE:
                base_config_file = self.base_dir / "controlplane.yaml"
            else:
                base_config_file = self.base_dir / "worker.yaml"

            if not base_config_file.exists():
                logger.error(f"Base config file not found: {base_config_file}")
                return None

            # Read base configuration (handle multi-document YAML)
            with open(base_config_file, 'r') as f:
                # Load all documents and use the first one (machine config)
                docs = list(yaml.safe_load_all(f))
                if not docs:
                    logger.error(f"No YAML documents found in {base_config_file}")
                    return None
                config = docs[0]  # Use the first document (machine config)

            # Customize configuration with device-specific settings
            if 'machine' not in config:
                config['machine'] = {}
            if 'network' not in config['machine']:
                config['machine']['network'] = {}

            # Set hostname if provided
            if device.hostname:
                config['machine']['network']['hostname'] = device.hostname

            # Get network settings for CIDR, gateway, nameservers
            net_settings = self._get_network_settings()
            netmask = net_settings.get('dhcp_netmask', '255.255.0.0')
            gateway = net_settings.get('dns_server', '')
            nameservers = [net_settings['dns_server']] if net_settings.get('dns_server') else []

            # Set static IP by MAC address if provided
            if device.ip_address and device.mac_address:
                # Configure interface with MAC address selector, static IP, and default route
                interface_config = {
                    'deviceSelector': {
                        'hardwareAddr': device.mac_address
                    },
                    'addresses': [self._ensure_cidr(device.ip_address, netmask)],
                }

                # Add default route via gateway
                if gateway:
                    interface_config['routes'] = [
                        {'network': '0.0.0.0/0', 'gateway': gateway}
                    ]

                config['machine']['network']['interfaces'] = [interface_config]

            # Set nameservers
            if nameservers:
                config['machine']['network']['nameservers'] = nameservers

            # Set wipe/reinstall flag if requested
            if device.wipe_on_next_boot:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['wipe'] = True
                logger.info(f"Set machine.install.wipe=true for MAC {device.mac_address} (wipe on next boot)")

            # Update kubelet version to match Kubernetes version
            k8s_version = self._get_kubernetes_version()
            if k8s_version and 'machine' in config and 'kubelet' in config['machine']:
                config['machine']['kubelet']['image'] = f'ghcr.io/siderolabs/kubelet:{ensure_v_prefix(k8s_version)}'
                logger.info(f"Set kubelet version to {ensure_v_prefix(k8s_version)} for device {device.mac_address}")

            # Patch CNI settings: disable built-in flannel for custom CNIs
            cni = self._get_cni()
            if cni and cni.lower() != "flannel":
                if 'cluster' not in config:
                    config['cluster'] = {}
                if 'network' not in config['cluster']:
                    config['cluster']['network'] = {}
                config['cluster']['network']['cni'] = {'name': 'none'}
                # Disable kube-proxy for Cilium (it provides its own replacement)
                if cni.lower() == "cilium":
                    if 'proxy' not in config['cluster']:
                        config['cluster']['proxy'] = {}
                    config['cluster']['proxy']['disabled'] = True
                logger.info(f"Set CNI to none (custom CNI: {cni}) for device {device.mac_address}")

            # Override install disk if device has per-device setting
            if device.install_disk:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['disk'] = device.install_disk
                logger.info(f"Set per-device install disk to {device.install_disk} for {device.mac_address}")

            # Override install image with factory URL (or vanilla installer)
            install_image = self._get_install_image()
            if install_image:
                if 'install' not in config['machine']:
                    config['machine']['install'] = {}
                config['machine']['install']['image'] = install_image
                logger.info(f"Set install image to {install_image} for device {device.mac_address}")

            # Inject kernel modules
            kernel_modules = self._get_kernel_modules()
            if kernel_modules:
                config['machine']['kernel'] = {'modules': [{'name': m} for m in kernel_modules]}
                logger.info(f"Added {len(kernel_modules)} kernel modules for device {device.mac_address}")

            # Inject extra disk partitions (e.g., Longhorn storage)
            disk_partitions = self._get_disk_partitions(device=device)
            if disk_partitions:
                # Get the install disk for this device (per-device or global)
                install_disk = device.install_disk
                if not install_disk:
                    if 'install' in config.get('machine', {}) and 'disk' in config['machine']['install']:
                        install_disk = config['machine']['install']['disk']
                    else:
                        install_disk = '/dev/sda'

                disks_config = {}  # keyed by device path
                for part in disk_partitions:
                    disk = part.get('disk') or install_disk
                    if disk not in disks_config:
                        disks_config[disk] = {'device': disk, 'partitions': []}
                    partition = {'mountpoint': part['mountpoint']}
                    disks_config[disk]['partitions'].append(partition)

                if disks_config:
                    config['machine']['disks'] = list(disks_config.values())
                    logger.info(f"Added {len(disk_partitions)} extra disk partition(s) for device {device.mac_address}")

            # Generate multi-document YAML with VolumeConfigs
            config_docs = [config]

            # Add VolumeConfig documents (with per-device overrides if set)
            db = SessionLocal()
            try:
                volume_configs = self._generate_volume_configs(db, device=device)
                if volume_configs:
                    config_docs.extend(volume_configs)
                    logger.info(f"Added {len(volume_configs)} VolumeConfig documents for device {device.mac_address}")
            finally:
                db.close()

            # Generate output filename: {mac}.yaml
            output_filename = f"{device.mac_address}.yaml"
            output_path = self.output_dir / output_filename

            # Write customized configuration as multi-document YAML
            with open(output_path, 'w') as f:
                # Write each document separated by ---
                for i, doc in enumerate(config_docs):
                    if i > 0:
                        f.write('\n---\n')
                    yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Generated config for device {device.mac_address} at {output_path} with {len(config_docs)} documents")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate config for device {device.mac_address}: {e}")
            return None

    def delete_device_config(self, device: Device) -> bool:
        """
        Delete the static configuration file for a device.

        Args:
            device: Device model

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            output_filename = f"{device.mac_address}.yaml"
            output_path = self.output_dir / output_filename

            if output_path.exists():
                output_path.unlink()
                logger.info(f"Deleted config for device {device.mac_address}")
                return True
            else:
                logger.warning(f"Config file not found for device {device.mac_address}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete config for device {device.mac_address}: {e}")
            return False

    def regenerate_all_configs(self, devices: list[Device]) -> int:
        """
        Regenerate configuration files for all approved devices.

        Args:
            devices: List of approved Device models

        Returns:
            Number of configs successfully generated
        """
        count = 0
        for device in devices:
            if self.generate_device_config(device):
                count += 1

        logger.info(f"Regenerated {count}/{len(devices)} device configurations")
        return count
