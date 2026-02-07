from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class NetworkSettingsBase(BaseModel):
    """Base schema for network settings"""
    interface: Optional[str] = Field(None, description="Network interface to listen on")
    server_ip: str = Field(..., description="Server IP address for TFTP/PXE")
    dhcp_mode: str = Field(default="proxy", description="DHCP mode: 'proxy' (ProxyDHCP) or 'server' (full DHCP server)")
    dhcp_network: str = Field(default="10.0.0.0", description="DHCP network range start")
    dhcp_netmask: str = Field(default="255.255.0.0", description="DHCP network mask")
    dhcp_range_start: Optional[str] = Field(None, description="DHCP range start IP (for server mode)")
    dhcp_range_end: Optional[str] = Field(None, description="DHCP range end IP (for server mode)")
    dns_port: int = Field(default=0, description="DNS port (0 to disable)")
    dns_server: Optional[str] = Field(None, description="DNS server IP")
    tftp_root: str = Field(default="/var/lib/tftpboot", description="TFTP root directory")
    tftp_secure: bool = Field(default=True, description="Enable TFTP secure mode")
    ipxe_boot_script: str = Field(default="pxe/boot.ipxe", description="iPXE boot script path (relative to tftp_root)")
    pxe_prompt: str = Field(default="Press F8 for boot menu", description="PXE menu prompt")
    pxe_timeout: int = Field(default=3, description="PXE menu timeout in seconds")
    strict_boot_mode: bool = Field(default=True, description="If True, unapproved devices exit immediately instead of attempting local boot")
    talos_version: str = Field(default="1.12.2", description="Talos version to boot")
    enable_logging: bool = Field(default=True, description="Enable DHCP logging")

class NetworkSettingsCreate(NetworkSettingsBase):
    """Schema for creating network settings"""
    pass

class NetworkSettingsUpdate(BaseModel):
    """Schema for updating network settings (all fields optional)"""
    interface: Optional[str] = None
    server_ip: Optional[str] = None
    dhcp_mode: Optional[str] = None
    dhcp_network: Optional[str] = None
    dhcp_netmask: Optional[str] = None
    dhcp_range_start: Optional[str] = None
    dhcp_range_end: Optional[str] = None
    dns_port: Optional[int] = None
    dns_server: Optional[str] = None
    tftp_root: Optional[str] = None
    tftp_secure: Optional[bool] = None
    ipxe_boot_script: Optional[str] = None
    pxe_prompt: Optional[str] = None
    pxe_timeout: Optional[int] = None
    strict_boot_mode: Optional[bool] = None
    talos_version: Optional[str] = None
    enable_logging: Optional[bool] = None

class NetworkSettingsResponse(NetworkSettingsBase):
    """Schema for network settings response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
