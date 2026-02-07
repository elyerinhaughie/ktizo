from fastapi import APIRouter, HTTPException, Depends, Response, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.device import (
    DeviceResponse,
    DeviceCreate,
    DeviceUpdate,
    DeviceApprovalRequest,
    ConfigDownloadRequest
)
from app.crud import device as device_crud
from app.crud import cluster as cluster_crud
from app.crud import network as network_crud
from app.db.models import DeviceStatus, DeviceRole, Device
from app.services.config_generator import ConfigGenerator
from app.services.ipxe_generator import IPXEGenerator
from app.services.websocket_manager import websocket_manager
from app.utils.network import get_next_available_ip, get_first_usable_ip, is_fqdn
from typing import List, Optional
from pathlib import Path
import yaml

router = APIRouter()
config_generator = ConfigGenerator()
ipxe_generator = IPXEGenerator()

@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(skip: int = 0, limit: int = 100, status: str = None, db: Session = Depends(get_db)):
    """List all devices, optionally filtered by status"""
    if status:
        try:
            status_enum = DeviceStatus(status)
            devices = device_crud.get_devices_by_status(db, status_enum, skip, limit)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        devices = device_crud.get_devices(db, skip, limit)
    return devices

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int, db: Session = Depends(get_db)):
    """Get device by ID"""
    device = device_crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.post("/devices", response_model=DeviceResponse)
async def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """Create a new device"""
    # Check if device with MAC already exists
    existing = device_crud.get_device_by_mac(db, device.mac_address)
    if existing:
        raise HTTPException(status_code=400, detail="Device with this MAC address already exists")

    return device_crud.create_device(db, device)

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: int, device: DeviceUpdate, db: Session = Depends(get_db)):
    """Update device"""
    # Get the current device
    current_device = device_crud.get_device(db, device_id)
    if not current_device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Check if this is the only control plane node
    if current_device.status == DeviceStatus.APPROVED and current_device.role == DeviceRole.CONTROLPLANE:
        # Count total approved control plane nodes
        all_controlplanes = db.query(Device).filter(
            Device.status == DeviceStatus.APPROVED,
            Device.role == DeviceRole.CONTROLPLANE
        ).all()

        is_only_controlplane = len(all_controlplanes) == 1

        if is_only_controlplane:
            # Prevent changing IP address
            if device.ip_address and device.ip_address != current_device.ip_address:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot change IP address of the only control plane node. Add another control plane node first."
                )

            # Prevent changing role
            if device.role and device.role != current_device.role:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot change role of the only control plane node. Add another control plane node first."
                )

    # Check if IP address is being changed and if it conflicts with another device
    if device.ip_address:
        existing_device_with_ip = db.query(Device).filter(
            Device.ip_address == device.ip_address,
            Device.id != device_id
        ).first()
        if existing_device_with_ip:
            raise HTTPException(
                status_code=400,
                detail=f"IP address {device.ip_address} is already assigned to device {existing_device_with_ip.mac_address} ({existing_device_with_ip.hostname or 'no hostname'})"
            )

    updated = device_crud.update_device(db, device_id, device)
    if not updated:
        raise HTTPException(status_code=404, detail="Device not found")
    return updated

@router.get("/devices/{device_id}/approval-suggestions")
async def get_approval_suggestions(device_id: int, db: Session = Depends(get_db)):
    """
    Get suggestions for approving a device including:
    - Suggested hostname
    - Suggested IP address
    - Suggested role
    - Whether this is the first device (must be control plane)
    """
    device = device_crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get cluster and network settings
    cluster_settings = cluster_crud.get_cluster_settings(db)
    network_settings = network_crud.get_network_settings(db)

    if not cluster_settings:
        raise HTTPException(status_code=400, detail="Cluster settings not configured. Please configure cluster settings first.")

    if not network_settings:
        raise HTTPException(status_code=400, detail="Network settings not configured. Please configure network settings first.")

    # Check if this is the first device
    approved_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1)
    is_first_device = len(approved_devices) == 0

    # Determine suggested role
    if is_first_device:
        suggested_role = DeviceRole.CONTROLPLANE.value
        role_locked = True
        role_reason = "First device must be a control plane node"
    else:
        # Check how many control plane nodes exist
        controlplane_count = len([d for d in device_crud.get_devices(db, skip=0, limit=1000)
                                 if d.status == DeviceStatus.APPROVED and d.role == DeviceRole.CONTROLPLANE])

        # Default to worker for any device after the first
        suggested_role = DeviceRole.WORKER.value
        role_locked = False

        if controlplane_count < 3:
            role_reason = f"You have {controlplane_count} control plane node(s). 3 recommended for HA. Change to control plane if needed."
        else:
            role_reason = "You have 3+ control plane nodes."

    # Determine suggested IP
    external_subnet = cluster_settings.external_subnet
    if not external_subnet:
        raise HTTPException(status_code=400, detail="External subnet not configured in cluster settings")

    if is_first_device:
        # First device must use cluster endpoint IP
        cluster_endpoint = cluster_settings.cluster_endpoint

        # Check if cluster_endpoint is FQDN or IP
        if is_fqdn(cluster_endpoint):
            # Use first usable IP in subnet
            suggested_ip = get_first_usable_ip(external_subnet)
            ip_reason = f"First IP in subnet (cluster endpoint '{cluster_endpoint}' is FQDN)"
        else:
            # Use the cluster endpoint IP
            suggested_ip = cluster_endpoint
            ip_reason = "Must match cluster endpoint IP"

        ip_locked = True
    else:
        # Suggest next available IP
        suggested_ip = get_next_available_ip(db, external_subnet)
        ip_locked = False
        ip_reason = "Next available IP in subnet"

    # Suggested hostname
    if device.hostname:
        suggested_hostname = device.hostname
    else:
        # Auto-generate hostname with "node" prefix
        device_count = len([d for d in device_crud.get_devices(db, skip=0, limit=1000)
                           if d.status == DeviceStatus.APPROVED])
        suggested_hostname = f"node-{device_count + 1:02d}"

    return {
        "device_id": device_id,
        "mac_address": device.mac_address,
        "is_first_device": is_first_device,
        "suggestions": {
            "hostname": suggested_hostname,
            "ip_address": suggested_ip,
            "role": suggested_role
        },
        "locked_fields": {
            "ip_address": ip_locked,
            "role": role_locked
        },
        "reasons": {
            "ip_address": ip_reason,
            "role": role_reason
        },
        "subnet": external_subnet
    }

@router.post("/devices/{device_id}/approve", response_model=DeviceResponse)
async def approve_device(device_id: int, approval_data: DeviceApprovalRequest, db: Session = Depends(get_db)):
    """
    Approve a device with required hostname, IP, and role.
    The first device must use the cluster endpoint IP and be a control plane.
    """
    device = device_crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Validate that required fields are provided
    if not approval_data.hostname:
        raise HTTPException(status_code=400, detail="Hostname is required for approval")
    if not approval_data.ip_address:
        raise HTTPException(status_code=400, detail="IP address is required for approval")
    if not approval_data.role:
        raise HTTPException(status_code=400, detail="Role is required for approval")

    # Check if IP address conflicts with another device
    existing_device_with_ip = db.query(Device).filter(
        Device.ip_address == approval_data.ip_address,
        Device.id != device_id
    ).first()
    if existing_device_with_ip:
        raise HTTPException(
            status_code=400,
            detail=f"IP address {approval_data.ip_address} is already assigned to device {existing_device_with_ip.mac_address} ({existing_device_with_ip.hostname or 'no hostname'})"
        )

    # Get cluster settings for validation
    cluster_settings = cluster_crud.get_cluster_settings(db)
    if not cluster_settings or not cluster_settings.external_subnet:
        raise HTTPException(status_code=400, detail="Cluster settings with external subnet required")

    # Check if this is the first device
    approved_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1)
    is_first_device = len(approved_devices) == 0

    # Validate first device requirements
    if is_first_device:
        # Must be control plane
        if approval_data.role != DeviceRole.CONTROLPLANE:
            raise HTTPException(
                status_code=400,
                detail="First device must be a control plane node"
            )

        # Must use cluster endpoint IP
        cluster_endpoint = cluster_settings.cluster_endpoint
        if is_fqdn(cluster_endpoint):
            # If FQDN, must use first IP in subnet
            required_ip = get_first_usable_ip(cluster_settings.external_subnet)
            if approval_data.ip_address != required_ip:
                raise HTTPException(
                    status_code=400,
                    detail=f"First device with FQDN cluster endpoint must use first IP in subnet: {required_ip}"
                )
        else:
            # If IP, must match cluster endpoint
            if approval_data.ip_address != cluster_endpoint:
                raise HTTPException(
                    status_code=400,
                    detail=f"First device must use cluster endpoint IP: {cluster_endpoint}"
                )

    # Update device with approval data
    device.hostname = approval_data.hostname
    device.ip_address = approval_data.ip_address
    device.role = approval_data.role
    db.commit()

    # Now approve the device
    device = device_crud.approve_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # If this is a control plane node, update talosconfig with endpoint and node
    if device.role == DeviceRole.CONTROLPLANE and device.ip_address:
        cp_ip = device.ip_address
        if '/' in cp_ip:
            cp_ip = cp_ip.split('/')[0]
        
        try:
            from app.api.cluster_router import update_talosconfig_endpoint_and_node
            if update_talosconfig_endpoint_and_node(cp_ip):
                logger.info(f"Updated talosconfig with new control plane node: {cp_ip}")
            else:
                logger.warning(f"Failed to update talosconfig with control plane node: {cp_ip}")
        except Exception as e:
            logger.warning(f"Error updating talosconfig after device approval: {e}")

    # Notify WebSocket clients of device approval
    await websocket_manager.broadcast_event({
        "type": "device_approved",
        "device_id": device_id
    })

    return device

@router.post("/devices/{device_id}/reject", response_model=DeviceResponse)
async def reject_device(device_id: int, db: Session = Depends(get_db)):
    """Reject a device"""
    device = device_crud.reject_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Notify WebSocket clients of device rejection
    await websocket_manager.broadcast_event({
        "type": "device_rejected",
        "device_id": device_id
    })

    return device

@router.delete("/devices/{device_id}")
async def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Delete a device"""
    success = device_crud.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    # Notify WebSocket clients of device deletion
    await websocket_manager.broadcast_event({
        "type": "device_deleted",
        "device_id": device_id
    })

    return {"message": "Device deleted successfully"}

@router.post("/config/download")
async def download_config(request: ConfigDownloadRequest, db: Session = Depends(get_db)):
    """
    Endpoint for devices to download their Talos configuration.
    This is called by the iPXE boot process with the device's MAC address.

    Returns the appropriate Talos config (controlplane or worker) if the device is approved.
    """
    # Register or get device
    device, is_new = device_crud.register_or_get_device(db, request.mac_address)

    # Broadcast device_discovered event if this is a new device
    if is_new:
        await websocket_manager.broadcast_event({
            "type": "device_discovered",
            "mac_address": device.mac_address
        })

    # Check if device is approved
    if device.status != DeviceStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail=f"Device not approved. Current status: {device.status.value}"
        )

    # Update last config download time
    device_crud.update_config_download_time(db, request.mac_address)

    # Determine which config to serve based on device role
    base_dir = Path(__file__).parent.parent.parent.parent / "templates" / "base"

    if device.role == DeviceRole.CONTROLPLANE:
        config_file = base_dir / "controlplane.yaml"
    else:
        config_file = base_dir / "worker.yaml"

    if not config_file.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Configuration file not found. Please generate cluster configs first."
        )

    # Read the base config
    config_content = config_file.read_text()

    # Parse YAML to potentially customize per-device
    config_yaml = yaml.safe_load(config_content)

    # Customize config with device-specific settings
    if device.hostname:
        config_yaml['machine']['network']['hostname'] = device.hostname

    if device.ip_address:
        # Add static IP configuration if specified
        if 'machine' not in config_yaml:
            config_yaml['machine'] = {}
        if 'network' not in config_yaml['machine']:
            config_yaml['machine']['network'] = {}
        if 'interfaces' not in config_yaml['machine']['network']:
            config_yaml['machine']['network']['interfaces'] = []

        # Add or update first interface with static IP
        if len(config_yaml['machine']['network']['interfaces']) == 0:
            config_yaml['machine']['network']['interfaces'].append({})

        config_yaml['machine']['network']['interfaces'][0]['addresses'] = [device.ip_address]

    # Convert back to YAML
    customized_config = yaml.dump(config_yaml, default_flow_style=False)

    return Response(
        content=customized_config,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f"attachment; filename=talos-config-{device.mac_address}.yaml"
        }
    )

@router.get("/talos/configs/{mac_address}.yaml")
async def get_device_config(mac_address: str, db: Session = Depends(get_db)):
    """
    Serve Talos configuration for a specific device by MAC address.
    This endpoint matches the iPXE boot script URL format:
    http://server/talos/configs/{mac}.yaml

    Example: http://10.0.5.113/talos/configs/6c:4b:90:8b:a1:6d.yaml

    The device role is looked up from the database, so it doesn't need to be in the URL.
    
    If strict mode is disabled and device is not approved, returns a default worker config.
    """
    # Register or get device
    device, is_new = device_crud.register_or_get_device(db, mac_address)

    # Broadcast device_discovered event if this is a new device
    if is_new:
        await websocket_manager.broadcast_event({
            "type": "device_discovered",
            "mac_address": device.mac_address
        })

    # Check if device is approved
    if device.status != DeviceStatus.APPROVED:
        # Check if strict mode is disabled - if so, return default worker config
        from app.crud import network as network_crud
        network_settings = network_crud.get_network_settings(db)
        strict_mode = network_settings.strict_boot_mode if network_settings else True
        
        if strict_mode:
            raise HTTPException(
                status_code=403,
                detail=f"Device {mac_address} not approved. Current status: {device.status.value}. Please approve in Device Management."
            )
        else:
            # Strict mode disabled - return default worker config
            base_dir = Path("/templates") / "base"
            default_config = base_dir / "worker.yaml"
            
            if not default_config.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Default worker configuration not found. Please generate cluster configs first."
                )
            
            config_content = default_config.read_text()
            return Response(
                content=config_content,
                media_type="application/x-yaml",
                headers={
                    "Content-Disposition": f"inline; filename={mac_address}.yaml"
                }
            )

    # Update last config download time
    device_crud.update_config_download_time(db, mac_address)

    # Notify WebSocket clients of config download event
    await websocket_manager.broadcast_event({
        "type": "config_downloaded",
        "mac_address": device.mac_address
    })

    # Read the pre-generated config file for this device
    import os
    from app.core.config import settings
    
    compiled_dir_env = os.getenv("COMPILED_DIR", settings.COMPILED_DIR)
    compiled_dir = Path(compiled_dir_env) / "talos" / "configs"
    
    if not compiled_dir.is_absolute():
        # Assume relative to project root
        compiled_dir = Path(__file__).parent.parent.parent.parent.parent / compiled_dir
    
    # Fallback to Docker path if not set
    if not compiled_dir.exists() and not os.getenv("COMPILED_DIR"):
        compiled_dir = Path("/compiled/talos/configs")
    
    config_file = compiled_dir / f"{mac_address}.yaml"

    if not config_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Configuration file not found for {mac_address}. Config may not have been generated yet."
        )

    # Read and return the config
    config_content = config_file.read_text()

    return Response(
        content=config_content,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f"inline; filename={mac_address}.yaml"
        }
    )

@router.post("/devices/register")
async def register_device(request: ConfigDownloadRequest, db: Session = Depends(get_db)):
    """
    Endpoint for devices to register themselves.
    This can be called during initial boot to register the device for approval.
    """
    device, is_new = device_crud.register_or_get_device(db, request.mac_address)

    # Notify WebSocket clients of device event if this is a new device
    if is_new:
        await websocket_manager.broadcast_event({
            "type": "device_discovered",
            "mac_address": device.mac_address
        })

    return {
        "mac_address": device.mac_address,
        "status": device.status.value,
        "message": "Device registered successfully. Awaiting approval." if device.status == DeviceStatus.PENDING else f"Device status: {device.status.value}"
    }

@router.post("/devices/regenerate")
async def regenerate_all_configs(db: Session = Depends(get_db)):
    """
    Manually regenerate all device configurations and boot.ipxe script.
    Useful after bulk changes or troubleshooting.
    """
    try:
        # Get all approved devices
        approved_devices = device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, skip=0, limit=1000)

        # Regenerate all device configs
        config_count = config_generator.regenerate_all_configs(approved_devices)

        # Regenerate boot.ipxe
        network_settings = network_crud.get_network_settings(db)
        tftp_root = network_settings.tftp_root if network_settings else "/var/lib/tftpboot"
        ipxe_generator = IPXEGenerator(tftp_root=tftp_root)
        server_ip = ipxe_generator.get_server_ip_from_settings(db)
        strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
        ipxe_success = ipxe_generator.generate_boot_script(approved_devices, server_ip, strict_mode=strict_mode)

        return {
            "message": "Configuration regeneration completed",
            "device_configs_generated": config_count,
            "boot_script_generated": ipxe_success,
            "approved_devices": len(approved_devices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate configs: {str(e)}")

@router.get("/events/recent")
async def get_recent_events(since: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get recent device events (new devices discovered and config downloads).

    Args:
        since: Unix timestamp (seconds) to get events since. If not provided, returns last 10 minutes of events.

    Returns:
        List of events with type, device info, and timestamp
    """
    from datetime import datetime, timedelta

    if since:
        since_time = datetime.fromtimestamp(since)
    else:
        since_time = datetime.utcnow() - timedelta(minutes=10)

    events = []

    # Get recently discovered devices (created after since_time)
    devices = device_crud.get_devices(db, skip=0, limit=1000)
    for device in devices:
        if device.created_at and device.created_at > since_time:
            events.append({
                "type": "device_discovered",
                "mac_address": device.mac_address,
                "ip_address": device.ip_address,
                "hostname": device.hostname,
                "status": device.status.value,
                "timestamp": device.created_at.timestamp()
            })

        # Get devices that downloaded config recently
        if device.last_config_download and device.last_config_download > since_time:
            events.append({
                "type": "config_downloaded",
                "mac_address": device.mac_address,
                "ip_address": device.ip_address,
                "hostname": device.hostname,
                "role": device.role.value if device.role else None,
                "timestamp": device.last_config_download.timestamp()
            })

    # Sort by timestamp descending (newest first)
    events.sort(key=lambda x: x['timestamp'], reverse=True)

    return {"events": events}


@router.websocket("/events/ws")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for real-time device event notifications.

    Clients connect to this endpoint to receive real-time updates about:
    - New devices discovered
    - Configuration downloads
    """
    await websocket_manager.connect(websocket)
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
