<template>
  <div class="storage-settings">
    <div class="header">
      <h2>Storage Settings</h2>
      <p class="subtitle">Configure disk space allocation for Talos system partitions</p>
    </div>

    <div class="content-wrapper">
      <aside class="toc">
        <h3>Table of Contents</h3>
        <nav>
          <ul>
            <li><a href="#overview" @click.prevent="scrollTo('overview')">Overview</a></li>
            <li><a href="#install-disk" @click.prevent="scrollTo('install-disk')">Installation Disk</a></li>
            <li><a href="#ephemeral-config" @click.prevent="scrollTo('ephemeral-config')">EPHEMERAL Storage</a></li>
            <li><a href="#advanced" @click.prevent="scrollTo('advanced')">Advanced Options</a></li>
          </ul>
        </nav>
      </aside>

      <div class="form-container">
        <div v-if="loading" class="loading">Loading storage configuration...</div>

        <div v-else>
          <!-- Overview Section -->
          <div class="section" id="overview">
            <h3>📊 Understanding Talos Disk Layout</h3>

            <div class="info-box">
              <strong>What is this page for?</strong>
              <p>
                When Talos installs on a machine, it automatically creates several partitions on your disk.
                By default, the <strong>EPHEMERAL</strong> partition will consume all remaining disk space.
                This page lets you <strong>limit how much space</strong> Talos uses, leaving room for other
                storage systems like Rook/Ceph.
              </p>
            </div>

            <div class="disk-layout-diagram">
              <h4>Default Talos Disk Layout (Automatic)</h4>
              <div class="partition-viz">
                <div class="partition partition-efi" title="EFI Boot Partition">
                  <span>EFI</span>
                  <small>~100MB</small>
                </div>
                <div class="partition partition-meta" title="Metadata">
                  <span>META</span>
                  <small>~1MB</small>
                </div>
                <div class="partition partition-state" title="System State">
                  <span>STATE</span>
                  <small>~100MB</small>
                </div>
                <div class="partition partition-ephemeral" title="Container Data, Images, Logs">
                  <span>EPHEMERAL</span>
                  <small>Rest of disk</small>
                </div>
              </div>
              <p class="diagram-note">
                <strong>EPHEMERAL</strong> stores: Container data, downloaded images, logs, and etcd database (on control planes)
              </p>
            </div>

            <div class="warning-box" style="margin-top: 1rem;">
              <strong>🎯 Why limit EPHEMERAL?</strong>
              <p>
                If you plan to use storage solutions like <strong>Rook/Ceph</strong>, they need unpartitioned
                space on the disk. By limiting EPHEMERAL to a specific size (e.g., 100GB), you leave the
                remaining disk space available for Rook/Ceph to claim as Object Storage Devices (OSDs).
              </p>
            </div>
          </div>

          <!-- Installation Disk Section -->
          <div class="section" id="install-disk">
            <h3>💿 Installation Disk Configuration</h3>

            <form @submit.prevent="saveClusterSettings">
              <div class="form-group">
                <label>Install Disk *</label>
                <input
                  v-model="clusterSettings.install_disk"
                  type="text"
                  required
                  placeholder="/dev/sda"
                  :disabled="loading"
                />
                <div class="info-box" style="margin-top: 0.5rem;">
                  <strong>What is this?</strong>
                  <p>
                    This is the disk device where Talos Linux will be installed. Talos will automatically
                    partition this disk and create the EFI, META, STATE, and EPHEMERAL partitions.
                  </p>
                  <p>
                    <strong>Common device names:</strong>
                  </p>
                  <ul>
                    <li><code>/dev/sda</code> - First SATA/SCSI disk</li>
                    <li><code>/dev/nvme0n1</code> - First NVMe disk</li>
                    <li><code>/dev/vda</code> - First virtio disk (virtual machines)</li>
                  </ul>
                  <p>
                    <strong>How to find your disk:</strong> When a device boots via PXE, check the device discovery
                    information or boot into a live environment and run <code>lsblk</code> to list available disks.
                  </p>
                  <p>
                    <strong>⚠️ Warning:</strong> The installation process will <strong>wipe all data</strong>
                    on this disk. Make sure you select the correct device!
                  </p>
                </div>
              </div>

              <div class="form-actions">
                <button type="submit" class="save-btn" :disabled="loading">
                  {{ loading ? 'Saving...' : 'Save Disk Configuration' }}
                </button>
              </div>
            </form>
          </div>

          <!-- EPHEMERAL Configuration Section -->
          <div class="section" id="ephemeral-config">
            <h3>💾 EPHEMERAL Storage Configuration</h3>

            <form @submit.prevent="saveEphemeralConfig">
              <div class="form-group">
                <label>
                  <input
                    type="checkbox"
                    v-model="ephemeralConfig.enabled"
                  />
                  Limit EPHEMERAL partition size
                </label>
                <small>Enable to prevent EPHEMERAL from using the entire disk</small>
              </div>

              <div v-if="ephemeralConfig.enabled" class="config-panel">
                <div class="form-group">
                  <label>Maximum Size *</label>
                  <div class="size-input-group">
                    <input
                      v-model="ephemeralConfig.maxSize"
                      type="text"
                      required
                      placeholder="e.g., 100GB"
                      :disabled="loading"
                    />
                  </div>
                  <div class="info-box" style="margin-top: 0.5rem;">
                    <strong>How much space should I allocate?</strong>
                    <p>
                      <strong>Minimum recommended:</strong> 20GB for basic operations<br>
                      <strong>Control Plane nodes:</strong> 50-100GB (needs space for etcd database)<br>
                      <strong>Worker nodes:</strong> 50-200GB (depending on workload size)
                    </p>
                    <p>
                      <strong>Format:</strong> Specify size with units: <code>20GB</code>, <code>100GB</code>, <code>500GB</code>, <code>1TB</code>
                    </p>
                    <p>
                      <strong>Example calculation:</strong> If you have a 1TB disk and set max size to 100GB,
                      you'll have ~900GB of unpartitioned space remaining for Rook/Ceph.
                    </p>
                  </div>
                </div>

                <div class="form-group">
                  <label>Minimum Size</label>
                  <input
                    v-model="ephemeralConfig.minSize"
                    type="text"
                    placeholder="e.g., 2GB (default)"
                    :disabled="loading"
                  />
                  <small>Minimum space Talos will guarantee for EPHEMERAL (default: 2GB)</small>
                </div>
              </div>

              <div v-if="!ephemeralConfig.enabled" class="info-box">
                <strong>ℹ️ Default Behavior</strong>
                <p>
                  When unchecked, EPHEMERAL will automatically grow to use all available disk space.
                  This is fine if you don't need space for other storage systems.
                </p>
              </div>

              <div class="form-actions">
                <button type="submit" class="save-btn" :disabled="loading">
                  {{ loading ? 'Saving...' : 'Save Configuration' }}
                </button>
              </div>
            </form>
          </div>

          <!-- Advanced Section -->
          <div class="section" id="advanced">
            <h3>⚙️ Advanced Options</h3>

            <div class="form-group">
              <label>Disk Selector (CEL Expression)</label>
              <input
                v-model="ephemeralConfig.diskSelector"
                type="text"
                placeholder="e.g., disk.transport == 'nvme'"
                :disabled="loading || !ephemeralConfig.enabled"
              />
              <div class="info-box" style="margin-top: 0.5rem;">
                <strong>What is a Disk Selector?</strong>
                <p>
                  By default, Talos uses the installation disk (usually <code>/dev/sda</code>).
                  If you have multiple disks, you can use a CEL (Common Expression Language) expression
                  to select which disk to use for EPHEMERAL.
                </p>
                <p>
                  <strong>Examples:</strong>
                </p>
                <ul>
                  <li><code>disk.transport == 'nvme'</code> - Use NVMe drives</li>
                  <li><code>disk.size > 500GB</code> - Use disks larger than 500GB</li>
                  <li><code>disk.model == 'Samsung SSD'</code> - Use specific drive model</li>
                </ul>
                <p>
                  <strong>⚠️ Leave empty unless you know what you're doing!</strong>
                  Most users should leave this blank to use the default installation disk.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div v-if="message" :class="['message', messageType]">
          {{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'

export default {
  name: 'StorageSettings',
  data() {
    return {
      loading: true,
      clusterSettings: {
        id: null,
        install_disk: '/dev/sda'
      },
      ephemeralConfig: {
        enabled: false,
        maxSize: '100GB',
        minSize: '2GB',
        diskSelector: ''
      },
      ephemeralConfigId: null,
      message: null,
      messageType: 'success'
    }
  },
  async mounted() {
    await this.loadConfiguration()
  },
  methods: {
    async loadConfiguration() {
      this.loading = true
      try {
        // Load cluster settings (for install disk)
        try {
          const cluster = await apiService.getClusterSettings()
          this.clusterSettings = {
            id: cluster.id,
            install_disk: cluster.install_disk || '/dev/sda'
          }
        } catch (error) {
          if (error.response?.status !== 404) {
            console.error('Error loading cluster settings:', error)
          }
        }

        // Try to load existing EPHEMERAL configuration
        const config = await apiService.getVolumeConfigByName('EPHEMERAL')
        this.ephemeralConfigId = config.id
        this.ephemeralConfig = {
          enabled: true,
          maxSize: config.max_size || '100GB',
          minSize: config.min_size || '2GB',
          diskSelector: config.disk_selector_match || ''
        }
      } catch (error) {
        // No configuration exists yet, use defaults
        if (error.response?.status !== 404) {
          console.error('Error loading volume config:', error)
        }
      } finally {
        this.loading = false
      }
    },
    async saveClusterSettings() {
      this.loading = true
      try {
        const payload = {
          install_disk: this.clusterSettings.install_disk
        }

        if (this.clusterSettings.id) {
          // Update existing settings
          await apiService.updateClusterSettings(this.clusterSettings.id, payload)
          this.showMessage('Installation disk configuration updated successfully', 'success')
        } else {
          // Create new settings (unlikely for this scenario but handle it)
          const created = await apiService.createClusterSettings(payload)
          this.clusterSettings.id = created.id
          this.showMessage('Installation disk configuration created successfully', 'success')
        }
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || 'Failed to save installation disk configuration',
          'error'
        )
      } finally {
        this.loading = false
      }
    },
    async saveEphemeralConfig() {
      this.loading = true
      try {
        const payload = {
          name: 'EPHEMERAL',
          max_size: this.ephemeralConfig.enabled ? this.ephemeralConfig.maxSize : null,
          min_size: this.ephemeralConfig.enabled ? this.ephemeralConfig.minSize : null,
          disk_selector_match: this.ephemeralConfig.enabled && this.ephemeralConfig.diskSelector ? this.ephemeralConfig.diskSelector : null,
          grow: false  // Don't auto-grow when we set a max size
        }

        if (this.ephemeralConfigId) {
          // Update existing configuration
          if (this.ephemeralConfig.enabled) {
            await apiService.updateVolumeConfig(this.ephemeralConfigId, payload)
            this.showMessage('EPHEMERAL configuration updated successfully', 'success')
          } else {
            // Delete configuration if disabled
            await apiService.deleteVolumeConfig(this.ephemeralConfigId)
            this.ephemeralConfigId = null
            this.showMessage('EPHEMERAL size limit removed - will use full disk', 'success')
          }
        } else if (this.ephemeralConfig.enabled) {
          // Create new configuration
          const created = await apiService.createVolumeConfig(payload)
          this.ephemeralConfigId = created.id
          this.showMessage('EPHEMERAL configuration created successfully', 'success')
        }
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || 'Failed to save configuration',
          'error'
        )
      } finally {
        this.loading = false
      }
    },
    scrollTo(id) {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    },
    showMessage(text, type) {
      this.message = text
      this.messageType = type
      setTimeout(() => {
        this.message = null
      }, 5000)
    }
  }
}
</script>

<style scoped>
.storage-settings {
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
  scroll-margin-top: 2rem;
}

.section:last-of-type {
  border-bottom: none;
  margin-bottom: 1.5rem;
}

.section h3 {
  color: #2c3e50;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e9ecef;
}

.section h4 {
  color: #495057;
  margin-bottom: 1rem;
  font-size: 1rem;
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

.warning-box {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  border-radius: 4px;
  padding: 1rem;
  font-size: 0.9rem;
  line-height: 1.5;
}

.warning-box strong {
  display: block;
  color: #92400e;
  margin-bottom: 0.5rem;
}

.warning-box p {
  color: #78350f;
  margin: 0;
}

.disk-layout-diagram {
  margin: 1.5rem 0;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.partition-viz {
  display: flex;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin: 1rem 0;
}

.partition {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 0.85rem;
  position: relative;
}

.partition small {
  font-size: 0.7rem;
  font-weight: normal;
  opacity: 0.9;
}

.partition-efi {
  background: #6366f1;
  flex: 0 0 80px;
}

.partition-meta {
  background: #8b5cf6;
  flex: 0 0 40px;
}

.partition-state {
  background: #ec4899;
  flex: 0 0 80px;
}

.partition-ephemeral {
  background: #f59e0b;
  flex: 1;
}

.diagram-note {
  font-size: 0.85rem;
  color: #666;
  margin-top: 0.5rem;
  font-style: italic;
}

.config-panel {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #2c3e50;
  font-weight: 500;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input[type="text"]:focus {
  outline: none;
  border-color: #5a67d8;
}

.form-group input[type="text"]:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.85rem;
}

.size-input-group {
  display: flex;
  gap: 0.5rem;
}

.form-actions {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  background: #42b983;
  color: white;
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background 0.3s;
}

.save-btn:hover:not(:disabled) {
  background: #35a372;
}

.save-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
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
</style>
