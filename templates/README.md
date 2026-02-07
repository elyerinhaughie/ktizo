# Templates Directory

This directory contains Jinja2 templates used by the FastAPI backend to generate configuration files for Talos Linux nodes and PXE boot infrastructure.

## Structure

- `talos/` - Talos Linux node configuration templates
  - `controlplane.yaml.j2` - Control plane node configuration
  - `worker.yaml.j2` - Worker node configuration

- `pxe/` - PXE boot configuration templates
  - `pxelinux.cfg.j2` - PXE boot menu configuration

- `network/` - Network infrastructure templates
  - `dnsmasq.conf.j2` - DNSMASQ configuration with dynamic DHCP/TFTP settings

## Usage

The FastAPI backend will use these templates with Jinja2 to synthesize configurations based on user input from the Vue frontend. Templates support variable substitution and conditional logic to generate customized configurations for different deployment scenarios.
