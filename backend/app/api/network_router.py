from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.network import NetworkSettingsResponse, NetworkSettingsCreate, NetworkSettingsUpdate
from app.crud import network as network_crud
from app.models.network import DNSMasqConfig
from app.services.template_service import template_service
from app.services.talos_downloader import talos_downloader

router = APIRouter()

@router.get("/settings", response_model=NetworkSettingsResponse)
async def get_network_settings(db: Session = Depends(get_db)):
    """Get current network settings"""
    settings = network_crud.get_network_settings(db)
    if not settings:
        raise HTTPException(status_code=404, detail="Network settings not found. Please create settings first.")
    return settings

@router.post("/settings", response_model=NetworkSettingsResponse)
async def create_network_settings(settings: NetworkSettingsCreate, db: Session = Depends(get_db)):
    """Create network settings"""
    existing = network_crud.get_network_settings(db)
    if existing:
        raise HTTPException(status_code=400, detail="Network settings already exist. Use PUT to update.")
    return network_crud.create_network_settings(db, settings)

@router.put("/settings/{settings_id}", response_model=NetworkSettingsResponse)
async def update_network_settings(settings_id: int, settings: NetworkSettingsUpdate, db: Session = Depends(get_db)):
    """Update network settings and automatically apply changes"""
    from app.crud import device as device_crud
    from app.db.models import DeviceStatus
    from app.services.ipxe_generator import IPXEGenerator

    # Get current settings to check if talos_version changed
    current = network_crud.get_network_settings(db)
    old_version = current.talos_version if current else None

    updated = network_crud.update_network_settings(db, settings_id, settings)
    if not updated:
        raise HTTPException(status_code=404, detail="Network settings not found")

    # Automatically apply settings: compile dnsmasq config and regenerate boot.ipxe
    errors = []

    # Download Talos files if version changed or files are missing
    version_to_check = updated.talos_version
    if version_to_check:
        try:
            # Check if files exist
            vmlinuz_exists = talos_downloader.file_exists(version_to_check, "vmlinuz-amd64")
            initramfs_exists = talos_downloader.file_exists(version_to_check, "initramfs-amd64.xz")

            # Download if version changed OR if files are missing
            version_changed = version_to_check != old_version
            files_missing = not vmlinuz_exists or not initramfs_exists

            if version_changed or files_missing:
                if version_changed:
                    print(f"Talos version changed from {old_version} to {version_to_check}, downloading files...")
                else:
                    print(f"Talos {version_to_check} files missing, downloading...")

                success, download_errors = talos_downloader.download_talos_files(version_to_check)
                if not success:
                    error_msg = f"Failed to download Talos files: {'; '.join(download_errors)}"
                    print(f"ERROR: {error_msg}")
                    errors.append(error_msg)
                else:
                    print(f"Successfully downloaded Talos {version_to_check} files")
            else:
                print(f"Talos {version_to_check} files already exist, skipping download")
        except Exception as e:
            error_msg = f"Failed to download Talos files: {str(e)}"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)

    # Compile dnsmasq configuration
    try:
        config_dict = {
            "interface": updated.interface,
            "server_ip": updated.server_ip,
            "dhcp_mode": updated.dhcp_mode,
            "dhcp_network": updated.dhcp_network,
            "dhcp_netmask": updated.dhcp_netmask,
            "dhcp_range_start": updated.dhcp_range_start,
            "dhcp_range_end": updated.dhcp_range_end,
            "dns_port": updated.dns_port,
            "dns_server": updated.dns_server,
            "tftp_root": updated.tftp_root,
            "tftp_secure": updated.tftp_secure,
            "ipxe_boot_script": updated.ipxe_boot_script,
            "pxe_prompt": updated.pxe_prompt,
            "pxe_timeout": updated.pxe_timeout,
            "enable_logging": updated.enable_logging,
        }
        config_text, output_path = template_service.compile_dnsmasq_config(**config_dict)
        print(f"Successfully generated dnsmasq config at {output_path}")
    except PermissionError as e:
        error_msg = f"Permission denied generating dnsmasq config: {str(e)}. Check write permissions for compiled directory."
        print(f"ERROR: {error_msg}")
        errors.append(error_msg)
    except FileNotFoundError as e:
        error_msg = f"Template or directory not found: {str(e)}. Check that templates directory exists and is accessible."
        print(f"ERROR: {error_msg}")
        errors.append(error_msg)
    except Exception as e:
        error_msg = f"Failed to generate dnsmasq.conf: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        errors.append(error_msg)

    # Regenerate boot.ipxe with all approved devices
    try:
        from app.crud import cluster as cluster_crud

        # Initialize generator with TFTP root (generates directly there)
        ipxe_generator = IPXEGenerator(tftp_root=updated.tftp_root)
        approved_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)

        # Get cluster settings for install_disk
        cluster_settings = cluster_crud.get_cluster_settings(db)
        install_disk = cluster_settings.install_disk if cluster_settings else "/dev/sda"

        try:
            success = ipxe_generator.generate_boot_script(
                approved_devices,
                updated.server_ip,
                talos_version=updated.talos_version,
                strict_mode=updated.strict_boot_mode,
                install_disk=install_disk
            )
            if success:
                print(f"Successfully generated boot.ipxe at {ipxe_generator.output_dir}/boot.ipxe")
        except PermissionError as e:
            error_msg = f"Permission denied generating boot.ipxe: {str(e)}. Check write permissions for compiled directory."
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
        except FileNotFoundError as e:
            error_msg = f"Template or directory not found for boot.ipxe: {str(e)}. Check that templates directory exists."
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            # Exception already has detailed message from generate_boot_script
            error_msg = str(e)
            print(f"ERROR: {error_msg}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            errors.append(error_msg)
    except Exception as e:
        # Catch any unexpected errors in the outer try block
        error_msg = f"Unexpected error during boot.ipxe generation: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        errors.append(error_msg)

    # If there were errors, raise an exception with details
    if errors:
        error_summary = "Settings saved to database, but the following errors occurred while applying them:\n\n"
        for i, error in enumerate(errors, 1):
            error_summary += f"{i}. {error}\n"
        error_summary += "\nCheck the backend logs for more details."
        raise HTTPException(
            status_code=500,
            detail=error_summary.strip()
        )

    print(f"Auto-applied network settings: regenerated dnsmasq.conf and boot.ipxe")
    return updated

@router.post("/settings/apply")
async def apply_network_settings(db: Session = Depends(get_db)):
    """Apply current network settings by compiling DNSMASQ configuration"""
    settings = network_crud.get_network_settings(db)
    if not settings:
        raise HTTPException(status_code=404, detail="Network settings not found")

    # Convert database model to dict for template rendering
    config_dict = {
        "interface": settings.interface,
        "server_ip": settings.server_ip,
        "dhcp_mode": settings.dhcp_mode,
        "dhcp_network": settings.dhcp_network,
        "dhcp_netmask": settings.dhcp_netmask,
        "dhcp_range_start": settings.dhcp_range_start,
        "dhcp_range_end": settings.dhcp_range_end,
        "dns_port": settings.dns_port,
        "dns_server": settings.dns_server,
        "tftp_root": settings.tftp_root,
        "tftp_secure": settings.tftp_secure,
        "ipxe_boot_script": settings.ipxe_boot_script,
        "pxe_prompt": settings.pxe_prompt,
        "pxe_timeout": settings.pxe_timeout,
        "enable_logging": settings.enable_logging,
    }

    try:
        config_text, output_path = template_service.compile_dnsmasq_config(**config_dict)
        return {
            "message": f"Network settings applied successfully. DNSMASQ config written to {output_path}. DNSMASQ will reload automatically.",
            "config": config_text,
            "path": output_path
        }
    except PermissionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Permission denied: Failed to write dnsmasq config. {str(e)}. Check that the compiled directory is writable."
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"File or directory not found: {str(e)}. Check that templates and compiled directories exist."
        )
    except Exception as e:
        import traceback
        error_detail = f"Failed to apply settings: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
