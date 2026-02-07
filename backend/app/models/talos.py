from pydantic import BaseModel, Field
from typing import List, Optional

class NetworkConfig(BaseModel):
    hostname: str
    interface: str = "eth0"
    dhcp: bool = True
    ip_address: Optional[str] = None
    netmask: Optional[str] = None
    gateway: Optional[str] = None
    nameservers: List[str] = ["8.8.8.8", "8.8.4.4"]

class TalosNodeConfig(BaseModel):
    node_type: str = Field(..., description="controlplane or worker")
    hostname: str
    mac_address: Optional[str] = Field(None, description="MAC address for file naming (required for compile)")
    cluster_name: str
    cluster_endpoint: str
    network: NetworkConfig
    machine_token: str
    ca_crt: str
    ca_key: str
    install_disk: str = "/dev/sda"
    wipe_disk: bool = False
    debug: bool = False

class ControlPlaneConfig(TalosNodeConfig):
    node_type: str = "controlplane"
    cert_sans: List[str] = []
    api_cert_sans: List[str] = []
    etcd_ca_crt: str
    etcd_ca_key: str
    pod_subnets: List[str] = ["10.244.0.0/16"]
    service_subnets: List[str] = ["10.96.0.0/12"]
    cni: str = "flannel"

class WorkerConfig(TalosNodeConfig):
    node_type: str = "worker"

class ConfigGenerateRequest(BaseModel):
    config: TalosNodeConfig

class ConfigGenerateResponse(BaseModel):
    config: str
    filename: str
