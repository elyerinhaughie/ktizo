from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClusterSettingsBase(BaseModel):
    """Base schema for cluster settings"""
    cluster_name: str = Field(..., description="Name of the Kubernetes cluster")
    external_subnet: Optional[str] = Field(default="10.0.128.0/24", description="External network range where physical nodes reside (e.g., 10.0.128.0/24)")
    cluster_endpoint: str = Field(default="10.0.128.1", description="Cluster endpoint IP or hostname")
    kubernetes_version: str = Field(default="1.28.0", description="Kubernetes version")
    kubectl_version: str = Field(default="1.28.0", description="kubectl version to use in terminal")
    talos_version: str = Field(default="1.12.2", description="Talos version for talosctl")
    install_disk: str = Field(default="/dev/sda", description="Disk to install Talos on")
    install_image: str = Field(default="ghcr.io/siderolabs/installer:latest", description="Talos installer image")
    pod_subnet: str = Field(default="10.244.0.0/16", description="Pod network CIDR")
    service_subnet: str = Field(default="10.96.0.0/12", description="Service network CIDR")
    cni: str = Field(default="flannel", description="CNI plugin (flannel, calico, cilium)")
    dns_domain: str = Field(default="cluster.local", description="Cluster DNS domain")
    secrets_file: Optional[str] = Field(None, description="Talos secrets YAML content")

class ClusterSettingsCreate(ClusterSettingsBase):
    """Schema for creating cluster settings"""
    pass

class ClusterSettingsUpdate(BaseModel):
    """Schema for updating cluster settings (all fields optional)"""
    cluster_name: Optional[str] = None
    external_subnet: Optional[str] = None
    cluster_endpoint: Optional[str] = None
    kubernetes_version: Optional[str] = None
    kubectl_version: Optional[str] = None
    talos_version: Optional[str] = None
    install_disk: Optional[str] = None
    install_image: Optional[str] = None
    pod_subnet: Optional[str] = None
    service_subnet: Optional[str] = None
    cni: Optional[str] = None
    dns_domain: Optional[str] = None
    secrets_file: Optional[str] = None

class ClusterSettingsResponse(ClusterSettingsBase):
    """Schema for cluster settings response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GenerateSecretsRequest(BaseModel):
    """Request to generate Talos secrets"""
    cluster_name: str = Field(..., description="Cluster name for secrets generation")

class GenerateSecretsResponse(BaseModel):
    """Response with generated secrets"""
    secrets: str = Field(..., description="Generated secrets YAML content")
    message: str = Field(..., description="Success message")
