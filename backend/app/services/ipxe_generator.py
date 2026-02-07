"""Service for generating iPXE boot script with approved devices"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging
import os
from typing import List
from app.db.models import Device, DeviceStatus
from app.core.config import settings, ensure_v_prefix

logger = logging.getLogger(__name__)

class IPXEGenerator:
    def __init__(self, tftp_root: str = None):
        # Use environment variables if set, otherwise use config defaults, otherwise Docker paths
        templates_dir = os.getenv("TEMPLATES_DIR", settings.TEMPLATES_DIR)
        
        templates_path = Path(templates_dir) / "pxe"
        if not templates_path.is_absolute():
            templates_path = (Path(__file__).parent.parent.parent / templates_path).resolve()
        
        # Fallback to Docker paths if environment not set and relative path doesn't exist
        if not templates_path.exists() and not os.getenv("TEMPLATES_DIR"):
            templates_path = Path("/templates") / "pxe"
        
        self.templates_dir = templates_path
        
        # Use provided TFTP root, or get from database/environment, or use default
        if tftp_root:
            output_path = Path(tftp_root) / "pxe"
        else:
            # Try to get from environment or config
            tftp_root_env = os.getenv("TFTP_ROOT", settings.TFTP_ROOT)
            output_path = Path(tftp_root_env) / "pxe"
        
        # Create TFTP PXE directory with proper permissions
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            # Ensure directory is writable
            if not os.access(output_path, os.W_OK):
                raise PermissionError(f"Cannot write to TFTP directory: {output_path}")
            self.output_dir = output_path
            logger.info(f"Using TFTP root for boot.ipxe: {self.output_dir}")
        except (PermissionError, OSError) as e:
            # Fallback to compiled directory if we can't write to TFTP root
            logger.warning(f"Cannot write to TFTP root {output_path}: {e}")
            logger.warning("Falling back to compiled directory - boot.ipxe will need to be manually copied to TFTP root")
            compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
            fallback_path = Path(compiled_dir) / "pxe"
            if not fallback_path.is_absolute():
                fallback_path = (Path(__file__).parent.parent.parent / fallback_path).resolve()
            fallback_path.mkdir(parents=True, exist_ok=True)
            self.output_dir = fallback_path
            logger.info(f"Using fallback directory: {self.output_dir}")

        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def get_talos_version_from_settings(self, db) -> str:
        """Get Talos version from network settings in database."""
        try:
            from app.crud import network as network_crud
            ns = network_crud.get_network_settings(db)
            if ns and ns.talos_version:
                return ns.talos_version
            return "1.12.2"
        except Exception as e:
            logger.error(f"Failed to get Talos version from settings: {e}")
            return "1.12.2"

    def generate_boot_script(self, devices: List[Device], server_ip: str, talos_version: str = None, strict_mode: bool = False, install_disk: str = "/dev/sda") -> bool:
        """
        Generate boot.ipxe script with approved device mappings.

        Args:
            devices: List of approved Device models
            server_ip: Server IP address for TFTP/HTTP
            talos_version: Talos version to boot
            strict_mode: If True, unapproved devices exit immediately
            install_disk: Disk to install Talos on (e.g., /dev/sda)

        Returns:
            True if generation succeeded, False otherwise
        """
        try:
            # Fetch talos_version and install_disk from DB if not provided
            if not talos_version or install_disk == "/dev/sda":
                from app.db.database import SessionLocal
                from app.crud import network as network_crud
                from app.crud import cluster as cluster_crud
                db = SessionLocal()
                try:
                    if not talos_version:
                        talos_version = self.get_talos_version_from_settings(db)
                    if install_disk == "/dev/sda":
                        cs = cluster_crud.get_cluster_settings(db)
                        if cs and cs.install_disk:
                            install_disk = cs.install_disk
                finally:
                    db.close()

            # Filter only approved devices
            approved_devices = [d for d in devices if d.status == DeviceStatus.APPROVED]

            # Prepare device data for template
            device_mappings = []
            for device in approved_devices:
                device_mappings.append({
                    'mac_address': device.mac_address,
                    'role': device.role.value,
                    'ip_address': device.ip_address or '0.0.0.0',
                    'hostname': device.hostname or f'node-{device.mac_address[-8:]}'
                })

            # Load template
            try:
                template = self.env.get_template('boot.ipxe.j2')
            except Exception as e:
                template_path = self.templates_dir / 'boot.ipxe.j2'
                raise Exception(
                    f"Failed to load iPXE template from {template_path}: {str(e)}. "
                    f"Check that the template file exists and templates directory is accessible."
                ) from e

            # Render template — version needs v prefix for filenames
            try:
                rendered = template.render(
                    server=server_ip,
                    version=ensure_v_prefix(talos_version),
                    devices=device_mappings,
                    strict_mode=strict_mode,
                    install_disk=install_disk
                )
            except Exception as e:
                raise Exception(
                    f"Failed to render iPXE template: {str(e)}. "
                    f"Check that template variables are correct and template syntax is valid."
                ) from e

            # Write to output
            output_path = self.output_dir / "boot.ipxe"
            try:
                with open(output_path, 'w') as f:
                    f.write(rendered)
                
                # Set proper permissions for dnsmasq/TFTP
                if os.getuid() == 0:
                    try:
                        import stat
                        import pwd
                        # Try to find dnsmasq user ID
                        try:
                            dnsmasq_user = pwd.getpwnam('dnsmasq')
                            dnsmasq_uid = dnsmasq_user.pw_uid
                            dnsmasq_gid = dnsmasq_user.pw_gid
                        except KeyError:
                            # dnsmasq user doesn't exist, use root
                            dnsmasq_uid = 0
                            dnsmasq_gid = 0
                        
                        # 644 permissions: owner read/write, group/others read
                        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                        os.chown(output_path, dnsmasq_uid, dnsmasq_gid)
                    except Exception as perm_err:
                        logger.warning(f"Could not set file permissions (non-fatal): {perm_err}")
            except PermissionError as e:
                raise Exception(
                    f"Permission denied writing boot.ipxe to {output_path}: {str(e)}. "
                    f"Check that directory {self.output_dir} is writable."
                ) from e
            except OSError as e:
                raise Exception(
                    f"Failed to write boot.ipxe to {output_path}: {str(e)}. "
                    f"Check disk space and directory permissions."
                ) from e

            logger.info(f"Generated boot.ipxe with {len(device_mappings)} approved devices at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate boot.ipxe: {e}", exc_info=True)
            # Re-raise with more context
            raise

    def get_server_ip_from_settings(self, db) -> str:
        """
        Get server IP from network settings in database.

        Args:
            db: Database session

        Returns:
            Server IP address or default
        """
        try:
            from app.crud import network as network_crud
            settings = network_crud.get_network_settings(db)
            if settings and settings.server_ip:
                return settings.server_ip
            return "10.0.5.113"  # Default fallback
        except Exception as e:
            logger.error(f"Failed to get server IP from settings: {e}")
            return "10.0.5.113"

    def get_strict_mode_from_settings(self, db) -> bool:
        """
        Get strict boot mode from network settings in database.

        Args:
            db: Database session

        Returns:
            Strict mode boolean or False as default
        """
        try:
            from app.crud import network as network_crud
            settings = network_crud.get_network_settings(db)
            if settings and hasattr(settings, 'strict_boot_mode'):
                return settings.strict_boot_mode
            return False
        except Exception as e:
            logger.error(f"Failed to get strict mode from settings: {e}")
            return False
