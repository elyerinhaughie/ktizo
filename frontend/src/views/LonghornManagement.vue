<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Longhorn Storage Management</h2>
        <p class="text-gray-500 mt-1 mb-0">Manage Longhorn storage disks across your cluster nodes</p>
      </div>
      <button @click="loadNodes" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed" :disabled="loading">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" :class="{ 'animate-spin': loading }" /> Refresh
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading && !nodes.length" class="bg-white p-12 rounded-lg shadow-md text-center text-gray-500">
      <div class="inline-block w-8 h-8 border-4 border-gray-200 border-t-[#42b983] rounded-full animate-spin mb-4"></div>
      <p class="m-0">Loading Longhorn nodes...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 rounded-md p-6 mb-8">
      <strong class="block text-red-800 mb-2"><font-awesome-icon :icon="['fas', 'circle-xmark']" /> Failed to load Longhorn nodes</strong>
      <p class="m-0 text-red-700 text-sm">{{ error }}</p>
      <button @click="loadNodes" class="mt-3 bg-red-600 text-white py-1.5 px-4 border-none rounded text-sm cursor-pointer hover:bg-red-700">Retry</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && !nodes.length" class="bg-white p-12 rounded-lg shadow-md text-center">
      <font-awesome-icon :icon="['fas', 'database']" class="text-5xl text-gray-300 mb-4" />
      <h3 class="text-lg font-semibold text-gray-700 mb-2">No Longhorn Nodes Found</h3>
      <p class="text-gray-500 text-sm m-0">Longhorn may not be installed, or no nodes have registered yet. Install Longhorn from the <router-link to="/modules" class="text-blue-600 hover:underline">Modules</router-link> page.</p>
    </div>

    <template v-else>
      <!-- Overview Gauges -->
      <div class="bg-white p-6 rounded-lg shadow-md mb-6">
        <div class="grid grid-cols-3 gap-8">
          <!-- Storage Usage Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[140px] h-[140px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="usageColor" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="usageDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ usagePercent }}%</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">used</span>
              </div>
            </div>
            <div class="mt-3 text-center">
              <div class="text-sm font-semibold text-gray-700">Storage</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ formatBytes(totalUsed) }} / {{ formatBytes(totalCapacity) }}</div>
            </div>
          </div>

          <!-- Resiliency Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[140px] h-[140px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="resiliencyColor" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="resiliencyDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ schedulingNodes }}</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">of {{ nodes.length }}</span>
              </div>
            </div>
            <div class="mt-3 text-center">
              <div class="text-sm font-semibold text-gray-700">Nodes Online</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ schedulingNodes }} scheduling, {{ nodes.length - schedulingNodes }} offline</div>
            </div>
          </div>

          <!-- Drives Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[140px] h-[140px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  stroke="#6366f1" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="drivesDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ schedulingDisks }}</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">of {{ totalDisks }}</span>
              </div>
            </div>
            <div class="mt-3 text-center">
              <div class="text-sm font-semibold text-gray-700">Drives</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ schedulingDisks }} active across {{ nodes.length }} nodes</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Node Cards -->
      <div v-for="node in nodes" :key="node.name" class="bg-white rounded-lg shadow-md mb-6 overflow-hidden">
        <!-- Node Header -->
        <div class="flex items-center justify-between p-5 border-b border-gray-100 bg-gray-50">
          <div class="flex items-center gap-3">
            <font-awesome-icon :icon="['fas', 'desktop']" class="text-lg text-gray-500" />
            <div>
              <h3 class="text-base font-semibold text-gray-900 m-0">{{ node.name }}</h3>
              <span class="text-xs text-gray-400 mt-0.5">{{ node.disks.length }} disk{{ node.disks.length !== 1 ? 's' : '' }} &middot; {{ formatBytes(nodeCapacity(node)) }} total</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="toggleAutoConfig(node)"
              class="py-1.5 px-3 rounded text-xs font-medium border cursor-pointer transition-colors duration-200"
              :class="autoConfig[node.name] ? 'bg-[#42b983]/10 text-[#42b983] border-[#42b983]/30 hover:bg-[#42b983]/20' : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'"
              :title="autoConfig[node.name] ? 'Auto-add disks after provisioning (enabled)' : 'Auto-add disks after provisioning (disabled)'"
            >
              <font-awesome-icon :icon="['fas', autoConfig[node.name] ? 'check' : 'bolt']" />
              Auto
            </button>
            <button
              @click="openAddDiskModal(node)"
              class="bg-blue-500 text-white py-1.5 px-3 border-none rounded text-xs font-medium cursor-pointer hover:bg-blue-600 transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
              :disabled="nodeDiscovering[node.name]"
            >
              <font-awesome-icon :icon="['fas', 'plus']" /> Add Disk
            </button>
            <button
              @click="useAllDisks(node)"
              class="bg-[#42b983] text-white py-1.5 px-3 border-none rounded text-xs font-medium cursor-pointer hover:bg-[#35a372] transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
              :disabled="nodeOperating[node.name]"
            >
              <font-awesome-icon :icon="['fas', nodeOperating[node.name] ? 'arrows-rotate' : 'hard-drive']" :class="{ 'animate-spin': nodeOperating[node.name] }" />
              {{ nodeOperating[node.name] ? 'Adding...' : 'Use All Disks' }}
            </button>
          </div>
        </div>

        <!-- Disk Table -->
        <div v-if="node.disks.length" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-400 uppercase tracking-wider">
                <th class="py-3 px-5 font-medium">Path</th>
                <th class="py-3 px-5 font-medium w-[300px]">Usage</th>
                <th class="py-3 px-5 font-medium text-center">Scheduling</th>
                <th class="py-3 px-5 font-medium text-right">Replicas</th>
                <th class="py-3 px-5 font-medium text-right w-[80px]"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="disk in node.disks" :key="disk.name" class="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                <td class="py-3 px-5">
                  <div class="font-mono text-sm text-gray-900">{{ disk.path }}</div>
                  <div class="text-xs text-gray-400 mt-0.5">{{ disk.name }}</div>
                </td>
                <td class="py-3 px-5">
                  <div class="flex items-center gap-3">
                    <div class="flex-1 h-2.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all duration-500"
                        :class="diskUsageClass(disk)"
                        :style="{ width: diskUsagePercent(disk) + '%' }"
                      ></div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap w-[140px] text-right">
                      {{ formatBytes(diskUsed(disk)) }} / {{ formatBytes(disk.storageMaximum) }}
                    </span>
                  </div>
                </td>
                <td class="py-3 px-5 text-center">
                  <span
                    class="inline-flex items-center gap-1 py-1 px-2.5 rounded-full text-xs font-medium"
                    :class="disk.allowScheduling ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                  >
                    <font-awesome-icon :icon="['fas', disk.allowScheduling ? 'check' : 'xmark']" />
                    {{ disk.allowScheduling ? 'On' : 'Off' }}
                  </span>
                </td>
                <td class="py-3 px-5 text-right font-mono text-gray-700">{{ disk.replicaCount ?? 0 }}</td>
                <td class="py-3 px-5 text-right">
                  <button
                    @click="confirmRemoveDisk(node, disk)"
                    class="text-gray-400 hover:text-red-500 bg-transparent border-none cursor-pointer p-1 transition-colors duration-200"
                    title="Remove disk"
                    :disabled="removingDisk[node.name + '/' + disk.name]"
                  >
                    <font-awesome-icon :icon="['fas', removingDisk[node.name + '/' + disk.name] ? 'arrows-rotate' : 'trash']" :class="{ 'animate-spin': removingDisk[node.name + '/' + disk.name] }" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- No disks -->
        <div v-else class="p-8 text-center text-gray-400 text-sm">
          No disks configured on this node. Click <strong>Add Disk</strong> or <strong>Use All Disks</strong> to get started.
        </div>
      </div>
    </template>

    <!-- Add Disk Modal -->
    <div v-if="showAddDiskModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" @click.self="showAddDiskModal = false">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-xl mx-4">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900 m-0">
            Add Disk to {{ addDiskNodeName }}
          </h3>
          <button @click="showAddDiskModal = false" class="text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer text-xl">
            <font-awesome-icon :icon="['fas', 'xmark']" />
          </button>
        </div>
        <div class="p-5">
          <!-- Discovering -->
          <div v-if="discovering" class="text-center py-8 text-gray-500">
            <div class="inline-block w-6 h-6 border-3 border-gray-200 border-t-[#42b983] rounded-full animate-spin mb-3"></div>
            <p class="m-0 text-sm">Discovering available disks via Talos...</p>
          </div>

          <!-- Discovery error -->
          <div v-else-if="discoverError" class="bg-red-50 border-l-4 border-red-500 rounded p-4">
            <strong class="text-red-800 text-sm">Discovery failed</strong>
            <p class="text-red-700 text-sm m-0 mt-1">{{ discoverError }}</p>
          </div>

          <!-- No available disks -->
          <div v-else-if="!availableDisks.length" class="text-center py-8 text-gray-500">
            <font-awesome-icon :icon="['fas', 'hard-drive']" class="text-3xl text-gray-300 mb-3" />
            <p class="m-0 text-sm font-medium text-gray-600">No available disks found</p>
            <p class="m-0 mt-1 text-xs text-gray-400">All disks on this node are either already in use or are the system disk.</p>
          </div>

          <!-- Available disks list -->
          <div v-else>
            <p class="text-sm text-gray-500 mt-0 mb-4">Select a disk to add to Longhorn on <strong>{{ addDiskNodeName }}</strong>:</p>
            <div class="space-y-2 max-h-[400px] overflow-y-auto">
              <div
                v-for="disk in availableDisks"
                :key="disk.dev_path"
                @click="selectedAvailableDisk = disk"
                class="flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all duration-200"
                :class="selectedAvailableDisk === disk ? 'border-[#42b983] bg-[#42b983]/5' : 'border-gray-200 hover:border-gray-300'"
              >
                <font-awesome-icon :icon="['fas', 'hard-drive']" class="text-xl text-gray-400" />
                <div class="flex-1 min-w-0">
                  <div class="font-mono text-sm font-medium text-gray-900">{{ disk.dev_path }}</div>
                  <div class="text-xs text-gray-500 mt-0.5">
                    {{ disk.model || 'Unknown model' }}
                    <span v-if="disk.transport" class="ml-2 bg-gray-100 px-1.5 py-0.5 rounded text-gray-400 uppercase">{{ disk.transport }}</span>
                    <span v-if="disk.rotational" class="ml-1 bg-gray-100 px-1.5 py-0.5 rounded text-gray-400">HDD</span>
                    <span v-else class="ml-1 bg-gray-100 px-1.5 py-0.5 rounded text-gray-400">SSD</span>
                  </div>
                </div>
                <div class="text-sm font-semibold text-gray-700 whitespace-nowrap">{{ formatBytes(disk.size) }}</div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="availableDisks.length" class="flex justify-end gap-3 p-5 border-t border-gray-200">
          <button @click="showAddDiskModal = false" class="py-2 px-4 bg-gray-100 text-gray-700 border-none rounded text-sm cursor-pointer hover:bg-gray-200">
            Cancel
          </button>
          <button
            @click="addSelectedDisk"
            class="py-2 px-4 bg-[#42b983] text-white border-none rounded text-sm font-medium cursor-pointer hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed"
            :disabled="!selectedAvailableDisk || addingDisk"
          >
            {{ addingDisk ? 'Adding...' : 'Add Disk' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Remove Disk Confirmation Modal -->
    <div v-if="showRemoveModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" @click.self="showRemoveModal = false">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4">
        <div class="p-5 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900 m-0">Remove Disk</h3>
        </div>
        <div class="p-5">
          <p class="text-sm text-gray-700 m-0">
            Are you sure you want to remove <strong class="font-mono">{{ removeDiskInfo.diskPath }}</strong> from <strong>{{ removeDiskInfo.nodeName }}</strong>?
          </p>
          <div v-if="removeDiskInfo.replicaCount > 0" class="mt-4 bg-amber-50 border-l-4 border-amber-500 rounded p-3">
            <strong class="text-amber-800 text-sm"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> This disk has {{ removeDiskInfo.replicaCount }} replica(s)</strong>
            <p class="text-amber-700 text-xs m-0 mt-1">Longhorn will evict replicas before removing the disk. This may take some time.</p>
          </div>
          <label v-if="removeDiskInfo.replicaCount > 0" class="flex! items-center gap-2 mt-4 cursor-pointer text-sm text-gray-600">
            <input type="checkbox" v-model="forceRemove" class="w-auto m-0 cursor-pointer" />
            Force remove (skip eviction)
          </label>
        </div>
        <div class="flex justify-end gap-3 p-5 border-t border-gray-200">
          <button @click="showRemoveModal = false" class="py-2 px-4 bg-gray-100 text-gray-700 border-none rounded text-sm cursor-pointer hover:bg-gray-200">
            Cancel
          </button>
          <button
            @click="doRemoveDisk"
            class="py-2 px-4 bg-red-500 text-white border-none rounded text-sm font-medium cursor-pointer hover:bg-red-600"
          >
            Remove Disk
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import { useToast } from 'vue-toastification'

export default {
  name: 'LonghornManagement',
  data() {
    return {
      loading: false,
      error: null,
      nodes: [],
      autoConfig: {},
      // Add Disk modal
      showAddDiskModal: false,
      addDiskNodeName: '',
      discovering: false,
      discoverError: null,
      availableDisks: [],
      selectedAvailableDisk: null,
      addingDisk: false,
      // Remove Disk modal
      showRemoveModal: false,
      removeDiskInfo: { nodeName: '', diskName: '', diskPath: '', replicaCount: 0 },
      forceRemove: false,
      // Per-node operation states
      nodeOperating: {},
      nodeDiscovering: {},
      removingDisk: {},
    }
  },
  computed: {
    totalDisks() {
      return this.nodes.reduce((sum, n) => sum + n.disks.length, 0)
    },
    totalCapacity() {
      return this.nodes.reduce((sum, n) => sum + this.nodeCapacity(n), 0)
    },
    totalAvailable() {
      return this.nodes.reduce((sum, n) =>
        sum + n.disks.reduce((s, d) => s + (d.storageAvailable || 0), 0), 0)
    },
    totalUsed() {
      return this.totalCapacity - this.totalAvailable
    },
    usagePercent() {
      if (!this.totalCapacity) return 0
      return Math.round((this.totalUsed / this.totalCapacity) * 100)
    },
    usageColor() {
      if (this.usagePercent >= 90) return '#ef4444'
      if (this.usagePercent >= 70) return '#f59e0b'
      return '#42b983'
    },
    usageDash() {
      const circ = 2 * Math.PI * 15.5
      const filled = (this.usagePercent / 100) * circ
      return `${filled} ${circ - filled}`
    },
    schedulingNodes() {
      return this.nodes.filter(n => n.disks.some(d => d.allowScheduling)).length
    },
    resiliencyColor() {
      const pct = this.nodes.length ? this.schedulingNodes / this.nodes.length : 0
      if (pct >= 0.8) return '#42b983'
      if (pct >= 0.5) return '#f59e0b'
      return '#ef4444'
    },
    resiliencyDash() {
      const circ = 2 * Math.PI * 15.5
      const pct = this.nodes.length ? this.schedulingNodes / this.nodes.length : 0
      const filled = pct * circ
      return `${filled} ${circ - filled}`
    },
    schedulingDisks() {
      return this.nodes.reduce((sum, n) => sum + n.disks.filter(d => d.allowScheduling).length, 0)
    },
    drivesDash() {
      const circ = 2 * Math.PI * 15.5
      const pct = this.totalDisks ? this.schedulingDisks / this.totalDisks : 0
      const filled = pct * circ
      return `${filled} ${circ - filled}`
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadNodes()
    await this.loadAutoConfig()
  },
  methods: {
    async loadNodes() {
      this.loading = true
      this.error = null
      try {
        this.nodes = await apiService.longhornNodes()
      } catch (e) {
        this.error = e.message || 'Failed to load Longhorn nodes'
      } finally {
        this.loading = false
      }
    },
    async loadAutoConfig() {
      try {
        const cfg = await apiService.longhornAutoConfig({})
        this.autoConfig = cfg || {}
      } catch (e) {
        // Non-critical, just log
        console.warn('Failed to load auto config:', e)
      }
    },
    nodeCapacity(node) {
      return node.disks.reduce((s, d) => s + (d.storageMaximum || 0), 0)
    },
    diskUsed(disk) {
      return (disk.storageMaximum || 0) - (disk.storageAvailable || 0)
    },
    diskUsagePercent(disk) {
      if (!disk.storageMaximum) return 0
      return Math.min(100, (this.diskUsed(disk) / disk.storageMaximum) * 100)
    },
    diskUsageClass(disk) {
      const pct = this.diskUsagePercent(disk)
      if (pct >= 90) return 'bg-red-500'
      if (pct >= 70) return 'bg-amber-500'
      return 'bg-[#42b983]'
    },
    formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B'
      const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
      const k = 1024
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      const val = bytes / Math.pow(k, i)
      return val.toFixed(val >= 100 ? 0 : val >= 10 ? 1 : 2) + ' ' + units[i]
    },
    async toggleAutoConfig(node) {
      const current = !!this.autoConfig[node.name]
      const newVal = !current
      try {
        await apiService.longhornAutoConfig({
          node_name: node.name,
          auto_add_disks: newVal
        })
        this.autoConfig = { ...this.autoConfig, [node.name]: newVal ? { auto_add_disks: true } : null }
        if (!newVal) {
          const copy = { ...this.autoConfig }
          delete copy[node.name]
          this.autoConfig = copy
        }
        this.toast.success(`Auto-add disks ${newVal ? 'enabled' : 'disabled'} for ${node.name}`)
      } catch (e) {
        this.toast.error(e.message || 'Failed to update auto config')
      }
    },
    async openAddDiskModal(node) {
      this.addDiskNodeName = node.name
      this.availableDisks = []
      this.selectedAvailableDisk = null
      this.discoverError = null
      this.discovering = true
      this.showAddDiskModal = true
      this.nodeDiscovering = { ...this.nodeDiscovering, [node.name]: true }
      try {
        this.availableDisks = await apiService.longhornDiscoverDisks(node.name)
      } catch (e) {
        this.discoverError = e.message || 'Failed to discover disks'
      } finally {
        this.discovering = false
        this.nodeDiscovering = { ...this.nodeDiscovering, [node.name]: false }
      }
    },
    async addSelectedDisk() {
      if (!this.selectedAvailableDisk) return
      this.addingDisk = true
      try {
        await apiService.longhornAddDisk({
          node_name: this.addDiskNodeName,
          disk_path: this.selectedAvailableDisk.dev_path,
          allow_scheduling: true,
        })
        this.toast.success(`Added ${this.selectedAvailableDisk.dev_path} to ${this.addDiskNodeName}`)
        this.showAddDiskModal = false
        await this.loadNodes()
      } catch (e) {
        this.toast.error(e.message || 'Failed to add disk')
      } finally {
        this.addingDisk = false
      }
    },
    async useAllDisks(node) {
      this.nodeOperating = { ...this.nodeOperating, [node.name]: true }
      try {
        const result = await apiService.longhornUseAllDisks(node.name)
        if (result.added > 0) {
          this.toast.success(`Added ${result.added} disk(s) to ${node.name}`)
        } else {
          this.toast.info(result.message || `No new disks to add on ${node.name}`)
        }
        await this.loadNodes()
      } catch (e) {
        this.toast.error(e.message || 'Failed to add disks')
      } finally {
        this.nodeOperating = { ...this.nodeOperating, [node.name]: false }
      }
    },
    confirmRemoveDisk(node, disk) {
      this.removeDiskInfo = {
        nodeName: node.name,
        diskName: disk.name,
        diskPath: disk.path,
        replicaCount: disk.replicaCount || 0,
      }
      this.forceRemove = false
      this.showRemoveModal = true
    },
    async doRemoveDisk() {
      const { nodeName, diskName } = this.removeDiskInfo
      const key = nodeName + '/' + diskName
      this.showRemoveModal = false
      this.removingDisk = { ...this.removingDisk, [key]: true }
      try {
        await apiService.longhornRemoveDisk({
          node_name: nodeName,
          disk_name: diskName,
          force: this.forceRemove,
        })
        this.toast.success(`Removed disk from ${nodeName}`)
        await this.loadNodes()
      } catch (e) {
        this.toast.error(e.message || 'Failed to remove disk')
      } finally {
        this.removingDisk = { ...this.removingDisk, [key]: false }
      }
    },
  }
}
</script>
