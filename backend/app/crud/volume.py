"""CRUD operations for volume configurations"""
from sqlalchemy.orm import Session
from app.db.models import VolumeConfig, VolumeType
from app.schemas.volume import VolumeConfigCreate, VolumeConfigUpdate
from typing import List, Optional

def get_volume_configs(db: Session, skip: int = 0, limit: int = 100) -> List[VolumeConfig]:
    """Get all volume configurations"""
    return db.query(VolumeConfig).offset(skip).limit(limit).all()

def get_volume_config(db: Session, volume_id: int) -> Optional[VolumeConfig]:
    """Get volume configuration by ID"""
    return db.query(VolumeConfig).filter(VolumeConfig.id == volume_id).first()

def get_volume_config_by_name(db: Session, name: str) -> Optional[VolumeConfig]:
    """Get volume configuration by name (EPHEMERAL or IMAGE-CACHE)"""
    try:
        volume_type = VolumeType(name)
        return db.query(VolumeConfig).filter(VolumeConfig.name == volume_type).first()
    except ValueError:
        return None

def create_volume_config(db: Session, volume: VolumeConfigCreate) -> VolumeConfig:
    """Create a new volume configuration"""
    # Convert string name to VolumeType enum
    volume_type = VolumeType(volume.name)

    db_volume = VolumeConfig(
        name=volume_type,
        disk_selector_match=volume.disk_selector_match,
        min_size=volume.min_size,
        max_size=volume.max_size,
        grow=volume.grow
    )
    db.add(db_volume)
    db.commit()
    db.refresh(db_volume)
    return db_volume

def update_volume_config(db: Session, volume_id: int, volume: VolumeConfigUpdate) -> Optional[VolumeConfig]:
    """Update volume configuration"""
    db_volume = get_volume_config(db, volume_id)
    if not db_volume:
        return None

    update_data = volume.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_volume, field, value)

    db.commit()
    db.refresh(db_volume)
    return db_volume

def delete_volume_config(db: Session, volume_id: int) -> bool:
    """Delete volume configuration"""
    db_volume = get_volume_config(db, volume_id)
    if not db_volume:
        return False

    db.delete(db_volume)
    db.commit()
    return True
