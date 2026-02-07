from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import network_router, cluster_router, device_router, volume_router
from app.db.database import init_db, SessionLocal
from app.services.talos_downloader import talos_downloader
from app.services.ipxe_downloader import ipxe_downloader
from app.crud import network as network_crud
import logging

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
    try:
        logger.info("Checking for iPXE bootloader files...")
        if not ipxe_downloader.check_all_bootloaders_exist():
            logger.info("iPXE bootloader files missing, downloading...")
            success, errors = ipxe_downloader.download_all_bootloaders()
            if success:
                logger.info("Successfully downloaded all iPXE bootloader files")
            else:
                logger.error(f"Failed to download some iPXE bootloaders: {'; '.join(errors)}")
        else:
            logger.info("All iPXE bootloader files already present")
        
        # Sync iPXE files to TFTP root (from database settings or default)
        db = SessionLocal()
        try:
            network_settings = network_crud.get_network_settings(db)
            tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
            logger.info(f"Syncing iPXE files to TFTP root: {tftp_root}")
            sync_success, sync_errors = ipxe_downloader.sync_to_tftp_root(tftp_root)
            if sync_success:
                logger.info("Successfully synced iPXE files to TFTP root")
            else:
                logger.warning(f"Synced iPXE files with some errors: {'; '.join(sync_errors)}")
        except Exception as e:
            logger.warning(f"Could not sync iPXE files to TFTP root: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error checking iPXE bootloader files on startup: {e}")

    # Check if Talos boot files exist for the configured version
    db = SessionLocal()
    try:
        settings = network_crud.get_network_settings(db)
        if settings and settings.talos_version:
            version = settings.talos_version
            logger.info(f"Checking for Talos {version} boot files...")

            # Check if files exist
            vmlinuz_exists = talos_downloader.file_exists(version, "vmlinuz-amd64")
            initramfs_exists = talos_downloader.file_exists(version, "initramfs-amd64.xz")

            if not vmlinuz_exists or not initramfs_exists:
                logger.info(f"Talos {version} files missing, downloading...")
                success, errors = talos_downloader.download_talos_files(version)
                if success:
                    logger.info(f"Successfully downloaded Talos {version} boot files")
                else:
                    logger.error(f"Failed to download Talos files: {'; '.join(errors)}")
            else:
                logger.info(f"Talos {version} boot files already present")
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

# Include routers
app.include_router(network_router.router, prefix="/api/v1/network", tags=["network"])
app.include_router(cluster_router.router, prefix="/api/v1/cluster", tags=["cluster"])
app.include_router(device_router.router, prefix="/api/v1", tags=["devices"])
app.include_router(volume_router.router, prefix="/api/v1/volumes", tags=["volumes"])
# Also include device_router without prefix for /talos/configs route (used by iPXE)
app.include_router(device_router.router, prefix="", tags=["talos-configs"])

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
