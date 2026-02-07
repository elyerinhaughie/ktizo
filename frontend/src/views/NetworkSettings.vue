<template>
  <div class="network-settings">
    <div class="header">
      <h2>Network Settings</h2>
      <p class="subtitle">Configure PXE/TFTP server network parameters</p>
    </div>

    <div class="content-wrapper">
      <aside class="toc">
        <h3>Table of Contents</h3>
        <nav>
          <ul>
            <li><a href="#server-config" @click.prevent="scrollTo('server-config')">Server Configuration</a></li>
            <li><a href="#dhcp-config" @click.prevent="scrollTo('dhcp-config')">DHCP Configuration</a></li>
            <li><a href="#dns-config" @click.prevent="scrollTo('dns-config')">DNS Configuration</a></li>
            <li><a href="#tftp-config" @click.prevent="scrollTo('tftp-config')">TFTP Configuration</a></li>
            <li><a href="#pxe-config" @click.prevent="scrollTo('pxe-config')">PXE Boot Configuration</a></li>
            <li><a href="#logging-config" @click.prevent="scrollTo('logging-config')">Logging</a></li>
          </ul>
        </nav>
      </aside>

      <div class="form-container">
      <form @submit.prevent="saveSettings">
        <div class="section" id="server-config">
          <h3>Server Configuration</h3>

          <div class="form-group">
            <label>Server IP Address *</label>
            <input
              v-model="settings.server_ip"
              type="text"
              required
              placeholder="e.g., 10.0.5.113"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                This is the IP address of the host machine where Ktizo is running. Since Ktizo runs in a Docker
                container using host networking mode, it shares the network stack with your host machine.
              </p>
              <p>
                <strong>How to find it:</strong> On your host machine, run <code>ip addr</code> or <code>ifconfig</code>
                to see your network interfaces. Look for the IP address on the interface connected to your local network
                (typically something like 192.168.x.x or 10.x.x.x).
              </p>
              <p>
                <strong>Why it matters:</strong> Client machines booting via PXE will contact this IP address to download
                boot files via TFTP and retrieve their Talos configurations. This IP must be reachable from the network
                where your bare-metal servers are located.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>Network Interface</label>
            <input
              v-model="settings.interface"
              type="text"
              placeholder="e.g., eth0 (leave empty for all interfaces)"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The network interface name on your host machine to bind services to. Because Ktizo uses Docker's
                host networking mode, you can specify which physical network interface the DHCP and TFTP services
                should listen on.
              </p>
              <p>
                <strong>When to use it:</strong> Leave this empty to listen on all interfaces (recommended for most setups).
                Only specify an interface if you have multiple networks and want to restrict PXE services to a specific one.
              </p>
              <p>
                <strong>Example interfaces:</strong>
              </p>
              <ul>
                <li><code>eth0</code> or <code>enp0s3</code> - Common wired Ethernet interfaces</li>
                <li><code>ens192</code> - VMware virtual network interface</li>
                <li><code>br0</code> - Bridge interface (if using network bridging)</li>
              </ul>
              <p>
                <strong>How to find it:</strong> Run <code>ip link show</code> or <code>ifconfig</code> on your host
                machine to list all available network interfaces.
              </p>
            </div>
          </div>
        </div>

        <div class="section" id="dhcp-config">
          <h3>DHCP Configuration</h3>

          <div class="form-group">
            <label>DHCP Mode</label>
            <select v-model="settings.dhcp_mode" :disabled="loading">
              <option value="proxy">ProxyDHCP (recommended - works with existing DHCP server)</option>
              <option value="server">Full DHCP Server (assigns IP addresses)</option>
            </select>
            <small v-if="settings.dhcp_mode === 'proxy'">
              ProxyDHCP mode: Ktizo provides PXE boot information but doesn't assign IP addresses. Your existing DHCP server handles IP assignment.
            </small>
            <small v-else>
              Full DHCP Server mode: Ktizo will assign IP addresses and provide PXE boot information. Make sure to disable your existing DHCP server to avoid conflicts!
            </small>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>DHCP Network</label>
              <input
                v-model="settings.dhcp_network"
                type="text"
                placeholder="10.0.0.0"
                :disabled="loading"
              />
            </div>

            <div class="form-group">
              <label>DHCP Netmask</label>
              <input
                v-model="settings.dhcp_netmask"
                type="text"
                placeholder="255.255.0.0"
                :disabled="loading"
              />
            </div>
          </div>

          <div v-if="settings.dhcp_mode === 'server'" class="form-row">
            <div class="form-group">
              <label>DHCP Range Start</label>
              <input
                v-model="settings.dhcp_range_start"
                type="text"
                placeholder="10.0.128.10"
                :disabled="loading"
              />
              <small>First IP address to assign</small>
            </div>

            <div class="form-group">
              <label>DHCP Range End</label>
              <input
                v-model="settings.dhcp_range_end"
                type="text"
                placeholder="10.0.128.250"
                :disabled="loading"
              />
              <small>Last IP address to assign</small>
            </div>
          </div>
        </div>

        <div class="section" id="dns-config">
          <h3>DNS Configuration</h3>

          <div class="form-row">
            <div class="form-group">
              <label>DNS Port</label>
              <input
                v-model.number="settings.dns_port"
                type="number"
                placeholder="0"
                :disabled="loading"
              />
              <small>0 to disable DNS resolution</small>
            </div>

            <div class="form-group">
              <label>DNS Server</label>
              <input
                v-model="settings.dns_server"
                type="text"
                placeholder="Leave empty to use server IP"
                :disabled="loading"
              />
            </div>
          </div>
        </div>

        <div class="section" id="tftp-config">
          <h3>TFTP Configuration</h3>

          <div class="form-group">
            <label>TFTP Root Directory</label>
            <input
              value="/var/lib/tftpboot"
              type="text"
              disabled
              class="readonly-field"
            />
            <small>Fixed path - automatically managed by Ktizo</small>
          </div>

          <div class="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                v-model="settings.tftp_secure"
                :disabled="loading"
              />
              Enable TFTP Secure Mode
            </label>
            <small>Prevents path traversal attacks by blocking requests containing ".." (recommended: enabled)</small>
            <div v-if="!settings.tftp_secure" class="warning-box" style="margin-top: 0.5rem;">
              <strong>⚠️ Security Warning</strong>
              <p>Disabling TFTP secure mode allows clients to use ".." in file paths, which could allow access to files outside the TFTP root directory. Only disable this if you have a specific reason and understand the security implications.</p>
            </div>
          </div>
        </div>

        <div class="section" id="pxe-config">
          <h3>PXE Boot Configuration</h3>

          <div class="form-group">
            <label>iPXE Boot Script Path</label>
            <input
              value="pxe/boot.ipxe"
              type="text"
              disabled
              class="readonly-field"
            />
            <small>Fixed path - automatically managed by Ktizo</small>
          </div>

          <div class="form-group">
            <label>Talos Version</label>
            <input
              v-model="settings.talos_version"
              type="text"
              placeholder="v1.11.3"
              :disabled="loading"
            />
            <small>Version of Talos Linux to download and boot (e.g., v1.11.3). Files will be downloaded automatically when version changes.</small>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>PXE Prompt Text</label>
              <input
                v-model="settings.pxe_prompt"
                type="text"
                placeholder="Press F8 for boot menu"
                :disabled="loading"
              />
            </div>

            <div class="form-group">
              <label>PXE Timeout (seconds)</label>
              <input
                v-model.number="settings.pxe_timeout"
                type="number"
                placeholder="3"
                :disabled="loading"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="settings.strict_boot_mode"
                :disabled="loading"
              />
              <span>Strict Boot Mode</span>
            </label>
            <small class="help-text">
              When enabled, unapproved devices will exit immediately to the next BIOS boot device
              instead of attempting to boot from local disk. This prevents unapproved devices from
              accessing the network boot system.
            </small>
            <div v-if="!settings.strict_boot_mode" class="warning-box">
              <strong>⚠️ Warning:</strong> With strict mode disabled, unapproved devices may attempt to boot from
              local disk. If no bootable OS is found, the device will automatically enter the Talos installation
              menu, which could result in <strong>unintended disk wiping and OS installation</strong>. Enable strict
              mode to prevent this behavior in production environments.
            </div>
          </div>
        </div>

        <div class="section" id="logging-config">
          <h3>Logging</h3>

          <div class="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                v-model="settings.enable_logging"
                :disabled="loading"
              />
              Enable DHCP Logging
            </label>
          </div>
        </div>

        <div class="button-group">
          <button type="submit" class="save-btn" :disabled="loading || saving">
            {{ saving ? 'Saving...' : 'Save & Apply Settings' }}
          </button>
        </div>
        <p class="info-text" style="margin-top: 0.5rem;">
          Settings are automatically applied when saved (regenerates dnsmasq.conf and boot.ipxe)
        </p>

        <div v-if="message" :class="['message', messageType]">
          {{ message }}
        </div>
      </form>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'

export default {
  name: 'NetworkSettings',
  data() {
    return {
      settings: {
        interface: '',
        server_ip: '',
        dhcp_mode: 'proxy',
        dhcp_network: '10.0.0.0',
        dhcp_netmask: '255.255.0.0',
        dhcp_range_start: '',
        dhcp_range_end: '',
        dns_port: 0,
        dns_server: '',
        tftp_root: '/var/lib/tftpboot',
        tftp_secure: true,
        ipxe_boot_script: 'pxe/boot.ipxe',
        pxe_prompt: 'Press F8 for boot menu',
        pxe_timeout: 3,
        strict_boot_mode: true,
        talos_version: 'v1.11.3',
        enable_logging: true
      },
      settingsId: null,
      loading: true,
      saving: false,
      message: null,
      messageType: 'success'
    }
  },
  async mounted() {
    await this.loadSettings()
  },
  methods: {
    async loadSettings() {
      this.loading = true
      try {
        const response = await apiService.getNetworkSettings()
        this.settings = {
          interface: response.interface,
          server_ip: response.server_ip,
          dhcp_mode: response.dhcp_mode || 'proxy',
          dhcp_network: response.dhcp_network,
          dhcp_netmask: response.dhcp_netmask,
          dhcp_range_start: response.dhcp_range_start || '',
          dhcp_range_end: response.dhcp_range_end || '',
          dns_port: response.dns_port,
          dns_server: response.dns_server,
          tftp_root: response.tftp_root,
          tftp_secure: response.tftp_secure,
          ipxe_boot_script: response.ipxe_boot_script,
          pxe_prompt: response.pxe_prompt,
          pxe_timeout: response.pxe_timeout,
          strict_boot_mode: response.strict_boot_mode || false,
          talos_version: response.talos_version || 'v1.11.3',
          enable_logging: response.enable_logging
        }
        this.settingsId = response.id
        this.showMessage('Settings loaded successfully', 'success')
      } catch (error) {
        if (error.response?.status === 404) {
          // 404 is expected on first run - no settings exist yet
          this.showMessage('No settings found. Please configure and save your network settings below.', 'info')
        } else if (error.response?.data?.detail) {
          // Show detailed error message from API
          this.showMessage(`Failed to load settings: ${error.response.data.detail}`, 'error')
        } else if (error.message) {
          // Network error or other error with message
          this.showMessage(`Failed to load settings: ${error.message}`, 'error')
        } else {
          // Generic fallback
          this.showMessage('Failed to load settings. Check that the backend is running and accessible.', 'error')
        }
        console.error('Error loading network settings:', error)
      } finally {
        this.loading = false
      }
    },
    async saveSettings() {
      this.saving = true
      try {
        let response
        if (this.settingsId) {
          response = await apiService.updateNetworkSettings(this.settingsId, this.settings)
        } else {
          response = await apiService.createNetworkSettings(this.settings)
          this.settingsId = response.id
        }
        this.showMessage('Settings saved and applied successfully (dnsmasq.conf and boot.ipxe regenerated)', 'success')
      } catch (error) {
        let errorMessage = 'Failed to save settings'
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.message) {
          errorMessage = `${errorMessage}: ${error.message}`
        }
        this.showMessage(errorMessage, 'error')
        console.error('Error saving network settings:', error)
      } finally {
        this.saving = false
      }
    },
    showMessage(text, type) {
      this.message = text
      this.messageType = type
      setTimeout(() => {
        this.message = null
      }, 5000)
    },
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
.network-settings {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  margin-bottom: 2rem;
}

h2 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 0;
}

.content-wrapper {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.toc {
  position: sticky;
  top: 2rem;
  width: 250px;
  flex-shrink: 0;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.toc h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #2c3e50;
  font-size: 1.1rem;
  border-bottom: 2px solid #42b983;
  padding-bottom: 0.5rem;
}

.toc nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc nav li {
  margin-bottom: 0.75rem;
}

.toc nav a {
  color: #666;
  text-decoration: none;
  font-size: 0.9rem;
  line-height: 1.4;
  display: block;
  padding: 0.25rem 0;
  transition: color 0.2s;
}

.toc nav a:hover {
  color: #42b983;
}

.form-container {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  flex: 1;
  min-width: 0;
}

.section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.section:last-of-type {
  border-bottom: none;
  margin-bottom: 1.5rem;
}

h3 {
  color: #2c3e50;
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #2c3e50;
  font-weight: 500;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
  cursor: pointer;
}

.checkbox-label span {
  font-weight: 500;
}

.help-text {
  display: block;
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.85rem;
  line-height: 1.5;
}

.warning-box {
  margin-top: 0.75rem;
  padding: 1rem;
  background: #fff3cd;
  border-left: 4px solid #ff9800;
  border-radius: 4px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #856404;
}

.warning-box strong {
  color: #721c24;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.85rem;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  margin-right: 0.5rem;
  width: auto;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.save-btn,
.apply-btn {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

.save-btn {
  background: #42b983;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #35a372;
}

.apply-btn {
  background: #2c3e50;
  color: white;
}

.apply-btn:hover:not(:disabled) {
  background: #1a252f;
}

.save-btn:disabled,
.apply-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.message.info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.info-box {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 1rem;
  border-radius: 6px;
  margin-top: 0.5rem;
}

.info-box strong {
  color: #1565c0;
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.info-box p {
  color: #424242;
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
}

.info-box ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
  color: #424242;
  font-size: 0.9rem;
  line-height: 1.6;
}

.info-box li {
  margin: 0.25rem 0;
}

.readonly-field {
  background: #f8f9fa !important;
  color: #6c757d !important;
  cursor: not-allowed !important;
}
</style>
