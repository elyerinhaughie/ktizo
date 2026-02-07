"""Service for building custom iPXE bootloaders with embedded chainboot scripts"""
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class IPXEBuilder:
    def __init__(self, tftp_root: str = None, server_ip: str = None):
        """
        Initialize iPXE builder.
        
        Args:
            tftp_root: TFTP root directory where bootloaders are stored
            server_ip: Server IP address for chainloading boot.ipxe
        """
        # Use provided TFTP root, or get from database/environment, or use default
        if tftp_root:
            tftp_path = Path(tftp_root) / "pxe"
        else:
            tftp_root_env = os.getenv("TFTP_ROOT", settings.TFTP_ROOT)
            tftp_path = Path(tftp_root_env) / "pxe"
        
        self.tftp_root = tftp_path
        self.server_ip = server_ip or "10.0.42.2"
        
        # Check if makebin is available (from iPXE tools)
        self.makebin_available = self._check_makebin()
        
    def _check_makebin(self) -> bool:
        """Check if makebin tool is available"""
        try:
            result = subprocess.run(
                ["which", "makebin"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _create_chainboot_script(self, use_http: bool = True) -> str:
        """
        Create the embedded chainboot script that auto-loads boot.ipxe.
        
        Args:
            use_http: If True, use HTTP URL; if False, use TFTP
            
        Returns:
            The chainboot script content
        """
        if use_http:
            boot_url = f"http://{self.server_ip}:8000/pxe/boot.ipxe"
        else:
            boot_url = f"tftp://{self.server_ip}/pxe/boot.ipxe"
        
        script = f"""#!ipxe

echo ========================================
echo Ktizo PXE Chainboot
echo ========================================
echo Auto-loading boot script from server...
echo Server: {self.server_ip}
echo Boot URL: {boot_url}

# Prevent infinite loops
isset chainboot_done && exit || set chainboot_done 1

# Auto-chainload the boot script
chain {boot_url} || {{
    echo ========================================
    echo ERROR: Failed to load boot script
    echo ========================================
    echo Could not load: {boot_url}
    echo Check network connectivity and server availability
    sleep 10
    exit
}}
"""
        return script
    
    def build_custom_bootloader(self, base_bootloader: str = "undionly.kpxe", output_name: str = "undionly-k chainboot.kpxe") -> Tuple[bool, Optional[str]]:
        """
        Build a custom iPXE bootloader with embedded chainboot script.
        
        This uses makebin to embed the chainboot script into the bootloader.
        If makebin is not available, creates a standalone script file instead.
        
        Args:
            base_bootloader: Base bootloader file to embed script into (e.g., "undionly.kpxe")
            output_name: Output filename for custom bootloader
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            base_path = self.tftp_root / base_bootloader
            if not base_path.exists():
                return False, f"Base bootloader not found: {base_path}"
            
            # Create chainboot script
            chainboot_script = self._create_chainboot_script(use_http=True)
            chainboot_path = self.tftp_root / "chainboot.ipxe"
            
            try:
                with open(chainboot_path, 'w') as f:
                    f.write(chainboot_script)
                logger.info(f"Created chainboot script at {chainboot_path}")
            except Exception as e:
                return False, f"Failed to create chainboot script: {e}"
            
            output_path = self.tftp_root / output_name
            
            if self.makebin_available:
                # Use makebin to embed script into bootloader
                try:
                    cmd = [
                        "makebin",
                        chainboot_path,
                        base_path,
                        output_path
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully built custom bootloader: {output_path}")
                        # Set proper permissions
                        if os.getuid() == 0:
                            try:
                                import stat
                                import pwd
                                try:
                                    dnsmasq_user = pwd.getpwnam('dnsmasq')
                                    dnsmasq_uid = dnsmasq_user.pw_uid
                                    dnsmasq_gid = dnsmasq_user.pw_gid
                                except KeyError:
                                    dnsmasq_uid = 0
                                    dnsmasq_gid = 0
                                
                                os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                                os.chown(output_path, dnsmasq_uid, dnsmasq_gid)
                            except Exception as perm_err:
                                logger.warning(f"Could not set file permissions: {perm_err}")
                        
                        return True, None
                    else:
                        error_msg = f"makebin failed: {result.stderr}"
                        logger.error(error_msg)
                        return False, error_msg
                        
                except subprocess.TimeoutExpired:
                    return False, "makebin command timed out"
                except Exception as e:
                    return False, f"Failed to run makebin: {e}"
            else:
                # Fallback: just copy the chainboot script
                # This won't work as a bootloader, but documents the approach
                logger.warning("makebin not available - cannot embed script into bootloader")
                logger.warning("Install iPXE tools (makebin) to build custom bootloaders")
                return False, "makebin tool not available. Install iPXE development tools."
                
        except Exception as e:
            logger.error(f"Failed to build custom bootloader: {e}", exc_info=True)
            return False, str(e)
    
    def build_all_custom_bootloaders(self) -> Tuple[bool, list]:
        """
        Build custom bootloaders for all architectures.
        
        Returns:
            Tuple of (success: bool, errors: list)
        """
        errors = []
        
        # Map of base bootloaders to custom output names
        bootloaders = {
            "undionly.kpxe": "undionly-chainboot.kpxe",
            "ipxe.efi": "ipxe-chainboot.efi",
            "ipxe.pxe": "ipxe-chainboot.pxe",
        }
        
        for base_name, output_name in bootloaders.items():
            if (self.tftp_root / base_name).exists():
                success, error = self.build_custom_bootloader(base_name, output_name)
                if not success:
                    errors.append(f"{base_name}: {error}")
            else:
                logger.warning(f"Base bootloader not found: {base_name}, skipping")
        
        return len(errors) == 0, errors

