from sqlalchemy.orm import Session
from app.db.models import NetworkSettings
from app.schemas.network import NetworkSettingsCreate, NetworkSettingsUpdate
from typing import Optional

def get_network_settings(db: Session) -> Optional[NetworkSettings]:
    """Get the current network settings (returns first record)"""
    return db.query(NetworkSettings).first()

def create_network_settings(db: Session, settings: NetworkSettingsCreate) -> NetworkSettings:
    """Create new network settings"""
    db_settings = NetworkSettings(**settings.model_dump())
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings

def update_network_settings(db: Session, settings_id: int, settings: NetworkSettingsUpdate) -> Optional[NetworkSettings]:
    """Update existing network settings"""
    db_settings = db.query(NetworkSettings).filter(NetworkSettings.id == settings_id).first()
    if not db_settings:
        return None

    update_data = settings.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)

    db.commit()
    db.refresh(db_settings)
    return db_settings

def get_or_create_network_settings(db: Session, default_settings: NetworkSettingsCreate) -> NetworkSettings:
    """Get existing settings or create default if none exist"""
    settings = get_network_settings(db)
    if not settings:
        settings = create_network_settings(db, default_settings)
    return settings
