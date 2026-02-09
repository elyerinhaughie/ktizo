<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Device Management</h2>
        <p class="text-gray-500 mt-1 mb-0">Approve and manage devices for cluster deployment</p>
      </div>
    </div>

    <div class="bg-blue-50 border-l-4 border-blue-500 rounded-md p-4 mt-8 mb-8 text-[0.9rem] leading-relaxed">
      <strong class="block text-blue-800 mb-2 text-[0.95rem]"><font-awesome-icon :icon="['fas', 'circle-info']" /> How Device Discovery Works</strong>
      <p class="m-0 mt-2 text-gray-700">
        Devices appear here automatically when they boot via PXE and request a Talos configuration.
        Unapproved devices will retry periodically until approved.
        <router-link to="/wiki#device-config" class="text-blue-500 no-underline hover:underline">Learn more</router-link>
      </p>
      <p class="m-0 mt-2 text-gray-700">
        <strong class="text-blue-800">Strict Boot Mode:</strong> Control what happens to unapproved devices in
        <router-link to="/pxe" class="text-blue-500 no-underline hover:underline">PXE Settings</router-link>.
        <router-link to="/wiki#strict-mode" class="text-blue-500 no-underline hover:underline">Learn more</router-link>
      </p>
    </div>

    <!-- Rolling Refresh Active Banner -->
    <div v-if="rollingRefreshActive" class="bg-amber-50 border-l-4 border-amber-500 rounded-md p-4 mb-6 text-[0.9rem]">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="inline-block w-5 h-5 border-2 border-amber-500/30 border-t-amber-600 rounded-full refresh-spin"></span>
          <div>
            <strong class="text-amber-800 block">Worker Refresh in Progress</strong>
            <p class="m-0 mt-1 text-amber-700 text-sm">
              {{ refreshProgressSummary }}
              <span class="ml-1">&mdash;</span>
              <span class="ml-1 italic">{{ refreshStepLabel }}</span>
            </p>
          </div>
        </div>
        <button @click="showRefreshModal = true" class="text-amber-700 bg-amber-100 hover:bg-amber-200 border-none rounded px-3 py-1.5 text-sm font-medium cursor-pointer transition-colors">
          View Details
        </button>
      </div>
    </div>

    <div class="flex justify-between items-center mb-6 gap-4">
      <div class="flex items-center gap-4 flex-1">
        <div class="flex-1 max-w-[400px]">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by MAC, hostname, or IP..."
            class="w-full py-2 px-4 border border-gray-300 rounded text-[0.9rem] transition-colors duration-300 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div class="flex items-center gap-2">
          <label class="font-medium text-sidebar-dark whitespace-nowrap">Status:</label>
          <select v-model="statusFilter" @change="loadDevices" class="p-2 border border-gray-300 rounded text-[0.9rem]">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div class="flex gap-3">
        <button
          v-if="approvedWorkerCount > 0"
          @click="showRefreshConfirm = true"
          class="bg-amber-500 text-white py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] font-semibold transition-colors duration-300 whitespace-nowrap hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          :disabled="rollingRefreshActive"
        >
          <template v-if="rollingRefreshActive">
            <span class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full refresh-spin mr-1 align-middle"></span>
            Refreshing...
          </template>
          <template v-else><font-awesome-icon :icon="['fas', 'arrows-rotate']" class="mr-1" /> Refresh Workers</template>
        </button>
        <button
          v-if="hasApprovedControlPlane"
          @click="bootstrapCluster"
          class="bg-amber-500 text-white py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] font-semibold transition-colors duration-300 whitespace-nowrap hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          :disabled="bootstrapping"
        >
          <template v-if="bootstrapping">Bootstrapping...</template><template v-else><font-awesome-icon :icon="['fas', 'rocket']" class="mr-1" /> Bootstrap Cluster</template>
        </button>
        <button @click="showAddModal = true" class="bg-indigo-600 text-white py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] transition-colors duration-300 whitespace-nowrap hover:bg-indigo-700">
          + Add Device Manually
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12 bg-white rounded-lg shadow-md">Loading devices...</div>

    <div v-else-if="devices.length === 0" class="text-center py-12 bg-white rounded-lg shadow-md">
      <p>No devices found.</p>
      <p class="text-gray-500 mt-4 text-[0.9rem]">
        Devices will appear here automatically when they attempt to boot via PXE,
        or you can add them manually using the button above.
      </p>
    </div>

    <div v-else class="bg-white rounded-lg shadow-md overflow-x-auto">
      <table class="w-full border-collapse">
        <thead class="bg-gray-50">
          <tr>
            <th @click="sortBy('mac_address')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              MAC Address
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'mac_address'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th @click="sortBy('hostname')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              Hostname
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'hostname'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th @click="sortBy('ip_address')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              IP Address
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'ip_address'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th @click="sortBy('role')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              Role
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'role'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th @click="sortBy('status')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              Status
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'status'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">
              Health
            </th>
            <th @click="sortBy('first_seen')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              First Seen
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'first_seen'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th @click="sortBy('last_config_download')" class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200 cursor-pointer select-none transition-colors duration-200 hover:bg-gray-200">
              Last Config Download
              <span class="ml-2 text-[0.7rem] text-indigo-600" v-if="sortColumn === 'last_config_download'">
                <font-awesome-icon :icon="['fas', sortDirection === 'asc' ? 'sort-up' : 'sort-down']" />
              </span>
            </th>
            <th class="p-4 text-left font-semibold text-sidebar-dark border-b-2 border-gray-200">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="device in filteredAndSortedDevices" :key="device.id" class="hover:bg-gray-50">
            <td class="p-4 border-b border-gray-200 font-mono text-[0.9rem]">{{ device.mac_address }}</td>
            <td class="p-4 border-b border-gray-200">{{ device.hostname || '-' }}</td>
            <td class="p-4 border-b border-gray-200 font-mono text-[0.9rem]">{{ device.ip_address || '-' }}</td>
            <td class="p-4 border-b border-gray-200">
              <span v-if="device.status !== 'pending' && device.role" class="px-3 py-1 rounded-xl text-sm font-medium capitalize" :class="{
                'bg-indigo-500 text-white': device.role === 'controlplane',
                'bg-green-500 text-white': device.role === 'worker'
              }">
                {{ device.role }}
              </span>
              <span v-else class="text-gray-400 italic">-</span>
            </td>
            <td class="p-4 border-b border-gray-200">
              <span class="px-3 py-1 rounded-xl text-sm font-medium capitalize" :class="{
                'bg-amber-100 text-amber-800': device.status === 'pending',
                'bg-green-100 text-green-800': device.status === 'approved',
                'bg-red-100 text-red-800': device.status === 'rejected'
              }">
                {{ device.status }}
              </span>
            </td>
            <td class="p-4 border-b border-gray-200">
              <div v-if="health[device.mac_address]" class="flex items-center gap-2">
                <span class="inline-flex items-center gap-1" :data-tooltip="health[device.mac_address].ping ? 'Ping OK' : 'Ping failed'">
                  <span class="w-2.5 h-2.5 rounded-full" :class="health[device.mac_address].ping ? 'bg-green-500' : 'bg-red-500'"></span>
                  <span class="text-xs text-gray-500">Net</span>
                </span>
                <span class="inline-flex items-center gap-1" :data-tooltip="health[device.mac_address].talos_api ? 'Talos API responding' : 'Talos API not responding'">
                  <span class="w-2.5 h-2.5 rounded-full" :class="health[device.mac_address].talos_api ? 'bg-green-500' : 'bg-red-500'"></span>
                  <span class="text-xs text-gray-500">API</span>
                </span>
              </div>
              <span v-else class="text-gray-400 italic text-sm">-</span>
            </td>
            <td class="p-4 border-b border-gray-200">{{ formatDate(device.first_seen) }}</td>
            <td class="p-4 border-b border-gray-200">{{ device.last_config_download ? formatDate(device.last_config_download) : 'Never' }}</td>
            <td class="p-4 border-b border-gray-200 flex gap-2">
              <button
                v-if="device.status === 'pending'"
                @click="openApprovalModal(device.id)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-green-100 text-green-800 hover:bg-green-200"
                data-tooltip="Approve"
              >
                <font-awesome-icon :icon="['fas', 'check']" />
              </button>
              <button
                v-if="device.status === 'pending'"
                @click="rejectDevice(device.id)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-red-100 text-red-800 hover:bg-red-200"
                data-tooltip="Reject"
              >
                <font-awesome-icon :icon="['fas', 'xmark']" />
              </button>
              <button
                v-if="device.status === 'approved'"
                @click="toggleWipeFlag(device)"
                :class="[
                  'px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 inline-flex items-center gap-1',
                  device.wipe_on_next_boot
                    ? 'bg-red-600 text-white font-semibold text-[0.8rem] px-2.5 py-1 animate-wipe-pulse'
                    : 'bg-red-100 text-red-800 hover:bg-red-200'
                ]"
                :data-tooltip="device.wipe_on_next_boot ? 'Cancel scheduled wipe' : 'Wipe and reinstall on next boot'"
              >
                <font-awesome-icon :icon="['fas', 'hard-drive']" />
                <span v-if="device.wipe_on_next_boot" class="leading-none">WIPE</span>
              </button>
              <button
                v-if="device.status === 'approved' && isDeviceOnline(device)"
                @click="shutdownDevice(device)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-orange-100 text-orange-800 hover:bg-orange-200"
                data-tooltip="Shutdown"
              >
                <font-awesome-icon :icon="['fas', 'power-off']" />
              </button>
              <button
                v-if="device.status === 'approved' && !isDeviceOnline(device)"
                @click="wakeDevice(device)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-emerald-100 text-emerald-800 hover:bg-emerald-200"
                data-tooltip="Wake on LAN"
              >
                <font-awesome-icon :icon="['fas', 'bolt']" />
              </button>
              <button
                @click="editDevice(device)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-blue-100 text-blue-800 hover:bg-blue-200"
                data-tooltip="Edit"
              >
                <font-awesome-icon :icon="['fas', 'pen']" />
              </button>
              <button
                @click="deleteDevice(device.id)"
                class="px-2 py-1 border-none rounded cursor-pointer text-base transition-all duration-200 bg-gray-100 text-gray-500 hover:bg-gray-200"
                data-tooltip="Delete"
              >
                <font-awesome-icon :icon="['fas', 'trash']" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Device Modal -->
    <div v-if="showAddModal || editingDevice" class="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000]" @click="closeModal">
      <div class="bg-white p-8 rounded-lg max-w-[500px] w-[90%] max-h-[90vh] overflow-y-auto" @click.stop>
        <h3 class="mt-0 mb-6 text-sidebar-dark">{{ editingDevice ? 'Edit Device' : 'Add Device' }}</h3>

        <div v-if="isEditingOnlyControlPlane" class="bg-amber-50 border-l-4 border-amber-500 rounded p-4 text-[0.9rem] leading-normal" style="margin-bottom: 1.5rem;">
          <strong class="block text-amber-800 mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Only Control Plane Node</strong>
          <p class="text-amber-900 m-0">This is the only control plane node in your cluster. IP address and role cannot be changed. Add another control plane node first if you need to make changes.</p>
        </div>

        <form @submit.prevent="saveDevice">
          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">MAC Address *</label>
            <input
              v-model="deviceForm.mac_address"
              type="text"
              required
              placeholder="00:11:22:33:44:55"
              :disabled="!!editingDevice"
              class="w-full p-2 border border-gray-300 rounded text-base"
            />
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">Hostname</label>
            <input
              v-model="deviceForm.hostname"
              type="text"
              placeholder="node-01"
              class="w-full p-2 border border-gray-300 rounded text-base"
            />
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">IP Address</label>
            <input
              v-model="deviceForm.ip_address"
              type="text"
              placeholder="10.0.5.100"
              :disabled="isEditingOnlyControlPlane"
              class="w-full p-2 border border-gray-300 rounded text-base"
            />
            <small v-if="!isEditingOnlyControlPlane" class="block mt-1 text-gray-500 text-sm">Leave empty for DHCP assignment</small>
            <small v-else class="block mt-1 text-red-600 font-medium text-sm">Cannot change IP of only control plane node</small>
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">Role</label>
            <select v-model="deviceForm.role" :disabled="isEditingOnlyControlPlane" class="w-full p-2 border border-gray-300 rounded text-base">
              <option value="worker">Worker</option>
              <option value="controlplane">Control Plane</option>
            </select>
            <small v-if="isEditingOnlyControlPlane" class="block mt-1 text-red-600 font-medium text-sm">Cannot change role of only control plane node</small>
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">Notes</label>
            <textarea
              v-model="deviceForm.notes"
              rows="3"
              placeholder="Additional notes about this device..."
              class="w-full p-2 border border-gray-300 rounded text-base"
            ></textarea>
          </div>

          <div v-if="editingDevice && editingDevice.status === 'approved'" class="mb-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="deviceForm.wipe_on_next_boot"
                type="checkbox"
                class="w-auto cursor-pointer"
              />
              <span>Wipe on Next Boot</span>
            </label>
            <small class="block mt-1 text-blue-600 italic text-sm">
              If enabled, this device will be wiped and reinstalled on its next boot. The flag will be automatically reset after the config is downloaded.
            </small>
          </div>

          <!-- Storage Configuration (collapsible, for approved devices) -->
          <div v-if="editingDevice && editingDevice.status === 'approved'" class="mb-4">
            <button type="button" @click="showEditStorage = !showEditStorage" class="flex items-center gap-2 text-sidebar-dark font-medium bg-transparent border-none cursor-pointer p-0 text-base">
              <font-awesome-icon :icon="['fas', showEditStorage ? 'chevron-down' : 'chevron-right']" class="text-sm" />
              Storage Configuration
            </button>
            <small class="block mt-1 text-gray-500 text-sm">Per-device storage overrides. Leave empty to use global defaults.</small>
          </div>

          <div v-if="editingDevice && editingDevice.status === 'approved' && showEditStorage" class="bg-gray-50 p-4 rounded-lg mb-4">
            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">Install Disk</label>
              <input
                v-model="deviceForm.install_disk"
                type="text"
                :placeholder="'Default: ' + storageDefaults.install_disk"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small class="block mt-1 text-gray-500 text-sm">Leave empty to use global default ({{ storageDefaults.install_disk }})</small>
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Max Size</label>
              <input
                v-model="deviceForm.ephemeral_max_size"
                type="text"
                :placeholder="storageDefaults.ephemeral_max_size ? 'Default: ' + storageDefaults.ephemeral_max_size : 'Not set (uses full disk)'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small v-if="storageDefaults.ephemeral_max_size" class="block mt-1 text-gray-500 text-sm">Leave empty to use global default ({{ storageDefaults.ephemeral_max_size }})</small>
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Min Size</label>
              <input
                v-model="deviceForm.ephemeral_min_size"
                type="text"
                :placeholder="storageDefaults.ephemeral_min_size ? 'Default: ' + storageDefaults.ephemeral_min_size : 'Not set'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small v-if="storageDefaults.ephemeral_min_size" class="block mt-1 text-gray-500 text-sm">Leave empty to use global default ({{ storageDefaults.ephemeral_min_size }})</small>
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Disk Selector</label>
              <input
                v-model="deviceForm.ephemeral_disk_selector"
                type="text"
                :placeholder="storageDefaults.ephemeral_disk_selector ? 'Default: ' + storageDefaults.ephemeral_disk_selector : 'Not set (uses install disk)'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small v-if="storageDefaults.ephemeral_disk_selector" class="block mt-1 text-gray-500 text-sm">Leave empty to use global default</small>
            </div>
          </div>

          <div class="flex gap-4 mt-6 justify-end">
            <button type="button" @click="closeModal" class="bg-gray-100 text-gray-700 py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] hover:bg-gray-200">
              Cancel
            </button>
            <button type="submit" class="bg-[#42b983] text-white py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] hover:bg-[#35a372]">
              {{ editingDevice ? 'Update' : 'Add' }} Device
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Approval Modal -->
    <div v-if="showApprovalModal && approvalSuggestions" class="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000]" @click="closeApprovalModal">
      <div class="bg-white p-8 rounded-lg max-w-[500px] w-[90%] max-h-[90vh] overflow-y-auto" @click.stop>
        <h3 class="mt-0 mb-6 text-sidebar-dark">Approve Device</h3>

        <div v-if="approvalSuggestions.is_first_device" class="bg-amber-50 border-l-4 border-amber-500 rounded p-4 text-[0.9rem] leading-normal" style="margin-bottom: 1.5rem;">
          <strong class="block text-amber-800 mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> First Device</strong>
          <p class="text-amber-900 m-0">This is the first device in your cluster. It must be a control plane node and use the cluster endpoint IP.</p>
        </div>

        <div class="bg-gray-50 p-3 rounded mb-4 text-[0.9rem]">
          <strong>MAC Address:</strong> {{ approvingDevice.mac_address }}
        </div>

        <form @submit.prevent="confirmApproval">
          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">Hostname *</label>
            <input
              v-model="approvalForm.hostname"
              type="text"
              required
              placeholder="controlplane-01"
              class="w-full p-2 border border-gray-300 rounded text-base"
            />
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">IP Address *</label>
            <input
              v-model="approvalForm.ip_address"
              type="text"
              required
              placeholder="10.0.5.100"
              :disabled="approvalSuggestions.locked_fields.ip_address"
              class="w-full p-2 border border-gray-300 rounded text-base"
            />
            <small class="block mt-1 text-blue-600 italic text-sm">{{ approvalSuggestions.reasons.ip_address }}</small>
          </div>

          <div class="mb-4">
            <label class="block mb-2 text-sidebar-dark font-medium">Role *</label>
            <select
              v-model="approvalForm.role"
              :disabled="approvalSuggestions.locked_fields.role"
              class="w-full p-2 border border-gray-300 rounded text-base"
            >
              <option value="worker">Worker</option>
              <option value="controlplane">Control Plane</option>
            </select>
            <small class="block mt-1 text-blue-600 italic text-sm">{{ approvalSuggestions.reasons.role }}</small>
          </div>

          <!-- Storage Configuration (collapsible) -->
          <div class="mb-4">
            <button type="button" @click="showApprovalStorage = !showApprovalStorage" class="flex items-center gap-2 text-sidebar-dark font-medium bg-transparent border-none cursor-pointer p-0 text-base">
              <font-awesome-icon :icon="['fas', showApprovalStorage ? 'chevron-down' : 'chevron-right']" class="text-sm" />
              Storage Configuration
            </button>
            <small class="block mt-1 text-gray-500 text-sm">Pre-filled from default storage settings. Modify to override for this device.</small>
          </div>

          <div v-if="showApprovalStorage" class="bg-gray-50 p-4 rounded-lg mb-4">
            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">Install Disk</label>
              <input
                v-model="approvalForm.install_disk"
                type="text"
                :placeholder="'Default: ' + storageDefaults.install_disk"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small class="block mt-1 text-gray-500 text-sm">Disk device where Talos will be installed</small>
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Max Size</label>
              <input
                v-model="approvalForm.ephemeral_max_size"
                type="text"
                :placeholder="storageDefaults.ephemeral_max_size ? 'Default: ' + storageDefaults.ephemeral_max_size : 'Not set (uses full disk)'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Min Size</label>
              <input
                v-model="approvalForm.ephemeral_min_size"
                type="text"
                :placeholder="storageDefaults.ephemeral_min_size ? 'Default: ' + storageDefaults.ephemeral_min_size : 'Not set'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
            </div>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">EPHEMERAL Disk Selector</label>
              <input
                v-model="approvalForm.ephemeral_disk_selector"
                type="text"
                :placeholder="storageDefaults.ephemeral_disk_selector ? 'Default: ' + storageDefaults.ephemeral_disk_selector : 'Not set (uses install disk)'"
                class="w-full p-2 border border-gray-300 rounded text-base"
              />
              <small class="block mt-1 text-gray-500 text-sm">CEL expression for disk selection</small>
            </div>
          </div>

          <div class="flex gap-4 mt-6 justify-end">
            <button type="button" @click="closeApprovalModal" class="bg-gray-100 text-gray-700 py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] hover:bg-gray-200">
              Cancel
            </button>
            <button type="submit" class="bg-[#42b983] text-white py-2 px-6 border-none rounded cursor-pointer text-[0.9rem] hover:bg-[#35a372]">
              Approve Device
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Wipe Confirmation Modal -->
    <div v-if="showWipeModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" @click.self="showWipeModal = false">
      <div class="bg-white p-8 rounded-lg max-w-[450px] w-[90%] shadow-xl">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
            <font-awesome-icon :icon="['fas', 'triangle-exclamation']" class="text-red-600" />
          </div>
          <h3 class="text-sidebar-dark text-xl m-0">Wipe & Reinstall</h3>
        </div>
        <p class="text-gray-600 text-sm mb-2">
          <strong>{{ wipeTarget?.hostname || wipeTarget?.mac_address }}</strong> will be wiped and reinstalled on its next boot.
        </p>
        <p class="text-red-700 text-sm mb-4 font-medium">
          All data on the install disk will be destroyed.
        </p>

        <label class="flex items-center gap-2 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer mb-6">
          <input type="checkbox" v-model="wipeRebootNow" class="w-auto cursor-pointer" />
          <div>
            <span class="font-medium text-sidebar-dark text-sm">Reboot now</span>
            <span class="text-gray-500 text-xs block mt-0.5">Immediately reboot the device to start the wipe process</span>
          </div>
        </label>

        <div class="flex justify-end gap-3">
          <button @click="showWipeModal = false" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
          <button @click="confirmWipe" class="bg-red-600 text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-red-700">
            Confirm Wipe
          </button>
        </div>
      </div>
    </div>

    <!-- Rolling Refresh Confirmation Modal -->
    <div v-if="showRefreshConfirm" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" @click.self="showRefreshConfirm = false">
      <div class="bg-white p-8 rounded-lg max-w-[520px] w-[90%] shadow-xl">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
            <font-awesome-icon :icon="['fas', 'arrows-rotate']" class="text-amber-600" />
          </div>
          <h3 class="text-sidebar-dark text-xl m-0">Refresh Worker Nodes</h3>
        </div>

        <!-- Strategy selector -->
        <div class="mb-4">
          <label class="text-sm font-medium text-gray-700 block mb-2">Refresh Strategy</label>
          <div class="space-y-2">
            <label class="flex items-start gap-2.5 cursor-pointer p-2 rounded hover:bg-gray-50 transition-colors">
              <input type="radio" v-model="refreshMode" value="sequential" class="mt-0.5 accent-amber-500" />
              <div>
                <span class="text-sm font-medium text-gray-800">Sequential (Safest)</span>
                <p class="text-xs text-gray-500 m-0 mt-0.5">One node at a time. Drains pods before each wipe. Cluster stays available.</p>
              </div>
            </label>
            <label class="flex items-start gap-2.5 cursor-pointer p-2 rounded hover:bg-gray-50 transition-colors">
              <input type="radio" v-model="refreshMode" value="parallel" class="mt-0.5 accent-amber-500" />
              <div>
                <span class="text-sm font-medium text-gray-800">Parallel</span>
                <p class="text-xs text-gray-500 m-0 mt-0.5">Multiple nodes concurrently. Faster but reduces cluster capacity.</p>
                <div v-if="refreshMode === 'parallel'" class="mt-1.5 flex items-center gap-2">
                  <label class="text-xs text-gray-600 whitespace-nowrap">Batch size:</label>
                  <input type="number" v-model.number="refreshParallelism" min="2" :max="refreshableWorkers.length"
                    class="w-16 text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-amber-500" />
                </div>
              </div>
            </label>
            <label class="flex items-start gap-2.5 cursor-pointer p-2 rounded hover:bg-red-50 transition-colors">
              <input type="radio" v-model="refreshMode" value="all_at_once" class="mt-0.5 accent-red-500" />
              <div>
                <span class="text-sm font-medium text-red-600">All at Once (Dangerous)</span>
                <p class="text-xs text-red-500 m-0 mt-0.5">Wipes ALL workers simultaneously. No drain. Cluster will be completely unavailable.</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Danger confirmation for all-at-once -->
        <div v-if="refreshMode === 'all_at_once'" class="bg-red-50 border border-red-200 rounded p-3 mb-4">
          <p class="text-xs text-red-700 font-medium m-0 mb-2">Type CONFIRM to proceed with all-at-once wipe:</p>
          <input v-model="dangerConfirmText" type="text" placeholder="Type CONFIRM"
            class="w-full text-sm border border-red-300 rounded px-3 py-1.5 focus:outline-none focus:border-red-500" />
        </div>

        <p class="text-amber-700 text-sm mb-4 font-medium">
          All data on the install disk of each worker will be destroyed.
        </p>

        <div class="bg-gray-50 rounded p-3 mb-6 max-h-[160px] overflow-y-auto">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Workers to refresh ({{ refreshableWorkers.length }}):</p>
          <div v-for="worker in refreshableWorkers" :key="worker.id" class="flex items-center gap-2 py-1.5 border-b border-gray-200 last:border-0">
            <span class="w-2 h-2 rounded-full bg-green-500 shrink-0"></span>
            <span class="text-sm text-sidebar-dark font-medium">{{ worker.hostname || worker.mac_address }}</span>
            <span class="text-xs text-gray-400 font-mono ml-auto">{{ worker.ip_address }}</span>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button @click="showRefreshConfirm = false; dangerConfirmText = ''" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
          <button @click="startRollingRefresh"
            :disabled="refreshMode === 'all_at_once' && dangerConfirmText !== 'CONFIRM'"
            :class="refreshMode === 'all_at_once' ? 'bg-red-500 hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed' : 'bg-amber-500 hover:bg-amber-600'"
            class="text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors">
            {{ refreshMode === 'all_at_once' ? 'Wipe All Now' : 'Start Refresh' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rolling Refresh Progress Modal -->
    <div v-if="showRefreshModal" class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center">
      <div class="bg-gray-900 p-8 rounded-lg max-w-[550px] w-[90%] shadow-xl border border-gray-700">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
              <font-awesome-icon :icon="['fas', 'arrows-rotate']" class="text-indigo-400 refresh-spin" />
            </div>
            <div>
              <h3 class="text-gray-100 text-xl m-0">Refreshing Worker Nodes</h3>
              <p class="text-gray-400 text-xs m-0 mt-0.5">
                {{ refreshProgressSummary }}
              </p>
            </div>
          </div>
        </div>

        <div class="space-y-3 mb-6 max-h-[300px] overflow-y-auto">
          <div v-for="(node, idx) in refreshNodeList" :key="node.id"
               class="flex items-center gap-3 p-3 rounded border"
               :class="{
                 'border-gray-700 bg-gray-800': node.state === 'pending',
                 'border-indigo-500/50 bg-indigo-500/10': node.state === 'in_progress',
                 'border-green-500/50 bg-green-500/10': node.state === 'completed',
                 'border-red-500/50 bg-red-500/10': node.state === 'failed',
               }">
            <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0" :class="{
              'bg-gray-700 text-gray-500': node.state === 'pending',
              'bg-indigo-500 text-white': node.state === 'in_progress',
              'bg-green-500 text-white': node.state === 'completed',
              'bg-red-500 text-white': node.state === 'failed',
            }">
              <font-awesome-icon v-if="node.state === 'pending'" :icon="['fas', 'clock']" class="text-xs" />
              <span v-else-if="node.state === 'in_progress'" class="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full refresh-spin"></span>
              <font-awesome-icon v-else-if="node.state === 'completed'" :icon="['fas', 'check']" class="text-xs" />
              <font-awesome-icon v-else :icon="['fas', 'xmark']" class="text-xs" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-200 m-0 truncate">{{ node.hostname }}</p>
              <p class="text-xs m-0 mt-0.5 truncate" :class="{
                'text-gray-500': node.state === 'pending',
                'text-indigo-400': node.state === 'in_progress',
                'text-green-400': node.state === 'completed',
                'text-red-400': node.state === 'failed',
              }">{{ node.stepText }}</p>
            </div>
            <span class="text-xs text-gray-500 font-mono shrink-0">{{ node.ip_address }}</span>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button v-if="rollingRefreshActive" @click="cancelRollingRefresh"
                  class="py-2.5 px-6 border border-gray-600 rounded text-sm cursor-pointer bg-gray-800 text-gray-300 hover:bg-gray-700"
                  :disabled="refreshCancelling">
            {{ refreshCancelling ? 'Cancelling...' : 'Cancel' }}
          </button>
          <button v-else @click="showRefreshModal = false"
                  class="bg-indigo-600 text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-indigo-700">
            Close
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
        notes: '',
        wipe_on_next_boot: false,
        install_disk: '',
        ephemeral_min_size: '',
        ephemeral_max_size: '',
        ephemeral_disk_selector: ''
      },
      approvalForm: {
        hostname: '',
        ip_address: '',
        role: 'worker',
        install_disk: '',
        ephemeral_min_size: '',
        ephemeral_max_size: '',
        ephemeral_disk_selector: ''
      },
      showApprovalStorage: false,
      showEditStorage: false,
      unsubscribeWs: null,
      deviceMap: new Map(), // Track devices by MAC address for change detection
      health: {},
      bootstrapping: false,
      isEditingOnlyControlPlane: false,
      showWipeModal: false,
      wipeTarget: null,
      wipeRebootNow: false,
      // Rolling refresh
      rollingRefreshActive: false,
      rollingRefreshProgress: null,
      nodeStates: {},  // idx -> {step, message} for concurrent modes
      refreshDeviceList: [],
      showRefreshConfirm: false,
      showRefreshModal: false,
      refreshCancelling: false,
      refreshMode: 'sequential',
      refreshParallelism: 2,
      dangerConfirmText: '',
      storageDefaults: {
        install_disk: '/dev/sda',
        ephemeral_min_size: null,
        ephemeral_max_size: null,
        ephemeral_disk_selector: null
      }
    }
  },
  computed: {
    hasApprovedControlPlane() {
      return this.devices.some(
        device => device.status === 'approved' && device.role === 'controlplane'
      )
    },
    approvedWorkerCount() {
      return this.devices.filter(
        d => d.status === 'approved' && d.role === 'worker' && d.ip_address
      ).length
    },
    refreshableWorkers() {
      return this.devices.filter(
        d => d.status === 'approved' && d.role === 'worker' && d.ip_address
      )
    },
    refreshStepLabel() {
      // For the banner — show summary of active nodes
      const activeNodes = Object.values(this.nodeStates).filter(s => s.step && !['pending', 'completed', 'failed', 'cancelled'].includes(s.step))
      if (activeNodes.length === 0) {
        if (!this.rollingRefreshProgress) return ''
        const labels = {
          starting: 'Starting...', draining: 'Draining pods...', setting_wipe: 'Setting wipe flag...',
          rebooting: 'Rebooting...', waiting_for_boot: 'Waiting for boot...',
          waiting_for_kubernetes: 'Waiting for Kubernetes...', configuring_storage: 'Configuring storage...', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled',
        }
        return labels[this.rollingRefreshProgress.step] || this.rollingRefreshProgress.step
      }
      if (activeNodes.length === 1) {
        const stepLabels = {
          draining: 'Draining pods...', setting_wipe: 'Setting wipe...', rebooting: 'Rebooting...',
          waiting_for_boot: 'Waiting for boot...', waiting_for_kubernetes: 'Waiting for Kubernetes...', configuring_storage: 'Configuring storage...',
        }
        return stepLabels[activeNodes[0].step] || activeNodes[0].step
      }
      return `${activeNodes.length} nodes active`
    },
    refreshProgressSummary() {
      const completed = Object.values(this.nodeStates).filter(s => s.step === 'completed').length
      const failed = Object.values(this.nodeStates).filter(s => s.step === 'failed').length
      const total = this.refreshDeviceList.length
      const active = Object.values(this.nodeStates).filter(s => s.step && !['pending', 'completed', 'failed', 'cancelled'].includes(s.step)).length
      const parts = []
      if (active > 0) parts.push(`${active} active`)
      if (completed > 0) parts.push(`${completed} done`)
      if (failed > 0) parts.push(`${failed} failed`)
      return parts.length > 0 ? `${parts.join(', ')} of ${total}` : `0 of ${total}`
    },
    refreshNodeList() {
      const stepLabels = {
        pending: 'Waiting...', draining: 'Draining pods...', setting_wipe: 'Setting wipe flag...',
        rebooting: 'Rebooting...', waiting_for_boot: 'Waiting for boot...',
        waiting_for_kubernetes: 'Waiting for Kubernetes...', configuring_storage: 'Configuring storage...', starting: 'Starting...',
        completed: 'Refreshed successfully', failed: 'Failed', cancelled: 'Cancelled',
      }

      return this.refreshDeviceList.map((dev, idx) => {
        const ns = this.nodeStates[idx]
        let state = 'pending'
        let stepText = 'Waiting...'

        if (ns) {
          const step = ns.step
          if (step === 'completed') {
            state = 'completed'
            stepText = 'Refreshed successfully'
          } else if (step === 'failed') {
            state = 'failed'
            stepText = ns.message || 'Failed'
          } else if (step === 'cancelled') {
            state = 'pending'
            stepText = 'Cancelled'
          } else if (step === 'pending') {
            state = 'pending'
            stepText = 'Waiting...'
          } else {
            state = 'in_progress'
            stepText = stepLabels[step] || ns.message || step
          }
        }

        if (!this.rollingRefreshActive && state === 'pending' && this.refreshDeviceList.length > 0) {
          stepText = 'Skipped'
        }

        return { ...dev, state, stepText }
      })
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
    this.loadStorageDefaults()
    this.subscribeToWebSocket()
    apiService.getDeviceHealth().then(h => { this.health = h || {} }).catch(() => {})
    this.checkRollingRefreshStatus()
  },
  beforeUnmount() {
    if (this.unsubscribeWs) {
      this.unsubscribeWs()
    }
  },
  methods: {
    async loadStorageDefaults() {
      try {
        const cluster = await apiService.getClusterSettings()
        this.storageDefaults.install_disk = cluster.install_disk || '/dev/sda'
      } catch (e) { /* no cluster settings yet */ }
      try {
        const ephemeral = await apiService.getVolumeConfigByName('EPHEMERAL')
        this.storageDefaults.ephemeral_min_size = ephemeral.min_size || null
        this.storageDefaults.ephemeral_max_size = ephemeral.max_size || null
        this.storageDefaults.ephemeral_disk_selector = ephemeral.disk_selector_match || null
      } catch (e) { /* no EPHEMERAL config yet */ }
    },
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
          this.toast.error('Failed to load devices')
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
        if (event.type === 'device_health') {
          this.health = event.data || {}
          return
        }
        // Reload devices when any device event occurs
        const deviceEvents = [
          'device_discovered',
          'config_downloaded',
          'device_approved',
          'device_rejected',
          'device_deleted',
          'device_updated',
          'device_wipe_started',
          'device_shutdown',
          'device_reboot',
          'device_wol'
        ]
        if (deviceEvents.includes(event.type)) {
          // Optimistically clear wipe badge when wipe boot starts
          if (event.type === 'device_wipe_started' && event.data?.mac_address) {
            const dev = this.devices.find(d => d.mac_address === event.data.mac_address)
            if (dev) dev.wipe_on_next_boot = false
          }
          this.loadDevices(true) // Background refresh
          this.showEventToast(event)
        }

        // Rolling refresh events
        if (event.type === 'rolling_refresh_progress') {
          const d = event.data
          this.rollingRefreshProgress = d
          this.rollingRefreshActive = true
          // Update per-node state map
          if (d.node_index !== undefined) {
            this.nodeStates = { ...this.nodeStates, [d.node_index]: { step: d.step, message: d.message } }
          }
          if (!this.showRefreshModal) this.showRefreshModal = true
        }
        if (event.type === 'rolling_refresh_complete') {
          this.rollingRefreshActive = false
          this.refreshCancelling = false
          const d = event.data || {}
          if (d.cancelled) {
            this.toast.warning(`Rolling refresh cancelled. ${d.succeeded} of ${d.total} nodes refreshed.`, { timeout: 8000 })
          } else if (d.failed > 0) {
            this.toast.error(`Rolling refresh stopped. ${d.succeeded} succeeded, ${d.failed} failed.`, { timeout: 10000 })
          } else {
            this.toast.success(`All ${d.succeeded} worker nodes refreshed successfully.`, { timeout: 8000 })
          }
          this.loadDevices(true)
        }
        if (event.type === 'rolling_refresh_error') {
          const d = event.data || {}
          const name = d.device?.hostname || 'Unknown'
          this.toast.error(`Refresh failed for ${name}: ${d.error}`, { timeout: 10000 })
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
        const sd = this.approvalSuggestions.storage_defaults || {}
        this.approvalForm = {
          hostname: this.approvalSuggestions.suggestions.hostname,
          ip_address: this.approvalSuggestions.suggestions.ip_address,
          role: this.approvalSuggestions.suggestions.role,
          install_disk: sd.install_disk || '',
          ephemeral_min_size: sd.ephemeral_min_size || '',
          ephemeral_max_size: sd.ephemeral_max_size || '',
          ephemeral_disk_selector: sd.ephemeral_disk_selector || ''
        }
        this.showApprovalStorage = false

        this.showApprovalModal = true
      } catch (error) {
        this.toast.error(error.message || 'Failed to load approval suggestions')
      }
    },
    async confirmApproval() {
      try {
        const payload = {
          ...this.approvalForm,
          install_disk: this.approvalForm.install_disk || null,
          ephemeral_min_size: this.approvalForm.ephemeral_min_size || null,
          ephemeral_max_size: this.approvalForm.ephemeral_max_size || null,
          ephemeral_disk_selector: this.approvalForm.ephemeral_disk_selector || null
        }
        await apiService.approveDevice(this.approvingDevice.id, payload)
        this.toast.success(`${this.approvalForm.hostname || 'Device'} approved and added to fleet`)
        this.closeApprovalModal()
        await this.loadDevices()
      } catch (error) {
        this.toast.error(error.message || 'Failed to approve device')
      }
    },
    closeApprovalModal() {
      this.showApprovalModal = false
      this.approvingDevice = null
      this.approvalSuggestions = null
      this.showApprovalStorage = false
      this.approvalForm = {
        hostname: '',
        ip_address: '',
        role: 'worker',
        install_disk: '',
        ephemeral_min_size: '',
        ephemeral_max_size: '',
        ephemeral_disk_selector: ''
      }
    },
    async rejectDevice(deviceId) {
      try {
        await apiService.rejectDevice(deviceId)
        this.toast.success('Device rejected and removed from queue')
        await this.loadDevices()
      } catch (error) {
        this.toast.error('Failed to reject device')
      }
    },
    async deleteDevice(deviceId) {
      if (!confirm('Are you sure you want to delete this device?')) {
        return
      }

      try {
        await apiService.deleteDevice(deviceId)
        this.toast.success('Device removed from inventory')
        await this.loadDevices()
      } catch (error) {
        this.toast.error('Failed to delete device')
      }
    },
    toggleWipeFlag(device) {
      if (device.wipe_on_next_boot) {
        // Cancel wipe — no modal needed
        this.cancelWipe(device)
        return
      }
      // Open wipe modal
      this.wipeTarget = device
      this.wipeRebootNow = false
      this.showWipeModal = true
    },
    async cancelWipe(device) {
      try {
        await apiService.updateDevice(device.id, { wipe_on_next_boot: false })
        this.toast.success(`Wipe cancelled for ${device.hostname || device.mac_address}`)
        await this.loadDevices()
      } catch (error) {
        this.toast.error(error.message || 'Failed to cancel wipe')
      }
    },
    confirmWipe() {
      if (!this.wipeTarget) return
      const device = this.wipeTarget
      const name = device.hostname || device.mac_address
      const rebootNow = this.wipeRebootNow

      // Close modal and optimistically update local state
      this.showWipeModal = false
      this.wipeTarget = null
      device.wipe_on_next_boot = true
      if (rebootNow) {
        this.toast.info(`Sending reboot command for ${name}...`)
      }

      // Dispatch asynchronously
      apiService.updateDevice(device.id, { wipe_on_next_boot: true }).then(() => {
        if (rebootNow) {
          apiService.rebootDevice(device.id).catch(err => {
            this.toast.warning(`Wipe scheduled for ${name}, but reboot failed: ${err.message}`)
          })
        } else {
          this.toast.warning(`${name} will be wiped and reinstalled on next boot`)
        }
        this.loadDevices(true)
      }).catch(error => {
        this.toast.error(error.message || 'Failed to set wipe flag')
      })
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

      this.showEditStorage = false
      this.deviceForm = {
        mac_address: device.mac_address,
        hostname: device.hostname || '',
        ip_address: device.ip_address || '',
        role: device.role,
        notes: device.notes || '',
        wipe_on_next_boot: device.wipe_on_next_boot || false,
        install_disk: device.install_disk || '',
        ephemeral_min_size: device.ephemeral_min_size || '',
        ephemeral_max_size: device.ephemeral_max_size || '',
        ephemeral_disk_selector: device.ephemeral_disk_selector || ''
      }
    },
    async saveDevice() {
      try {
        const formData = {
          ...this.deviceForm,
          install_disk: this.deviceForm.install_disk || null,
          ephemeral_min_size: this.deviceForm.ephemeral_min_size || null,
          ephemeral_max_size: this.deviceForm.ephemeral_max_size || null,
          ephemeral_disk_selector: this.deviceForm.ephemeral_disk_selector || null
        }
        if (this.editingDevice) {
          await apiService.updateDevice(this.editingDevice.id, formData)
          this.toast.success(`${formData.hostname || formData.mac_address} configuration updated`)
        } else {
          await apiService.createDevice(formData)
          this.toast.success(`${formData.hostname || formData.mac_address} added to inventory`)
        }
        this.closeModal()
        await this.loadDevices()
      } catch (error) {
        this.toast.error(error.message || 'Failed to save device')
      }
    },
    closeModal() {
      this.showAddModal = false
      this.editingDevice = null
      this.isEditingOnlyControlPlane = false
      this.showEditStorage = false
      this.deviceForm = {
        mac_address: '',
        hostname: '',
        ip_address: '',
        role: 'worker',
        notes: '',
        wipe_on_next_boot: false,
        install_disk: '',
        ephemeral_min_size: '',
        ephemeral_max_size: '',
        ephemeral_disk_selector: ''
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
      } catch (error) {
        const errorMessage = error.message || 'Failed to bootstrap cluster'
        this.toast.error(errorMessage, { timeout: 10000 })
      } finally {
        this.bootstrapping = false
      }
    },
    formatDate(dateString) {
      return new Date(dateString).toLocaleString()
    },
    isDeviceOnline(device) {
      const h = this.health[device.mac_address]
      return h && h.talos_api
    },
    async shutdownDevice(device) {
      const name = device.hostname || device.mac_address
      if (!confirm(`Shutdown ${name}? The node will power off and must be manually restarted or woken via WoL.`)) return
      try {
        const result = await apiService.shutdownDevice(device.id)
        this.toast.success(result.message, { timeout: 6000 })
      } catch (error) {
        this.toast.error(error.message || `Failed to shutdown ${name}`, { timeout: 8000 })
      }
    },
    async wakeDevice(device) {
      const name = device.hostname || device.mac_address
      try {
        const result = await apiService.wakeDevice(device.id)
        this.toast.info(result.message, { timeout: 6000 })
      } catch (error) {
        this.toast.error(error.message || `Failed to send WoL to ${name}`, { timeout: 8000 })
      }
    },
    async checkRollingRefreshStatus() {
      try {
        const status = await apiService.getRollingRefreshStatus()
        if (status.active) {
          this.rollingRefreshActive = true
          this.rollingRefreshProgress = status
          // Rebuild device list and node states from status
          this.refreshDeviceList = this.refreshableWorkers.map(d => ({
            id: d.id,
            hostname: d.hostname || d.mac_address,
            mac_address: d.mac_address,
            ip_address: d.ip_address,
          }))
          if (status.node_states) {
            this.nodeStates = { ...status.node_states }
          }
          this.showRefreshModal = true
        }
      } catch (e) { /* backend may not support this yet */ }
    },
    async startRollingRefresh() {
      this.showRefreshConfirm = false
      this.refreshCancelling = false
      this.dangerConfirmText = ''
      // Build device list for tracking
      this.refreshDeviceList = this.refreshableWorkers.map(d => ({
        id: d.id,
        hostname: d.hostname || d.mac_address,
        mac_address: d.mac_address,
        ip_address: d.ip_address,
      }))
      // Initialize per-node state map
      this.nodeStates = {}
      this.refreshDeviceList.forEach((_, idx) => {
        this.nodeStates[idx] = { step: 'pending', message: 'Waiting...' }
      })
      this.rollingRefreshProgress = null
      this.showRefreshModal = true

      try {
        const result = await apiService.rollingRefreshWorkers(null, {
          mode: this.refreshMode,
          parallelism: this.refreshParallelism,
        })
        this.rollingRefreshActive = true
        if (result.devices) {
          this.refreshDeviceList = result.devices
        }
      } catch (error) {
        this.toast.error(error.message || 'Failed to start rolling refresh')
        this.showRefreshModal = false
      }
    },
    async cancelRollingRefresh() {
      this.refreshCancelling = true
      try {
        await apiService.cancelRollingRefresh()
        this.toast.info('Cancellation requested — will stop after current node(s)')
      } catch (error) {
        this.toast.error(error.message || 'Failed to cancel')
        this.refreshCancelling = false
      }
    },
    showEventToast(event) {
      const data = event.data || {}
      const name = data.hostname || data.mac_address || ''
      switch (event.type) {
        case 'device_discovered':
          // Handled by detectDeviceChanges
          break
        case 'config_downloaded':
          // Handled by detectDeviceChanges
          break
        case 'device_approved':
          this.toast.success(`${name || 'Device'} approved and added to fleet`, { timeout: 5000 })
          break
        case 'device_rejected':
          this.toast.warning(`${name || 'Device'} rejected and removed from queue`, { timeout: 5000 })
          break
        case 'device_deleted':
          this.toast.info(`${name || 'Device'} removed from inventory`, { timeout: 5000 })
          break
        case 'device_updated':
          if (data.changes && Object.keys(data.changes).length > 0) {
            const fields = Object.keys(data.changes).filter(k => k !== 'device_id').join(', ')
            this.toast.info(`${name} updated: ${fields}`, { timeout: 5000 })
          }
          break
        case 'device_wipe_started':
          this.toast.warning(`${data.hostname || data.mac_address || 'Device'} wipe boot started`, { timeout: 8000 })
          break
        case 'device_shutdown':
          this.toast.warning(`${name || 'Device'} is shutting down`, { timeout: 6000 })
          break
        case 'device_reboot':
          this.toast.warning(`${name || 'Device'} is rebooting`, { timeout: 6000 })
          break
        case 'device_wol':
          this.toast.info(`Wake-on-LAN sent to ${name || 'device'}`, { timeout: 6000 })
          break
      }
    },
  }
}
</script>

<style>
.refresh-spin {
  animation: refresh-spin 0.8s linear infinite;
}

@keyframes refresh-spin {
  to { transform: rotate(360deg); }
}
</style>
