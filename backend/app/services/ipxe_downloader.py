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
            
            # Also copy to TFTP root if it's different from compiled directory
            # This ensures files are available for dnsmasq to serve
            tftp_root = os.getenv("TFTP_ROOT", "/var/lib/tftpboot")
            if tftp_root and Path(tftp_root).exists():
                tftp_pxe_dir = Path(tftp_root) / "pxe"
                tftp_pxe_dir.mkdir(parents=True, exist_ok=True)
                tftp_file = tftp_pxe_dir / filename
                try:
                    import shutil
                    shutil.copy2(output_path, tftp_file)
                    logger.info(f"Copied {filename} to TFTP root: {tftp_file}")
                except Exception as copy_error:
                    logger.warning(f"Failed to copy {filename} to TFTP root: {copy_error}")
            
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
    
    def sync_to_tftp_root(self, tftp_root: str) -> Tuple[bool, List[str]]:
        """
        Sync all iPXE bootloader files to the TFTP root directory.
        This ensures files are available for dnsmasq to serve.
        
        Args:
            tftp_root: Path to TFTP root directory (e.g., /var/lib/tftpboot)
            
        Returns:
            Tuple of (success: bool, errors: list[str])
        """
        errors = []
        tftp_pxe_dir = Path(tftp_root) / "pxe"
        
        try:
            # Create TFTP PXE directory if it doesn't exist
            tftp_pxe_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Syncing iPXE files to TFTP root: {tftp_pxe_dir}")
        except Exception as e:
            error_msg = f"Failed to create TFTP PXE directory {tftp_pxe_dir}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
        
        # Copy each bootloader file to TFTP root
        for local_name in self.bootloader_files.values():
            source_file = self.tftp_root / local_name
            dest_file = tftp_pxe_dir / local_name
            
            if not source_file.exists():
                error_msg = f"Source file not found: {source_file}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            
            try:
                import shutil
                shutil.copy2(source_file, dest_file)
                logger.info(f"Synced {local_name} to {dest_file}")
            except Exception as e:
                error_msg = f"Failed to copy {local_name} to {dest_file}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        success = len(errors) == 0
        if success:
            logger.info(f"Successfully synced all iPXE files to TFTP root: {tftp_pxe_dir}")
        else:
            logger.warning(f"Synced iPXE files with {len(errors)} errors")
        
        return success, errors

ipxe_downloader = IPXEDownloader()
