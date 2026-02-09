<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Audit Log</h2>
        <p class="text-gray-500 mt-1 mb-0">Track all actions performed across the system</p>
      </div>
    </div>

    <div class="flex justify-between items-center mb-6 mt-8 gap-4">
      <div class="flex items-center gap-4 flex-1">
        <div class="flex items-center gap-2">
          <label class="font-medium text-sidebar-dark whitespace-nowrap">Page:</label>
          <select v-model="pageFilter" @change="loadLogs()" class="p-2 border border-gray-300 rounded text-[0.9rem]">
            <option value="">All</option>
            <option value="Device Management">Device Management</option>
            <option value="Network Settings">Network Settings</option>
            <option value="Cluster Settings">Cluster Settings</option>
            <option value="Storage Settings">Storage Settings</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <label class="font-medium text-sidebar-dark whitespace-nowrap">Action:</label>
          <select v-model="actionFilter" @change="loadLogs()" class="p-2 border border-gray-300 rounded text-[0.9rem]">
            <option value="">All</option>
            <option value="approved_device">Approved Device</option>
            <option value="rejected_device">Rejected Device</option>
            <option value="deleted_device">Deleted Device</option>
            <option value="updated_device">Updated Device</option>
            <option value="updated_network_settings">Updated Network Settings</option>
            <option value="applied_network_settings">Applied Network Settings</option>
            <option value="updated_cluster_settings">Updated Cluster Settings</option>
            <option value="generated_cluster_config">Generated Cluster Config</option>
            <option value="generated_secrets">Generated Secrets</option>
            <option value="bootstrapped_cluster">Bootstrapped Cluster</option>
            <option value="downloaded_kubeconfig">Downloaded Kubeconfig</option>
            <option value="created_volume_config">Created Volume Config</option>
            <option value="updated_volume_config">Updated Volume Config</option>
            <option value="deleted_volume_config">Deleted Volume Config</option>
            <option value="created_rbac_user">Created RBAC User</option>
            <option value="created_service_account">Created Service Account</option>
            <option value="deleted_service_account">Deleted Service Account</option>
            <option value="created_role">Created Role</option>
            <option value="deleted_role">Deleted Role</option>
            <option value="created_cluster_role">Created Cluster Role</option>
            <option value="deleted_cluster_role">Deleted Cluster Role</option>
            <option value="created_role_binding">Created Role Binding</option>
            <option value="deleted_role_binding">Deleted Role Binding</option>
            <option value="created_cluster_role_binding">Created Cluster Role Binding</option>
            <option value="deleted_cluster_role_binding">Deleted Cluster Role Binding</option>
          </select>
        </div>
      </div>
      <button
        @click="confirmClear"
        class="bg-red-500 text-white py-2 px-4 border-none rounded cursor-pointer text-[0.9rem] transition-colors duration-300 whitespace-nowrap hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        :disabled="total === 0"
      >
        <font-awesome-icon :icon="['fas', 'trash']" class="mr-1" /> Clear All
      </button>
    </div>

    <div v-if="loading" class="text-center py-12 bg-white rounded-lg shadow-md">Loading audit logs...</div>

    <div v-else-if="logs.length === 0" class="text-center py-12 bg-white rounded-lg shadow-md">
      <p>No audit log entries found.</p>
      <p class="text-gray-500 mt-4 text-[0.9rem]">Actions performed in the system will be recorded here.</p>
    </div>

    <div v-else>
      <div class="bg-white rounded-lg shadow-md overflow-x-auto">
        <table class="w-full border-collapse">
          <thead class="bg-gray-50">
            <tr>
              <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">Timestamp</th>
              <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">Action</th>
              <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">Page</th>
              <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id" class="hover:bg-gray-50">
              <td class="p-4 border-b border-gray-200 whitespace-nowrap" :title="formatAbsolute(log.timestamp)">
                {{ formatRelative(log.timestamp) }}
              </td>
              <td class="p-4 border-b border-gray-200">
                <span class="px-3 py-1 rounded-xl text-sm font-medium" :class="actionBadgeClass(log.action)">
                  {{ formatAction(log.action) }}
                </span>
              </td>
              <td class="p-4 border-b border-gray-200">{{ log.page }}</td>
              <td class="p-4 border-b border-gray-200 text-[0.85rem] text-gray-600 max-w-[400px] truncate" :title="log.details">
                {{ formatDetails(log.details) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex justify-between items-center mt-4 text-[0.9rem] text-gray-600">
        <span>Showing {{ skip + 1 }}-{{ Math.min(skip + limit, total) }} of {{ total }}</span>
        <div class="flex gap-2">
          <button
            @click="prevPage"
            :disabled="skip === 0"
            class="px-4 py-2 border border-gray-300 rounded cursor-pointer text-[0.9rem] transition-colors duration-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            @click="nextPage"
            :disabled="skip + limit >= total"
            class="px-4 py-2 border border-gray-300 rounded cursor-pointer text-[0.9rem] transition-colors duration-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'

const ACTION_LABELS = {
  approved_device: 'Approved Device',
  rejected_device: 'Rejected Device',
  deleted_device: 'Deleted Device',
  updated_device: 'Updated Device',
  updated_network_settings: 'Updated Network Settings',
  applied_network_settings: 'Applied Network Settings',
  updated_cluster_settings: 'Updated Cluster Settings',
  generated_cluster_config: 'Generated Cluster Config',
  generated_secrets: 'Generated Secrets',
  bootstrapped_cluster: 'Bootstrapped Cluster',
  downloaded_kubeconfig: 'Downloaded Kubeconfig',
  created_volume_config: 'Created Volume Config',
  updated_volume_config: 'Updated Volume Config',
  deleted_volume_config: 'Deleted Volume Config',
  created_rbac_user: 'Created RBAC User',
  created_service_account: 'Created Service Account',
  deleted_service_account: 'Deleted Service Account',
  created_role: 'Created Role',
  deleted_role: 'Deleted Role',
  created_cluster_role: 'Created Cluster Role',
  deleted_cluster_role: 'Deleted Cluster Role',
  created_role_binding: 'Created Role Binding',
  deleted_role_binding: 'Deleted Role Binding',
  created_cluster_role_binding: 'Created Cluster Role Binding',
  deleted_cluster_role_binding: 'Deleted Cluster Role Binding',
}

export default {
  name: 'AuditLog',
  data() {
    return {
      logs: [],
      total: 0,
      loading: true,
      skip: 0,
      limit: 25,
      pageFilter: '',
      actionFilter: '',
      unsubscribeWs: null,
    }
  },
  async mounted() {
    this.toast = useToast()
    await this.loadLogs()
    this.subscribeToWebSocket()
  },
  beforeUnmount() {
    if (this.unsubscribeWs) {
      this.unsubscribeWs()
    }
  },
  methods: {
    async loadLogs() {
      this.loading = true
      try {
        const params = { skip: this.skip, limit: this.limit }
        if (this.pageFilter) params.page = this.pageFilter
        if (this.actionFilter) params.action = this.actionFilter
        const data = await apiService.getAuditLogs(params)
        this.logs = data.logs
        this.total = data.total
      } catch (error) {
        console.error('Failed to load audit logs:', error)
      } finally {
        this.loading = false
      }
    },
    subscribeToWebSocket() {
      this.unsubscribeWs = websocketService.subscribe((event) => {
        if (event.type === 'audit_log_created') {
          this.loadLogs()
        }
      })
    },
    prevPage() {
      if (this.skip > 0) {
        this.skip = Math.max(0, this.skip - this.limit)
        this.loadLogs()
      }
    },
    nextPage() {
      if (this.skip + this.limit < this.total) {
        this.skip += this.limit
        this.loadLogs()
      }
    },
    async confirmClear() {
      if (!confirm('Are you sure you want to clear all audit logs? This cannot be undone.')) {
        return
      }
      try {
        await apiService.clearAuditLogs()
        this.toast.success('Audit logs cleared')
        this.skip = 0
        await this.loadLogs()
      } catch (error) {
        this.toast.error('Failed to clear audit logs')
      }
    },
    formatAction(action) {
      return ACTION_LABELS[action] || action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    },
    actionBadgeClass(action) {
      if (action.includes('delete') || action.includes('reject')) return 'bg-red-100 text-red-800'
      if (action.includes('approve') || action.includes('bootstrap') || action.includes('create')) return 'bg-green-100 text-green-800'
      if (action.includes('update') || action.includes('applied')) return 'bg-blue-100 text-blue-800'
      if (action.includes('generate') || action.includes('download')) return 'bg-purple-100 text-purple-800'
      return 'bg-gray-100 text-gray-800'
    },
    formatRelative(timestamp) {
      const now = new Date()
      const date = new Date(timestamp)
      const diffMs = now - date
      const diffSec = Math.floor(diffMs / 1000)
      const diffMin = Math.floor(diffSec / 60)
      const diffHr = Math.floor(diffMin / 60)
      const diffDay = Math.floor(diffHr / 24)

      if (diffSec < 60) return 'just now'
      if (diffMin < 60) return `${diffMin}m ago`
      if (diffHr < 24) return `${diffHr}h ago`
      if (diffDay < 7) return `${diffDay}d ago`
      return date.toLocaleDateString()
    },
    formatAbsolute(timestamp) {
      return new Date(timestamp).toLocaleString()
    },
    formatDetails(details) {
      if (!details) return '-'
      try {
        const parsed = JSON.parse(details)
        return Object.entries(parsed)
          .map(([k, v]) => {
            if (typeof v === 'object' && v !== null) return `${k}: ${JSON.stringify(v)}`
            return `${k}: ${v}`
          })
          .join(', ')
      } catch {
        return details
      }
    },
  },
}
</script>
