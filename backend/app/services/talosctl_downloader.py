"""
Service for downloading and managing talosctl binary versions
"""
import os
import platform
import subprocess
import logging
from pathlib import Path
import shutil
import requests

logger = logging.getLogger(__name__)


class TalosctlDownloader:
    """Manages talosctl binary downloads and version management"""
    
    def __init__(self):
        # Install to ktizo project backend directory
        self.backend_dir = Path(__file__).parent.parent.parent
        self.talosctl_dir = self.backend_dir
        self.talosctl_path = self.talosctl_dir / "talosctl"
    
    def _get_os_arch(self) -> tuple[str, str]:
        """Get OS and architecture for talosctl download"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "darwin":
            os_type = "darwin"
        elif system == "linux":
            os_type = "linux"
        else:
            raise ValueError(f"Unsupported OS: {system}")
        
        if machine in ("arm64", "aarch64"):
            arch = "arm64"
        elif machine in ("x86_64", "amd64"):
            arch = "amd64"
        else:
            arch = "amd64"  # Default fallback
        
        return os_type, arch
    
    def _ensure_v_prefix(self, version: str) -> str:
        """Ensure version has 'v' prefix"""
        if not version.startswith("v"):
            return f"v{version}"
        return version
    
    def download_talosctl(self, version: str) -> tuple[bool, str]:
        """
        Download a specific version of talosctl
        
        Args:
            version: Talos version (e.g., "1.12.2" or "v1.12.2")
            
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            version = self._ensure_v_prefix(version)
            os_type, arch = self._get_os_arch()
            
            # Download URL
            url = f"https://github.com/siderolabs/talos/releases/download/{version}/talosctl-{os_type}-{arch}"
            
            logger.info(f"Downloading talosctl {version} from {url}")
            
            # Ensure directory exists
            self.talosctl_dir.mkdir(parents=True, exist_ok=True)
            
            # Download to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
                tmp_path = Path(tmp_file.name)
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
            
            # Make temp file executable
            os.chmod(tmp_path, 0o755)
            
            # Verify it works before installing
            result = subprocess.run(
                [str(tmp_path), "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                tmp_path.unlink()
                error_msg = f"Downloaded talosctl failed verification: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
            
            # Move to final location
            if self.talosctl_path.exists():
                self.talosctl_path.unlink()
            
            shutil.move(str(tmp_path), str(self.talosctl_path))
            
            # Ensure executable
            os.chmod(self.talosctl_path, 0o755)
            
            # Verify it works (already verified before moving, but double-check)
            result = subprocess.run(
                [str(self.talosctl_path), "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"✅ talosctl {version} installed to {self.talosctl_path} and verified")
                return True, ""
            else:
                error_msg = f"talosctl installed but verification failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Failed to download talosctl: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error downloading talosctl: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def set_talosctl_version(self, version: str) -> tuple[bool, str]:
        """
        Download and set a specific talosctl version
        
        Args:
            version: Talos version (e.g., "1.12.2" or "v1.12.2")
            
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Check if current version matches
        current_version = self.get_talosctl_version()
        version = self._ensure_v_prefix(version)
        
        if current_version and current_version == version:
            logger.info(f"talosctl {version} already installed")
            return True, ""
        
        # Download new version
        return self.download_talosctl(version)
    
    def get_talosctl_version(self) -> str | None:
        """Get the version of the currently installed talosctl"""
        if not self.talosctl_path.exists():
            return None
        
        try:
            result = subprocess.run(
                [str(self.talosctl_path), "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse version from output (e.g., "Client:\n\tTag: v1.12.2")
                for line in result.stdout.split('\n'):
                    if 'Tag:' in line:
                        version = line.split('Tag:')[-1].strip()
                        return self._ensure_v_prefix(version)
            
            return None
        except Exception as e:
            logger.warning(f"Could not get talosctl version: {e}")
            return None
    
    def get_talosctl_path(self) -> Path | None:
        """Get the path to the talosctl binary"""
        if self.talosctl_path.exists():
            return self.talosctl_path
        
        # Check if it's in PATH
        talosctl_in_path = shutil.which("talosctl")
        if talosctl_in_path:
            return Path(talosctl_in_path)
        
        return None

