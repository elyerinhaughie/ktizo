from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class VolumeConfigBase(BaseModel):
    """Base schema for volume configuration"""
    name: str = Field(..., description="Volume name: EPHEMERAL or IMAGE-CACHE")
    disk_selector_match: Optional[str] = Field(None, description="CEL expression to select disk, e.g., disk.transport == 'nvme'")
    min_size: Optional[str] = Field(None, description="Minimum size, e.g., '2GB', '100GB'")
    max_size: Optional[str] = Field(None, description="Maximum size, e.g., '40GB', '500GB'")
    grow: bool = Field(True, description="Whether to auto-grow to maximum available space")

class VolumeConfigCreate(VolumeConfigBase):
    """Schema for creating volume configuration"""
    pass

class VolumeConfigUpdate(BaseModel):
    """Schema for updating volume configuration (all fields optional)"""
    disk_selector_match: Optional[str] = None
    min_size: Optional[str] = None
    max_size: Optional[str] = None
    grow: Optional[bool] = None

class VolumeConfigResponse(VolumeConfigBase):
    """Schema for volume configuration response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
