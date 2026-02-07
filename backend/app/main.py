from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import network_router, cluster_router, device_router, volume_router
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
