<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">PXE Boot Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Configure PXE boot behavior and boot script options</p>
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
              <a href="#boot-behavior" @click.prevent="scrollTo('boot-behavior')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Boot Behavior</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#strict-mode" @click.prevent="scrollTo('strict-mode')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Strict Mode</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#pxe-menu" @click.prevent="scrollTo('pxe-menu')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">PXE Menu</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#pxe-prompt" @click.prevent="scrollTo('pxe-prompt')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Prompt Text</a></li>
                <li><a href="#pxe-timeout" @click.prevent="scrollTo('pxe-timeout')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Timeout</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#tftp" @click.prevent="scrollTo('tftp')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">TFTP</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#tftp-root" @click.prevent="scrollTo('tftp-root')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Root Directory</a></li>
                <li><a href="#tftp-secure" @click.prevent="scrollTo('tftp-secure')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Secure Mode</a></li>
              </ul>
            </li>
            <li class="mb-2"><a href="#ipxe-script" @click.prevent="scrollTo('ipxe-script')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">iPXE Script</a></li>
          </ul>
        </nav>
      </aside>

      <div class="bg-white p-8 rounded-lg shadow-md flex-1 min-w-0">
        <form @submit.prevent="saveSettings">
          <!-- Boot Behavior -->
          <div id="boot-behavior" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">Boot Behavior</h3>
            <p class="text-gray-500 text-sm mb-4">
              Control how PXE clients behave during boot.
              <router-link to="/wiki#strict-mode" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div id="strict-mode" class="mb-4 scroll-mt-24">
              <label class="flex! items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="settings.strict_boot_mode" :disabled="loading" class="w-auto m-0 cursor-pointer" />
                <span class="font-medium">Strict Boot Mode</span>
              </label>
              <small class="block mt-2 text-gray-500 text-sm leading-normal">
                When enabled, unapproved devices exit immediately to the next BIOS boot device.
              </small>
              <div v-if="!settings.strict_boot_mode" class="mt-3 p-4 bg-amber-50 border-l-4 border-orange-500 rounded text-[0.9rem] leading-relaxed text-amber-800">
                <strong class="text-red-800"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Warning:</strong>
                Unapproved devices may attempt to boot from local disk. If no bootable OS is found,
                the device could enter the Talos installation menu, which may result in
                <strong class="text-red-800">unintended disk wiping</strong>.
              </div>
            </div>
          </div>

          <!-- PXE Menu -->
          <div id="pxe-menu" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">PXE Menu</h3>
            <p class="text-gray-500 text-sm mb-4">
              Configure the PXE boot menu prompt and timeout.
              <router-link to="/wiki#pxe-boot" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="grid grid-cols-2 gap-4">
              <div id="pxe-prompt" class="mb-2 scroll-mt-24">
                <label class="block mb-2 text-sidebar-dark font-medium">PXE Prompt Text</label>
                <input
                  v-model="settings.pxe_prompt"
                  type="text"
                  placeholder="Press F8 for boot menu"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div id="pxe-timeout" class="mb-2 scroll-mt-24">
                <label class="block mb-2 text-sidebar-dark font-medium">PXE Timeout (seconds)</label>
                <input
                  v-model.number="settings.pxe_timeout"
                  type="number"
                  placeholder="3"
                  :disabled="loading"
                  class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          <!-- TFTP Configuration -->
          <div id="tftp" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">TFTP</h3>
            <p class="text-gray-500 text-sm mb-4">
              TFTP server settings for serving boot files to PXE clients.
              <router-link to="/wiki#dnsmasq" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div id="tftp-root" class="mb-4 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">TFTP Root Directory</label>
              <input value="/var/lib/tftpboot" type="text" disabled class="w-full max-w-sm p-2 border border-gray-300 rounded text-base !bg-gray-50 !text-gray-500 !cursor-not-allowed" />
              <small class="block mt-1 text-gray-500 text-sm">Fixed path — automatically managed by Ktizo</small>
            </div>

            <div id="tftp-secure" class="mb-4 scroll-mt-24">
              <label class="flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings.tftp_secure" :disabled="loading" class="mr-2 w-auto" />
                Enable TFTP Secure Mode
              </label>
              <small class="block mt-1 text-gray-500 text-sm">Prevents path traversal attacks by blocking requests containing ".." (recommended: enabled)</small>
              <div v-if="!settings.tftp_secure" class="mt-3 p-4 bg-amber-50 border-l-4 border-orange-500 rounded text-[0.9rem] leading-relaxed text-amber-800">
                <strong class="text-red-800"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Security Warning</strong>
                <p class="mt-1 mb-0">Disabling TFTP secure mode allows clients to use ".." in file paths, which could allow access to files outside the TFTP root directory.</p>
              </div>
            </div>
          </div>

          <!-- iPXE Script (read-only info) -->
          <div id="ipxe-script" class="mb-8 pb-8 border-b border-gray-200 scroll-mt-8">
            <h3 class="text-sidebar-dark mb-1 text-xl">iPXE Script</h3>
            <p class="text-gray-500 text-sm mb-4">
              Boot script path — automatically managed by Ktizo.
              <router-link to="/wiki#ipxe-chain" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
            </p>

            <div class="mb-2">
              <label class="block mb-2 text-sidebar-dark font-medium">iPXE Boot Script Path</label>
              <input value="pxe/boot.ipxe" type="text" disabled class="w-full max-w-sm p-2 border border-gray-300 rounded text-base !bg-gray-50 !text-gray-500 !cursor-not-allowed" />
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
  name: 'PxeSettings',
  data() {
    return {
      settings: {
        strict_boot_mode: true,
        pxe_prompt: 'Press F8 for boot menu',
        pxe_timeout: 3,
        ipxe_boot_script: 'pxe/boot.ipxe',
        tftp_secure: true,
      },
      settingsId: null,
      loading: true,
      saving: false,
    }
  },
  async mounted() {
    this.toast = useToast()
    await this.loadSettings()
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
        this.settings.strict_boot_mode = response.strict_boot_mode || false
        this.settings.pxe_prompt = response.pxe_prompt || 'Press F8 for boot menu'
        this.settings.pxe_timeout = response.pxe_timeout ?? 3
        this.settings.ipxe_boot_script = response.ipxe_boot_script || 'pxe/boot.ipxe'
        this.settings.tftp_secure = response.tftp_secure ?? true
        this.settingsId = response.id
      } catch (error) {
        if (error.message?.toLowerCase().includes('not found')) {
          this.toast.info('No settings found — configure network settings first')
        } else {
          this.toast.error('Failed to load PXE settings')
        }
      } finally {
        this.loading = false
      }
    },
    async saveSettings() {
      if (!this.settingsId) {
        this.toast.error('Network settings must be configured first')
        return
      }
      this.saving = true
      try {
        await apiService.updateNetworkSettings(this.settingsId, this.settings)
        this.toast.success('PXE settings saved — dnsmasq.conf and boot.ipxe regenerated')
      } catch (error) {
        this.toast.error(error.message || 'Failed to save PXE settings')
      } finally {
        this.saving = false
      }
    },
  }
}
</script>
