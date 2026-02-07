from sqlalchemy.orm import Session
from app.db.models import ClusterSettings
from app.schemas.cluster import ClusterSettingsCreate, ClusterSettingsUpdate
from typing import Optional

def get_cluster_settings(db: Session) -> Optional[ClusterSettings]:
    """Get the current cluster settings (returns first record)"""
    return db.query(ClusterSettings).first()

def create_cluster_settings(db: Session, settings: ClusterSettingsCreate) -> ClusterSettings:
    """Create new cluster settings"""
    db_settings = ClusterSettings(**settings.model_dump())
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings

def update_cluster_settings(db: Session, settings_id: int, settings: ClusterSettingsUpdate) -> Optional[ClusterSettings]:
    """Update existing cluster settings"""
    db_settings = db.query(ClusterSettings).filter(ClusterSettings.id == settings_id).first()
    if not db_settings:
        return None

    update_data = settings.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)

    db.commit()
    db.refresh(db_settings)
    return db_settings

def get_or_create_cluster_settings(db: Session, default_settings: ClusterSettingsCreate) -> ClusterSettings:
    """Get existing settings or create default if none exist"""
    settings = get_cluster_settings(db)
    if not settings:
        settings = create_cluster_settings(db, default_settings)
    return settings
