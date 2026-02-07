"""Service for downloading iPXE bootloader files"""
import requests
import logging
import os
from pathlib import Path
from typing import List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class IPXEDownloader:
    def __init__(self, tftp_root: str = None):
        self.base_url = "https://boot.ipxe.org"
        
        # Use provided TFTP root, or get from database/environment, or use default
        if tftp_root:
            tftp_path = Path(tftp_root) / "pxe"
        else:
            # Try to get from environment or config
            tftp_root_env = os.getenv("TFTP_ROOT", settings.TFTP_ROOT)
            tftp_path = Path(tftp_root_env) / "pxe"
        
        # Create TFTP PXE directory with proper permissions
        try:
            # Check if directory exists and is writable
            if tftp_path.exists():
                if not os.access(tftp_path, os.W_OK):
                    raise PermissionError(f"Cannot write to existing TFTP directory: {tftp_path}")
            else:
                # Try to create directory
                try:
                    tftp_path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    raise PermissionError(f"Cannot create TFTP directory: {tftp_path}")
                # Verify we can write to it
                if not os.access(tftp_path, os.W_OK):
                    raise PermissionError(f"Cannot write to TFTP directory: {tftp_path}")
            
            self.tftp_root = tftp_path
            logger.info(f"Using TFTP root: {self.tftp_root}")
        except (PermissionError, OSError) as e:
            # Fallback to compiled directory if we can't write to TFTP root
            logger.warning(f"Cannot write to TFTP root {tftp_path}: {e}")
            logger.warning("Falling back to compiled directory - files will need to be manually copied to TFTP root")
            compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
            fallback_path = Path(compiled_dir) / "pxe"
            if not fallback_path.is_absolute():
                fallback_path = Path(__file__).parent.parent.parent.parent.parent / fallback_path
            fallback_path.mkdir(parents=True, exist_ok=True)
            self.tftp_root = fallback_path
            logger.info(f"Using fallback directory: {self.tftp_root}")

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

            logger.info(f"Successfully downloaded {filename} ({len(response.content)} bytes) to {output_path}")
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
