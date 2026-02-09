<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Network Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Configure server network and DHCP parameters</p>
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
            <li class="mb-2"><a href="#interface" @click.prevent="scrollTo('interface')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Network Interface</a></li>
            <li class="mb-2">
              <a href="#network-config" @click.prevent="scrollTo('network-config')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Network Configuration</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#server-ip" @click.prevent="scrollTo('server-ip')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Server IP</a></li>
                <li><a href="#dns-server" @click.prevent="scrollTo('dns-server')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">DNS Server</a></li>
                <li><a href="#network-addr" @click.prevent="scrollTo('network-addr')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Network / Netmask</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#dhcp-mode" @click.prevent="scrollTo('dhcp-mode')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">DHCP Mode</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#dhcp-range" @click.prevent="scrollTo('dhcp-range')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">DHCP Range</a></li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="bg-white p-8 rounded-lg shadow-md flex-1 min-w-0">
        <form @submit.prevent="saveSettings">
          <!-- Step 1: Interface Selection -->
          <div id="interface" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">1. Select Network Interface</h3>
            <p class="text-gray-500 text-sm mb-4">
              Choose the interface connected to your bare-metal network, then autoconfigure.
              <router-link to="/wiki#network-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="flex gap-2">
              <select
                v-model="settings.interface"
                :disabled="loading"
                class="flex-1 p-2.5 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="" disabled>Select an interface...</option>
                <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">
                  {{ iface.name }} ({{ iface.state }})
                </option>
              </select>
              <button
                type="button"
                @click="autoconfigure"
                :disabled="!settings.interface || detecting"
                class="px-5 py-2.5 bg-indigo-600 text-white rounded text-sm font-medium transition-colors hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed whitespace-nowrap"
              >
                <template v-if="detecting">Detecting...</template>
                <template v-else><font-awesome-icon :icon="['fas', 'bolt']" class="mr-1" /> Autoconfigure</template>
              </button>
            </div>
          </div>

          <!-- Step 2: Network Configuration -->
          <div id="network-config" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">2. Network Configuration</h3>
            <p class="text-gray-500 text-sm mb-4">
              Auto-detected from interface. Edit if needed.
              <router-link to="/wiki#gs-network" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="grid grid-cols-2 gap-4">
              <div id="server-ip" class="mb-2 scroll-mt-24">
                <label class="block mb-2 text-sidebar-dark font-medium">Server IP Address *</label>
                <input
                  v-model="settings.server_ip"
                  type="text"
                  required
                  placeholder="Auto-detected after selecting interface"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div id="dns-server" class="mb-2 scroll-mt-24">
                <label class="block mb-2 text-sidebar-dark font-medium">DNS Server</label>
                <input
                  v-model="settings.dns_server"
                  type="text"
                  placeholder="Auto-detected"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div id="network-addr" class="mb-2 scroll-mt-24">
                <label class="block mb-2 text-sidebar-dark font-medium">Network</label>
                <input
                  v-model="settings.dhcp_network"
                  type="text"
                  placeholder="Auto-detected"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div class="mb-2">
                <label class="block mb-2 text-sidebar-dark font-medium">Netmask</label>
                <input
                  v-model="settings.dhcp_netmask"
                  type="text"
                  placeholder="Auto-detected"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          <!-- Step 3: DHCP Mode -->
          <div id="dhcp-mode" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">3. DHCP Mode</h3>
            <p class="text-gray-500 text-sm mb-4">
              Choose how Ktizo interacts with your network's DHCP.
              <router-link to="/wiki#proxydhcp" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="mb-4">
              <label class="block mb-2 text-sidebar-dark font-medium">DHCP Mode</label>
              <select v-model="settings.dhcp_mode" :disabled="loading" class="w-full max-w-md p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed">
                <option value="proxy">ProxyDHCP (works with existing DHCP)</option>
                <option value="server">Full DHCP Server</option>
              </select>
            </div>

            <div id="dhcp-range" v-if="settings.dhcp_mode === 'server'" class="grid grid-cols-2 gap-4 scroll-mt-24">
              <div>
                <label class="block mb-2 text-sidebar-dark font-medium">DHCP Range Start</label>
                <input v-model="settings.dhcp_range_start" type="text" placeholder="10.0.128.10" :disabled="loading" class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed" />
              </div>
              <div>
                <label class="block mb-2 text-sidebar-dark font-medium">DHCP Range End</label>
                <input v-model="settings.dhcp_range_end" type="text" placeholder="10.0.128.250" :disabled="loading" class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed" />
              </div>
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
      detecting: false,
      interfaces: [],
    }
  },
  watch: {
    'settings.interface'(val) {
      if (val) localStorage.setItem('ktizo_network_iface', val)
    },
  },
  async mounted() {
    this.toast = useToast()
    this.loadInterfaces()
    await this.loadSettings()
    if (!this.settings.interface) {
      const saved = localStorage.getItem('ktizo_network_iface')
      if (saved) this.settings.interface = saved
    }
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
      } catch (error) {
        if (error.message?.toLowerCase().includes('not found')) {
          this.toast.info('No network settings found — configure and save below')
        } else if (error.message) {
          this.toast.error(`Failed to load settings: ${error.message}`)
        } else {
          this.toast.error('Failed to load settings — check that the backend is running')
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
        this.toast.success('Network settings saved — dnsmasq.conf and boot.ipxe regenerated')
      } catch (error) {
        this.toast.error(error.message || 'Failed to save network settings')
        console.error('Error saving network settings:', error)
      } finally {
        this.saving = false
      }
    },
    async loadInterfaces() {
      try {
        this.interfaces = await apiService.getNetworkInterfaces()
      } catch (e) {
        // Non-critical
      }
    },
    async autoconfigure() {
      if (!this.settings.interface) {
        this.toast.error('Select an interface first')
        return
      }
      this.detecting = true
      try {
        const config = await apiService.detectNetworkConfig(this.settings.interface)
        if (config.server_ip) this.settings.server_ip = config.server_ip
        if (config.dhcp_network) this.settings.dhcp_network = config.dhcp_network
        if (config.dhcp_netmask) this.settings.dhcp_netmask = config.dhcp_netmask
        if (config.dns_server) this.settings.dns_server = config.dns_server
        this.toast.success(`Detected: ${config.server_ip} on ${config.interface} (${config.dhcp_network}/${config.dhcp_netmask})`)
      } catch (error) {
        this.toast.error(error.message || 'Failed to detect network configuration')
      } finally {
        this.detecting = false
      }
    },
  }
}
</script>
