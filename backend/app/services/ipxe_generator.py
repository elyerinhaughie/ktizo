"""Service for generating iPXE boot script with approved devices"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging
import os
from typing import List
from app.db.models import Device, DeviceStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

class IPXEGenerator:
    def __init__(self):
        # Use environment variables if set, otherwise use config defaults, otherwise Docker paths
        templates_dir = os.getenv("TEMPLATES_DIR", settings.TEMPLATES_DIR)
        compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
        
        templates_path = Path(templates_dir) / "pxe"
        if not templates_path.is_absolute():
            templates_path = Path(__file__).parent.parent.parent.parent.parent / templates_path
        
        output_path = Path(compiled_dir) / "pxe"
        if not output_path.is_absolute():
            output_path = Path(__file__).parent.parent.parent.parent.parent / output_path
        
        # Fallback to Docker paths if environment not set and relative path doesn't exist
        if not templates_path.exists() and not os.getenv("TEMPLATES_DIR"):
            templates_path = Path("/templates") / "pxe"
        if not output_path.exists() and not os.getenv("COMPILED_DIR"):
            output_path = Path("/compiled") / "pxe"
        
        self.templates_dir = templates_path
        self.output_dir = output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def generate_boot_script(self, devices: List[Device], server_ip: str, talos_version: str = "v1.10.0", strict_mode: bool = False, install_disk: str = "/dev/sda") -> bool:
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
            template = self.env.get_template('boot.ipxe.j2')

            # Render template
            rendered = template.render(
                server=server_ip,
                version=talos_version,
                devices=device_mappings,
                strict_mode=strict_mode,
                install_disk=install_disk
            )

            # Write to output
            output_path = self.output_dir / "boot.ipxe"
            with open(output_path, 'w') as f:
                f.write(rendered)

            logger.info(f"Generated boot.ipxe with {len(device_mappings)} approved devices at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate boot.ipxe: {e}")
            return False

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
