from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import network_router, cluster_router, device_router, volume_router, terminal_router
from app.db.database import init_db, SessionLocal
from app.services.talos_downloader import talos_downloader
from app.services.ipxe_downloader import ipxe_downloader
from app.crud import network as network_crud
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ktizo API",
    description="PXE-based deployment system for Talos Linux on Kubernetes",
    version="0.1.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

    # Download iPXE bootloader files if missing (one-time setup)
    # Files are downloaded directly to TFTP root since we're running as root
    try:
        db = SessionLocal()
        try:
            # Get TFTP root from database settings or use default
            network_settings = network_crud.get_network_settings(db)
            tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
            logger.info(f"Using TFTP root: {tftp_root}")
            
            # Initialize downloader with TFTP root (downloads directly there)
            from app.services.ipxe_downloader import IPXEDownloader
            ipxe_downloader = IPXEDownloader(tftp_root=tftp_root)
            
            logger.info("Checking for iPXE bootloader files...")
            if not ipxe_downloader.check_all_bootloaders_exist():
                logger.info("iPXE bootloader files missing, downloading...")
                success, errors = ipxe_downloader.download_all_bootloaders()
                if success:
                    logger.info("Successfully downloaded all iPXE bootloader files to TFTP root")
                else:
                    logger.error(f"Failed to download some iPXE bootloaders: {'; '.join(errors)}")
            else:
                logger.info("All iPXE bootloader files already present in TFTP root")
            
            # Build custom chainboot bootloaders with embedded scripts
            # These auto-load boot.ipxe without showing menu prompts
            # The builder will automatically attempt to install/build makebin if needed
            try:
                from app.services.ipxe_builder import IPXEBuilder
                server_ip = network_settings.server_ip if network_settings else "10.0.42.2"
                ipxe_builder = IPXEBuilder(tftp_root=tftp_root, server_ip=server_ip)
                
                logger.info("Building custom chainboot bootloaders (auto-installing tools if needed)...")
                success, errors = ipxe_builder.build_all_custom_bootloaders()
                if success:
                    logger.info("Successfully built custom chainboot bootloaders")
                    logger.info("Custom bootloaders will auto-chainload boot.ipxe without menu prompts")
                else:
                    if "makebin" in str(errors).lower() or "not available" in str(errors).lower():
                        logger.warning("Could not build custom bootloaders - makebin unavailable")
                        logger.warning("The builder attempted to install/build makebin automatically")
                        logger.warning("You may need to install build tools manually:")
                        logger.warning("  - git, make, gcc (for building from source)")
                        logger.warning("  - Or install iPXE development packages")
                        logger.warning("Falling back to standard bootloaders (may show menu prompts)")
                        logger.info("Chainboot script created at TFTP root - can be used manually")
                    else:
                        logger.error(f"Failed to build some custom bootloaders: {'; '.join(errors)}")
            except Exception as e:
                logger.warning(f"Could not build custom bootloaders (non-fatal): {e}")
                import traceback
                logger.debug(traceback.format_exc())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error checking iPXE bootloader files on startup: {e}")

    # Check if Talos boot files exist for the configured version
    # Files are downloaded directly to TFTP root since we're running as root
    db = SessionLocal()
    try:
        network_settings = network_crud.get_network_settings(db)
        if network_settings and network_settings.talos_version:
            version = network_settings.talos_version
            tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
            logger.info(f"Checking for Talos {version} boot files in TFTP root: {tftp_root}")
            
            # Initialize downloader with TFTP root (downloads directly there)
            from app.services.talos_downloader import TalosDownloader
            talos_downloader = TalosDownloader(tftp_root=tftp_root)
            
            # Check if files exist
            vmlinuz_exists = talos_downloader.file_exists(version, "vmlinuz-amd64")
            initramfs_exists = talos_downloader.file_exists(version, "initramfs-amd64.xz")

            if not vmlinuz_exists or not initramfs_exists:
                logger.info(f"Talos {version} files missing, downloading...")
                success, errors = talos_downloader.download_talos_files(version)
                if success:
                    logger.info(f"Successfully downloaded Talos {version} boot files to TFTP root")
                else:
                    logger.error(f"Failed to download Talos files: {'; '.join(errors)}")
            else:
                logger.info(f"Talos {version} boot files already present in TFTP root")
    except Exception as e:
        logger.error(f"Error checking Talos files on startup: {e}")
    finally:
        db.close()
    
    # Check and download kubectl if needed
    try:
        db = SessionLocal()
        try:
            from app.crud import cluster as cluster_crud
            from app.services.kubectl_downloader import KubectlDownloader
            
            cluster_settings = cluster_crud.get_cluster_settings(db)
            if cluster_settings and cluster_settings.kubectl_version:
                kubectl_version = cluster_settings.kubectl_version
                logger.info(f"Checking for kubectl {kubectl_version}...")
                
                kubectl_downloader = KubectlDownloader()
                
                # Set kubectl version (downloads if needed)
                success, error = kubectl_downloader.set_kubectl_version(kubectl_version)
                if success:
                    logger.info(f"kubectl {kubectl_version} is ready for terminal use")
                else:
                    logger.warning(f"Could not set kubectl version {kubectl_version}: {error}")
            else:
                # Default kubectl version if no cluster settings
                logger.info("No cluster settings found, using default kubectl version 1.28.0")
                kubectl_downloader = KubectlDownloader()
                kubectl_downloader.set_kubectl_version("1.28.0")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error setting up kubectl on startup (non-fatal): {e}")

# Additional middleware to ensure CORS headers are always present
# This runs after CORSMiddleware to ensure headers are on all responses
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add CORS headers to all responses (ensures they're present even on errors)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# CORS middleware for Vue frontend
# Allow all origins for native installation (when accessing from remote IPs)
# Note: allow_credentials must be False when allow_origins=["*"]
# In production, you may want to restrict this to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for native installation
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Explicit methods
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add CORS header middleware (runs last to ensure headers on all responses)
app.add_middleware(CORSHeaderMiddleware)

# Define routes before including routers to avoid conflicts
@app.get("/")
async def root():
    return {
        "message": "Ktizo API",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Serve boot.ipxe via HTTP - must be defined before device_router with empty prefix
@app.get("/pxe/boot.ipxe")
async def serve_boot_ipxe():
    """Serve boot.ipxe script via HTTP for iPXE auto-execution"""
    db = SessionLocal()
    try:
        network_settings = network_crud.get_network_settings(db)
        tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
        boot_ipxe_path = Path(tftp_root) / "pxe" / "boot.ipxe"
        
        if boot_ipxe_path.exists():
            return FileResponse(
                str(boot_ipxe_path),
                media_type="text/plain",
                headers={"Content-Type": "text/plain; charset=utf-8"}
            )
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="boot.ipxe not found")
    finally:
        db.close()

# Register a device by MAC address during PXE boot
# Called by boot.ipxe to ensure all booting devices appear in the UI
@app.get("/pxe/register/{mac_address}")
async def register_pxe_device(mac_address: str):
    """Register a PXE-booting device. Creates a pending device entry if unknown."""
    from app.crud import device as device_crud
    from app.services.websocket_manager import websocket_manager

    db = SessionLocal()
    try:
        device, is_new = device_crud.register_or_get_device(db, mac_address)
        if is_new:
            await websocket_manager.broadcast_event({
                "type": "device_discovered",
                "mac_address": device.mac_address
            })
            logger.info(f"New PXE device registered: {mac_address}")
        return Response(content="ok", media_type="text/plain")
    finally:
        db.close()

# Serve Talos machine configs via HTTP at /talos/configs/{mac}.yaml
# This is the URL format used by iPXE boot scripts (no /api/v1 prefix)
# Generates configs on the fly from base templates + device settings
@app.get("/talos/configs/{mac_address}.yaml")
async def serve_talos_config(mac_address: str):
    """Generate and serve Talos machine configuration for a device by MAC address."""
    from fastapi.responses import Response as FastResponse
    from app.crud import device as device_crud
    from app.crud import network as network_crud
    from app.db.models import DeviceStatus
    from app.services.config_generator import ConfigGenerator

    db = SessionLocal()
    try:
        # Register or get device
        device, is_new = device_crud.register_or_get_device(db, mac_address)

        # Check if device is approved
        if device.status != DeviceStatus.APPROVED:
            network_settings = network_crud.get_network_settings(db)
            strict_mode = network_settings.strict_boot_mode if network_settings else True

            if strict_mode:
                return FastResponse(
                    content=f"# Device {mac_address} not approved (status: {device.status.value})\n",
                    status_code=403,
                    media_type="text/plain",
                )

        # Update last config download time
        device_crud.update_config_download_time(db, mac_address)

        # Reset wipe_on_next_boot flag after config is downloaded
        # (the wipe will happen on next boot when this config is applied)
        wipe_flag_was_set = False
        if device.wipe_on_next_boot:
            wipe_flag_was_set = True
            device.wipe_on_next_boot = False
            db.commit()
            db.refresh(device)  # Refresh to get updated device
            logger.info(f"Reset wipe_on_next_boot flag for device {mac_address} after config download")
            
            # Regenerate boot.ipxe script to reflect the flag change
            # This ensures the next PXE boot won't have the wipe parameter
            try:
                from app.services.ipxe_generator import IPXEGenerator
                network_settings = network_crud.get_network_settings(db)
                tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
                ipxe_generator = IPXEGenerator(tftp_root=tftp_root)
                all_devices = device_crud.get_devices(db, skip=0, limit=1000)
                server_ip = ipxe_generator.get_server_ip_from_settings(db)
                strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
                ipxe_generator.generate_boot_script(all_devices, server_ip, strict_mode=strict_mode)
                logger.info(f"Regenerated boot.ipxe after resetting wipe flag for {mac_address}")
            except Exception as e:
                logger.warning(f"Failed to regenerate boot.ipxe after wipe flag reset: {e}")

        # Generate config on the fly from base template + device settings
        try:
            config_generator = ConfigGenerator()
            config_yaml, _ = config_generator.generate_config_from_params(
                mac_address=device.mac_address,
                node_type=device.role.value if device.role else "worker",
                hostname=device.hostname,
                ip_address=device.ip_address,
                wipe_on_next_boot=False,  # Always False here since we just reset it
                save_to_disk=True,
            )
            return FastResponse(
                content=config_yaml,
                media_type="application/x-yaml",
            )
        except FileNotFoundError as e:
            return FastResponse(
                content=f"# Base config template not found: {e}\n# Generate cluster configs first via the Ktizo UI.\n",
                status_code=503,
                media_type="text/plain",
            )
        except Exception as e:
            logger.error(f"Failed to generate config for {mac_address}: {e}")
            return FastResponse(
                content=f"# Error generating config for {mac_address}: {e}\n",
                status_code=500,
                media_type="text/plain",
            )
    finally:
        db.close()

# Add explicit OPTIONS handler for CORS preflight (backup)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    from fastapi import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Include API routers
app.include_router(device_router.router, prefix="/api/v1", tags=["devices"])
app.include_router(network_router.router, prefix="/api/v1/network", tags=["network"])
app.include_router(cluster_router.router, prefix="/api/v1/cluster", tags=["cluster"])
app.include_router(volume_router.router, prefix="/api/v1/volumes", tags=["volumes"])
app.include_router(terminal_router.router, tags=["terminal"])
