<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Talos Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Configure Talos Linux version, system extensions, and kernel modules</p>
      </div>
      <button @click="saveSettings" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed whitespace-nowrap" :disabled="loading || saving">
        {{ saving ? 'Saving...' : 'Save & Apply' }}
      </button>
    </div>

    <div class="flex gap-8 items-start">
      <aside class="sticky top-24 w-[250px] shrink-0 bg-white p-6 rounded-lg shadow-md max-h-[calc(100vh-7rem)] overflow-y-auto">
        <h3 class="mt-0 mb-4 text-sidebar-dark text-lg border-b-2 border-[#42b983] pb-2">Table of Contents</h3>
        <nav>
          <ul class="list-none p-0 m-0">
            <li class="mb-2">
              <a href="#talos-version" @click.prevent="scrollTo('talos-version')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Talos Version</a>
            </li>
            <li class="mb-2">
              <a href="#installer-image" @click.prevent="scrollTo('installer-image')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Installer Image</a>
            </li>
            <li class="mb-2">
              <a href="#system-extensions" @click.prevent="scrollTo('system-extensions')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">System Extensions</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#ext-storage" @click.prevent="scrollTo('ext-storage')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Storage</a></li>
                <li><a href="#ext-virtualization" @click.prevent="scrollTo('ext-virtualization')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Virtualization</a></li>
                <li><a href="#ext-gpu" @click.prevent="scrollTo('ext-gpu')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">GPU / Hardware</a></li>
                <li><a href="#ext-network" @click.prevent="scrollTo('ext-network')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Network / Firmware</a></li>
                <li><a href="#ext-utilities" @click.prevent="scrollTo('ext-utilities')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Utilities</a></li>
                <li><a href="#ext-custom" @click.prevent="scrollTo('ext-custom')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Custom</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#kernel-modules" @click.prevent="scrollTo('kernel-modules')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Kernel Modules</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#mod-custom" @click.prevent="scrollTo('mod-custom')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Custom</a></li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="bg-white p-8 rounded-lg shadow-md flex-1 min-w-0">
        <form @submit.prevent="saveSettings">

          <!-- Talos Version -->
          <div id="talos-version" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Talos Version</h3>
            <p class="text-gray-500 text-sm mb-4">
              Version of Talos Linux to PXE boot and use for talosctl.
              <router-link to="/wiki#talos-boot" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">Talos Version</label>
              <select
                v-model="settings.talos_version"
                :disabled="loading"
                class="w-full max-w-sm p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option v-if="settings.talos_version && !talosVersions.includes(settings.talos_version)" :value="settings.talos_version">
                  {{ settings.talos_version }} (current)
                </option>
                <option v-for="v in talosVersions" :key="v" :value="v">{{ v }}</option>
                <option v-if="!talosVersions.length && !loadingVersions" disabled>Failed to load versions</option>
              </select>
              <small class="block mt-1 text-gray-500 text-sm">
                {{ loadingVersions ? 'Loading versions from GitHub...' : 'Kernel and initramfs are downloaded when version changes.' }}
              </small>
            </div>
          </div>

          <!-- Installer Image (computed, read-only) -->
          <div id="installer-image" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Installer Image</h3>
            <p class="text-gray-500 text-sm mb-4">
              Auto-generated from your Talos version and selected extensions via the Talos Factory API.
            </p>

            <div class="p-4 bg-gray-50 rounded border border-gray-200">
              <div class="mb-3">
                <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Image URL</label>
                <code class="block text-sm text-gray-800 break-all">{{ installImage || 'Not yet generated — save settings to generate' }}</code>
              </div>
              <div v-if="factorySchematicId">
                <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Schematic ID</label>
                <code class="block text-sm text-gray-500 break-all">{{ factorySchematicId }}</code>
              </div>
            </div>
          </div>

          <!-- System Extensions -->
          <div id="system-extensions" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">System Extensions</h3>
            <p class="text-gray-500 text-sm mb-4">
              OCI images baked into the installer image via the <a href="https://factory.talos.dev" target="_blank" class="text-blue-500 no-underline hover:underline">Talos Factory API</a>. Changing extensions regenerates the installer schematic automatically.
            </p>

            <!-- Storage -->
            <div id="ext-storage" class="mb-6 scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Storage</h4>
              <div class="space-y-2">
                <label v-for="ext in extensionGroups.storage" :key="ext.image" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input type="checkbox" :checked="isExtEnabled(ext.image)" @change="toggleExtension(ext)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sidebar-dark text-sm">{{ ext.label }}</div>
                    <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ ext.description }}</div>
                    <code class="text-[0.65rem] text-gray-400 mt-1 block truncate">{{ ext.image }}</code>
                  </div>
                </label>
              </div>
            </div>

            <!-- Virtualization -->
            <div id="ext-virtualization" class="mb-6 scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Virtualization</h4>
              <div class="space-y-2">
                <label v-for="ext in extensionGroups.virtualization" :key="ext.image" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input type="checkbox" :checked="isExtEnabled(ext.image)" @change="toggleExtension(ext)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sidebar-dark text-sm">{{ ext.label }}</div>
                    <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ ext.description }}</div>
                    <code class="text-[0.65rem] text-gray-400 mt-1 block truncate">{{ ext.image }}</code>
                  </div>
                </label>
              </div>
            </div>

            <!-- GPU / Hardware -->
            <div id="ext-gpu" class="mb-6 scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">GPU / Hardware</h4>
              <div class="space-y-2">
                <label v-for="ext in extensionGroups.gpu" :key="ext.image" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input type="checkbox" :checked="isExtEnabled(ext.image)" @change="toggleExtension(ext)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sidebar-dark text-sm">{{ ext.label }}</div>
                    <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ ext.description }}</div>
                    <code class="text-[0.65rem] text-gray-400 mt-1 block truncate">{{ ext.image }}</code>
                  </div>
                </label>
              </div>
            </div>

            <!-- Network / Firmware -->
            <div id="ext-network" class="mb-6 scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Network / Firmware</h4>
              <div class="space-y-2">
                <label v-for="ext in extensionGroups.network" :key="ext.image" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input type="checkbox" :checked="isExtEnabled(ext.image)" @change="toggleExtension(ext)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sidebar-dark text-sm">{{ ext.label }}</div>
                    <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ ext.description }}</div>
                    <code class="text-[0.65rem] text-gray-400 mt-1 block truncate">{{ ext.image }}</code>
                  </div>
                </label>
              </div>
            </div>

            <!-- Utilities -->
            <div id="ext-utilities" class="mb-6 scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Utilities</h4>
              <div class="space-y-2">
                <label v-for="ext in extensionGroups.utilities" :key="ext.image" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input type="checkbox" :checked="isExtEnabled(ext.image)" @change="toggleExtension(ext)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sidebar-dark text-sm">{{ ext.label }}</div>
                    <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ ext.description }}</div>
                    <code class="text-[0.65rem] text-gray-400 mt-1 block truncate">{{ ext.image }}</code>
                  </div>
                </label>
              </div>
            </div>

            <!-- Custom Extensions -->
            <div id="ext-custom" class="scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Custom Extensions</h4>
              <div v-for="(ext, index) in customExtensions" :key="'cext-' + index" class="flex items-center gap-2 mb-2">
                <input
                  v-model="customExtensions[index]"
                  type="text"
                  placeholder="ghcr.io/siderolabs/my-extension:v1.0.0"
                  :disabled="loading"
                  class="flex-1 p-2 border border-gray-300 rounded text-sm font-mono disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <button type="button" @click="customExtensions.splice(index, 1)" class="p-2 text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer" :disabled="loading">
                  <font-awesome-icon :icon="['fas', 'trash']" />
                </button>
              </div>
              <button type="button" @click="customExtensions.push('')" class="flex items-center gap-2 mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded text-sm cursor-pointer transition-colors" :disabled="loading">
                <font-awesome-icon :icon="['fas', 'plus']" /> Add Custom Extension
              </button>
            </div>
          </div>

          <!-- Kernel Modules -->
          <div id="kernel-modules" class="mb-8 scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Kernel Modules</h3>
            <p class="text-gray-500 text-sm mb-4">
              Additional kernel modules loaded at boot. Added to <code class="bg-gray-100 text-pink-600 px-1 rounded text-xs">machine.kernel.modules</code> in every machine config.
              Talos already loads modules required by Kubernetes (br_netfilter, nf_conntrack, ip_tables, overlay) automatically.
            </p>

            <div class="space-y-2 mb-6">
              <label v-for="mod in knownModules" :key="mod.name" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                <input type="checkbox" :checked="isModEnabled(mod.name)" @change="toggleModule(mod.name)" :disabled="loading" class="mt-0.5 w-auto cursor-pointer" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-sidebar-dark text-sm font-mono">{{ mod.name }}</div>
                  <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ mod.description }}</div>
                </div>
              </label>
            </div>

            <!-- Custom Modules -->
            <div id="mod-custom" class="scroll-mt-24">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500">Custom Modules</h4>
              <div v-for="(mod, index) in customModules" :key="'cmod-' + index" class="flex items-center gap-2 mb-2">
                <input
                  v-model="customModules[index]"
                  type="text"
                  placeholder="module_name"
                  :disabled="loading"
                  class="flex-1 max-w-sm p-2 border border-gray-300 rounded text-sm font-mono disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <button type="button" @click="customModules.splice(index, 1)" class="p-2 text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer" :disabled="loading">
                  <font-awesome-icon :icon="['fas', 'trash']" />
                </button>
              </div>
              <button type="button" @click="customModules.push('')" class="flex items-center gap-2 mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded text-sm cursor-pointer transition-colors" :disabled="loading">
                <font-awesome-icon :icon="['fas', 'plus']" /> Add Custom Module
              </button>
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
  name: 'TalosSettings',
  data() {
    return {
      settings: {
        talos_version: 'v1.12.2',
        system_extensions: [],
        kernel_modules: [],
      },
      installImage: '',
      factorySchematicId: '',
      loading: true,
      saving: false,
      talosVersions: [],
      loadingVersions: false,
      customExtensions: [],
      customModules: [],

      extensionGroups: {
        storage: [
          {
            label: 'iSCSI Tools',
            image: 'ghcr.io/siderolabs/iscsi-tools:v0.1.6',
            description: 'iSCSI initiator tools. Required by storage solutions like Longhorn, OpenEBS, and Democratic-CSI that use iSCSI to attach network block devices.',
          },
          {
            label: 'DRBD',
            image: 'ghcr.io/siderolabs/drbd:v9.2.12',
            description: 'Distributed Replicated Block Device. Mirrors storage across nodes in real time, used by LINSTOR and Piraeus for highly available persistent volumes.',
          },
        ],
        virtualization: [
          {
            label: 'QEMU Guest Agent',
            image: 'ghcr.io/siderolabs/qemu-guest-agent:v0.2.2',
            description: 'Lets the hypervisor (Proxmox, libvirt, QEMU/KVM) communicate with the VM — enables graceful shutdown, freeze/thaw for snapshots, and IP reporting.',
          },
          {
            label: 'VMware Open VM Tools',
            image: 'ghcr.io/siderolabs/open-vm-tools:v12.5.0',
            description: 'VMware guest tools. Enables vMotion, guest OS info in vCenter, graceful shutdown, and clock synchronization on ESXi/vSphere hosts.',
          },
        ],
        gpu: [
          {
            label: 'NVIDIA Container Toolkit',
            image: 'ghcr.io/siderolabs/nvidia-container-toolkit:v1.17.4',
            description: 'Exposes NVIDIA GPUs to containers. Required for running GPU workloads like machine learning, transcoding, or rendering inside Kubernetes pods.',
          },
          {
            label: 'NVIDIA Open GPU Kernel Modules',
            image: 'ghcr.io/siderolabs/nvidia-open-gpu-kernel-modules:v570.86.16',
            description: 'Open-source NVIDIA kernel driver. Needed alongside the container toolkit for GPU passthrough. Supports datacenter (A100, H100) and recent consumer GPUs.',
          },
          {
            label: 'Gasket Driver',
            image: 'ghcr.io/siderolabs/gasket-driver:v1.0.0',
            description: 'Google Coral TPU driver. Required if your nodes have Coral Edge TPU accelerators (USB or M.2) for AI/ML inference workloads.',
          },
          {
            label: 'Intel GPU (i915)',
            image: 'ghcr.io/siderolabs/i915-ucode:v20250211',
            description: 'Intel integrated GPU firmware. Enables hardware video transcoding (Quick Sync) in containers — commonly used for Plex, Jellyfin, and Frigate.',
          },
        ],
        network: [
          {
            label: 'Tailscale',
            image: 'ghcr.io/siderolabs/tailscale:v1.80.2',
            description: 'Tailscale VPN mesh network. Allows your Talos nodes to join a Tailscale network for secure, zero-config connectivity across sites.',
          },
          {
            label: 'Broadcom BNX2/BNX2X',
            image: 'ghcr.io/siderolabs/bnx2-bnx2x:v1.0.0',
            description: 'Broadcom NetXtreme II network card drivers. Required for older Dell/HP servers with Broadcom BCM5709/BCM57710 NICs not included in the base kernel.',
          },
          {
            label: 'Realtek Firmware',
            image: 'ghcr.io/siderolabs/realtek-firmware:v1.0.0',
            description: 'Firmware for Realtek network adapters (RTL8111/8168/8125). Needed on consumer motherboards and mini PCs with Realtek Ethernet.',
          },
          {
            label: 'Intel Microcode',
            image: 'ghcr.io/siderolabs/intel-ucode:v20250211',
            description: 'Intel CPU microcode updates. Applies firmware patches at boot for security fixes and stability improvements on Intel processors.',
          },
          {
            label: 'AMD Microcode',
            image: 'ghcr.io/siderolabs/amd-ucode:v20250211',
            description: 'AMD CPU microcode updates. Applies firmware patches at boot for security fixes and stability improvements on AMD processors.',
          },
        ],
        utilities: [
          {
            label: 'util-linux Tools',
            image: 'ghcr.io/siderolabs/util-linux-tools:v2.40.4',
            description: 'Additional Linux utilities including nsenter, flock, and lsblk. Some storage drivers (e.g., Longhorn) need these for disk management operations.',
          },
          {
            label: 'Stargz Snapshotter',
            image: 'ghcr.io/siderolabs/stargz-snapshotter:v0.16.3',
            description: 'Lazy-pulling container images. Starts containers before the full image is downloaded by fetching only the layers needed, reducing pod startup time.',
          },
          {
            label: 'Thunderbolt',
            image: 'ghcr.io/siderolabs/thunderbolt:v1.0.0',
            description: 'Thunderbolt/USB4 device support. Required if your nodes use Thunderbolt-connected storage, networking, or docking stations.',
          },
          {
            label: 'USB Modem Drivers',
            image: 'ghcr.io/siderolabs/usb-modem-drivers:v1.0.0',
            description: 'USB cellular modem drivers. Enables USB LTE/5G modems for WAN failover or remote sites without wired internet.',
          },
        ],
      },

      knownModules: [
        { name: 'vfio-pci', description: 'PCI passthrough (VFIO). Passes PCI devices (GPUs, network cards, NVMe drives) directly to VMs or containers, bypassing the host kernel driver entirely.' },
        { name: 'btrfs', description: 'Btrfs filesystem. A copy-on-write filesystem with built-in snapshots, checksums, and RAID. Some container runtimes can use Btrfs as a storage driver.' },
        { name: 'drbd', description: 'DRBD kernel module. Network-based disk mirroring at the block level. Works with the DRBD system extension for replicated storage across nodes.' },
        { name: 'nvidia', description: 'NVIDIA GPU kernel module. Required alongside the NVIDIA container toolkit extension to expose GPUs to containers.' },
        { name: 'gasket', description: 'Google Coral TPU kernel module. Required alongside the Gasket driver extension for Coral Edge TPU accelerators.' },
        { name: 'nbd', description: 'Network Block Device. Maps a remote block device over the network as a local disk. Used by some distributed storage solutions.' },
        { name: 'thunderbolt', description: 'Thunderbolt/USB4 kernel support. Required alongside the Thunderbolt system extension for hot-plug Thunderbolt device support.' },
      ],
    }
  },
  computed: {
    allKnownExtImages() {
      return Object.values(this.extensionGroups).flat().map(e => this.extBase(e.image))
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadSettings()
    this.fetchTalosVersions()
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
    extBase(image) {
      // "ghcr.io/siderolabs/foo:v1.0" → "ghcr.io/siderolabs/foo"
      return image.split(':')[0]
    },
    isExtEnabled(image) {
      const base = this.extBase(image)
      return this.settings.system_extensions.some(e => this.extBase(e) === base)
    },
    toggleExtension(ext) {
      const base = this.extBase(ext.image)
      const idx = this.settings.system_extensions.findIndex(e => this.extBase(e) === base)
      if (idx >= 0) {
        this.settings.system_extensions.splice(idx, 1)
      } else {
        this.settings.system_extensions.push(ext.image)
      }
    },
    isModEnabled(name) {
      return this.settings.kernel_modules.includes(name)
    },
    toggleModule(name) {
      const idx = this.settings.kernel_modules.indexOf(name)
      if (idx >= 0) {
        this.settings.kernel_modules.splice(idx, 1)
      } else {
        this.settings.kernel_modules.push(name)
      }
    },
    async loadSettings() {
      this.loading = true
      try {
        const response = await apiService.getTalosSettings()
        this.settings.talos_version = response.talos_version || 'v1.12.2'
        this.settings.system_extensions = response.system_extensions || []
        this.settings.kernel_modules = response.kernel_modules || []
        this.installImage = response.install_image || ''
        this.factorySchematicId = response.factory_schematic_id || ''

        // Separate saved extensions into known (checkbox) vs custom (text input)
        const knownBases = this.allKnownExtImages
        this.customExtensions = this.settings.system_extensions
          .filter(e => !knownBases.includes(this.extBase(e)))

        // Separate saved modules into known vs custom
        const knownModNames = this.knownModules.map(m => m.name)
        this.customModules = this.settings.kernel_modules
          .filter(m => !knownModNames.includes(m))
      } catch (error) {
        if (error.message?.toLowerCase().includes('not found')) {
          this.toast.info('No settings found — configure network and cluster settings first')
        } else {
          this.toast.error('Failed to load Talos settings')
        }
      } finally {
        this.loading = false
      }
    },
    async fetchTalosVersions() {
      this.loadingVersions = true
      try {
        this.talosVersions = await apiService.getTalosVersions()
      } catch (e) {
        // Silently fail — dropdown will show current value
      } finally {
        this.loadingVersions = false
      }
    },
    async saveSettings() {
      this.saving = true
      try {
        // Merge checked known extensions + custom entries
        const knownBases = this.allKnownExtImages
        const knownExts = this.settings.system_extensions.filter(e => knownBases.includes(this.extBase(e)))
        const customExts = this.customExtensions.filter(e => e.trim())
        const allExtensions = [...knownExts, ...customExts]

        // Merge checked known modules + custom entries
        const knownModNames = this.knownModules.map(m => m.name)
        const knownMods = this.settings.kernel_modules.filter(m => knownModNames.includes(m))
        const customMods = this.customModules.filter(m => m.trim())
        const allModules = [...knownMods, ...customMods]

        const payload = {
          talos_version: this.settings.talos_version,
          system_extensions: allExtensions,
          kernel_modules: allModules,
        }
        const result = await apiService.updateTalosSettings(payload)

        // Update local state with merged data
        this.settings.system_extensions = allExtensions
        this.settings.kernel_modules = allModules
        this.customExtensions = customExts
        this.customModules = customMods

        // Update installer image from response
        if (result && result.install_image) {
          this.installImage = result.install_image
          this.factorySchematicId = result.factory_schematic_id || ''
        }

        this.toast.success('Talos settings saved — PXE files and machine configs regenerated')
      } catch (error) {
        this.toast.error(error.message || 'Failed to save Talos settings')
      } finally {
        this.saving = false
      }
    },
  }
}
</script>
