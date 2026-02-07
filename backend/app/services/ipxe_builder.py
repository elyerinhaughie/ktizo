"""Service for building custom iPXE bootloaders with embedded chainboot scripts"""
import logging
import os
import subprocess
import shutil
import stat
import pwd
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
    
    def _install_makebin(self) -> bool:
        """
        Attempt to install or build makebin automatically.
        
        Returns:
            True if makebin is now available, False otherwise
        """
        if self._check_makebin():
            return True
        
        logger.info("makebin not found, attempting to install/build...")
        
        # Method 1: Try to install via package manager
        install_commands = [
            ["apt-get", "update", "-qq"],
            ["apt-get", "install", "-y", "ipxe", "ipxe-qemu"],
            # Some distros have makebin in different packages
            ["apt-get", "install", "-y", "ipxe-tools"],
        ]
        
        if os.getuid() == 0:  # Only if running as root
            try:
                for cmd in install_commands:
                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        if result.returncode == 0:
                            logger.info(f"Installed package via: {cmd[0]}")
                            if self._check_makebin():
                                return True
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
            except Exception as e:
                logger.debug(f"Package installation failed: {e}")
        
        # Method 2: Try to download pre-built makebin
        # (This would require knowing where to get it)
        
        # Method 3: Build from iPXE source
        return self._build_makebin_from_source()
    
    def _build_makebin_from_source(self) -> bool:
        """
        Build makebin from iPXE source code.
        Actually, iPXE doesn't have a separate makebin - we build bootloaders directly with EMBED.
        
        Returns:
            True if we can build bootloaders, False otherwise
        """
        # iPXE uses EMBED parameter directly, not makebin
        # We'll build bootloaders directly in build_custom_bootloader
        # Just verify we have iPXE source available
        ipxe_dirs = [
            Path("/tmp/ipxe"),
            Path("/usr/src/ipxe"),
            Path.home() / "ipxe",
        ]
        
        # Check if iPXE source already exists
        ipxe_dir = None
        for dir_path in ipxe_dirs:
            if dir_path.exists() and (dir_path / "src" / "Makefile").exists():
                ipxe_dir = dir_path
                logger.info(f"Found existing iPXE source at {ipxe_dir}")
                return True
        
        # Clone if not found
        ipxe_dir = Path("/tmp/ipxe")
        logger.info("Cloning iPXE source code...")
        try:
            if ipxe_dir.exists():
                shutil.rmtree(ipxe_dir)
            
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/ipxe/ipxe.git", str(ipxe_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and (ipxe_dir / "src" / "Makefile").exists():
                logger.info("iPXE source cloned successfully")
                return True
            else:
                logger.error(f"Failed to clone iPXE: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Timeout cloning iPXE source")
            return False
        except Exception as e:
            logger.error(f"Error cloning iPXE: {e}")
            return False
    
    def _create_chainboot_script(self, use_http: bool = True) -> str:
        """
        Create the embedded chainboot script that auto-loads boot.ipxe.
        
        This script is embedded into the iPXE bootloader and runs automatically
        when the bootloader loads, preventing menu prompts.
        
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
echo Ktizo PXE Chainboot (Embedded)
echo ========================================

# Prevent chainboot from re-executing itself
isset chainboot_done && exit || set chainboot_done 1

echo Configuring network...

# IMPORTANT: Do NOT use 'dhcp net0' — in proxy DHCP mode it triggers
# PXE service discovery which causes dnsmasq to serve this chainboot
# binary again, creating a loop.
#
# Instead, just open the interface. The UNDI layer from the initial
# PXE boot still has network configured (IP from the real DHCP server).
# Then chain directly to the boot script via HTTP.

ifopen net0 || echo [WARN] ifopen failed, trying chain anyway...

echo Chainloading boot script...
echo URL: {boot_url}

# Try chain with UNDI network first (fastest path)
chain {boot_url} && exit ||

# If that failed, the interface may need DHCP.
# Use ifconf to get just an IP without triggering PXE vendor options.
echo [WARN] Direct chain failed, trying DHCP...
dhcp net0 || {{
    echo ERROR: DHCP failed
    sleep 3
    exit
}}

chain {boot_url} || {{
    echo ========================================
    echo ERROR: Failed to load boot script
    echo ========================================
    echo Could not load: {boot_url}
    echo
    echo Retrying via TFTP...
    chain tftp://{self.server_ip}/pxe/boot.ipxe || {{
        echo TFTP also failed. Exiting.
        sleep 5
        exit
    }}
}}
"""
        return script
    
    def _build_with_ipxe_embed(self, script_path: Path, base_bootloader: str, output_name: str) -> bool:
        """
        Build custom bootloader using iPXE make with EMBED parameter.
        This is the preferred method - builds directly from source with embedded script.
        
        Args:
            script_path: Path to chainboot script to embed
            base_bootloader: Base bootloader name (e.g., "undionly.kpxe")
            output_name: Output filename (e.g., "undionly-chainboot.kpxe")
            
        Returns:
            True if build succeeded, False otherwise
        """
        # Find iPXE source
        ipxe_dirs = [
            Path("/tmp/ipxe"),
            Path("/usr/src/ipxe"),
            Path.home() / "ipxe",
        ]
        
        ipxe_dir = None
        for dir_path in ipxe_dirs:
            if dir_path.exists() and (dir_path / "src" / "Makefile").exists():
                ipxe_dir = dir_path
                break
        
        # Clone if not found
        if ipxe_dir is None:
            ipxe_dir = Path("/tmp/ipxe")
            logger.info("Cloning iPXE source for building custom bootloaders...")
            try:
                if ipxe_dir.exists():
                    shutil.rmtree(ipxe_dir)
                
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", "https://github.com/ipxe/ipxe.git", str(ipxe_dir)],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode != 0:
                    logger.warning(f"Failed to clone iPXE: {result.stderr}")
                    return False
            except Exception as e:
                logger.warning(f"Error cloning iPXE: {e}")
                return False
        
        # Map bootloader names to iPXE make targets
        bootloader_targets = {
            "undionly.kpxe": "bin/undionly.kpxe",
            "ipxe.efi": "bin-x86_64-efi/ipxe.efi",
            "ipxe.pxe": "bin/ipxe.pxe",
        }
        
        target = bootloader_targets.get(base_bootloader)
        if not target:
            logger.warning(f"Unknown bootloader type: {base_bootloader}")
            return False
        
        # Build with embedded script
        try:
            logger.info(f"Building {base_bootloader} with embedded chainboot script...")
            result = subprocess.run(
                ["make", "-C", str(ipxe_dir / "src"), target, f"EMBED={script_path}"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            if result.returncode == 0:
                built_file = ipxe_dir / "src" / target
                if built_file.exists():
                    # Copy to TFTP root
                    output_path = self.tftp_root / output_name
                    shutil.copy(built_file, output_path)
                    self._set_file_permissions(output_path)
                    logger.info(f"Successfully built custom bootloader: {output_path}")
                    return True
                else:
                    logger.warning(f"Build succeeded but file not found: {built_file}")
                    return False
            else:
                logger.warning(f"iPXE build failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("Timeout building iPXE bootloader")
            return False
        except Exception as e:
            logger.warning(f"Error building iPXE bootloader: {e}")
            return False
    
    def _set_file_permissions(self, file_path: Path):
        """Set proper file permissions for dnsmasq"""
        if os.getuid() == 0:
            try:
                try:
                    dnsmasq_user = pwd.getpwnam('dnsmasq')
                    dnsmasq_uid = dnsmasq_user.pw_uid
                    dnsmasq_gid = dnsmasq_user.pw_gid
                except KeyError:
                    dnsmasq_uid = 0
                    dnsmasq_gid = 0
                
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                os.chown(file_path, dnsmasq_uid, dnsmasq_gid)
            except Exception as perm_err:
                logger.warning(f"Could not set file permissions: {perm_err}")
    
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
            
            # Method 1: Use iPXE make with EMBED parameter (preferred method)
            # This builds bootloaders directly from source with embedded script
            if self._build_with_ipxe_embed(chainboot_path, base_bootloader, output_name):
                return True, None
            
            # Method 2: Try makebin if available (legacy/alternative)
            if not self.makebin_available:
                logger.info("makebin not available, attempting to install/build...")
                if self._install_makebin():
                    self.makebin_available = True
                    logger.info("Successfully installed makebin")
            
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
                        self._set_file_permissions(output_path)
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
                # Fallback - chainboot script created but not embedded
                logger.warning("Cannot embed script into bootloader - iPXE source or makebin not available")
                logger.warning("Created standalone chainboot script - configure dnsmasq to serve it first")
                logger.info(f"Chainboot script available at: {chainboot_path}")
                return False, "iPXE source or makebin not available. Install build tools (git, make, gcc) to build custom bootloaders."
                
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

