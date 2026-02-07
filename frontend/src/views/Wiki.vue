<template>
  <div class="wiki">
    <div class="breadcrumbs">
      <router-link to="/">Home</router-link>
      <span class="separator">›</span>
      <span class="current">Wiki</span>
    </div>

    <div class="wiki-container">
      <aside class="toc">
        <h3>Table of Contents</h3>
        <nav>
          <div class="toc-section">
            <h4>Overview</h4>
            <ul>
              <li><a href="#introduction" @click.prevent="scrollTo('introduction')">Introduction</a></li>
              <li><a href="#architecture" @click.prevent="scrollTo('architecture')">Architecture</a></li>
              <li><a href="#workflow" @click.prevent="scrollTo('workflow')">Boot Workflow</a></li>
            </ul>
          </div>

          <div class="toc-section">
            <h4>Core Components</h4>
            <ul>
              <li><a href="#backend" @click.prevent="scrollTo('backend')">Backend API</a></li>
              <li><a href="#frontend" @click.prevent="scrollTo('frontend')">Frontend UI</a></li>
              <li><a href="#dnsmasq" @click.prevent="scrollTo('dnsmasq')">dnsmasq Service</a></li>
            </ul>
          </div>

          <div class="toc-section">
            <h4>Services</h4>
            <ul>
              <li><a href="#config-generator" @click.prevent="scrollTo('config-generator')">Config Generator</a></li>
              <li><a href="#ipxe-generator" @click.prevent="scrollTo('ipxe-generator')">iPXE Generator</a></li>
              <li><a href="#template-service" @click.prevent="scrollTo('template-service')">Template Service</a></li>
              <li><a href="#websocket" @click.prevent="scrollTo('websocket')">WebSocket Manager</a></li>
            </ul>
          </div>

          <div class="toc-section">
            <h4>Boot Process</h4>
            <ul>
              <li><a href="#pxe-boot" @click.prevent="scrollTo('pxe-boot')">PXE Boot</a></li>
              <li><a href="#ipxe-chain" @click.prevent="scrollTo('ipxe-chain')">iPXE Chainloading</a></li>
              <li><a href="#talos-boot" @click.prevent="scrollTo('talos-boot')">Talos Boot</a></li>
            </ul>
          </div>

          <div class="toc-section">
            <h4>Configuration</h4>
            <ul>
              <li><a href="#network-config" @click.prevent="scrollTo('network-config')">Network Settings</a></li>
              <li><a href="#cluster-config" @click.prevent="scrollTo('cluster-config')">Cluster Settings</a></li>
              <li><a href="#device-config" @click.prevent="scrollTo('device-config')">Device Configuration</a></li>
            </ul>
          </div>

          <div class="toc-section">
            <h4>Advanced Topics</h4>
            <ul>
              <li><a href="#proxydhcp" @click.prevent="scrollTo('proxydhcp')">ProxyDHCP Mode</a></li>
              <li><a href="#strict-mode" @click.prevent="scrollTo('strict-mode')">Strict Boot Mode</a></li>
              <li><a href="#file-structure" @click.prevent="scrollTo('file-structure')">File Structure</a></li>
            </ul>
          </div>
        </nav>
      </aside>

      <main class="wiki-content">
        <h1>Ktizo Wiki</h1>
        <p class="intro">
          Comprehensive documentation for Ktizo - a fast PXE-based deployment system for Talos Linux on Kubernetes.
        </p>

        <!-- Overview Section -->
        <section id="introduction" class="wiki-section">
          <h2>Introduction</h2>
          <p>
            Ktizo is an automated PXE provisioning system designed specifically for deploying Talos Linux clusters.
            It eliminates the need for manual installation by providing network boot capabilities, automatic device
            discovery, and centralized configuration management.
          </p>
          <h3>Key Features</h3>
          <ul>
            <li><strong>Zero-Touch Provisioning:</strong> Servers boot from the network and automatically register</li>
            <li><strong>Centralized Management:</strong> Web-based interface for device approval and configuration</li>
            <li><strong>Flexible DHCP Modes:</strong> Works alongside existing DHCP servers or operates standalone</li>
            <li><strong>Real-Time Updates:</strong> WebSocket-based notifications for device events</li>
            <li><strong>Template-Based Configuration:</strong> Jinja2 templates for flexible customization</li>
          </ul>
        </section>

        <section id="architecture" class="wiki-section">
          <h2>Architecture</h2>
          <p>
            Ktizo consists of three main components that work together to provide automated PXE provisioning:
          </p>
          <div class="architecture-diagram">
            <div class="component">
              <h4>Frontend (Vue 3)</h4>
              <p>Web interface for configuration and device management</p>
            </div>
            <div class="component">
              <h4>Backend (FastAPI)</h4>
              <p>REST API and business logic for provisioning</p>
            </div>
            <div class="component">
              <h4>dnsmasq</h4>
              <p>DHCP/TFTP/PXE services for network boot</p>
            </div>
          </div>
          <p>
            All components run in Docker containers and communicate via a shared network. The backend generates
            configuration files that dnsmasq serves to booting devices.
          </p>
        </section>

        <section id="workflow" class="wiki-section">
          <h2>Boot Workflow</h2>
          <p>The complete boot process from power-on to running Kubernetes cluster:</p>
          <ol class="workflow-steps">
            <li><strong>Device Powers On:</strong> Server configured for network boot sends DHCP request</li>
            <li><strong>DHCP Response:</strong> dnsmasq provides IP address and PXE boot information</li>
            <li><strong>PXE Boot:</strong> Device downloads iPXE bootloader via TFTP</li>
            <li><strong>iPXE Script:</strong> iPXE loads boot.ipxe script from Ktizo</li>
            <li><strong>Device Registration:</strong> Device registers with Ktizo backend using its MAC address</li>
            <li><strong>Approval Check:</strong> iPXE script checks device approval status</li>
            <li><strong>Talos Boot:</strong> Approved devices download Talos kernel and initramfs</li>
            <li><strong>Config Download:</strong> Talos downloads device-specific configuration</li>
            <li><strong>Installation:</strong> Talos installs to disk and reboots</li>
            <li><strong>Cluster Join:</strong> Device joins Kubernetes cluster</li>
          </ol>
        </section>

        <!-- Core Components Section -->
        <section id="backend" class="wiki-section">
          <h2>Backend API</h2>
          <p>
            The backend is built with FastAPI (Python) and provides a RESTful API for managing the entire
            provisioning lifecycle.
          </p>
          <h3>Key Responsibilities</h3>
          <ul>
            <li>Device registration and approval workflow</li>
            <li>Network and cluster configuration management</li>
            <li>Talos configuration generation for each device</li>
            <li>iPXE boot script generation</li>
            <li>Template rendering (dnsmasq, iPXE, Talos configs)</li>
            <li>WebSocket event broadcasting</li>
            <li>File downloads (iPXE bootloaders, Talos images)</li>
          </ul>
          <h3>API Endpoints</h3>
          <div class="code-block">
            <code>
GET  /api/v1/devices              # List all devices<br>
POST /api/v1/devices              # Create device manually<br>
POST /api/v1/devices/register     # Device self-registration<br>
POST /api/v1/devices/{id}/approve # Approve device<br>
POST /api/v1/devices/{id}/reject  # Reject device<br>
DELETE /api/v1/devices/{id}       # Delete device<br>
<br>
GET  /api/v1/network/settings     # Get network config<br>
POST /api/v1/network/settings/apply # Apply network config<br>
<br>
GET  /api/v1/cluster/settings     # Get cluster config<br>
POST /api/v1/cluster/secrets/generate # Generate cluster secrets<br>
<br>
GET  /api/v1/talos/configs/{mac}.yaml # Serve device config<br>
            </code>
          </div>
        </section>

        <section id="frontend" class="wiki-section">
          <h2>Frontend UI</h2>
          <p>
            The frontend is a Vue 3 single-page application that provides an intuitive interface for managing
            Ktizo and provisioning devices.
          </p>
          <h3>Pages</h3>
          <ul>
            <li><strong>Home:</strong> Getting started guide and overview</li>
            <li><strong>Network Settings:</strong> Configure DHCP, DNS, and TFTP services</li>
            <li><strong>Cluster Settings:</strong> Configure Kubernetes cluster parameters</li>
            <li><strong>Device Management:</strong> View, approve, and manage devices</li>
            <li><strong>Wiki:</strong> Comprehensive documentation</li>
          </ul>
          <h3>Real-Time Updates</h3>
          <p>
            The frontend uses a shared WebSocket service to receive real-time notifications about:
          </p>
          <ul>
            <li>New device discoveries</li>
            <li>Configuration downloads</li>
            <li>Device approvals/rejections</li>
            <li>Device deletions</li>
          </ul>
          <p>
            Toast notifications appear in the bottom-right corner when events occur, and the device table
            automatically refreshes to reflect changes.
          </p>
        </section>

        <section id="dnsmasq" class="wiki-section">
          <h2>dnsmasq Service</h2>
          <p>
            dnsmasq is a lightweight DHCP, DNS, and TFTP server that handles the network boot process.
            Ktizo generates dnsmasq configuration dynamically based on your settings.
          </p>
          <h3>Modes of Operation</h3>
          <div class="modes">
            <div class="mode-card">
              <h4>ProxyDHCP Mode (Recommended)</h4>
              <p>
                Works alongside your existing DHCP server. Your router/DHCP server continues to assign IP
                addresses, while dnsmasq only provides PXE boot information. This is the safest option and
                doesn't require changing your existing network setup.
              </p>
            </div>
            <div class="mode-card">
              <h4>Full DHCP Server Mode</h4>
              <p>
                dnsmasq acts as the sole DHCP server, assigning IP addresses and providing PXE boot
                information. Use this mode only if you don't have an existing DHCP server or can disable it.
                Running two DHCP servers on the same network will cause conflicts.
              </p>
            </div>
          </div>
          <h3>Services Provided</h3>
          <ul>
            <li><strong>DHCP:</strong> IP address assignment (full mode) or PXE boot info (proxy mode)</li>
            <li><strong>TFTP:</strong> Serves iPXE bootloaders and Talos boot files</li>
            <li><strong>DNS:</strong> Optional DNS resolution for local network</li>
            <li><strong>PXE:</strong> Detects firmware type (BIOS/UEFI) and serves appropriate bootloader</li>
          </ul>
        </section>

        <!-- Services Section -->
        <section id="config-generator" class="wiki-section">
          <h2>Config Generator Service</h2>
          <p>
            The Config Generator is responsible for creating Talos configuration files for each approved device.
            It uses YAML-based templates and merges cluster secrets, network settings, and device-specific
            parameters.
          </p>
          <h3>Configuration Process</h3>
          <ol>
            <li>Loads base Talos configuration template from <code>templates/talos/</code></li>
            <li>Injects cluster secrets (certificates, tokens, keys)</li>
            <li>Sets device-specific values (hostname, IP, role)</li>
            <li>Configures network settings (subnet, gateway, DNS)</li>
            <li>Saves configuration to <code>compiled/talos/configs/{mac}.yaml</code></li>
          </ol>
          <h3>File Naming</h3>
          <p>
            All device configurations are stored by MAC address to ensure consistency during PXE boot.
            Example: <code>aa:bb:cc:dd:ee:ff.yaml</code>
          </p>
          <h3>When Configs Are Generated</h3>
          <ul>
            <li>When a device is approved</li>
            <li>When cluster settings are updated</li>
            <li>When manual regeneration is triggered</li>
          </ul>
        </section>

        <section id="ipxe-generator" class="wiki-section">
          <h2>iPXE Generator Service</h2>
          <p>
            The iPXE Generator creates the boot.ipxe script that controls how devices boot. This script
            is loaded by iPXE after the initial PXE boot and determines whether a device can proceed to
            boot Talos or should exit.
          </p>
          <h3>Boot Script Logic</h3>
          <div class="code-block">
            <code>
1. Device boots and loads iPXE<br>
2. iPXE downloads boot.ipxe from Ktizo<br>
3. Script checks if device MAC address is approved<br>
4. If approved: Boot Talos (load kernel + initramfs)<br>
5. If not approved and strict mode enabled: Exit to next boot device<br>
6. If not approved and strict mode disabled: Attempt local boot<br>
            </code>
          </div>
          <h3>Device Matching</h3>
          <p>
            The boot script uses iPXE's conditional logic to match devices by MAC address. Each approved
            device gets an entry in the script that loads the Talos kernel and initramfs if the MAC address
            matches.
          </p>
          <h3>Strict Boot Mode</h3>
          <p>
            When enabled, unapproved devices immediately exit to the next boot device instead of attempting
            local boot. This prevents Talos from auto-wiping existing installations.
          </p>
        </section>

        <section id="template-service" class="wiki-section">
          <h2>Template Service</h2>
          <p>
            The Template Service uses Jinja2 to render configuration files from templates. It handles the
            dnsmasq configuration that controls DHCP, DNS, TFTP, and PXE services.
          </p>
          <h3>Templates</h3>
          <ul>
            <li><strong>dnsmasq.conf.j2:</strong> Main dnsmasq configuration with DHCP/TFTP/PXE settings</li>
            <li><strong>boot.ipxe.j2:</strong> iPXE boot script with device matching logic</li>
          </ul>
          <h3>Template Variables</h3>
          <p>Templates have access to:</p>
          <ul>
            <li>Network settings (server IP, subnet, gateway, DNS)</li>
            <li>DHCP configuration (mode, range, options)</li>
            <li>Approved devices list (MAC addresses, hostnames)</li>
            <li>Talos version and file paths</li>
            <li>Strict mode flag</li>
          </ul>
          <h3>Compilation Triggers</h3>
          <p>Templates are recompiled when:</p>
          <ul>
            <li>Network settings are updated and applied</li>
            <li>A device is approved, rejected, or deleted</li>
            <li>Manual regeneration is triggered</li>
          </ul>
        </section>

        <section id="websocket" class="wiki-section">
          <h2>WebSocket Manager</h2>
          <p>
            The WebSocket Manager provides real-time communication between the backend and frontend.
            It broadcasts events to all connected clients when important actions occur.
          </p>
          <h3>Architecture</h3>
          <p>
            A single WebSocket service is shared across the entire frontend application. Components can
            subscribe to events and receive notifications without maintaining individual connections.
          </p>
          <h3>Event Types</h3>
          <ul>
            <li><strong>device_discovered:</strong> New device registered with Ktizo</li>
            <li><strong>device_approved:</strong> Device was approved for provisioning</li>
            <li><strong>device_rejected:</strong> Device was rejected</li>
            <li><strong>device_deleted:</strong> Device was removed from system</li>
            <li><strong>config_downloaded:</strong> Device downloaded its Talos configuration</li>
          </ul>
          <h3>Inference-Based Notifications</h3>
          <p>
            Toast notifications are inferred from device table changes rather than explicit event payloads.
            When an event occurs, the frontend refreshes the device list and compares it to the previous
            state to determine what changed and show appropriate notifications.
          </p>
        </section>

        <!-- Boot Process Section -->
        <section id="pxe-boot" class="wiki-section">
          <h2>PXE Boot</h2>
          <p>
            PXE (Preboot Execution Environment) is a standardized network boot protocol that allows devices
            to boot from the network instead of local storage.
          </p>
          <h3>How It Works</h3>
          <ol>
            <li>Device firmware (BIOS/UEFI) sends DHCP request with PXE options</li>
            <li>dnsmasq responds with IP address and PXE boot filename</li>
            <li>Device downloads boot file via TFTP</li>
            <li>Boot file is executed (iPXE bootloader)</li>
          </ol>
          <h3>Firmware Detection</h3>
          <p>
            Ktizo automatically detects the device's firmware type and serves the appropriate bootloader:
          </p>
          <ul>
            <li><strong>BIOS:</strong> undionly.kpxe</li>
            <li><strong>UEFI 32-bit:</strong> ipxe.efi</li>
            <li><strong>UEFI 64-bit:</strong> ipxe.efi</li>
            <li><strong>ARM UEFI:</strong> ipxe.efi</li>
          </ul>
          <h3>TFTP File Serving</h3>
          <p>
            All boot files are served from <code>/var/lib/tftpboot</code> which maps to the
            <code>compiled/</code> directory in the project. Files are organized as:
          </p>
          <div class="code-block">
            <code>
compiled/<br>
├── pxe/<br>
│   ├── undionly.kpxe        # BIOS bootloader<br>
│   ├── ipxe.efi             # UEFI bootloader<br>
│   ├── boot.ipxe            # Boot script<br>
│   └── talos/<br>
│       ├── vmlinuz-amd64-*  # Talos kernel<br>
│       └── initramfs-amd64-* # Talos initramfs<br>
└── dnsmasq/<br>
    └── dnsmasq.conf          # dnsmasq config<br>
            </code>
          </div>
        </section>

        <section id="ipxe-chain" class="wiki-section">
          <h2>iPXE Chainloading</h2>
          <p>
            iPXE is an advanced network bootloader that extends standard PXE with additional features like
            HTTP booting, scripting, and conditional logic. Ktizo uses iPXE to implement intelligent boot
            logic based on device approval status.
          </p>
          <h3>Two-Stage Boot</h3>
          <ol>
            <li><strong>Stage 1 - PXE Boot:</strong> Firmware loads iPXE bootloader via TFTP</li>
            <li><strong>Stage 2 - iPXE Script:</strong> iPXE loads boot.ipxe script and executes it</li>
          </ol>
          <h3>iPXE Detection</h3>
          <p>
            Ktizo uses DHCP option 175 to detect if iPXE is already loaded. This prevents infinite loops:
          </p>
          <ul>
            <li><strong>First boot:</strong> Firmware PXE → load iPXE bootloader</li>
            <li><strong>Second boot:</strong> iPXE detected → load boot.ipxe script</li>
          </ul>
          <h3>Boot Script Features</h3>
          <p>The boot.ipxe script provides:</p>
          <ul>
            <li>Device identification by MAC address</li>
            <li>Conditional booting based on approval status</li>
            <li>Talos kernel and initramfs loading for approved devices</li>
            <li>Kernel command-line parameter configuration</li>
            <li>Error handling and fallback logic</li>
          </ul>
        </section>

        <section id="talos-boot" class="wiki-section">
          <h2>Talos Boot</h2>
          <p>
            Once a device is approved, iPXE loads the Talos Linux kernel and initramfs. Talos then boots
            and begins the installation process.
          </p>
          <h3>Kernel Parameters</h3>
          <p>
            The boot script passes critical parameters to the Talos kernel:
          </p>
          <div class="code-block">
            <code>
talos.platform=metal           # Bare metal platform<br>
talos.config=http://SERVER/api/v1/talos/configs/MAC.yaml # Config URL<br>
            </code>
          </div>
          <h3>Configuration Download</h3>
          <p>
            During boot, Talos downloads its configuration from Ktizo using the URL specified in kernel
            parameters. The configuration determines:
          </p>
          <ul>
            <li>Node role (control plane or worker)</li>
            <li>Network configuration (hostname, IP, gateway, DNS)</li>
            <li>Cluster membership (certificates, tokens, endpoint)</li>
            <li>Installation target disk</li>
          </ul>
          <h3>Installation Process</h3>
          <ol>
            <li>Talos boots into RAM from kernel/initramfs</li>
            <li>Downloads configuration from Ktizo</li>
            <li>Validates configuration</li>
            <li>Installs Talos to disk</li>
            <li>Writes configuration to disk</li>
            <li>Reboots from disk</li>
            <li>Joins Kubernetes cluster</li>
          </ol>
        </section>

        <!-- Configuration Section -->
        <section id="network-config" class="wiki-section">
          <h2>Network Settings</h2>
          <p>
            Network settings configure the DHCP, DNS, and TFTP services that enable PXE boot.
          </p>
          <h3>Server Configuration</h3>
          <ul>
            <li><strong>Server IP:</strong> The IP address where Ktizo is running. This is used for TFTP
            and HTTP file serving.</li>
            <li><strong>Network Interface:</strong> Optional - bind to specific network interface</li>
          </ul>
          <h3>DHCP Configuration</h3>
          <ul>
            <li><strong>DHCP Mode:</strong> ProxyDHCP (recommended) or Full DHCP Server</li>
            <li><strong>DHCP Network/Netmask:</strong> Network range for DHCP service</li>
            <li><strong>DHCP Range:</strong> (Full mode only) Start and end IP addresses to assign</li>
          </ul>
          <h3>DNS Configuration</h3>
          <ul>
            <li><strong>DNS Port:</strong> Port for DNS service (0 to disable)</li>
            <li><strong>DNS Server:</strong> DNS server to use (defaults to server IP)</li>
          </ul>
          <h3>TFTP Configuration</h3>
          <ul>
            <li><strong>TFTP Root:</strong> Fixed at /var/lib/tftpboot (not configurable)</li>
            <li><strong>TFTP Secure Mode:</strong> Restricts file access to root directory only</li>
          </ul>
        </section>

        <section id="cluster-config" class="wiki-section">
          <h2>Cluster Settings</h2>
          <p>
            Cluster settings define the Kubernetes cluster that Talos nodes will join.
          </p>
          <h3>Basic Settings</h3>
          <ul>
            <li><strong>Cluster Name:</strong> Identifier for your cluster (e.g., "production")</li>
            <li><strong>Cluster Endpoint:</strong> IP address or FQDN where the Kubernetes API is accessible.
            The first control plane node must use this IP/FQDN.</li>
            <li><strong>External Subnet:</strong> Network range for cluster nodes (e.g., 10.0.128.0/24)</li>
          </ul>
          <h3>Talos Configuration</h3>
          <ul>
            <li><strong>Talos Version:</strong> Version of Talos Linux to deploy. Ktizo automatically
            downloads the kernel and initramfs for this version.</li>
          </ul>
          <h3>Cluster Secrets</h3>
          <p>
            Cluster secrets include certificates, keys, and tokens that secure communication between nodes.
            Generate these once before approving any devices. They include:
          </p>
          <ul>
            <li>Cluster CA certificate and key</li>
            <li>Kubernetes CA certificate and key</li>
            <li>Aggregator CA certificate and key</li>
            <li>Service account key</li>
            <li>Bootstrap tokens</li>
            <li>AES-CBC encryption secret</li>
          </ul>
          <div class="warning-box">
            <strong>⚠️ Important:</strong>
            <p>
              Generate cluster secrets before approving devices. If you regenerate secrets after devices
              are approved, you must re-approve all devices to update their configurations.
            </p>
          </div>
        </section>

        <section id="device-config" class="wiki-section">
          <h2>Device Configuration</h2>
          <p>
            Each device receives a unique Talos configuration based on its approved parameters.
          </p>
          <h3>Approval Parameters</h3>
          <ul>
            <li><strong>Hostname:</strong> Unique name for the device (e.g., controlplane-01, worker-03)</li>
            <li><strong>IP Address:</strong> Static IP address assigned to device</li>
            <li><strong>Role:</strong> Control Plane (runs Kubernetes API) or Worker (runs workloads)</li>
          </ul>
          <h3>First Device Requirements</h3>
          <p>
            The first device in a cluster has special requirements:
          </p>
          <ul>
            <li>Must be a Control Plane node</li>
            <li>Must use the cluster endpoint IP address</li>
            <li>Will bootstrap the Kubernetes cluster</li>
          </ul>
          <h3>Configuration Contents</h3>
          <p>Generated Talos configurations include:</p>
          <ul>
            <li>Machine type (controlplane/worker)</li>
            <li>Network settings (hostname, IP, gateway, DNS)</li>
            <li>Cluster membership (endpoint, certificates, tokens)</li>
            <li>Kubelet configuration</li>
            <li>Installation disk configuration</li>
          </ul>
        </section>

        <!-- Advanced Topics Section -->
        <section id="proxydhcp" class="wiki-section">
          <h2>ProxyDHCP Mode</h2>
          <p>
            ProxyDHCP is a DHCP mode where two DHCP servers cooperate: one assigns IP addresses (your
            existing DHCP server), and the other provides PXE boot information (Ktizo).
          </p>
          <h3>How It Works</h3>
          <ol>
            <li>Device sends DHCP request</li>
            <li>Your existing DHCP server responds with IP address, gateway, DNS</li>
            <li>Ktizo responds with PXE boot information (next-server, filename)</li>
            <li>Device uses IP from existing DHCP server</li>
            <li>Device uses PXE info from Ktizo to boot</li>
          </ol>
          <h3>Advantages</h3>
          <ul>
            <li>No changes to existing DHCP server required</li>
            <li>No conflicts with existing network infrastructure</li>
            <li>Easy to enable/disable PXE boot</li>
            <li>Works with router-based DHCP</li>
          </ul>
          <h3>When to Use Full DHCP Mode</h3>
          <p>Use full DHCP server mode when:</p>
          <ul>
            <li>You don't have an existing DHCP server</li>
            <li>You can disable your existing DHCP server</li>
            <li>You want Ktizo to manage all network services</li>
          </ul>
        </section>

        <section id="strict-mode" class="wiki-section">
          <h2>Strict Boot Mode</h2>
          <p>
            Strict Boot Mode controls what happens when an unapproved device attempts to PXE boot.
          </p>
          <h3>Enabled (Recommended)</h3>
          <p>
            Unapproved devices immediately exit to the next boot device in BIOS/UEFI boot order.
            This allows devices to fall back to booting from local disk if present.
          </p>
          <ul>
            <li><strong>Advantage:</strong> Safe - won't interfere with existing installations</li>
            <li><strong>Disadvantage:</strong> Unapproved devices won't boot if no local OS exists</li>
          </ul>
          <h3>Disabled</h3>
          <p>
            Unapproved devices may attempt to boot locally. If Talos is already installed and detects
            no valid configuration, it may auto-wipe the disk and attempt fresh installation.
          </p>
          <ul>
            <li><strong>Advantage:</strong> Devices can boot even if unapproved</li>
            <li><strong>Disadvantage:</strong> Risk of unintended disk wipe on existing Talos installations</li>
          </ul>
          <h3>Recommendation</h3>
          <p>
            Enable strict mode unless you specifically need unapproved devices to attempt local boot.
            This prevents accidental data loss from Talos auto-wipe behavior.
          </p>
        </section>

        <section id="file-structure" class="wiki-section">
          <h2>File Structure</h2>
          <p>
            Understanding where files are stored helps with troubleshooting and advanced configuration.
          </p>
          <h3>Project Structure</h3>
          <div class="code-block">
            <code>
ktizo/<br>
├── backend/                  # FastAPI backend<br>
│   ├── app/<br>
│   │   ├── api/             # API routes<br>
│   │   ├── crud/            # Database operations<br>
│   │   ├── db/              # Database models<br>
│   │   ├── schemas/         # Pydantic models<br>
│   │   ├── services/        # Business logic<br>
│   │   └── utils/           # Utility functions<br>
│   └── requirements.txt     # Python dependencies<br>
├── frontend/                 # Vue 3 frontend<br>
│   ├── src/<br>
│   │   ├── services/        # API client, WebSocket<br>
│   │   ├── views/           # Page components<br>
│   │   └── App.vue          # Root component<br>
│   └── package.json         # Node dependencies<br>
├── templates/                # Jinja2 templates<br>
│   ├── network/<br>
│   │   └── dnsmasq.conf.j2  # dnsmasq config template<br>
│   ├── pxe/<br>
│   │   └── boot.ipxe.j2     # iPXE boot script template<br>
│   └── talos/               # Talos config templates<br>
├── compiled/                 # Generated files<br>
│   ├── dnsmasq/<br>
│   │   └── dnsmasq.conf     # Active dnsmasq config<br>
│   ├── pxe/<br>
│   │   ├── boot.ipxe        # Active boot script<br>
│   │   ├── *.kpxe, *.efi    # iPXE bootloaders<br>
│   │   └── talos/           # Talos boot files<br>
│   └── talos/configs/       # Device configs by MAC<br>
├── data/                     # SQLite database<br>
│   └── ktizo.db<br>
└── docker-compose.yaml       # Container orchestration<br>
            </code>
          </div>
          <h3>Container Mounts</h3>
          <p>Docker containers mount these directories:</p>
          <ul>
            <li><strong>Backend:</strong> ./backend, ./templates, ./compiled, ./data</li>
            <li><strong>Frontend:</strong> ./frontend</li>
            <li><strong>dnsmasq:</strong> ./compiled (as /var/lib/tftpboot)</li>
          </ul>
          <h3>Generated File Locations</h3>
          <ul>
            <li><strong>dnsmasq config:</strong> compiled/dnsmasq/dnsmasq.conf</li>
            <li><strong>Boot script:</strong> compiled/pxe/boot.ipxe</li>
            <li><strong>Device configs:</strong> compiled/talos/configs/{mac}.yaml</li>
            <li><strong>iPXE bootloaders:</strong> compiled/pxe/*.kpxe, *.efi</li>
            <li><strong>Talos images:</strong> compiled/pxe/talos/vmlinuz-*, initramfs-*</li>
          </ul>
        </section>

      </main>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Wiki',
  methods: {
    scrollTo(id) {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }
}
</script>

<style scoped>
.wiki {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
  color: #666;
}

.breadcrumbs a {
  color: #2196f3;
  text-decoration: none;
}

.breadcrumbs a:hover {
  text-decoration: underline;
}

.breadcrumbs .separator {
  color: #999;
}

.breadcrumbs .current {
  color: #2c3e50;
  font-weight: 500;
}

.wiki-container {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 2rem;
  align-items: start;
}

.toc {
  position: sticky;
  top: 1rem;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
}

.toc h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.1rem;
  border-bottom: 2px solid #42b983;
  padding-bottom: 0.5rem;
}

.toc-section {
  margin-bottom: 1.5rem;
}

.toc-section:last-child {
  margin-bottom: 0;
}

.toc-section h4 {
  margin: 0 0 0.5rem 0;
  color: #42b983;
  font-size: 0.95rem;
  font-weight: 600;
}

.toc-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-section li {
  margin-bottom: 0.4rem;
}

.toc-section a {
  color: #555;
  text-decoration: none;
  font-size: 0.9rem;
  display: block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.toc-section a:hover {
  background: #f0f0f0;
  color: #2c3e50;
  padding-left: 0.75rem;
}

.wiki-content {
  background: white;
  padding: 2.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  min-height: 80vh;
}

.wiki-content h1 {
  color: #2c3e50;
  margin: 0 0 1rem 0;
  font-size: 2.5rem;
}

.intro {
  font-size: 1.1rem;
  color: #666;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #e9ecef;
}

.wiki-section {
  margin-bottom: 3rem;
  scroll-margin-top: 2rem;
}

.wiki-section h2 {
  color: #2c3e50;
  font-size: 1.8rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #42b983;
}

.wiki-section h3 {
  color: #2c3e50;
  font-size: 1.3rem;
  margin: 1.5rem 0 0.75rem 0;
}

.wiki-section h4 {
  color: #2c3e50;
  font-size: 1.1rem;
  margin: 1rem 0 0.5rem 0;
}

.wiki-section p {
  color: #555;
  line-height: 1.8;
  margin-bottom: 1rem;
}

.wiki-section ul,
.wiki-section ol {
  color: #555;
  line-height: 1.8;
  margin: 1rem 0 1rem 1.5rem;
}

.wiki-section li {
  margin-bottom: 0.5rem;
}

.wiki-section strong {
  color: #2c3e50;
}

.architecture-diagram {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
}

.component {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  text-align: center;
  border: 2px solid #42b983;
}

.component h4 {
  color: #42b983;
  margin: 0 0 0.5rem 0;
}

.component p {
  color: #666;
  font-size: 0.9rem;
  margin: 0;
}

.workflow-steps {
  background: #f8f9fa;
  padding: 1.5rem 1.5rem 1.5rem 2.5rem;
  border-radius: 6px;
  border-left: 4px solid #42b983;
}

.workflow-steps li {
  margin-bottom: 1rem;
}

.code-block {
  background: #2c3e50;
  color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  margin: 1rem 0;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

.modes {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
}

.mode-card {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  border-left: 4px solid #2196f3;
}

.mode-card h4 {
  color: #2196f3;
  margin: 0 0 0.75rem 0;
}

.mode-card p {
  margin: 0;
  font-size: 0.95rem;
}

.warning-box {
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  padding: 1rem;
  border-radius: 6px;
  margin: 1rem 0;
}

.warning-box strong {
  color: #856404;
  display: block;
  margin-bottom: 0.5rem;
}

.warning-box p {
  color: #856404;
  margin: 0;
}

@media (max-width: 1024px) {
  .wiki-container {
    grid-template-columns: 1fr;
  }

  .toc {
    position: relative;
    top: 0;
    max-height: none;
  }

  .architecture-diagram,
  .modes {
    grid-template-columns: 1fr;
  }
}
</style>
