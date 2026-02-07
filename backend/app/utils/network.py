"""Network utility functions for IP address management"""
import ipaddress
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import Device


def get_first_usable_ip(subnet: str) -> str:
    """
    Get the first usable IP address in a subnet.

    Args:
        subnet: CIDR notation subnet (e.g., "10.0.0.0/24")

    Returns:
        First usable IP address as string
    """
    network = ipaddress.ip_network(subnet, strict=False)
    # First usable IP (skip network address)
    return str(next(network.hosts()))


def get_next_available_ip(db: Session, subnet: str) -> str:
    """
    Get the next available IP address in the subnet that's not already assigned.

    Args:
        db: Database session
        subnet: CIDR notation subnet (e.g., "10.0.0.0/24")

    Returns:
        Next available IP address as string
    """
    network = ipaddress.ip_network(subnet, strict=False)

    # Get all assigned IPs from database
    devices = db.query(Device).filter(Device.ip_address.isnot(None)).all()
    assigned_ips = {device.ip_address for device in devices}

    # Find first available IP
    for ip in network.hosts():
        ip_str = str(ip)
        if ip_str not in assigned_ips:
            return ip_str

    # If all IPs are taken, return the first one (shouldn't happen in practice)
    return get_first_usable_ip(subnet)


def is_valid_ip_in_subnet(ip_address: str, subnet: str) -> bool:
    """
    Check if an IP address is valid and within the given subnet.

    Args:
        ip_address: IP address to check
        subnet: CIDR notation subnet (e.g., "10.0.0.0/24")

    Returns:
        True if IP is valid and in subnet, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(subnet, strict=False)
        return ip in network
    except ValueError:
        return False


def is_fqdn(hostname: str) -> bool:
    """
    Check if a hostname is a fully qualified domain name (not an IP address).

    A FQDN contains dots but is NOT a valid IP address.

    Args:
        hostname: Hostname to check

    Returns:
        True if hostname is FQDN (not IP), False if it's an IP or simple hostname
    """
    if not hostname:
        return False

    # Check if it's a valid IP address
    try:
        ipaddress.ip_address(hostname)
        return False  # It's an IP address, not a FQDN
    except ValueError:
        # Not an IP, check if it has dots (FQDN)
        return '.' in hostname
