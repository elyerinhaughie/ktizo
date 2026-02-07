"""Service for downloading Talos boot files"""
import requests
import logging
import os
from pathlib import Path
from typing import Optional
from app.core.config import settings, ensure_v_prefix

logger = logging.getLogger(__name__)

class TalosDownloader:
    def __init__(self, tftp_root: str = None):
        self.base_url = "https://github.com/siderolabs/talos/releases/download"
        
        # Use provided TFTP root, or get from database/environment, or use default
        if tftp_root:
            tftp_talos_dir = Path(tftp_root) / "pxe" / "talos"
        else:
            # Try to get from environment or config
            tftp_root_env = os.getenv("TFTP_ROOT", settings.TFTP_ROOT)
            tftp_talos_dir = Path(tftp_root_env) / "pxe" / "talos"
        
        # Create TFTP Talos directory with proper permissions
        try:
            tftp_talos_dir.mkdir(parents=True, exist_ok=True)
            # Ensure directory is writable
            if not os.access(tftp_talos_dir, os.W_OK):
                raise PermissionError(f"Cannot write to TFTP Talos directory: {tftp_talos_dir}")
            self.output_dir = tftp_talos_dir
            logger.info(f"Using TFTP root for Talos files: {self.output_dir}")
        except (PermissionError, OSError) as e:
            # Fallback to compiled directory if we can't write to TFTP root
            logger.warning(f"Cannot write to TFTP root {tftp_talos_dir}: {e}")
            logger.warning("Falling back to compiled directory - files will need to be manually copied to TFTP root")
            compiled_dir = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
            fallback_path = Path(compiled_dir) / "pxe" / "talos"
            if not fallback_path.is_absolute():
                fallback_path = Path(__file__).parent.parent.parent.parent.parent / fallback_path
            fallback_path.mkdir(parents=True, exist_ok=True)
            self.output_dir = fallback_path
            logger.info(f"Using fallback directory: {self.output_dir}")

    def get_file_path(self, version: str, filename: str) -> Path:
        """Get the local file path for a Talos file"""
        # Store files as version-specific: vmlinuz-amd64-v1.12.2
        version = ensure_v_prefix(version)
        name_parts = filename.rsplit('.', 1)  # Split extension
        if len(name_parts) == 2:
            versioned_name = f"{name_parts[0]}-{version}.{name_parts[1]}"
        else:
            versioned_name = f"{filename}-{version}"
        return self.output_dir / versioned_name

    def file_exists(self, version: str, filename: str) -> bool:
        """Check if a file already exists locally"""
        return self.get_file_path(version, filename).exists()

    def download_file(self, version: str, filename: str) -> Optional[Path]:
        """
        Download a Talos file from GitHub releases.

        Args:
            version: Talos version (e.g., "v1.11.3")
            filename: File to download (e.g., "vmlinuz-amd64")

        Returns:
            Path to downloaded file, or None if download failed
        """
        try:
            output_path = self.get_file_path(version, filename)

            # Skip if already exists
            if output_path.exists():
                logger.info(f"File already exists: {output_path}")
                return output_path

            # Download URL — GitHub releases use v-prefixed tags
            version = ensure_v_prefix(version)
            url = f"{self.base_url}/{version}/{filename}"
            logger.info(f"Downloading {url} to {output_path}")

            # Stream download to handle large files
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            # Get file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Downloading {filename} ({total_size / 1024 / 1024:.1f} MB)")

            # Write to file
            with open(output_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Log progress every 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size * 100) if total_size > 0 else 0
                            logger.info(f"Progress: {progress:.1f}%")

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
                    # Also ensure parent directory is world-readable and executable (755)
                    os.chmod(output_path.parent, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    os.chown(output_path.parent, dnsmasq_uid, dnsmasq_gid)
                except Exception as perm_err:
                    logger.warning(f"Could not set file permissions (non-fatal): {perm_err}")

            logger.info(f"Successfully downloaded {filename} to {output_path}")
            return output_path

        except requests.RequestException as e:
            logger.error(f"Failed to download {filename} version {version}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            return None

    def download_talos_files(self, version: str) -> tuple[bool, list[str]]:
        """
        Download both vmlinuz and initramfs for a specific Talos version.

        Args:
            version: Talos version (e.g., "v1.11.3")

        Returns:
            Tuple of (success: bool, errors: list[str])
        """
        errors = []
        files_to_download = ["vmlinuz-amd64", "initramfs-amd64.xz"]

        for filename in files_to_download:
            result = self.download_file(version, filename)
            if result is None:
                errors.append(f"Failed to download {filename}")

        success = len(errors) == 0
        return success, errors

    def get_versioned_filenames(self, version: str) -> dict[str, str]:
        """
        Get the versioned filenames for TFTP serving.

        Returns:
            Dict with keys 'vmlinuz' and 'initramfs' containing versioned filenames
        """
        version = ensure_v_prefix(version)
        return {
            "vmlinuz": f"vmlinuz-amd64-{version}",
            "initramfs": f"initramfs-amd64-{version}.xz"
        }

talos_downloader = TalosDownloader()
