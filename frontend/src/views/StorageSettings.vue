<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Default Storage Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Configure default disk space allocation for Talos system partitions</p>
      </div>
      <button @click="saveAll" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed whitespace-nowrap" :disabled="loading || saving">
        {{ saving ? 'Saving...' : 'Save & Apply' }}
      </button>
    </div>

    <div class="bg-blue-50 border-l-4 border-blue-500 rounded-md p-4 mb-8 text-[0.9rem] leading-relaxed">
      <strong class="block text-blue-800 mb-2 text-[0.95rem]"><font-awesome-icon :icon="['fas', 'circle-info']" /> These are default settings</strong>
      <p class="m-0 mt-2 text-gray-700">
        These storage settings serve as defaults for newly approved devices. You can override
        them on a per-device basis when approving or editing a device in
        <router-link to="/devices" class="text-blue-600 underline font-medium hover:text-blue-800">Device Management</router-link>.
      </p>
    </div>

    <div class="flex gap-8 items-start">
      <aside class="sticky top-24 w-[250px] shrink-0 bg-white p-6 rounded-lg shadow-md max-h-[calc(100vh-7rem)] overflow-y-auto">
        <h3 class="mt-0 mb-4 text-sidebar-dark text-lg border-b-2 border-[#42b983] pb-2">Table of Contents</h3>
        <nav>
          <ul class="list-none p-0 m-0">
            <li class="mb-2">
              <a href="#overview" @click.prevent="scrollTo('overview')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Overview</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#disk-layout" @click.prevent="scrollTo('disk-layout')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Disk Layout</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#install-disk" @click.prevent="scrollTo('install-disk')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Installation Disk</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#install-disk-device" @click.prevent="scrollTo('install-disk-device')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Disk Device</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#ephemeral-config" @click.prevent="scrollTo('ephemeral-config')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">EPHEMERAL Storage</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#ephemeral-limit" @click.prevent="scrollTo('ephemeral-limit')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Size Limit</a></li>
                <li><a href="#ephemeral-max" @click.prevent="scrollTo('ephemeral-max')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Max / Min Size</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#advanced" @click.prevent="scrollTo('advanced')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Advanced Options</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#disk-selector" @click.prevent="scrollTo('disk-selector')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Disk Selector</a></li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="bg-white p-8 rounded-lg shadow-md flex-1 min-w-0">
        <div v-if="loading" class="text-center py-12 text-gray-500">Loading storage configuration...</div>

        <form v-else @submit.prevent="saveAll">
          <!-- Overview Section -->
          <div id="overview" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Overview</h3>
            <p class="text-gray-500 text-sm mb-4">
              Understanding how Talos partitions disks and why you might want to limit EPHEMERAL size.
              <router-link to="/wiki#storage-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-md">
              <strong class="text-blue-800 block mb-2 text-[0.95rem]">What is this page for?</strong>
              <p class="text-gray-700 m-0 text-[0.9rem] leading-relaxed">
                When Talos installs on a machine, it automatically creates several partitions on your disk.
                By default, the <strong>EPHEMERAL</strong> partition will consume all remaining disk space.
                This page lets you <strong>limit how much space</strong> Talos uses, leaving room for other
                storage systems like Rook/Ceph.
              </p>
            </div>

            <div id="disk-layout" class="my-6 p-4 bg-gray-50 rounded-lg scroll-mt-24">
              <h4 class="text-gray-600 mb-4 text-base">Default Talos Disk Layout (Automatic)</h4>
              <div class="flex h-[60px] rounded overflow-hidden shadow-sm my-4">
                <div class="flex flex-col items-center justify-center text-white font-semibold text-sm relative bg-indigo-500 basis-[80px] shrink-0 grow-0" data-tooltip="EFI Boot Partition">
                  <span>EFI</span>
                  <small class="text-[0.7rem] font-normal opacity-90">~100MB</small>
                </div>
                <div class="flex flex-col items-center justify-center text-white font-semibold text-sm relative bg-violet-500 basis-[40px] shrink-0 grow-0" data-tooltip="Metadata">
                  <span>META</span>
                  <small class="text-[0.7rem] font-normal opacity-90">~1MB</small>
                </div>
                <div class="flex flex-col items-center justify-center text-white font-semibold text-sm relative bg-pink-500 basis-[80px] shrink-0 grow-0" data-tooltip="System State">
                  <span>STATE</span>
                  <small class="text-[0.7rem] font-normal opacity-90">~100MB</small>
                </div>
                <div class="flex flex-col items-center justify-center text-white font-semibold text-sm relative bg-amber-500 flex-1" data-tooltip="Container Data, Images, Logs">
                  <span>EPHEMERAL</span>
                  <small class="text-[0.7rem] font-normal opacity-90">Rest of disk</small>
                </div>
              </div>
              <p class="text-sm text-gray-500 mt-2 italic">
                <strong>EPHEMERAL</strong> stores: Container data, downloaded images, logs, and etcd database (on control planes)
              </p>
            </div>

            <div class="bg-amber-50 border-l-4 border-amber-500 rounded p-4 text-[0.9rem] leading-normal mt-4">
              <strong class="block text-amber-800 mb-2"><font-awesome-icon :icon="['fas', 'circle-info']" /> Why limit EPHEMERAL?</strong>
              <p class="text-amber-900 m-0">
                If you plan to use storage solutions like <strong>Rook/Ceph</strong>, they need unpartitioned
                space on the disk. By limiting EPHEMERAL to a specific size (e.g., 100GB), you leave the
                remaining disk space available for Rook/Ceph to claim as Object Storage Devices (OSDs).
              </p>
            </div>
          </div>

          <!-- Installation Disk Section -->
          <div id="install-disk" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Installation Disk</h3>
            <p class="text-gray-500 text-sm mb-4">
              The target disk device where Talos Linux will be installed.
              <router-link to="/wiki#storage-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div id="install-disk-device" class="mb-4 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Install Disk *</label>
              <input
                v-model="clusterSettings.install_disk"
                type="text"
                required
                placeholder="/dev/sda"
                :disabled="loading"
                class="w-full max-w-sm p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">
                Common devices: <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/sda</code> (SATA),
                <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/nvme0n1</code> (NVMe),
                <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/vda</code> (virtio)
              </small>
              <div class="mt-3 p-4 bg-amber-50 border-l-4 border-orange-500 rounded text-[0.9rem] leading-relaxed text-amber-800">
                <strong class="text-red-800"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Warning:</strong>
                The installation process will <strong>wipe all data</strong> on this disk. Make sure you select the correct device.
              </div>
            </div>
          </div>

          <!-- EPHEMERAL Configuration Section -->
          <div id="ephemeral-config" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">EPHEMERAL Storage</h3>
            <p class="text-gray-500 text-sm mb-4">
              Control how much disk space the EPHEMERAL partition consumes.
              <router-link to="/wiki#storage-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div id="ephemeral-limit" class="mb-4 scroll-mt-24">
              <label class="flex! items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="ephemeralConfig.enabled" class="w-auto m-0 cursor-pointer" />
                <span class="font-medium">Limit EPHEMERAL partition size</span>
              </label>
              <small class="block mt-2 text-gray-500 text-sm leading-normal">Enable to prevent EPHEMERAL from using the entire disk</small>
            </div>

            <div id="ephemeral-max" v-if="ephemeralConfig.enabled" class="bg-gray-50 p-6 rounded-lg mt-4 scroll-mt-24">
              <div class="grid grid-cols-2 gap-4">
                <div class="mb-2">
                  <label class="block mb-2 text-sidebar-dark font-medium">Maximum Size *</label>
                  <input
                    v-model="ephemeralConfig.maxSize"
                    type="text"
                    required
                    placeholder="e.g., 100GB"
                    :disabled="loading"
                    class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                  <small class="block mt-1 text-gray-500 text-sm">Format: 20GB, 100GB, 500GB, 1TB</small>
                </div>
                <div class="mb-2">
                  <label class="block mb-2 text-sidebar-dark font-medium">Minimum Size</label>
                  <input
                    v-model="ephemeralConfig.minSize"
                    type="text"
                    placeholder="e.g., 2GB (default)"
                    :disabled="loading"
                    class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                  <small class="block mt-1 text-gray-500 text-sm">Minimum space Talos guarantees (default: 2GB)</small>
                </div>
              </div>
              <div class="mt-4 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-md text-[0.9rem] leading-relaxed">
                <strong class="text-blue-800 block mb-2 text-[0.95rem]">Recommended sizes</strong>
                <p class="text-gray-700 m-0">
                  <strong>Control Plane:</strong> 50–100GB (etcd database) &nbsp;|&nbsp;
                  <strong>Worker:</strong> 50–200GB (depending on workload)
                </p>
              </div>
            </div>

            <div v-if="!ephemeralConfig.enabled" class="mt-3 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-md text-[0.9rem] leading-relaxed">
              <strong class="text-blue-800 block mb-2 text-[0.95rem]"><font-awesome-icon :icon="['fas', 'circle-info']" /> Default Behavior</strong>
              <p class="text-gray-700 m-0">
                When unchecked, EPHEMERAL will automatically grow to use all available disk space.
                This is fine if you don't need space for other storage systems.
              </p>
            </div>
          </div>

          <!-- Advanced Section -->
          <div id="advanced" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Advanced Options</h3>
            <p class="text-gray-500 text-sm mb-4">
              Fine-grained disk selection using CEL expressions.
              <router-link to="/wiki#storage-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div id="disk-selector" class="mb-4 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Disk Selector (CEL Expression)</label>
              <input
                v-model="ephemeralConfig.diskSelector"
                type="text"
                placeholder="e.g., disk.transport == 'nvme'"
                :disabled="loading || !ephemeralConfig.enabled"
                class="w-full max-w-sm p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">
                Examples: <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">disk.transport == 'nvme'</code>,
                <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">disk.size > 500GB</code>
              </small>
              <div v-if="!ephemeralConfig.enabled" class="mt-2 text-gray-400 text-sm italic">Enable EPHEMERAL size limit above to use disk selectors.</div>
            </div>
          </div>
        </form>

      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import { useToast } from 'vue-toastification'

export default {
  name: 'StorageSettings',
  data() {
    return {
      loading: true,
      saving: false,
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
    }
  },
  async mounted() {
    this.toast = useToast()
    await this.loadConfiguration()
  },
  methods: {
    scrollTo(id) {
      const el = document.getElementById(id)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.classList.add('toc-highlight')
        el.addEventListener('animationend', () => el.classList.remove('toc-highlight'), { once: true })
      }
    },
    async loadConfiguration() {
      this.loading = true
      try {
        try {
          const cluster = await apiService.getClusterSettings()
          this.clusterSettings = {
            id: cluster.id,
            install_disk: cluster.install_disk || '/dev/sda'
          }
        } catch (error) {
          if (!error.message?.toLowerCase().includes('not found')) {
            console.error('Error loading cluster settings:', error)
          }
        }

        const config = await apiService.getVolumeConfigByName('EPHEMERAL')
        this.ephemeralConfigId = config.id
        this.ephemeralConfig = {
          enabled: true,
          maxSize: config.max_size || '100GB',
          minSize: config.min_size || '2GB',
          diskSelector: config.disk_selector_match || ''
        }
      } catch (error) {
        if (!error.message?.toLowerCase().includes('not found')) {
          console.error('Error loading volume config:', error)
        }
      } finally {
        this.loading = false
      }
    },
    async saveAll() {
      this.saving = true
      try {
        // Save install disk
        const diskPayload = { install_disk: this.clusterSettings.install_disk }
        if (this.clusterSettings.id) {
          await apiService.updateClusterSettings(this.clusterSettings.id, diskPayload)
        } else {
          const created = await apiService.createClusterSettings(diskPayload)
          this.clusterSettings.id = created.id
        }

        // Save EPHEMERAL config
        const ephPayload = {
          name: 'EPHEMERAL',
          max_size: this.ephemeralConfig.enabled ? this.ephemeralConfig.maxSize : null,
          min_size: this.ephemeralConfig.enabled ? this.ephemeralConfig.minSize : null,
          disk_selector_match: this.ephemeralConfig.enabled && this.ephemeralConfig.diskSelector ? this.ephemeralConfig.diskSelector : null,
          grow: false
        }

        if (this.ephemeralConfigId) {
          if (this.ephemeralConfig.enabled) {
            await apiService.updateVolumeConfig(this.ephemeralConfigId, ephPayload)
          } else {
            await apiService.deleteVolumeConfig(this.ephemeralConfigId)
            this.ephemeralConfigId = null
          }
        } else if (this.ephemeralConfig.enabled) {
          const created = await apiService.createVolumeConfig(ephPayload)
          this.ephemeralConfigId = created.id
        }

        this.toast.success('Storage settings saved')
      } catch (error) {
        this.toast.error(error.message || 'Failed to save storage settings')
      } finally {
        this.saving = false
      }
    },
  }
}
</script>
