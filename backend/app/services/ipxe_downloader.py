"""Service for downloading iPXE bootloader files"""
import requests
import logging
import os
from pathlib import Path
from typing import List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class IPXEDownloader:
    def __init__(self):
        self.base_url = "https://boot.ipxe.org"
        
        # Use environment variable if set, otherwise config, otherwise Docker path
        compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
        tftp_path = Path(compiled_dir) / "pxe"
        
        if not tftp_path.is_absolute():
            # Assume relative to project root
            tftp_path = Path(__file__).parent.parent.parent.parent.parent / tftp_path
        
        # Fallback to Docker path if not set
        if not tftp_path.exists() and not os.getenv("COMPILED_DIR"):
            tftp_path = Path("/compiled") / "pxe"
        
        self.tftp_root = tftp_path
        self.tftp_root.mkdir(parents=True, exist_ok=True)

        # iPXE bootloader files needed (name on boot.ipxe.org → local name)
        self.bootloader_files = {
            "undionly.kpxe": "undionly.kpxe",        # Legacy BIOS
            "ipxe.efi": "ipxe.efi",                  # Generic UEFI (covers all arches)
            "snponly.efi": "snponly.efi",            # SNP-only
            "ipxe.pxe": "ipxe.pxe",                  # Fallback
        }

    def file_exists(self, filename: str) -> bool:
        """Check if a bootloader file exists"""
        return (self.tftp_root / filename).exists()

    def download_file(self, filename: str) -> bool:
        """
        Download a single iPXE bootloader file.

        Args:
            filename: Name of the file to download

        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.tftp_root / filename

            # Skip if already exists
            if output_path.exists():
                logger.info(f"iPXE bootloader already exists: {filename}")
                return True

            url = f"{self.base_url}/{filename}"
            logger.info(f"Downloading iPXE bootloader: {url}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Successfully downloaded {filename} ({len(response.content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            return False

    def download_all_bootloaders(self) -> Tuple[bool, List[str]]:
        """
        Download all iPXE bootloader files.

        Returns:
            Tuple of (success: bool, errors: list[str])
        """
        errors = []

        for remote_name, local_name in self.bootloader_files.items():
            if not self.download_file(remote_name):
                errors.append(f"Failed to download {remote_name}")

        success = len(errors) == 0
        return success, errors

    def check_all_bootloaders_exist(self) -> bool:
        """Check if all required bootloader files exist"""
        return all(self.file_exists(local_name) for local_name in self.bootloader_files.values())

ipxe_downloader = IPXEDownloader()
