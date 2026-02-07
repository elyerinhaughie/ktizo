from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models import DeviceRole, DeviceStatus

class DeviceBase(BaseModel):
    """Base schema for device"""
    mac_address: str = Field(..., description="MAC address of the device")
    hostname: Optional[str] = Field(None, description="Hostname of the device")
    ip_address: Optional[str] = Field(None, description="IP address to assign to the device")
    role: DeviceRole = Field(default=DeviceRole.WORKER, description="Role in cluster (controlplane or worker)")
    notes: Optional[str] = Field(None, description="Additional notes about the device")

class DeviceCreate(DeviceBase):
    """Schema for creating a device"""
    pass

class DeviceUpdate(BaseModel):
    """Schema for updating a device (all fields optional)"""
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    role: Optional[DeviceRole] = None
    status: Optional[DeviceStatus] = None
    notes: Optional[str] = None

class DeviceResponse(DeviceBase):
    """Schema for device response"""
    id: int
    status: DeviceStatus
    first_seen: datetime
    approved_at: Optional[datetime] = None
    last_config_download: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DeviceApprovalRequest(BaseModel):
    """Request to approve a device with required details"""
    hostname: str = Field(..., description="Hostname for the device")
    ip_address: str = Field(..., description="IP address to assign")
    role: DeviceRole = Field(..., description="Role in cluster (controlplane or worker)")

class ConfigDownloadRequest(BaseModel):
    """Request from device to download config"""
    mac_address: str = Field(..., description="MAC address of requesting device")
