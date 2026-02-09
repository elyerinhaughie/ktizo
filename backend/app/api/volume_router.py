from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.volume import VolumeConfigResponse, VolumeConfigCreate, VolumeConfigUpdate
from app.crud import volume as volume_crud
from app.services.audit_service import log_action
from typing import List
import json

router = APIRouter()

@router.get("/configs", response_model=List[VolumeConfigResponse])
async def list_volume_configs(db: Session = Depends(get_db)):
    """List all volume configurations"""
    configs = volume_crud.get_volume_configs(db)
    return configs

@router.get("/configs/{volume_id}", response_model=VolumeConfigResponse)
async def get_volume_config(volume_id: int, db: Session = Depends(get_db)):
    """Get volume configuration by ID"""
    config = volume_crud.get_volume_config(db, volume_id)
    if not config:
        raise HTTPException(status_code=404, detail="Volume configuration not found")
    return config

@router.get("/configs/name/{name}", response_model=VolumeConfigResponse)
async def get_volume_config_by_name(name: str, db: Session = Depends(get_db)):
    """Get volume configuration by name (EPHEMERAL or IMAGE-CACHE)"""
    config = volume_crud.get_volume_config_by_name(db, name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Volume configuration '{name}' not found")
    return config

@router.post("/configs", response_model=VolumeConfigResponse)
async def create_volume_config(config: VolumeConfigCreate, db: Session = Depends(get_db)):
    """Create a new volume configuration"""
    # Check if volume config with this name already exists
    existing = volume_crud.get_volume_config_by_name(db, config.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Volume configuration for '{config.name}' already exists. Use PUT to update."
        )

    try:
        created = volume_crud.create_volume_config(db, config)
        await log_action(db, "created_volume_config", "Storage Settings",
            json.dumps({"name": str(config.name)}), "volume_config", str(created.id))
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid volume name: {str(e)}")

@router.put("/configs/{volume_id}", response_model=VolumeConfigResponse)
async def update_volume_config(volume_id: int, config: VolumeConfigUpdate, db: Session = Depends(get_db)):
    """Update volume configuration"""
    updated = volume_crud.update_volume_config(db, volume_id, config)
    if not updated:
        raise HTTPException(status_code=404, detail="Volume configuration not found")
    await log_action(db, "updated_volume_config", "Storage Settings",
        json.dumps({"name": str(updated.name)}), "volume_config", str(volume_id))
    return updated

@router.delete("/configs/{volume_id}")
async def delete_volume_config(volume_id: int, db: Session = Depends(get_db)):
    """Delete volume configuration"""
    success = volume_crud.delete_volume_config(db, volume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Volume configuration not found")
    await log_action(db, "deleted_volume_config", "Storage Settings",
        None, "volume_config", str(volume_id))
    return {"message": "Volume configuration deleted successfully"}
