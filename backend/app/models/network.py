from pydantic import BaseModel, Field
from typing import List, Optional

class DNSMasqConfig(BaseModel):
    """DNSMASQ PXE/iPXE configuration for Talos deployment"""

    # Network configuration
    interface: Optional[str] = Field(None, description="Network interface to listen on (e.g., eth0)")
    server_ip: str = Field(..., description="Server IP address for TFTP/PXE (e.g., 10.0.5.113)")

    # DHCP Proxy configuration
    dhcp_network: str = Field(default="10.0.0.0", description="DHCP network range start")
    dhcp_netmask: str = Field(default="255.255.0.0", description="DHCP network mask")

    # DNS configuration
    dns_port: int = Field(default=0, description="DNS port (0 to disable DNS)")
    dns_server: Optional[str] = Field(None, description="DNS server IP (defaults to server_ip)")

    # TFTP configuration
    tftp_root: str = Field(default="/var/lib/tftpboot", description="TFTP root directory")
    tftp_secure: bool = Field(default=True, description="Enable TFTP secure mode")

    # PXE Boot configuration
    ipxe_boot_script: str = Field(default="pxe/boot.ipxe", description="iPXE boot script path (relative to tftp_root)")
    pxe_prompt: str = Field(default="Press F8 for boot menu", description="PXE menu prompt text")
    pxe_timeout: int = Field(default=3, description="PXE menu timeout in seconds")

    # Logging
    enable_logging: bool = Field(default=True, description="Enable DHCP logging")

class DNSMasqCompileRequest(BaseModel):
    config: DNSMasqConfig

class DNSMasqCompileResponse(BaseModel):
    config: str
    path: str
    message: str
