<template>
  <div class="max-w-[1400px] mx-auto">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-32">
      <p class="text-lg text-gray-500">Loading dashboard...</p>
    </div>

    <template v-else>
      <!-- A. Header Row -->
      <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900 m-0">Dashboard</h2>
          <p class="text-gray-500 mt-1 mb-0">Cluster overview and real-time status</p>
        </div>
        <div class="flex items-center gap-2 text-sm">
          <span class="w-2.5 h-2.5 rounded-full inline-block" :class="apiStatus ? 'bg-green-500' : 'bg-red-500'"></span>
          <span class="text-gray-600" v-if="apiStatus">API v{{ apiStatus.version }}</span>
          <span class="text-gray-600" v-else>API Offline</span>
        </div>
      </div>

      <!-- Setup Banner -->
      <div v-if="!cluster && !network" class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-center gap-3">
        <font-awesome-icon :icon="['fas', 'triangle-exclamation']" class="text-amber-500 text-lg" />
        <p class="text-amber-800 m-0">
          Get started by configuring your network and cluster settings.
          <router-link to="/network" class="text-amber-900 font-semibold underline ml-1">Configure now</router-link>
        </p>
      </div>

      <!-- B. Cluster Overview Card -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-lg font-semibold text-sidebar-dark mb-4">Cluster Overview</h2>
        <div v-if="!cluster" class="text-gray-500">
          Cluster not configured yet.
          <router-link to="/cluster" class="text-primary font-medium ml-1">Configure cluster settings</router-link>
        </div>
        <div v-else>
          <div class="grid grid-cols-4 gap-4 mb-4 max-lg:grid-cols-2">
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Cluster Name</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.cluster_name || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Kubernetes Version</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.kubernetes_version || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Talos Version</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.talos_version || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">CNI</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.cni || 'N/A' }}</p>
            </div>
          </div>
          <div class="grid grid-cols-4 gap-4 max-lg:grid-cols-2">
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Cluster Endpoint</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.cluster_endpoint || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Pod Subnet</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.pod_subnet || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">Service Subnet</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.service_subnet || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-1">External Subnet</p>
              <p class="text-sm font-bold text-sidebar-dark">{{ cluster.external_subnet || 'N/A' }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- C. Gauges -->
      <div class="grid grid-cols-3 gap-4 mb-6 max-lg:grid-cols-2">
        <!-- Online -->
        <div class="bg-white rounded-lg shadow-md p-5 flex flex-col items-center">
          <svg viewBox="0 0 120 120" class="w-24 h-24">
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" class="stroke-gray-200" />
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round"
              class="transition-all duration-700"
              :stroke="onlinePercent >= 75 ? '#22c55e' : onlinePercent >= 40 ? '#f59e0b' : '#ef4444'"
              :stroke-dasharray="314"
              :stroke-dashoffset="314 - (314 * onlinePercent / 100)"
              transform="rotate(-90 60 60)" />
            <text x="60" y="56" text-anchor="middle" class="text-xl font-bold fill-sidebar-dark" style="font-size:22px">{{ onlinePercent }}%</text>
            <text x="60" y="72" text-anchor="middle" class="fill-gray-400" style="font-size:11px">{{ talosOnline }}/{{ healthCheckedCount }}</text>
          </svg>
          <p class="text-sm font-semibold text-sidebar-dark mt-2">Nodes Online</p>
          <p class="text-xs text-gray-400">{{ pingOnline }} reachable, {{ talosOnline }} Talos API up</p>
        </div>

        <!-- Fleet Readiness -->
        <div class="bg-white rounded-lg shadow-md p-5 flex flex-col items-center">
          <svg viewBox="0 0 120 120" class="w-24 h-24">
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" class="stroke-gray-200" />
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round"
              class="transition-all duration-700"
              stroke="#22c55e"
              :stroke-dasharray="314"
              :stroke-dashoffset="314 - (314 * approvalPercent / 100)"
              transform="rotate(-90 60 60)" />
            <text x="60" y="56" text-anchor="middle" class="text-xl font-bold fill-sidebar-dark" style="font-size:22px">{{ approvalPercent }}%</text>
            <text x="60" y="72" text-anchor="middle" class="fill-gray-400" style="font-size:11px">{{ approvedDevices.length }}/{{ devices.length }}</text>
          </svg>
          <p class="text-sm font-semibold text-sidebar-dark mt-2">Fleet Readiness</p>
          <p class="text-xs text-gray-400">{{ approvedDevices.length }} ready, {{ pendingDevices.length }} awaiting approval</p>
        </div>

        <!-- Role Distribution -->
        <div class="bg-white rounded-lg shadow-md p-5 flex flex-col items-center">
          <svg viewBox="0 0 120 120" class="w-24 h-24">
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" class="stroke-gray-200" />
            <!-- Workers arc -->
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round"
              class="transition-all duration-700"
              stroke="#14b8a6"
              :stroke-dasharray="314"
              :stroke-dashoffset="314 - (314 * workerPercent / 100)"
              transform="rotate(-90 60 60)" />
            <!-- Control planes arc (overlaid from 0) -->
            <circle cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round"
              class="transition-all duration-700"
              stroke="#6366f1"
              :stroke-dasharray="314"
              :stroke-dashoffset="314 - (314 * cpPercent / 100)"
              transform="rotate(-90 60 60)" />
            <text x="60" y="56" text-anchor="middle" class="text-xl font-bold fill-sidebar-dark" style="font-size:22px">{{ approvedDevices.length }}</text>
            <text x="60" y="72" text-anchor="middle" class="fill-gray-400" style="font-size:11px">nodes</text>
          </svg>
          <p class="text-sm font-semibold text-sidebar-dark mt-2">Roles</p>
          <p class="text-xs text-gray-400">
            <span class="inline-block w-2 h-2 rounded-full bg-indigo-500 mr-1"></span>{{ controlPlanes.length }} CP
            <span class="inline-block w-2 h-2 rounded-full bg-teal-500 ml-2 mr-1"></span>{{ workers.length }} Worker
          </p>
        </div>
      </div>

      <!-- D. Two-Column Layout -->
      <div class="grid grid-cols-5 gap-6 mb-6 max-lg:grid-cols-1">
        <!-- Devices Table -->
        <div class="col-span-3 bg-white rounded-lg shadow-md p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-sidebar-dark">Devices</h2>
            <router-link to="/devices" class="text-sm text-primary hover:text-primary-hover font-medium">View all</router-link>
          </div>
          <div v-if="devices.length === 0" class="text-gray-400 text-sm py-8 text-center">
            No devices discovered yet
          </div>
          <table v-else class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-400 uppercase tracking-wide border-b">
                <th class="pb-2 pr-4">Status</th>
                <th class="pb-2 pr-4">Name</th>
                <th class="pb-2 pr-4">IP</th>
                <th class="pb-2 pr-4">Role</th>
                <th class="pb-2">Health</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="device in devices.slice(0, 6)" :key="device.id" class="border-b border-gray-100 last:border-0">
                <td class="py-2.5 pr-4">
                  <span class="w-2.5 h-2.5 rounded-full inline-block" :class="statusDotClass(device.status)"></span>
                </td>
                <td class="py-2.5 pr-4 text-sidebar-dark font-medium">{{ device.hostname || device.mac_address }}</td>
                <td class="py-2.5 pr-4 text-gray-500">{{ device.ip_address || '-' }}</td>
                <td class="py-2.5 pr-4 text-gray-500 capitalize">{{ device.role || '-' }}</td>
                <td class="py-2.5">
                  <div v-if="health[device.mac_address]" class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full" :class="health[device.mac_address].ping ? 'bg-green-500' : 'bg-red-500'" :data-tooltip="health[device.mac_address].ping ? 'Ping OK' : 'Ping failed'"></span>
                    <span class="w-2 h-2 rounded-full" :class="health[device.mac_address].talos_api ? 'bg-green-500' : 'bg-red-500'" :data-tooltip="health[device.mac_address].talos_api ? 'Talos API OK' : 'Talos API down'"></span>
                  </div>
                  <span v-else class="text-xs text-gray-400">-</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="devices.length > 6" class="text-xs text-gray-400 mt-3">
            and {{ devices.length - 6 }} more...
          </p>
        </div>

        <!-- Recent Activity -->
        <div class="col-span-2 bg-white rounded-lg shadow-md p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-sidebar-dark">Recent Activity</h2>
            <router-link to="/audit" class="text-sm text-primary hover:text-primary-hover font-medium">View all</router-link>
          </div>
          <div v-if="auditLogs.length === 0" class="text-gray-400 text-sm py-8 text-center">
            No activity recorded yet
          </div>
          <ul v-else class="list-none p-0 m-0">
            <li v-for="(log, index) in auditLogs.slice(0, 5)" :key="index" class="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
              <span class="w-2 h-2 rounded-full mt-1.5 shrink-0" :class="actionDotClass(log.action)"></span>
              <div class="min-w-0 flex-1">
                <p class="text-sm text-sidebar-dark m-0 truncate">{{ formatAction(log.action) }}</p>
                <p class="text-xs text-gray-400 m-0">{{ formatRelative(log.created_at) }}</p>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- E. Quick Actions -->
      <div class="grid grid-cols-4 gap-4 max-lg:grid-cols-2">
        <router-link to="/network" class="bg-white rounded-lg shadow-md p-5 text-center no-underline hover:shadow-lg transition-shadow">
          <font-awesome-icon :icon="['fas', 'globe']" class="text-2xl text-primary mb-2" />
          <h3 class="text-sm font-semibold text-sidebar-dark mb-1">Network Settings</h3>
          <p class="text-xs text-gray-400 m-0">Configure DHCP & PXE</p>
        </router-link>
        <router-link to="/cluster" class="bg-white rounded-lg shadow-md p-5 text-center no-underline hover:shadow-lg transition-shadow">
          <font-awesome-icon :icon="['fas', 'cog']" class="text-2xl text-primary mb-2" />
          <h3 class="text-sm font-semibold text-sidebar-dark mb-1">Cluster Settings</h3>
          <p class="text-xs text-gray-400 m-0">Manage cluster config</p>
        </router-link>
        <router-link to="/devices" class="bg-white rounded-lg shadow-md p-5 text-center no-underline hover:shadow-lg transition-shadow">
          <font-awesome-icon :icon="['fas', 'desktop']" class="text-2xl text-primary mb-2" />
          <h3 class="text-sm font-semibold text-sidebar-dark mb-1">Device Management</h3>
          <p class="text-xs text-gray-400 m-0">Approve & manage nodes</p>
        </router-link>
        <router-link to="/storage" class="bg-white rounded-lg shadow-md p-5 text-center no-underline hover:shadow-lg transition-shadow">
          <font-awesome-icon :icon="['fas', 'hard-drive']" class="text-2xl text-primary mb-2" />
          <h3 class="text-sm font-semibold text-sidebar-dark mb-1">Storage Settings</h3>
          <p class="text-xs text-gray-400 m-0">Configure volumes</p>
        </router-link>
      </div>
    </template>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'

export default {
  name: 'Home',
  data() {
    return {
      loading: true,
      apiStatus: null,
      cluster: null,
      network: null,
      devices: [],
      volumes: [],
      auditLogs: [],
      health: {},
      unsubscribeWs: null
    }
  },
  computed: {
    approvedDevices() {
      return this.devices.filter(d => d.status === 'approved')
    },
    pendingDevices() {
      return this.devices.filter(d => d.status === 'pending')
    },
    rejectedDevices() {
      return this.devices.filter(d => d.status === 'rejected')
    },
    controlPlanes() {
      return this.approvedDevices.filter(d => d.role === 'controlplane')
    },
    workers() {
      return this.approvedDevices.filter(d => d.role === 'worker')
    },
    healthCheckedCount() {
      return Object.keys(this.health).length
    },
    pingOnline() {
      return Object.values(this.health).filter(h => h.ping).length
    },
    talosOnline() {
      return Object.values(this.health).filter(h => h.talos_api).length
    },
    onlinePercent() {
      if (!this.healthCheckedCount) return 0
      return Math.round((this.talosOnline / this.healthCheckedCount) * 100)
    },
    approvalPercent() {
      if (!this.devices.length) return 0
      return Math.round((this.approvedDevices.length / this.devices.length) * 100)
    },
    cpPercent() {
      if (!this.approvedDevices.length) return 0
      return Math.round((this.controlPlanes.length / this.approvedDevices.length) * 100)
    },
    workerPercent() {
      if (!this.approvedDevices.length) return 0
      return Math.round(((this.controlPlanes.length + this.workers.length) / this.approvedDevices.length) * 100)
    }
  },
  async mounted() {
    this.toast = useToast()
    await this.loadAllData()

    // Fetch initial health status
    apiService.getDeviceHealth().then(h => { this.health = h || {} }).catch(() => {})

    this.unsubscribeWs = websocketService.subscribe((event) => {
      if (event.type === 'device_health') {
        this.health = event.data || {}
        return
      }
      const deviceEvents = [
        'device_discovered', 'device_approved', 'device_rejected',
        'device_deleted', 'device_updated', 'config_downloaded',
        'device_wipe_started', 'device_shutdown', 'device_reboot', 'device_wol'
      ]
      if (deviceEvents.includes(event.type)) {
        apiService.getDevices().then(d => { this.devices = d }).catch(() => {})
        this.showEventToast(event)
      }
      if (['network_updated', 'network_applied'].includes(event.type)) {
        apiService.getNetworkSettings().then(d => { this.network = d }).catch(() => {})
      }
      if (['cluster_updated', 'cluster_config_generated', 'cluster_bootstrapped'].includes(event.type)) {
        apiService.getClusterSettings().then(d => { this.cluster = d }).catch(() => {})
      }
      // Refresh audit log on any change
      apiService.getAuditLogs({ limit: 10 }).then(r => {
        this.auditLogs = r?.logs || r || []
      }).catch(() => {})
    })
  },
  beforeUnmount() {
    this.unsubscribeWs?.()
  },
  methods: {
    async loadAllData() {
      this.loading = true
      const results = await Promise.allSettled([
        apiService.getStatus(),
        apiService.getClusterSettings(),
        apiService.getNetworkSettings(),
        apiService.getDevices(),
        apiService.getVolumeConfigs(),
        apiService.getAuditLogs({ limit: 10 })
      ])

      if (results[0].status === 'fulfilled') this.apiStatus = results[0].value
      if (results[1].status === 'fulfilled') this.cluster = results[1].value
      if (results[2].status === 'fulfilled') this.network = results[2].value
      if (results[3].status === 'fulfilled') this.devices = results[3].value
      if (results[4].status === 'fulfilled') this.volumes = results[4].value
      if (results[5].status === 'fulfilled') {
        this.auditLogs = results[5].value?.logs || results[5].value || []
      }

      this.loading = false
    },
    formatRelative(dateStr) {
      if (!dateStr) return 'Never'
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now - date
      const diffSec = Math.floor(diffMs / 1000)
      if (diffSec < 60) return 'Just now'
      const diffMin = Math.floor(diffSec / 60)
      if (diffMin < 60) return `${diffMin}m ago`
      const diffHr = Math.floor(diffMin / 60)
      if (diffHr < 24) return `${diffHr}h ago`
      const diffDay = Math.floor(diffHr / 24)
      return `${diffDay}d ago`
    },
    formatAction(action) {
      return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    },
    actionDotClass(action) {
      if (action.includes('approved') || action.includes('created') || action.includes('generated') || action.includes('bootstrap')) return 'bg-green-500'
      if (action.includes('deleted') || action.includes('rejected') || action.includes('cleared')) return 'bg-red-500'
      if (action.includes('updated') || action.includes('applied')) return 'bg-blue-500'
      return 'bg-gray-400'
    },
    showEventToast(event) {
      const data = event.data || {}
      const name = data.hostname || data.mac_address || 'Device'
      switch (event.type) {
        case 'device_discovered':
          this.toast.info(`New device discovered: ${data.mac_address || 'unknown'}`, { timeout: 6000 })
          break
        case 'device_approved':
          this.toast.success(`${name} approved and added to fleet`, { timeout: 5000 })
          break
        case 'device_rejected':
          this.toast.warning(`${name} rejected and removed from queue`, { timeout: 5000 })
          break
        case 'device_deleted':
          this.toast.info(`${name} removed from inventory`, { timeout: 5000 })
          break
        case 'device_updated':
          break
        case 'config_downloaded':
          this.toast.success(`${name} downloaded config and is booting Talos`, { timeout: 5000 })
          break
        case 'device_wipe_started':
          this.toast.warning(`${name} wipe boot started`, { timeout: 8000 })
          break
        case 'device_shutdown':
          this.toast.warning(`${name} is shutting down`, { timeout: 6000 })
          break
        case 'device_reboot':
          this.toast.warning(`${name} is rebooting`, { timeout: 6000 })
          break
        case 'device_wol':
          this.toast.info(`Wake-on-LAN sent to ${name}`, { timeout: 6000 })
          break
      }
    },
    statusDotClass(status) {
      if (status === 'approved') return 'bg-green-500'
      if (status === 'pending') return 'bg-amber-500'
      if (status === 'rejected') return 'bg-red-500'
      return 'bg-gray-400'
    }
  }
}
</script>
