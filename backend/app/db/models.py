from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class NetworkSettings(Base):
    __tablename__ = "network_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Network configuration
    interface = Column(String, nullable=True)
    server_ip = Column(String, nullable=False)

    # DHCP configuration
    dhcp_mode = Column(String, default="proxy")  # "proxy" or "server"
    dhcp_network = Column(String, default="10.0.0.0")
    dhcp_netmask = Column(String, default="255.255.0.0")
    dhcp_range_start = Column(String, nullable=True)  # For full DHCP mode
    dhcp_range_end = Column(String, nullable=True)  # For full DHCP mode

    # DNS configuration
    dns_port = Column(Integer, default=0)
    dns_server = Column(String, nullable=True)

    # TFTP configuration
    tftp_root = Column(String, default="/var/lib/tftpboot")
    tftp_secure = Column(Boolean, default=True)

    # PXE Boot configuration
    ipxe_boot_script = Column(String, default="pxe/boot.ipxe")
    pxe_prompt = Column(String, default="Press F8 for boot menu")
    pxe_timeout = Column(Integer, default=3)
    strict_boot_mode = Column(Boolean, default=True)  # If True, unapproved devices exit immediately
    talos_version = Column(String, default="v1.11.3")  # Talos version to boot

    # Logging
    enable_logging = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ClusterSettings(Base):
    __tablename__ = "cluster_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Cluster configuration
    cluster_name = Column(String, nullable=False)
    external_subnet = Column(String, default="10.0.128.0/24")  # Physical node network range
    cluster_endpoint = Column(String, default="10.0.128.1")

    # Kubernetes version
    kubernetes_version = Column(String, default="1.28.0")

    # Installation configuration
    install_disk = Column(String, default="/dev/sda")
    install_image = Column(String, default="ghcr.io/siderolabs/installer:latest")

    # Network configuration
    pod_subnet = Column(String, default="10.244.0.0/16")
    service_subnet = Column(String, default="10.96.0.0/12")
    cni = Column(String, default="flannel")
    dns_domain = Column(String, default="cluster.local")

    # Secrets (encrypted/sensitive data)
    secrets_file = Column(Text, nullable=True)  # Will store talosctl generated secrets

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VolumeType(str, enum.Enum):
    """Talos system volume types"""
    EPHEMERAL = "EPHEMERAL"
    IMAGE_CACHE = "IMAGE-CACHE"

class VolumeConfig(Base):
    __tablename__ = "volume_configs"

    id = Column(Integer, primary_key=True, index=True)

    # Volume identification
    name = Column(SQLEnum(VolumeType), nullable=False, unique=True)

    # Provisioning configuration
    disk_selector_match = Column(String, nullable=True)  # CEL expression, e.g., "disk.transport == 'nvme'"
    min_size = Column(String, nullable=True)  # e.g., "2GB", "100GB"
    max_size = Column(String, nullable=True)  # e.g., "40GB", "500GB"
    grow = Column(Boolean, default=True)  # Whether to auto-grow

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DeviceRole(str, enum.Enum):
    """Device role in cluster"""
    CONTROLPLANE = "controlplane"
    WORKER = "worker"

class DeviceStatus(str, enum.Enum):
    """Device approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    # Hardware identification
    mac_address = Column(String, unique=True, nullable=False, index=True)
    hostname = Column(String, nullable=True)

    # Network configuration
    ip_address = Column(String, nullable=True)

    # Cluster role
    role = Column(SQLEnum(DeviceRole), nullable=False, default=DeviceRole.WORKER)

    # Approval workflow
    status = Column(SQLEnum(DeviceStatus), nullable=False, default=DeviceStatus.PENDING)

    # Additional metadata
    notes = Column(Text, nullable=True)

    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    last_config_download = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
