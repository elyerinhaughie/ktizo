"""Service for downloading and managing kubectl versions"""
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class KubectlDownloader:
    """Downloads and manages kubectl binaries with version support"""
    
    def __init__(self, install_dir: str = None):
        """
        Initialize kubectl downloader.
        
        Args:
            install_dir: Directory where kubectl binaries are stored (default: backend directory)
        """
        if install_dir:
            self.install_dir = Path(install_dir)
        else:
            # Default to backend directory (same as talosctl)
            backend_dir = Path(__file__).parent.parent.parent
            self.install_dir = backend_dir
        
        # Create kubectl versions directory
        self.versions_dir = self.install_dir / "kubectl-versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Symlink to current kubectl
        self.kubectl_symlink = self.install_dir / "kubectl"
    
    def _detect_architecture(self) -> Tuple[str, str]:
        """Detect OS and architecture for kubectl download"""
        import platform
        
        os_name = platform.system().lower()
        arch = platform.machine().lower()
        
        # Map architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }
        
        kubectl_arch = arch_map.get(arch, "amd64")
        
        # Map OS names
        os_map = {
            "linux": "linux",
            "darwin": "darwin",
            "windows": "windows",
        }
        
        kubectl_os = os_map.get(os_name, "linux")
        
        return kubectl_os, kubectl_arch
    
    def _normalize_version(self, version: str) -> str:
        """Normalize version string (remove 'v' prefix if present)"""
        if version.startswith("v"):
            return version[1:]
        return version
    
    def _get_download_url(self, version: str, os_name: str, arch: str) -> str:
        """Get kubectl download URL for a specific version"""
        normalized_version = self._normalize_version(version)
        
        # kubectl download URL format:
        # https://dl.k8s.io/release/v{version}/bin/{os}/{arch}/kubectl
        url = f"https://dl.k8s.io/release/v{normalized_version}/bin/{os_name}/{arch}/kubectl"
        return url
    
    def download_kubectl(self, version: str) -> Tuple[bool, Optional[str]]:
        """
        Download kubectl for a specific version.
        
        Args:
            version: kubectl version (e.g., "1.28.0" or "v1.28.0")
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            normalized_version = self._normalize_version(version)
            os_name, arch = self._detect_architecture()
            
            # Check if already downloaded
            kubectl_path = self.versions_dir / f"kubectl-{normalized_version}"
            if kubectl_path.exists():
                logger.info(f"kubectl {version} already exists at {kubectl_path}")
                return True, None
            
            # Download kubectl
            url = self._get_download_url(version, os_name, arch)
            logger.info(f"Downloading kubectl {version} from {url}")
            
            import urllib.request
            urllib.request.urlretrieve(url, kubectl_path)
            
            # Make executable
            os.chmod(kubectl_path, 0o755)
            
            logger.info(f"Successfully downloaded kubectl {version} to {kubectl_path}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to download kubectl {version}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def set_kubectl_version(self, version: str) -> Tuple[bool, Optional[str]]:
        """
        Set the active kubectl version by creating/updating symlink.
        Downloads the version if not already present.
        
        Args:
            version: kubectl version to use
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            normalized_version = self._normalize_version(version)
            
            # Ensure version is downloaded
            kubectl_path = self.versions_dir / f"kubectl-{normalized_version}"
            if not kubectl_path.exists():
                success, error = self.download_kubectl(version)
                if not success:
                    return False, error
            
            # Create/update symlink
            if self.kubectl_symlink.exists():
                if self.kubectl_symlink.is_symlink():
                    self.kubectl_symlink.unlink()
                else:
                    # Backup existing kubectl if it's not a symlink
                    backup_path = self.kubectl_symlink.with_suffix(".backup")
                    shutil.move(self.kubectl_symlink, backup_path)
                    logger.info(f"Backed up existing kubectl to {backup_path}")
            
            # Create symlink
            self.kubectl_symlink.symlink_to(kubectl_path)
            logger.info(f"Set kubectl to version {version} (symlink: {self.kubectl_symlink} -> {kubectl_path})")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to set kubectl version {version}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_kubectl_path(self) -> Optional[Path]:
        """
        Get the path to the active kubectl binary.
        
        Returns:
            Path to kubectl binary, or None if not found
        """
        # Check symlink first
        if self.kubectl_symlink.exists():
            if self.kubectl_symlink.is_symlink():
                target = self.kubectl_symlink.readlink()
                if target.exists():
                    return self.kubectl_symlink
        
        # Check if kubectl is in PATH
        kubectl_in_path = shutil.which("kubectl")
        if kubectl_in_path:
            return Path(kubectl_in_path)
        
        return None
    
    def get_installed_versions(self) -> list:
        """Get list of installed kubectl versions"""
        versions = []
        for kubectl_file in self.versions_dir.glob("kubectl-*"):
            if kubectl_file.is_file() and os.access(kubectl_file, os.X_OK):
                version = kubectl_file.name.replace("kubectl-", "")
                versions.append(version)
        return sorted(versions, reverse=True)

