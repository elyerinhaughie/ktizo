<template>
  <div class="device-management">
    <h2>Device Management</h2>
    <p class="subtitle">Approve and manage devices for cluster deployment</p>

    <div class="info-banner">
      <strong>ℹ️ How Device Discovery Works</strong>
      <p>
        Devices will appear in this list automatically when Talos attempts to retrieve its configuration
        during the boot process. Unapproved devices will fail to get their config and Talos will retry
        periodically until the device is approved, at which point the config download will succeed.
      </p>
      <p>
        <strong>Strict Boot Mode:</strong> Control what happens to unapproved devices in
        <router-link to="/network" class="link">Network Settings</router-link>.
        When disabled, unapproved devices may attempt local boot and could auto-wipe if no OS is found.
        Enable Strict Mode to make unapproved devices exit immediately to the next boot device.
      </p>
    </div>

    <div class="controls">
      <div class="search-filter-group">
        <div class="search-box">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by MAC, hostname, or IP..."
            class="search-input"
          />
        </div>

        <div class="filter-group">
          <label>Status:</label>
          <select v-model="statusFilter" @change="loadDevices">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div class="action-buttons">
        <button
          v-if="hasApprovedControlPlane"
          @click="bootstrapCluster"
          class="bootstrap-btn"
          :disabled="bootstrapping"
        >
          {{ bootstrapping ? 'Bootstrapping...' : '🚀 Bootstrap Cluster' }}
        </button>
        <button @click="showAddModal = true" class="add-btn">
          + Add Device Manually
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading devices...</div>

    <div v-else-if="devices.length === 0" class="no-devices">
      <p>No devices found.</p>
      <p class="info-text">
        Devices will appear here automatically when they attempt to boot via PXE,
        or you can add them manually using the button above.
      </p>
    </div>

    <div v-else class="devices-table">
      <table>
        <thead>
          <tr>
            <th @click="sortBy('mac_address')" class="sortable">
              MAC Address
              <span class="sort-indicator" v-if="sortColumn === 'mac_address'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('hostname')" class="sortable">
              Hostname
              <span class="sort-indicator" v-if="sortColumn === 'hostname'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('ip_address')" class="sortable">
              IP Address
              <span class="sort-indicator" v-if="sortColumn === 'ip_address'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('role')" class="sortable">
              Role
              <span class="sort-indicator" v-if="sortColumn === 'role'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('status')" class="sortable">
              Status
              <span class="sort-indicator" v-if="sortColumn === 'status'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('first_seen')" class="sortable">
              First Seen
              <span class="sort-indicator" v-if="sortColumn === 'first_seen'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('last_config_download')" class="sortable">
              Last Config Download
              <span class="sort-indicator" v-if="sortColumn === 'last_config_download'">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="device in filteredAndSortedDevices" :key="device.id" :class="'status-' + device.status">
            <td class="mono">{{ device.mac_address }}</td>
            <td>{{ device.hostname || '-' }}</td>
            <td class="mono">{{ device.ip_address || '-' }}</td>
            <td>
              <span v-if="device.status !== 'pending' && device.role" class="role-badge" :class="'role-' + device.role">
                {{ device.role }}
              </span>
              <span v-else class="text-muted">-</span>
            </td>
            <td>
              <span class="status-badge" :class="'status-' + device.status">
                {{ device.status }}
              </span>
            </td>
            <td>{{ formatDate(device.first_seen) }}</td>
            <td>{{ device.last_config_download ? formatDate(device.last_config_download) : 'Never' }}</td>
            <td class="actions">
              <button
                v-if="device.status === 'pending'"
                @click="openApprovalModal(device.id)"
                class="approve-btn"
                title="Approve"
              >
                ✓
              </button>
              <button
                v-if="device.status === 'pending'"
                @click="rejectDevice(device.id)"
                class="reject-btn"
                title="Reject"
              >
                ✗
              </button>
              <button
                @click="editDevice(device)"
                class="edit-btn"
                title="Edit"
              >
                ✎
              </button>
              <button
                @click="deleteDevice(device.id)"
                class="delete-btn"
                title="Delete"
              >
                🗑
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Device Modal -->
    <div v-if="showAddModal || editingDevice" class="modal-overlay" @click="closeModal">
      <div class="modal" @click.stop>
        <h3>{{ editingDevice ? 'Edit Device' : 'Add Device' }}</h3>

        <div v-if="isEditingOnlyControlPlane" class="warning-box" style="margin-bottom: 1.5rem;">
          <strong>⚠️ Only Control Plane Node</strong>
          <p>This is the only control plane node in your cluster. IP address and role cannot be changed. Add another control plane node first if you need to make changes.</p>
        </div>

        <form @submit.prevent="saveDevice">
          <div class="form-group">
            <label>MAC Address *</label>
            <input
              v-model="deviceForm.mac_address"
              type="text"
              required
              placeholder="00:11:22:33:44:55"
              :disabled="!!editingDevice"
            />
          </div>

          <div class="form-group">
            <label>Hostname</label>
            <input
              v-model="deviceForm.hostname"
              type="text"
              placeholder="node-01"
            />
          </div>

          <div class="form-group">
            <label>IP Address</label>
            <input
              v-model="deviceForm.ip_address"
              type="text"
              placeholder="10.0.5.100"
              :disabled="isEditingOnlyControlPlane"
            />
            <small v-if="!isEditingOnlyControlPlane">Leave empty for DHCP assignment</small>
            <small v-else class="warning-text">Cannot change IP of only control plane node</small>
          </div>

          <div class="form-group">
            <label>Role</label>
            <select v-model="deviceForm.role" :disabled="isEditingOnlyControlPlane">
              <option value="worker">Worker</option>
              <option value="controlplane">Control Plane</option>
            </select>
            <small v-if="isEditingOnlyControlPlane" class="warning-text">Cannot change role of only control plane node</small>
          </div>

          <div class="form-group">
            <label>Notes</label>
            <textarea
              v-model="deviceForm.notes"
              rows="3"
              placeholder="Additional notes about this device..."
            ></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeModal" class="cancel-btn">
              Cancel
            </button>
            <button type="submit" class="save-btn">
              {{ editingDevice ? 'Update' : 'Add' }} Device
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Approval Modal -->
    <div v-if="showApprovalModal && approvalSuggestions" class="modal-overlay" @click="closeApprovalModal">
      <div class="modal" @click.stop>
        <h3>Approve Device</h3>

        <div v-if="approvalSuggestions.is_first_device" class="warning-box" style="margin-bottom: 1.5rem;">
          <strong>⚠️ First Device</strong>
          <p>This is the first device in your cluster. It must be a control plane node and use the cluster endpoint IP.</p>
        </div>

        <div class="device-info">
          <strong>MAC Address:</strong> {{ approvingDevice.mac_address }}
        </div>

        <form @submit.prevent="confirmApproval">
          <div class="form-group">
            <label>Hostname *</label>
            <input
              v-model="approvalForm.hostname"
              type="text"
              required
              placeholder="controlplane-01"
            />
          </div>

          <div class="form-group">
            <label>IP Address *</label>
            <input
              v-model="approvalForm.ip_address"
              type="text"
              required
              placeholder="10.0.5.100"
              :disabled="approvalSuggestions.locked_fields.ip_address"
            />
            <small class="info-text">{{ approvalSuggestions.reasons.ip_address }}</small>
          </div>

          <div class="form-group">
            <label>Role *</label>
            <select
              v-model="approvalForm.role"
              :disabled="approvalSuggestions.locked_fields.role"
            >
              <option value="worker">Worker</option>
              <option value="controlplane">Control Plane</option>
            </select>
            <small class="info-text">{{ approvalSuggestions.reasons.role }}</small>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeApprovalModal" class="cancel-btn">
              Cancel
            </button>
            <button type="submit" class="save-btn">
              Approve Device
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="message" :class="['message', messageType]">
      {{ message }}
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'

export default {
  name: 'DeviceManagement',
  data() {
    return {
      devices: [],
      loading: true,
      statusFilter: '',
      searchQuery: '',
      sortColumn: 'first_seen',
      sortDirection: 'desc',
      showAddModal: false,
      showApprovalModal: false,
      editingDevice: null,
      approvingDevice: null,
      approvalSuggestions: null,
      deviceForm: {
        mac_address: '',
        hostname: '',
        ip_address: '',
        role: 'worker',
        notes: ''
      },
      approvalForm: {
        hostname: '',
        ip_address: '',
        role: 'worker'
      },
      message: null,
      messageType: 'success',
      unsubscribeWs: null,
      deviceMap: new Map(), // Track devices by MAC address for change detection
      bootstrapping: false,
      isEditingOnlyControlPlane: false
    }
  },
  computed: {
    hasApprovedControlPlane() {
      return this.devices.some(
        device => device.status === 'approved' && device.role === 'controlplane'
      )
    },
    filteredAndSortedDevices() {
      let result = [...this.devices]

      // Apply search filter
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase()
        result = result.filter(device => {
          return (
            device.mac_address?.toLowerCase().includes(query) ||
            device.hostname?.toLowerCase().includes(query) ||
            device.ip_address?.toLowerCase().includes(query)
          )
        })
      }

      // Apply sorting
      if (this.sortColumn) {
        result.sort((a, b) => {
          let aVal = a[this.sortColumn]
          let bVal = b[this.sortColumn]

          // Handle null/undefined values
          if (aVal === null || aVal === undefined) aVal = ''
          if (bVal === null || bVal === undefined) bVal = ''

          // Convert to lowercase for string comparison
          if (typeof aVal === 'string') aVal = aVal.toLowerCase()
          if (typeof bVal === 'string') bVal = bVal.toLowerCase()

          // Compare
          if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1
          if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1
          return 0
        })
      }

      return result
    }
  },
  async mounted() {
    this.toast = useToast()
    await this.loadDevices()
    this.subscribeToWebSocket()
  },
  beforeUnmount() {
    if (this.unsubscribeWs) {
      this.unsubscribeWs()
    }
  },
  methods: {
    async loadDevices(background = false) {
      // Only show loading spinner on initial load or manual refresh
      if (!background) {
        this.loading = true
      }
      try {
        const newDevices = await apiService.getDevices(this.statusFilter || null)

        // Detect changes and show toast notifications
        if (background) {
          this.detectDeviceChanges(newDevices)
        }

        this.devices = newDevices
        // Update device map for future change detection
        this.updateDeviceMap()
      } catch (error) {
        if (!background) {
          this.showMessage('Failed to load devices', 'error')
        }
      } finally {
        if (!background) {
          this.loading = false
        }
      }
    },
    subscribeToWebSocket() {
      // Subscribe to WebSocket events
      this.unsubscribeWs = websocketService.subscribe((event) => {
        // Reload devices when any device event occurs
        const deviceEvents = [
          'device_discovered',
          'config_downloaded',
          'device_approved',
          'device_rejected',
          'device_deleted'
        ]
        if (deviceEvents.includes(event.type)) {
          this.loadDevices(true) // Background refresh
        }
      })
    },
    updateDeviceMap() {
      this.deviceMap.clear()
      this.devices.forEach(device => {
        this.deviceMap.set(device.mac_address, {
          status: device.status,
          last_config_download: device.last_config_download
        })
      })
    },
    detectDeviceChanges(newDevices) {
      newDevices.forEach(newDevice => {
        const oldDevice = this.deviceMap.get(newDevice.mac_address)

        if (!oldDevice) {
          // New device discovered
          const deviceName = newDevice.hostname || newDevice.mac_address
          this.toast.info(
            `Device ${deviceName} is attempting to boot via PXE and is awaiting approval to download its Talos configuration`,
            {
              timeout: 10000,
              icon: '🔍'
            }
          )
        } else if (newDevice.last_config_download && newDevice.last_config_download !== oldDevice.last_config_download) {
          // Config downloaded
          const deviceName = newDevice.hostname || newDevice.mac_address
          const roleText = newDevice.role ? ` (${newDevice.role})` : ''
          this.toast.success(
            `${deviceName}${roleText} downloaded configuration and is booting Talos`,
            {
              timeout: 8000,
              icon: '⬇️'
            }
          )
        }
      })
    },
    sortBy(column) {
      if (this.sortColumn === column) {
        // Toggle direction if clicking same column
        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc'
      } else {
        // New column, default to ascending
        this.sortColumn = column
        this.sortDirection = 'asc'
      }
    },
    async openApprovalModal(deviceId) {
      try {
        // Get approval suggestions from backend
        this.approvalSuggestions = await apiService.getApprovalSuggestions(deviceId)
        this.approvingDevice = this.devices.find(d => d.id === deviceId)

        // Pre-fill form with suggestions
        this.approvalForm = {
          hostname: this.approvalSuggestions.suggestions.hostname,
          ip_address: this.approvalSuggestions.suggestions.ip_address,
          role: this.approvalSuggestions.suggestions.role
        }

        this.showApprovalModal = true
      } catch (error) {
        this.showMessage(error.response?.data?.detail || 'Failed to load approval suggestions', 'error')
      }
    },
    async confirmApproval() {
      try {
        await apiService.approveDevice(this.approvingDevice.id, this.approvalForm)
        this.showMessage('Device approved successfully', 'success')
        this.closeApprovalModal()
        await this.loadDevices()
      } catch (error) {
        this.showMessage(error.response?.data?.detail || 'Failed to approve device', 'error')
      }
    },
    closeApprovalModal() {
      this.showApprovalModal = false
      this.approvingDevice = null
      this.approvalSuggestions = null
      this.approvalForm = {
        hostname: '',
        ip_address: '',
        role: 'worker'
      }
    },
    async rejectDevice(deviceId) {
      try {
        await apiService.rejectDevice(deviceId)
        this.showMessage('Device rejected', 'success')
        await this.loadDevices()
      } catch (error) {
        this.showMessage('Failed to reject device', 'error')
      }
    },
    async deleteDevice(deviceId) {
      if (!confirm('Are you sure you want to delete this device?')) {
        return
      }

      try {
        await apiService.deleteDevice(deviceId)
        this.showMessage('Device deleted successfully', 'success')
        await this.loadDevices()
      } catch (error) {
        this.showMessage('Failed to delete device', 'error')
      }
    },
    editDevice(device) {
      this.editingDevice = device

      // Check if this is the only approved control plane node
      const approvedControlPlanes = this.devices.filter(
        d => d.status === 'approved' && d.role === 'controlplane'
      )
      this.isEditingOnlyControlPlane =
        device.status === 'approved' &&
        device.role === 'controlplane' &&
        approvedControlPlanes.length === 1

      this.deviceForm = {
        mac_address: device.mac_address,
        hostname: device.hostname || '',
        ip_address: device.ip_address || '',
        role: device.role,
        notes: device.notes || ''
      }
    },
    async saveDevice() {
      try {
        if (this.editingDevice) {
          await apiService.updateDevice(this.editingDevice.id, this.deviceForm)
          this.showMessage('Device updated successfully', 'success')
        } else {
          await apiService.createDevice(this.deviceForm)
          this.showMessage('Device added successfully', 'success')
        }
        this.closeModal()
        await this.loadDevices()
      } catch (error) {
        this.showMessage(error.response?.data?.detail || 'Failed to save device', 'error')
      }
    },
    closeModal() {
      this.showAddModal = false
      this.editingDevice = null
      this.isEditingOnlyControlPlane = false
      this.deviceForm = {
        mac_address: '',
        hostname: '',
        ip_address: '',
        role: 'worker',
        notes: ''
      }
    },
    async bootstrapCluster() {
      if (!confirm('Bootstrap the Talos cluster? This should only be done once on the first control plane node.')) {
        return
      }

      this.bootstrapping = true
      try {
        const response = await apiService.bootstrapCluster()
        this.toast.success(response.message, {
          timeout: 8000,
          icon: '🚀'
        })
        this.showMessage('Cluster bootstrapped successfully! You can now download the kubeconfig.', 'success')
      } catch (error) {
        const errorMessage = error.response?.data?.detail || 'Failed to bootstrap cluster'
        this.toast.error(errorMessage, {
          timeout: 10000,
          icon: '❌'
        })
        this.showMessage(errorMessage, 'error')
      } finally {
        this.bootstrapping = false
      }
    },
    formatDate(dateString) {
      return new Date(dateString).toLocaleString()
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
.device-management {
  max-width: 1400px;
  margin: 0 auto;
}

h2 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 0;
}

.info-banner {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 2rem;
  margin-bottom: 2rem;
  font-size: 0.9rem;
  line-height: 1.6;
}

.info-banner strong {
  display: block;
  color: #1565c0;
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.info-banner p {
  margin: 0;
  margin-top: 0.5rem;
  color: #424242;
}

.info-banner .link {
  color: #1976d2;
  text-decoration: underline;
  font-weight: 500;
}

.info-banner .link:hover {
  color: #1565c0;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.search-filter-group {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.search-box {
  flex: 1;
  max-width: 400px;
}

.search-input {
  width: 100%;
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #5a67d8;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-group label {
  font-weight: 500;
  color: #2c3e50;
  white-space: nowrap;
}

.filter-group select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
}

.add-btn {
  background: #5a67d8;
  color: white;
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s;
  white-space: nowrap;
}

.add-btn:hover {
  background: #4c51bf;
}

.bootstrap-btn {
  background: #f59e0b;
  color: white;
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: background 0.3s;
  white-space: nowrap;
}

.bootstrap-btn:hover:not(:disabled) {
  background: #d97706;
}

.bootstrap-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.loading,
.no-devices {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.no-devices .info-text {
  color: #666;
  margin-top: 1rem;
  font-size: 0.9rem;
}

.devices-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8f9fa;
}

th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2c3e50;
  border-bottom: 2px solid #e9ecef;
}

th.sortable {
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

th.sortable:hover {
  background: #e9ecef;
}

.sort-indicator {
  margin-left: 0.5rem;
  font-size: 0.7rem;
  color: #5a67d8;
}

td {
  padding: 1rem;
  border-bottom: 1px solid #e9ecef;
}

tr:hover {
  background: #f8f9fa;
}

.mono {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.role-badge,
.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  text-transform: capitalize;
}

.role-controlplane {
  background: #667eea;
  color: white;
}

.role-worker {
  background: #48bb78;
  color: white;
}

.status-pending {
  background: #fef3c7;
  color: #92400e;
}

.status-approved {
  background: #d1fae5;
  color: #065f46;
}

.status-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.actions button {
  padding: 0.25rem 0.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.approve-btn {
  background: #d1fae5;
  color: #065f46;
}

.approve-btn:hover {
  background: #a7f3d0;
}

.reject-btn {
  background: #fee2e2;
  color: #991b1b;
}

.reject-btn:hover {
  background: #fecaca;
}

.edit-btn {
  background: #dbeafe;
  color: #1e40af;
}

.edit-btn:hover {
  background: #bfdbfe;
}

.delete-btn {
  background: #f3f4f6;
  color: #6b7280;
}

.delete-btn:hover {
  background: #e5e7eb;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #2c3e50;
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

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.85rem;
}

.form-group .info-text {
  color: #2563eb;
  font-style: italic;
}

.form-group .warning-text {
  color: #dc2626;
  font-weight: 500;
}

.device-info {
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
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

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  justify-content: flex-end;
}

.cancel-btn {
  background: #f3f4f6;
  color: #374151;
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.cancel-btn:hover {
  background: #e5e7eb;
}

.save-btn {
  background: #42b983;
  color: white;
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.save-btn:hover {
  background: #35a372;
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

.text-muted {
  color: #9ca3af;
  font-style: italic;
}
</style>
