from sqlalchemy.orm import Session
from app.db.models import Device, DeviceStatus
from app.schemas.device import DeviceCreate, DeviceUpdate
from datetime import datetime
from typing import List, Optional, Tuple
from app.services.config_generator import ConfigGenerator
from app.services.ipxe_generator import IPXEGenerator
import logging

logger = logging.getLogger(__name__)

# Initialize generators
config_generator = ConfigGenerator()
ipxe_generator = IPXEGenerator()

def get_device(db: Session, device_id: int) -> Optional[Device]:
    """Get device by ID"""
    return db.query(Device).filter(Device.id == device_id).first()

def get_device_by_mac(db: Session, mac_address: str) -> Optional[Device]:
    """Get device by MAC address"""
    return db.query(Device).filter(Device.mac_address == mac_address).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100) -> List[Device]:
    """Get all devices with pagination"""
    return db.query(Device).offset(skip).limit(limit).all()

def get_devices_by_status(db: Session, status: DeviceStatus, skip: int = 0, limit: int = 100) -> List[Device]:
    """Get devices filtered by status"""
    return db.query(Device).filter(Device.status == status).offset(skip).limit(limit).all()

def create_device(db: Session, device: DeviceCreate) -> Device:
    """Create a new device"""
    db_device = Device(
        mac_address=device.mac_address,
        hostname=device.hostname,
        ip_address=device.ip_address,
        role=device.role,
        notes=device.notes,
        status=DeviceStatus.PENDING
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def register_or_get_device(db: Session, mac_address: str) -> Tuple[Device, bool]:
    """
    Register device if it doesn't exist, or return existing device.
    
    Returns:
        tuple: (Device, is_new) where is_new is True if device was just created
    """
    device = get_device_by_mac(db, mac_address)
    is_new = False
    if not device:
        device = Device(
            mac_address=mac_address,
            status=DeviceStatus.PENDING
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        is_new = True
    return device, is_new

def update_device(db: Session, device_id: int, device_update: DeviceUpdate) -> Optional[Device]:
    """Update device and regenerate configs if approved"""
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    update_data = device_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_device, field, value)

    db.commit()
    db.refresh(db_device)

    # If device is approved, regenerate its config (in case hostname/IP changed)
    if db_device.status == DeviceStatus.APPROVED:
        logger.info(f"Regenerating config for updated device {db_device.mac_address}")
        config_generator.generate_device_config(db_device)

        # Regenerate boot.ipxe with updated info
        logger.info("Regenerating boot.ipxe with updated device info")
        all_devices = get_devices(db, skip=0, limit=1000)
        server_ip = ipxe_generator.get_server_ip_from_settings(db)
        strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
        ipxe_generator.generate_boot_script(all_devices, server_ip, strict_mode=strict_mode)

    return db_device

def approve_device(db: Session, device_id: int) -> Optional[Device]:
    """Approve a device and generate its configuration files"""
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    db_device.status = DeviceStatus.APPROVED
    db_device.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(db_device)

    # Generate static configuration file for this device
    logger.info(f"Generating config for approved device {db_device.mac_address}")
    config_generator.generate_device_config(db_device)

    # Regenerate boot.ipxe with all approved devices
    logger.info("Regenerating boot.ipxe with updated device list")
    all_devices = get_devices(db, skip=0, limit=1000)
    server_ip = ipxe_generator.get_server_ip_from_settings(db)
    strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
    ipxe_generator.generate_boot_script(all_devices, server_ip, strict_mode=strict_mode)

    return db_device

def reject_device(db: Session, device_id: int) -> Optional[Device]:
    """Reject a device and remove its configuration"""
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    # Delete config file if it exists
    config_generator.delete_device_config(db_device)

    db_device.status = DeviceStatus.REJECTED
    db.commit()
    db.refresh(db_device)

    # Regenerate boot.ipxe without this device
    logger.info("Regenerating boot.ipxe with updated device list")
    all_devices = get_devices(db, skip=0, limit=1000)
    server_ip = ipxe_generator.get_server_ip_from_settings(db)
    strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
    ipxe_generator.generate_boot_script(all_devices, server_ip, strict_mode=strict_mode)

    return db_device

def update_config_download_time(db: Session, mac_address: str) -> Optional[Device]:
    """Update last config download time for a device"""
    device = get_device_by_mac(db, mac_address)
    if device:
        device.last_config_download = datetime.utcnow()
        db.commit()
        db.refresh(device)
    return device

def delete_device(db: Session, device_id: int) -> bool:
    """Delete a device and its configuration"""
    db_device = get_device(db, device_id)
    if not db_device:
        return False

    # Delete config file
    config_generator.delete_device_config(db_device)

    db.delete(db_device)
    db.commit()

    # Regenerate boot.ipxe
    logger.info("Regenerating boot.ipxe with updated device list")
    all_devices = get_devices(db, skip=0, limit=1000)
    server_ip = ipxe_generator.get_server_ip_from_settings(db)
    strict_mode = ipxe_generator.get_strict_mode_from_settings(db)
    ipxe_generator.generate_boot_script(all_devices, server_ip, strict_mode=strict_mode)

    return True
